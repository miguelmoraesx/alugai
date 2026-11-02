"""Search-card adapters verified against November 2026 HTML snapshots.

Never execute embedded JavaScript, infer missing fees, or merge similar units.
"""
from dataclasses import dataclass, field
import re
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .parser import Listing, LayoutError, money, number

SOURCES = {
    "olx": ("olx.com.br", "https://www.olx.com.br/imoveis/aluguel/estado-am/regiao-de-manaus/manaus"),
    "vivareal": ("vivareal.com.br", "https://www.vivareal.com.br/aluguel/amazonas/manaus/"),
    "ponta_negra": ("pontanegraimoveis.com.br", "https://www.pontanegraimoveis.com.br/imobiliaria/imoveis/0/1"),
}
CURRENCY = r"R\$\s*([\d.]+(?:,\d{2})?)"


def url_for(value, source):
    p = urlsplit(value)
    domain = SOURCES[source][0]
    if p.scheme != "https" or not (p.hostname == domain or (p.hostname or "").endswith("." + domain)):
        raise ValueError("URL fora da fonte selecionada")
    if p.username or p.password or p.port not in (None, 443):
        raise ValueError("URL com credenciais ou porta inesperada")
    return urlunsplit(("https", p.hostname, p.path.rstrip("/"), "", ""))


def text(node, selector=None):
    selected = node.select_one(selector) if selector else node
    return selected.get_text(" ", strip=True) if selected else ""


def amount(value):
    found = re.search(CURRENCY, value)
    return money(found[1]) if found else None


def fee(value, label):
    found = re.search(label + r"\s*(R\$\s*[\d.,]+|isento|inclus[oa]|não informado)", value, re.I)
    raw = found[1] if found else "não informado"
    status = "exempt" if raw.lower() == "isento" else "included" if raw.lower().startswith("inclus") else "unknown"
    price = amount(raw)
    if price is not None:
        status = "reported" if price > 1 else "needs_review"
    elif status == "exempt":
        price = money(0)
    return price, status


def exact_number(value):
    value = value.strip()
    if re.search(r"\d\s*[-–+]|ou mais", value):
        return None  # ranges and "5+" must not become exact values
    found = re.search(r"\d+(?:[.,]\d+)?", value)
    return number(found[0]) if found else None


def count(value):
    n = exact_number(value)
    return int(n) if n is not None and n.is_integer() else None


@dataclass
class Candidate:
    listing: Listing
    source: str
    iptu: str | None = None
    iptu_period: str = "unknown"
    condo_status: str = "unknown"
    iptu_status: str = "unknown"
    street: str | None = None
    warnings: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    def data(self):
        listing = self.listing.data()
        flags = list(self.warnings)
        for key in ("city", "neighborhood", "area_m2", "bedrooms"):
            if listing[key] is None:
                flags.append("missing_" + key)
        if self.listing.city != "Manaus":
            flags.append("city_not_confirmed_manaus")
        if self.listing.rental_period != "monthly":
            flags.append("rental_period_unconfirmed")
        if self.condo_status in ("unknown", "needs_review"):
            flags.append("condo_" + self.condo_status)
        if self.iptu_status in ("unknown", "needs_review"):
            flags.append("iptu_" + self.iptu_status)
        if self.iptu is not None and self.iptu_status != "exempt" and self.iptu_period == "unknown":
            flags.append("iptu_period_unconfirmed")
        return {**listing, "source": self.source, "iptu": self.iptu,
                "iptu_period": self.iptu_period, "condo_status": self.condo_status,
                "iptu_status": self.iptu_status, "street": self.street,
                "warnings": sorted(set(flags)), "evidence": self.evidence,
                "review_status": "pending", "publication_status": "not_published",
                "monthly_total": None, "availability_verified": False}


def olx_card(card):
    link = card.select_one('[data-testid="adcard-link"]')
    if not link:
        raise ValueError("Cartão sem link de anúncio")
    url = url_for(link["href"], "olx")
    identifier = re.search(r"-(\d+)$", url)
    if not identifier:
        raise ValueError("URL sem ID")
    title = text(link)
    price_text = text(card, ".olx-adcard__price")
    price = amount(price_text)
    location = text(card, ".olx-adcard__location").split(",", 1)
    details = [d.get("aria-label", "") for d in card.select(".olx-adcard__detail")]
    def feature(label):
        return next((v for v in details if label in v.lower()), "")
    fees = text(card, '[data-testid="adcard-price-info-list"]')
    condo, cs = fee(fees, r"(?:Condomínio|Cond\.?)")
    iptu, its = fee(fees, "IPTU")
    period = "short_term" if re.search(r"\b(diária|temporada)\b", title, re.I) else "unknown"
    if re.search(r"\b(mensal|por mês)\b", title, re.I):
        period = "monthly"
    item = Listing(identifier[1], url, title, price, location[0].strip() or None,
                   location[1].strip() if len(location) == 2 else None, condo,
                   exact_number(feature("quadrad")), count(feature("quarto")),
                   count(feature("banheiro")), count(feature("vaga")), period)
    return Candidate(item, "olx", str(iptu) if iptu is not None else None,
                     condo_status=cs, iptu_status=its,
                     evidence={"price": price_text, "fees": fees, "features": details})


