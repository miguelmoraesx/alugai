"""OLX detail-page parsing and high-confidence house acceptance rules.

The OLX detail page embeds its structured listing data in a
<script id="initial-data" type="text/plain" data-json="..."> tag whose
attribute value is HTML-entity-escaped JSON. We decode that attribute
(HTML entities, then JSON) without executing the embedded script, and
never store the page's contacts or full raw HTML.

Acceptance is deliberately strict: a record is accepted only when every
required fact is proven by the page itself, never inferred from titles,
URL slugs, portal defaults, or neighbouring cards.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal

from bs4 import BeautifulSoup

from .cards import SOURCES, url_for
from .parser import LayoutError, money, number

# Contact patterns are removed from the stored excerpt, never persisted.
PHONE_RE = re.compile(
    r"(?:\+?55[\s.-]?)?(?:\(?0?\d{2}\)?[\s.-]?)?9?\d{4}[\s.-]?\d{4}"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CONTACT_LINE_RE = re.compile(
    r"\b(whatsapp|whats|instagram|facebook|telefone|tel\.?|contato|falar com|"
    r"chamar no|ligar|celular|e-?mail|fone)\b",
    re.I,
)
ANUNCIO_CODE_RE = re.compile(r"^\s*C[oó]digo do an[úu]ncio\s*:?\s*\S*", re.I)

MONTHLY_TOKENS = {"mês", "mes", "mensal", "mensalmente"}
ANNUAL_TOKENS = {"ano", "anual", "anualmente"}
ABSENT = {
    "", "não informado", "nao informado", "consultar", "a consultar",
    "isento", "isenta", "incluso", "inclusa", "inclusa no aluguel", "-",
}
UNCERTAIN_RE = re.compile(
    r"\b(aproximad[oa]s?|aproximadamente|cerca de|estimad[oa]s?|estimativa|"
    r"a partir de|entre\s+\d|de\s+\d[^.;\n]{0,20}\ba\s+\d)\b|\d\s*[-–]\s*\d|\d\s*\+",
    re.I,
)
SOURCE_DOMAINS = {source: values[0] for source, values in SOURCES.items()}


def _period(value):
    """Map an explicit period label to monthly/annual; None when absent/unclear."""
    if value is None:
        return None
    tokens = re.findall(r"[a-zà-úç]+", str(value).lower())
    if any(t in MONTHLY_TOKENS for t in tokens):
        return "monthly"
    if any(t in ANNUAL_TOKENS for t in tokens):
        return "annual"
    return None



IPTU_PERIOD_DESC_RE = re.compile(
    r"\biptu\b[^.;\n]{0,100}\b(anual|mensal|anualmente|mensalmente|"
    r"por ano|por m[êe]s)\b",
    re.I,
)


def _iptu_period_from_description(excerpt, iptu_value):
    """Detect an explicit IPTU period stated in the description, if any."""
    if not excerpt or iptu_value is None:
        return None, False
    match = IPTU_PERIOD_DESC_RE.search(excerpt)
    if not match:
        return None, False
    start = max(0, match.start() - 50)
    end = min(len(excerpt), match.end() + 50)
    uncertain = bool(UNCERTAIN_RE.search(excerpt[start:end]))
    token = match.group(1).lower()
    if token in ("mensal", "mensalmente", "por mês", "por mes"):
        return "monthly", uncertain
    if token in ("anual", "anualmente", "por ano"):
        return "annual", uncertain
    return None, uncertain


def _money(value):
    """Parse a price/fee, treating explicit absence markers as unknown."""
    if value is None:
        return None
    if str(value).strip().lower() in ABSENT:
        return None
    if isinstance(value, str) and UNCERTAIN_RE.search(value):
        return None
    try:
        return money(value)
    except ValueError:
        return None


def _money_with_period(value):
    if value is None or UNCERTAIN_RE.search(str(value)):
        return None
    match = re.fullmatch(
        r"\s*R\$\s*([\d.]+(?:,\d{2})?)\s*(?:(?:/|por)\s*"
        r"(?:m[êe]s|mensal|ano|anual))?\s*", str(value), re.I)
    return _money(match.group(1)) if match else _money(value)


def extract_ad(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="initial-data")
    if script is None or not script.get("data-json"):
        raise LayoutError("Detalhe OLX sem initial-data")
    # BeautifulSoup already decodes HTML attribute entities. A second unescape
    # corrupts valid JSON when listing text contains a literal entity such as
    # ``&quot;``.
    try:
        data = json.loads(script["data-json"])
    except ValueError as exc:
        raise LayoutError("initial-data não é JSON válido") from exc
    ad = data.get("ad") if isinstance(data, dict) else None
    if not isinstance(ad, dict):
        raise LayoutError("initial-data sem anúncio")
    return ad


def _price_info(ad):
    items = ad.get("realEstatePriceInfo")
    if not isinstance(items, list):
        return {}
    return {str(item.get("name")): item for item in items
            if isinstance(item, dict) and item.get("name")}


def _features(ad):
    props = {str(p.get("name")): p.get("value") for p in ad.get("properties", [])
             if isinstance(p, dict) and p.get("name")}
    summary = {str(s.get("name")): s.get("value") for s in ad.get("featuresSummary", [])
               if isinstance(s, dict) and s.get("name")}
    return props, summary


def sanitize_description(body) -> str:
    """Strip tags, contacts, and portal boilerplate from a detail body."""
    if not body:
        return ""
    soup = BeautifulSoup(body, "html.parser")
    kept = []
    for line in soup.get_text("\n", strip=True).split("\n"):
        line = ANUNCIO_CODE_RE.sub("", line)
        if not line.strip():
            continue
        if CONTACT_LINE_RE.search(line):
            continue
        line = PHONE_RE.sub(" ", line)
        line = EMAIL_RE.sub(" ", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            kept.append(line)
    return " ".join(kept)


def _source_url(value, source):
    try:
        return url_for(value, source)
    except (KeyError, TypeError, ValueError) as exc:
        raise LayoutError("URL de detalhe fora do domínio da fonte") from exc


def parse_olx_detail(html, url, *, requested_url=None, search_url=None,
                     scrape_id=None, collected_at=None):
    """Parse one OLX detail page into a candidate record (no acceptance yet)."""
    ad = extract_ad(html)
    external_id = str(ad.get("listId") or ad.get("adId") or "")
    if not external_id.isdigit():
        raise LayoutError("Detalhe OLX sem listId válido")
    final_url = _source_url(url, "olx")
    requested = _source_url(requested_url or url, "olx")
    canonical = _source_url(ad.get("canonicalUrl") or ad.get("friendlyUrl") or url, "olx")

    props, summary = _features(ad)
    real_estate_type = str(props.get("real_estate_type") or "")
    re_types = str(props.get("re_types") or "")
    category = str(ad.get("categoryName") or "")

    price_label = str(ad.get("priceLabel") or "")
    title = str(ad.get("subject") or "").strip()

    info = _price_info(ad)
    rent = info.get("Aluguel") or {}
    iptu = info.get("iptu") or {}
    condo = info.get("condominio") or {}

    location = ad.get("location") or {}
    if not isinstance(location, dict):
        location = {}

    def prop(name):
        return props.get(name) or summary.get(name)

    description_excerpt = sanitize_description(ad.get("description") or ad.get("body"))
    iptu_value = _money(iptu.get("value"))
    iptu_period = _period(iptu.get("period"))
    iptu_period_source = "structured" if iptu_period else "unknown"
    iptu_qualified = False
    if iptu_period is None:
        iptu_period, iptu_qualified = _iptu_period_from_description(
            description_excerpt, iptu_value)
        if iptu_period:
            iptu_period_source = "description"

    record = {
        "source": "olx",
        "external_id": external_id,
        "url": canonical,
        "title": title,
        "property_type": None,
        "transaction_type": None,
        "rent_price": _money(rent.get("value")),
        "rental_period": _period(rent.get("period")),
        "city": str(location.get("municipality") or "").strip() or None,
        "neighborhood": str(location.get("neighbourhood") or location.get("neighborhood") or "").strip() or None,
        "street": str(location.get("address") or "").strip() or None,
        "area_m2": number(prop("size")),
        "bedrooms": _count(prop("rooms")),
        "bathrooms": _count(prop("bathrooms")),
        "parking_spaces": _count(prop("garage_spaces")),
        "condo_fee": _money(condo.get("value")),
        "condo_status": _fee_status(condo.get("value")),
        "iptu": iptu_value,
        "iptu_period": iptu_period,
        "description_excerpt": description_excerpt,
        "warnings": [],
        "evidence": {
            "price_label": price_label,
            "real_estate_type": real_estate_type,
            "category": category,
            "re_types": re_types,
            "rent_raw": rent.get("value"),
            "rent_period_raw": rent.get("period"),
            "condo_raw": condo.get("value"),
            "iptu_raw": iptu.get("value"),
            "iptu_period_raw": iptu.get("period"),
            "iptu_period_source": iptu_period_source,
            "iptu_value_uncertain": iptu_qualified,
            "description_length": len(description_excerpt),
        },
        "provenance": {
            "source_url": canonical,
            "requested_url": requested,
            "final_url": final_url,
            "search_url": search_url,
            "collected_at": collected_at,
            "scrape_id": scrape_id,
            "content_hash": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "observation_scope": "detail_page",
        },
        "review_status": "pending",
        "publication_status": "not_published",
        "availability_verified": False,
    }
    _classify(record, real_estate_type, re_types, category, title, price_label)
    return record


LISTING_TYPES = {
    "realestatelisting", "product", "house", "singlefamilyresidence",
    "residence", "apartment", "accommodation",
}


def _type_names(value):
    values = value if isinstance(value, list) else [value]
    return {str(item).lower() for item in values if item}


def _jsonld_listings(html):
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.get_text())
        except (TypeError, ValueError):
            continue
        roots = payload if isinstance(payload, list) else [payload]
        for root in roots:
            if not isinstance(root, dict):
                continue
            nodes = root.get("@graph") if isinstance(root.get("@graph"), list) else [root]
            for node in nodes:
                if isinstance(node, dict) and _type_names(node.get("@type")) & LISTING_TYPES:
                    found.append(node)
    if len(found) != 1:
        raise LayoutError("Detalhe sem um único anúncio estruturado")
    return soup, found[0]


def _identifier(node):
    value = node.get("sku") or node.get("productID") or node.get("identifier")
    if isinstance(value, dict):
        value = value.get("value")
    value = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise LayoutError("Detalhe sem ID externo estável")
    return value


def _single_offer(node):
    offers = node.get("offers")
    if isinstance(offers, list):
        if len(offers) != 1:
            raise LayoutError("Detalhe com inventário ou ofertas agrupadas")
        offers = offers[0]
    if not isinstance(offers, dict):
        return {}
    return offers


def _address(node):
    candidates = [node.get("address")]
    for key in ("about", "itemOffered"):
        nested = node.get(key)
        if isinstance(nested, dict):
            candidates.append(nested.get("address"))
    return next((item for item in candidates if isinstance(item, dict)), {})


def _property_value(node, *names):
    wanted = {name.lower() for name in names}
    properties = node.get("additionalProperty") or []
    if isinstance(properties, dict):
        properties = [properties]
    for item in properties:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or item.get("propertyID") or "").strip().lower() in wanted:
            return item
    return {}


def _scalar(value):
    if isinstance(value, dict):
        return value.get("value") or value.get("amount")
    return value


def _floor_size(node):
    about = node.get("about") if isinstance(node.get("about"), dict) else {}
    raw = node.get("floorSize") or about.get("floorSize")
    return number(_scalar(raw))


def _explicit_house(node, *texts):
    types = _type_names(node.get("@type"))
    about = node.get("about") if isinstance(node.get("about"), dict) else {}
    types |= _type_names(about.get("@type"))
    if types & {"house", "singlefamilyresidence"}:
        return "casa"
    prop = _property_value(node, "tipo", "tipo do imóvel", "property type")
    explicit = " ".join(str(value or "") for value in (
        prop.get("value"), about.get("name"), *texts)).lower()
    if re.search(r"\b(casa|sobrado)\b", explicit):
        return "casa"
    if re.search(r"\b(apartamento|flat)\b", explicit):
        return "apartamento"
    if re.search(r"\b(kitnet|quitinete|studio)\b", explicit):
        return "kitnet"
    if re.search(r"\b(terreno|lote)\b", explicit):
        return "terreno"
    if re.search(r"\b(comercial|sala comercial|ponto comercial)\b", explicit):
        return "comercial"
    return None


def _record(source, external_id, canonical, requested, final_url, title, description,
            rent, rental_period, city, neighborhood, street, property_type,
            iptu, iptu_period, condo, condo_status, evidence, *, search_url,
            scrape_id, collected_at, area=None, bedrooms=None, bathrooms=None,
            parking=None, transaction_type="unknown"):
    raw_html = evidence.pop("_html")
    return {
        "source": source,
        "external_id": external_id,
        "url": canonical,
        "title": title,
        "property_type": property_type,
        "transaction_type": transaction_type,
        "rent_price": rent,
        "rental_period": rental_period,
        "city": city,
        "neighborhood": neighborhood,
        "street": street,
        "area_m2": area,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parking_spaces": parking,
        "condo_fee": condo,
        "condo_status": condo_status,
        "iptu": iptu,
        "iptu_period": iptu_period,
        "description_excerpt": description,
        "warnings": [],
        "evidence": {**evidence, "description_length": len(description)},
        "provenance": {
            "source_url": canonical,
            "requested_url": requested,
            "final_url": final_url,
            "search_url": search_url,
            "collected_at": collected_at,
            "scrape_id": scrape_id,
            "content_hash": hashlib.sha256(raw_html.encode("utf-8")).hexdigest(),
            "observation_scope": "detail_page",
        },
        "review_status": "pending",
        "publication_status": "not_published",
        "availability_verified": False,
    }


def parse_vivareal_detail(html, url, *, requested_url=None, search_url=None,
                          scrape_id=None, collected_at=None):
    soup, node = _jsonld_listings(html)
    requested = _source_url(requested_url or url, "vivareal")
    final_url = _source_url(url, "vivareal")
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical_raw = node.get("url") or (canonical_tag.get("href") if canonical_tag else url)
    canonical = _source_url(canonical_raw, "vivareal")
    external_id = _identifier(node)
    offer = _single_offer(node)
    price_spec = offer.get("priceSpecification") if isinstance(offer.get("priceSpecification"), dict) else {}
    rent_raw = offer.get("price") or price_spec.get("price")
    unit = price_spec.get("unitText") or offer.get("unitText")
    business = str(offer.get("businessFunction") or offer.get("category") or "").lower()
    transaction = "rental" if re.search(r"lease|rent|alug", business) else "unknown"
    address = _address(node)
    title = str(node.get("name") or "").strip()
    description = sanitize_description(node.get("description"))
    iptu_prop = _property_value(node, "iptu", "property tax")
    condo_prop = _property_value(node, "condomínio", "condominio", "hoa")
    iptu_raw = iptu_prop.get("value")
    iptu_period = _period(iptu_prop.get("unitText") or iptu_prop.get("unitCode"))
    return _record(
        "vivareal", external_id, canonical, requested, final_url, title, description,
        _money(rent_raw), _period(unit),
        str(address.get("addressLocality") or "").strip() or None,
        str(address.get("addressSuburb") or "").strip() or None,
        str(address.get("streetAddress") or "").strip() or None,
        _explicit_house(node), _money(iptu_raw), iptu_period,
        _money(condo_prop.get("value")), _fee_status(condo_prop.get("value")),
        {"_html": html, "structured_type": node.get("@type"),
         "rent_raw": rent_raw, "rent_period_raw": unit,
         "iptu_raw": iptu_raw, "iptu_period_raw": iptu_prop.get("unitText"),
         "iptu_period_source": "structured" if iptu_period else "unknown",
         "iptu_value_uncertain": bool(UNCERTAIN_RE.search(str(iptu_raw or "")))},
        search_url=search_url, scrape_id=scrape_id, collected_at=collected_at,
        area=_floor_size(node),
        bedrooms=_count(_scalar(_property_value(node, "quartos", "bedrooms").get("value"))),
        bathrooms=_count(_scalar(_property_value(node, "banheiros", "bathrooms").get("value"))),
        parking=_count(_scalar(_property_value(node, "vagas", "parking").get("value"))),
        transaction_type=transaction,
    )


def _dom_pairs(soup, selector, label_selector=None, value_selector=None):
    result = {}
    for node in soup.select(selector):
        if label_selector and value_selector:
            label_node, value_node = node.select_one(label_selector), node.select_one(value_selector)
        else:
            children = node.find_all(recursive=False)
            label_node = children[0] if children else None
            value_node = children[-1] if len(children) > 1 else None
        if label_node and value_node:
            result[label_node.get_text(" ", strip=True).lower()] = value_node.get_text(" ", strip=True)
    return result


def _pair(result, prefix):
    return next((value for label, value in result.items() if label.startswith(prefix)), None)


def parse_ponta_detail(html, url, *, requested_url=None, search_url=None,
                       scrape_id=None, collected_at=None):
    soup, node = _jsonld_listings(html)
    requested = _source_url(requested_url or url, "ponta_negra")
    final_url = _source_url(url, "ponta_negra")
    canonical = _source_url(node.get("url") or url, "ponta_negra")
    external_id = _identifier(node)
    offer = _single_offer(node)
    prices = _dom_pairs(soup, ".c49-property-price",
                       ".c49-property-price-title", ".c49-property-price-value")
    basics = _dom_pairs(soup, ".table-row")
    rent_raw = _pair(prices, "loca")
    condo_raw = _pair(prices, "condom")
    iptu_raw = _pair(prices, "iptu")
    title = str(node.get("name") or "").strip()
    description = sanitize_description(node.get("description"))
    about = node.get("about") if isinstance(node.get("about"), dict) else {}
    address = _address(node)
    type_text = _pair(basics, "tipo")
    city = str(address.get("addressLocality") or _pair(basics, "cidade") or "").strip() or None
    neighborhood = str(address.get("addressRegion") or address.get("addressSuburb") or
                       _pair(basics, "bairro") or "").strip() or None
    rental_period = _period(rent_raw)
    iptu_period = _period(iptu_raw)
    business = str(offer.get("businessFunction") or "").lower()
    transaction = "rental" if rent_raw and (not business or re.search(r"lease|rent|alug", business)) else "unknown"
    return _record(
        "ponta_negra", external_id, canonical, requested, final_url, title, description,
        _money_with_period(rent_raw), rental_period, city, neighborhood,
        str(address.get("streetAddress") or "").strip() or None,
        _explicit_house(node, type_text), _money_with_period(iptu_raw), iptu_period,
        _money_with_period(condo_raw), _fee_status(condo_raw),
        {"_html": html, "structured_type": node.get("@type"),
         "rent_raw": rent_raw, "rent_period_raw": rental_period,
         "iptu_raw": iptu_raw, "iptu_period_raw": iptu_period,
         "iptu_period_source": "detail_label" if iptu_period else "unknown",
         "iptu_value_uncertain": bool(UNCERTAIN_RE.search(str(iptu_raw or "")))},
        search_url=search_url, scrape_id=scrape_id, collected_at=collected_at,
        area=_floor_size(node), bedrooms=_count(about.get("numberOfRooms")),
        bathrooms=_count(about.get("numberOfBathroomsTotal")),
        transaction_type=transaction,
    )


def _count(value):
    n = number(value)
    return int(n) if n is not None and float(n).is_integer() else None


def _fee_status(value):
    if value is None:
        return "unknown"
    text = str(value).strip().lower()
    if text in ("isento", "isenta"):
        return "exempt"
    if text.startswith("inclus"):
        return "included"
    if text in ABSENT:
        return "unknown"
    return "reported" if _money_with_period(value) is not None else "needs_review"


def _classify(record, real_estate_type, re_types, category, title, price_label):
    rt = real_estate_type.lower()
    combined = (rt + " " + re_types.lower() + " " + category.lower() + " " + title.lower())

    if rt.startswith("aluguel") or price_label.lower() == "aluguel":
        record["transaction_type"] = "rental"
    elif rt.startswith("venda") or re.search(r"\b(venda|vendo|vende-se)\b", title, re.I):
        record["transaction_type"] = "sale"
    elif re.search(r"\b(di[áa]ria|temporada|season)\b", title, re.I):
        record["transaction_type"] = "short_term"
    else:
        record["transaction_type"] = "unknown"

    if "casa" in rt or (category.lower() == "casas" and "casa" in combined):
        record["property_type"] = "casa"
    elif "quitinete" in combined or "kitnet" in combined or "kit net" in combined:
        record["property_type"] = "kitnet"
    elif "studio" in combined or "stud.io" in combined:
        record["property_type"] = "studio"
    elif "apartamento" in combined or "apart" in combined:
        record["property_type"] = "apartamento"
    elif "terreno" in combined or "lote" in combined:
        record["property_type"] = "terreno"
    elif "comercial" in combined or "ponto" in combined or "sala" in combined:
        record["property_type"] = "comercial"
    else:
        record["property_type"] = None


def evaluate(record):
    """Apply the strict acceptance rules. Returns (accepted, reasons)."""
    reasons = []
    if record["transaction_type"] != "rental":
        reasons.append("transaction_not_rental")
    if record["property_type"] != "casa":
        reasons.append("not_house")
    if record["city"] != "Manaus":
        reasons.append("city_not_manaus")
    if record["rent_price"] is None or record["rent_price"] <= 0:
        reasons.append("rent_price_invalid")
    if record["rental_period"] != "monthly":
        reasons.append("rental_period_not_monthly")
    if record["iptu"] is None or record["iptu"] <= 1:
        reasons.append("iptu_missing_or_invalid")
    if record["iptu_period"] not in ("monthly", "annual"):
        reasons.append("iptu_period_unclear")
    if record.get("evidence", {}).get("iptu_value_uncertain"):
        reasons.append("iptu_value_uncertain")
    excerpt = record["description_excerpt"] or ""
    if len(excerpt) < 120:
        reasons.append("description_too_short")

    # Material-contradiction checks.
    title = (record["title"] or "").lower()
    description = excerpt.lower()
    if record["transaction_type"] == "rental" and re.search(
            r"\b(venda|vendo|vende-se|comprar)\b", title):
        reasons.append("title_contradicts_rental")
    if record["property_type"] == "casa" and re.search(
            r"\b(apartamento|quitinete|kitnet|studio|loft|sal[ao] comercial)\b", title):
        reasons.append("title_contradicts_house")
    if record["transaction_type"] == "rental" and re.search(
            r"\b(para venda|[àa] venda|valor de venda|vende-se|temporada|di[áa]ria)\b",
            description):
        reasons.append("description_contradicts_rental")
    if record["property_type"] == "casa" and re.search(
            r"\b(im[óo]vel comercial|ponto comercial|apartamento|quitinete|kitnet|"
            r"studio|terreno)\b", description):
        reasons.append("description_contradicts_house")

    record["warnings"] = sorted(set(reasons))
    return (not reasons), reasons


def accept(html, url, *, source="olx", requested_url=None, search_url=None,
           scrape_id=None, collected_at=None):
    """Parse and evaluate; returns (accepted, record, reasons)."""
    parsers = {
        "olx": parse_olx_detail,
        "vivareal": parse_vivareal_detail,
        "ponta_negra": parse_ponta_detail,
    }
    if source not in parsers:
        raise ValueError("Fonte de detalhe inválida")
    record = parsers[source](html, url, requested_url=requested_url,
                             search_url=search_url, scrape_id=scrape_id,
                             collected_at=collected_at)
    accepted, reasons = evaluate(record)
    return accepted, record, reasons


def serialize(record):
    """Return a JSON-safe copy with monetary Decimals as canonical strings."""
    data = dict(record)
    for key in ("rent_price", "condo_fee", "iptu"):
        value = data.get(key)
        data[key] = str(value) if isinstance(value, Decimal) else value
    return data
