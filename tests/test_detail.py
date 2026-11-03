from decimal import Decimal

import pytest

from alugai.detail import (parse_olx_detail, evaluate, sanitize_description,
                           extract_ad, _period, _money, accept)
from alugai.parser import LayoutError


def _escape_json(value):
    # OLX writes the JSON inside an HTML attribute, escaping quotes/ampersands.
    return (value.replace("&", "&amp;").replace('"', "&quot;"))


def fixture(ad):
    import json
    payload = json.dumps({"ad": ad}, ensure_ascii=False)
    return ('<html><body><script id="initial-data" type="text/plain" '
            'data-json="' + _escape_json(payload) + '"></script></body></html>')


def house_ad(**overrides):
    ad = {
        "listId": 100000001,
        "adId": 500000001,
        "subject": "Casa 3 quartos com quintal no Alvorada",
        "priceLabel": "Aluguel",
        "priceValue": "R$ 2.500",
        "categoryName": "Casas",
        "canonicalUrl": "https://am.olx.com.br/regiao-de-manaus/imoveis/casa-alvorada-100000001",
        "location": {"municipality": "Manaus", "neighbourhood": "Alvorada",
                     "address": "Rua das Flores, 12", "zipcode": "69000000"},
        "properties": [
            {"name": "real_estate_type", "label": "Tipo", "value": "Aluguel - casa em rua pública"},
            {"name": "size", "label": "Área construída", "value": "120m²"},
            {"name": "rooms", "label": "Quartos", "value": "3"},
            {"name": "bathrooms", "label": "Banheiros", "value": "2"},
            {"name": "garage_spaces", "label": "Vagas na garagem", "value": "2"},
            {"name": "re_types", "label": "Tipo", "value": "Casa de condomínio"},
        ],
        "realEstatePriceInfo": [
            {"name": "Aluguel", "label": "Aluguel", "value": "R$ 2.500", "period": "mês"},
            {"name": "condominio", "label": "Condomínio", "value": "Não informado", "period": None},
            {"name": "iptu", "label": "IPTU", "value": "R$ 350", "period": "anual"},
            {"name": "estimated_monthly_cost", "label": "Valor total previsto",
             "value": "R$ 2.529,17", "period": "mês"},
        ],
        "description": ("Código do anúncio: Casa Alvorada<br><br>"
                        "Casa espaçosa com três quartos, sendo uma suíte, sala ampla, "
                        "cozinha planejada e quintal com área gourmet. "
                        "Próxima a escolas, mercado e ponto de ônibus. "
                        "Bairro tranquilo e seguro. Agende uma visita."),
        "body": None,
    }
    ad.update(overrides)
    return ad


def test_extract_ad_decodes_html_entities():
    ad = extract_ad(fixture(house_ad()))
    assert ad["listId"] == 100000001
    assert ad["subject"] == "Casa 3 quartos com quintal no Alvorada"


def test_parse_house_accepts_all_fields():
    record = parse_olx_detail(fixture(house_ad()),
                              "https://am.olx.com.br/regiao-de-manaus/imoveis/casa-alvorada-100000001")
    assert record["external_id"] == "100000001"
    assert record["property_type"] == "casa"
    assert record["transaction_type"] == "rental"
    assert record["rent_price"] == Decimal("2500.00")
    assert record["rental_period"] == "monthly"
    assert record["city"] == "Manaus"
    assert record["neighborhood"] == "Alvorada"
    assert record["street"] == "Rua das Flores, 12"
    assert record["area_m2"] == 120
    assert record["bedrooms"] == 3
    assert record["bathrooms"] == 2
    assert record["parking_spaces"] == 2
    assert record["iptu"] == Decimal("350.00")
    assert record["iptu_period"] == "annual"
    assert record["provenance"]["observation_scope"] == "detail_page"
    assert len(record["provenance"]["content_hash"]) == 64


def test_evaluate_accepts_complete_house():
    record = parse_olx_detail(fixture(house_ad()),
                              "https://am.olx.com.br/regiao-de-manaus/imoveis/casa-alvorada-100000001")
    accepted, reasons = evaluate(record)
    assert accepted
    assert reasons == []


def test_sanitize_description_removes_contacts_and_boilerplate():
    body = ("Código do anúncio: Casa<br>"
            "Casa com três quartos e quintal amplo, próxima ao mercado.<br>"
            "WhatsApp: (92) 99999-0000<br>"
            "contato@exemplo.com<br>"
            "Bairro tranquilo com boa localização e acesso fácil ao centro.")
    text = sanitize_description(body)
    assert "(92)" not in text
    assert "contato@" not in text
    assert "Código do anúncio" not in text
    assert "WhatsApp" not in text


@pytest.mark.parametrize("value,expected", [
    ("mês", "monthly"), ("mensal", "monthly"), ("por mês", "monthly"),
    ("anual", "annual"), ("ano", "annual"), ("por ano", "annual"),
    (None, None), ("", None), ("indefinido", None),
])
def test_period_mapping(value, expected):
    assert _period(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("R$ 350", Decimal("350.00")),
    ("Não informado", None),
    ("Consultar", None),
    ("Isento", None),
    (None, None),
])
def test_money_absence_markers(value, expected):
    assert _money(value) == expected