def vivareal_card(card):
    link = card.select_one('a[href*="/imovel/"]')
    if not link:
        return None  # grouped cards have several units; not one listing
    url = url_for(link["href"], "vivareal")
    identifier = re.search(r"-id-(\d+)$", url)
    if not identifier:
        raise ValueError("URL sem ID Viva Real")
    def field_value(name):
        return text(card, f'[data-cy="rp-cardProperty-{name}-txt"]')
    price_text = field_value("price")
    condo, cs = fee(price_text, r"Cond\.")
    iptu, its = fee(price_text, "IPTU")
    location = field_value("location").rsplit(",", 1)
    area_text = field_value("propertyArea")
    item = Listing(identifier[1], url, link.get("title") or text(card, "h2"), amount(price_text),
                   location[1].strip() if len(location) == 2 else None,
                   location[0].strip() or None, condo, exact_number(area_text),
                   count(field_value("bedroomQuantity")), count(field_value("bathroomQuantity")),
                   count(field_value("parkingSpacesQuantity")),
                   "monthly" if re.search(r"/\s*mês", price_text) else "unknown")
    return Candidate(item, "vivareal", str(iptu) if iptu is not None else None,
                     condo_status=cs, iptu_status=its, street=field_value("street") or None,
                     evidence={"price_and_fees": price_text, "area": area_text})


def ponta_card(card):
    # Observed class names are misleading: rent-price can contain a sale price.
    price_node = next((p for p in card.select(".c49-property-card_price > div")
                       if re.search(r"Locação\s*$", text(p))), None)
    if not price_node:
        return None
    link = card.select_one("a.c49btn-details[href]")
    if not link:
        raise ValueError("Cartão sem link de detalhes")
    url = url_for(link["href"], "ponta_negra")
    identifier = re.search(r"/(\d+)/imoveis/", url)
    if not identifier:
        raise ValueError("URL sem código da imobiliária")
    location = text(card, ".c49-property-card_address").rsplit(",", 1)
    fees = text(card, ".c49-property-card_other-prices")
    condo, cs = fee(fees, "Condomínio")
    iptu, its = fee(fees, "IPTU")
    def feature(icon):
        node = card.select_one(".c49icon-" + icon + "-1")
        return text(node.parent, ".c49-property-number") if node else ""
    price_text = text(price_node)
    item = Listing(identifier[1], url, text(card, ".c49-property-card_title"), amount(price_text),
                   location[1].split(" - ")[0].strip() if len(location) == 2 else None,
                   location[0].strip() or None, condo, exact_number(feature("area")),
                   count(feature("bedroom")), count(feature("bathroom")), count(feature("garage")))
    description = text(card, ".c49-property-card_description")
    warnings = []
    if re.search(r"\b(?:venda|vendo)\b", item.title, re.I):
        warnings.append("transaction_title_conflict")
    # Explicit advertised-price statement only: other currency amounts may be deposits or fees.
    stated = re.search(r"valor do anúncio de\s*" + CURRENCY, description, re.I)
    if stated and money(stated[1]) != item.rent_price:
        warnings.append("description_price_conflict")
    return Candidate(item, "ponta_negra", str(iptu) if iptu is not None else None,
                     condo_status=cs, iptu_status=its, warnings=warnings,
                     evidence={"price": price_text, "fees": fees,
                               "description_price": str(money(stated[1])) if stated else None})


def parse_cards(html, source, limit=20):
    if source not in SOURCES or limit < 1:
        raise ValueError("Fonte ou limite inválido")
    selector, adapter = {
        "olx": ("section.olx-adcard", olx_card),
        "vivareal": ('li[data-cy="rp-property-cd"]', vivareal_card),
        "ponta_negra": ("article.c49-property-card", ponta_card),
    }[source]
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(selector)
    if not cards:
        raise LayoutError("Nenhum cartão reconhecido para " + source)
    rows, errors, skipped = {}, [], 0
    for i, card in enumerate(cards):
        try:
            result = adapter(card)
            if result is None:
                skipped += 1
                continue
            listing = result.listing
            if not listing.title or listing.rent_price is None or listing.rent_price <= 0:
                raise ValueError("Título ou preço de aluguel ausente/inválido")
            rows[listing.external_id] = result
            if len(rows) >= limit:
                break
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            errors.append({"card_index": i, "error": str(exc)})
    if not rows:
        raise LayoutError("Nenhum anúncio de aluguel válido para " + source)
    return list(rows.values()), {"cards_available": len(cards), "selected": len(rows),
                                "skipped_sale_or_group": skipped, "errors": errors,
                                "requested_limit": limit, "limit_reached": len(rows) >= limit}
