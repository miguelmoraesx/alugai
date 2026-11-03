"""Explicit structured-data adapters. Unknown layouts fail closed."""
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import urlsplit, urlunsplit, urljoin

from bs4 import BeautifulSoup

SEED = "https://www.olx.com.br/imoveis/aluguel/estado-am/regiao-de-manaus/manaus"


class LayoutError(ValueError):
    pass


def canonical_url(value: str, allowed_domains=("olx.com.br",)) -> str:
    if isinstance(allowed_domains, str):
        allowed_domains = (allowed_domains,)
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    allowed = any(host == domain or host.endswith("." + domain)
                  for domain in allowed_domains)
    if parsed.scheme != "https" or not allowed:
        raise ValueError("URL fora do domínio HTTPS permitido")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("URL com credenciais/porta não permitida")
    # Only for listing identity, never for bypassing robots on fetch URLs.
    return urlunsplit(("https", host, parsed.path.rstrip("/"), "", ""))


def money(value) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("Preço inválido")
    if isinstance(value, str):
        value = value.replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
        if not re.fullmatch(r"\d+(?:[.,]\d+)*", value):
            raise ValueError("Preço ambíguo ou inválido")
        if "," in value:
            value = value.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
            value = value.replace(".", "")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Preço inválido") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Preço negativo/não finito")
    return result.quantize(Decimal("0.01"))


def number(value):
    if value is None or value == "":
        return None
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2)?", str(value).strip())
    if not match:
        return None  # e.g. "5+" is not exactly five
    return float(match[1].replace(",", "."))


@dataclass
class Listing:
    external_id: str
    url: str
    title: str
    rent_price: Decimal
    city: str | None = None
    neighborhood: str | None = None
    condo_fee: Decimal | None = None
    area_m2: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking_spaces: int | None = None
    rental_period: str = "unknown"

    def data(self):
        return {key: str(value) if isinstance(value, Decimal) else value
                for key, value in asdict(self).items()}


def from_olx(ad: dict) -> Listing:
    url = canonical_url(ad.get("url") or ad.get("friendlyUrl") or "")
    suffix = re.search(r"-(\d+)$", url)
    external_id = str(ad.get("listId") or ad.get("id") or (suffix[1] if suffix else ""))
    title = str(ad.get("subject") or ad.get("title") or "").strip()
    price = money(ad.get("priceValue") if ad.get("priceValue") is not None else ad.get("price"))
    if not external_id.isdigit() or not title or price is None or price <= 0:
        raise ValueError("Anúncio sem ID, título ou preço válido")
    props = {p.get("name"): p.get("value") for p in ad.get("properties", []) if isinstance(p, dict)}
    location = ad.get("locationDetails") or {}
    if not isinstance(location, dict):
        location = {}
    period = "unknown"
    if re.search(r"\b(diária|diarias|diárias|temporada)\b", title, re.I):
        period = "short_term"
    elif re.search(r"\b(mensal|por mês|por mes)\b", title, re.I):
        period = "monthly"
    def count(name):
        n = number(props.get(name))
        return int(n) if n is not None and n.is_integer() else None
    return Listing(external_id, url, title, price,
                   location.get("municipality"), location.get("neighbourhood") or location.get("neighborhood"),
                   money(props.get("condominio")), number(props.get("size")),
                   count("rooms"), count("bathrooms"), count("garage_spaces"), period)


def parse_page(html: str, url: str) -> tuple[list[Listing], list[str], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        # Current search pages render semantic HTML cards rather than __NEXT_DATA__.
        from .cards import parse_cards
        rows, stats = parse_cards(html, "olx", limit=100)
        return [row.listing for row in rows], [], [str(e) for e in stats["errors"]]
    try:
        page = json.loads(script.get_text())["props"]["pageProps"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LayoutError("Estrutura __NEXT_DATA__ desconhecida") from exc
    if not isinstance(page, dict):
        raise LayoutError("pageProps não é objeto")
    # Deliberately avoid recursive searches: recommended ads may be unrelated.
    if isinstance(page.get("ads"), list):
        candidates = page["ads"]
    elif isinstance(page.get("ad"), dict):
        candidates = [page["ad"]]
    elif isinstance(page.get("adDetails"), dict):
        candidates = [page["adDetails"]]
    else:
        raise LayoutError("Sem coleção ads/ad/adDetails reconhecida")
    rows, errors = {}, []
    for position, ad in enumerate(candidates):
        try:
            if not isinstance(ad, dict):
                raise ValueError("Registro não é objeto")
            listing = from_olx(ad)
            rows[listing.external_id] = listing
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f"registro {position}: {exc}")
    if not rows:
        raise LayoutError("Nenhum anúncio válido; não inferir indisponibilidade")
    next_urls = []
    for link in soup.select('a[rel~="next"][href]'):
        candidate = urljoin(url, link["href"])
        canonical_url(candidate)  # validate without removing query used by robots
        next_urls.append(candidate)
    return list(rows.values()), next_urls, errors