def test_apartment_is_rejected_as_not_house():
    ad = house_ad(properties=[
        {"name": "real_estate_type", "value": "Aluguel - apartamento padrão"},
        {"name": "size", "value": "57m²"},
        {"name": "rooms", "value": "1"},
    ], categoryName="Apartamentos", subject="Apartamento mobiliado no centro")
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/regiao-de-manaus/imoveis/apt-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "not_house" in reasons


def test_iptu_missing_is_rejected():
    ad = house_ad(realEstatePriceInfo=[
        {"name": "Aluguel", "value": "R$ 2.500", "period": "mês"},
        {"name": "condominio", "value": "Não informado", "period": None},
        {"name": "iptu", "value": "Não informado", "period": None},
    ])
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "iptu_missing_or_invalid" in reasons


def test_iptu_value_without_period_is_rejected():
    ad = house_ad(realEstatePriceInfo=[
        {"name": "Aluguel", "value": "R$ 2.500", "period": "mês"},
        {"name": "condominio", "value": "Não informado", "period": None},
        {"name": "iptu", "value": "R$ 350", "period": None},
    ])
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "iptu_period_unclear" in reasons


def test_sale_is_rejected():
    ad = house_ad(properties=[
        {"name": "real_estate_type", "value": "Venda - casa em rua pública"},
    ], priceLabel="Venda", subject="Casa à venda")
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "transaction_not_rental" in reasons


def test_short_description_is_rejected():
    ad = house_ad(description="Casa. Aluguel.")
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "description_too_short" in reasons


def test_title_contradicting_house_is_rejected():
    ad = house_ad(subject="Apartamento 2 quartos para alugar")
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "title_contradicts_house" in reasons


def test_missing_initial_data_raises_layout_error():
    with pytest.raises(LayoutError):
        extract_ad("<html><body>sem dados</body></html>")


def test_accept_helper_returns_record_and_reasons():
    accepted, record, reasons = accept(
        fixture(house_ad()), "https://am.olx.com.br/regiao-de-manaus/imoveis/casa-alvorada-100000001")
    assert accepted
    assert record["review_status"] == "pending"
    assert record["publication_status"] == "not_published"
    assert record["availability_verified"] is False
    assert reasons == []


def test_iptu_period_from_description_fallback():
    ad = house_ad(realEstatePriceInfo=[
        {"name": "Aluguel", "value": "R$ 2.500", "period": "mês"},
        {"name": "condominio", "value": "Não informado", "period": None},
        {"name": "iptu", "value": "R$ 350", "period": None},
    ], description=("Casa com três quartos e quintal amplo, próxima ao mercado e "
                    "escola. IPTU anual de R$ 350 pago separadamente. Bairro tranquilo "
                    "com boa localização e fácil acesso ao centro da cidade."))
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert accepted
    assert record["iptu_period"] == "annual"
    assert record["evidence"]["iptu_period_source"] == "description"


def test_iptu_period_absent_in_description_still_rejected():
    ad = house_ad(realEstatePriceInfo=[
        {"name": "Aluguel", "value": "R$ 2.500", "period": "mês"},
        {"name": "condominio", "value": "Não informado", "period": None},
        {"name": "iptu", "value": "R$ 350", "period": None},
    ], description=("Casa com três quartos e quintal amplo, próxima ao mercado e "
                    "escola. Bairro tranquilo com boa localização e fácil acesso ao centro."))
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "iptu_period_unclear" in reasons


def test_literal_html_entity_inside_json_is_not_double_unescaped():
    ad = house_ad(description=("Casa com três quartos e quintal amplo, próxima ao mercado e "
                               "escola. Texto com entidade literal &quot;especial&quot; que deve "
                               "continuar sendo JSON válido e descrição útil para revisão."))
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    assert '"especial"' in record["description_excerpt"]


def test_approximate_iptu_period_fallback_is_not_accepted():
    ad = house_ad(realEstatePriceInfo=[
        {"name": "Aluguel", "value": "R$ 2.500", "period": "mês"},
        {"name": "iptu", "value": "R$ 350", "period": None},
    ], description=("Casa com três quartos, suíte, sala ampla, cozinha e quintal. "
                    "IPTU aproximadamente R$ 350 anual, conforme estimativa do anunciante. "
                    "Imóvel próximo a escolas, mercados e transporte público."))
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "iptu_value_uncertain" in reasons


def test_description_contradicting_rental_is_rejected():
    ad = house_ad(description=("Casa ampla com três quartos, suíte, cozinha e quintal. "
                               "O imóvel também está à venda pelo valor informado ao corretor. "
                               "Boa localização, próxima a escolas e mercados do bairro."))
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    accepted, reasons = evaluate(record)
    assert not accepted
    assert "description_contradicts_rental" in reasons


def test_ranges_are_not_converted_to_exact_physical_values():
    ad = house_ad(properties=[
        {"name": "real_estate_type", "value": "Aluguel - casa em rua pública"},
        {"name": "size", "value": "100 a 120 m²"},
        {"name": "rooms", "value": "5 ou mais"},
        {"name": "bathrooms", "value": "2-4"},
        {"name": "garage_spaces", "value": "3+"},
    ])
    record = parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
    assert record["area_m2"] is None
    assert record["bedrooms"] is None
    assert record["bathrooms"] is None
    assert record["parking_spaces"] is None


def test_embedded_canonical_url_must_stay_on_source_domain():
    ad = house_ad(canonicalUrl="https://example.com/imovel/100000001")
    with pytest.raises(LayoutError, match="domínio"):
        parse_olx_detail(fixture(ad), "https://am.olx.com.br/x-100000001")
