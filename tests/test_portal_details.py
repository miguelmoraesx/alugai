import json

import pytest

from alugai.detail import accept, parse_ponta_detail, parse_vivareal_detail
from alugai.parser import LayoutError


DESCRIPTION = (
    "Casa residencial ampla com três quartos, uma suíte, sala bem ventilada, "
    "cozinha funcional e quintal. Localizada perto de escolas, mercados e "
    "transporte público, em rua tranquila do bairro."
)


def jsonld_page(node, extra=""):
    return ("<html><head><script type='application/ld+json'>" +
            json.dumps(node, ensure_ascii=False) +
            "</script></head><body>" + extra + "</body></html>")


def viva_node(**overrides):
    node = {
        "@context": "https://schema.org",
        "@type": "Product",
        "sku": "2910000001",
        "url": "https://www.vivareal.com.br/imovel/casa-3-quartos-manaus-id-2910000001/",
        "name": "Casa residencial com três quartos em Manaus",
        "description": DESCRIPTION,
        "address": {"addressLocality": "Manaus", "addressSuburb": "Alvorada",
                    "streetAddress": "Rua Exemplo"},
        "floorSize": {"value": "120"},
        "additionalProperty": [
            {"name": "Tipo do imóvel", "value": "Casa"},
            {"name": "Quartos", "value": "3"},
            {"name": "Banheiros", "value": "2"},
            {"name": "Vagas", "value": "2"},
            {"name": "IPTU", "value": "R$ 360", "unitText": "anual"},
            {"name": "Condomínio", "value": "Não informado"},
        ],
        "offers": {"@type": "Offer", "price": "2500",
                   "businessFunction": "LeaseOut",
                   "priceSpecification": {"price": "2500", "unitText": "mês"}},
    }
    node.update(overrides)
    return node


def ponta_page(**overrides):
    node = {
        "@context": "https://schema.org", "@type": "RealEstateListing",
        "sku": "7659",
        "url": "https://www.pontanegraimoveis.com.br/7659/imoveis/locacao-casa-manaus-am",
        "name": "Casa residencial em Manaus", "description": DESCRIPTION,
        "about": {"@type": "House", "numberOfRooms": "3",
                  "numberOfBathroomsTotal": "2", "floorSize": {"value": "120"},
                  "address": {"addressLocality": "Manaus", "addressSuburb": "Flores"}},
        "offers": {"@type": "Offer", "businessFunction": "LeaseOut", "price": "2500"},
    }
    node.update(overrides)
    prices = "".join(
        "<div class='c49-property-price'><div class='c49-property-price-title'>%s</div>"
        "<div class='c49-property-price-value'>%s</div></div>" % pair
        for pair in (("Locação", "R$ 2.500 / mês"), ("Condomínio", "Não informado"),
                     ("IPTU", "R$ 360 / ano")))
    return jsonld_page(node, prices)


def test_vivareal_valid_individual_house_is_parsed_and_accepted():
    url = viva_node()["url"]
    accepted, record, reasons = accept(jsonld_page(viva_node()), url, source="vivareal")
    assert accepted and reasons == []
    assert record["external_id"] == "2910000001"
    assert record["property_type"] == "casa"
    assert record["rental_period"] == "monthly"
    assert record["iptu_period"] == "annual"
    assert record["provenance"]["observation_scope"] == "detail_page"


def test_vivareal_requires_explicit_id_and_one_listing():
    url = viva_node()["url"]
    node = viva_node()
    node.pop("sku")
    with pytest.raises(LayoutError, match="ID externo"):
        parse_vivareal_detail(jsonld_page(node), url)
    grouped = jsonld_page(viva_node()) + jsonld_page(viva_node(sku="2910000002"))
    with pytest.raises(LayoutError, match="único anúncio"):
        parse_vivareal_detail(grouped, url)


def test_vivareal_rejects_canonical_outside_source_domain():
    node = viva_node(url="https://example.com/imovel/2910000001")
    with pytest.raises(LayoutError, match="domínio"):
        parse_vivareal_detail(jsonld_page(node), viva_node()["url"])


def test_ponta_negra_valid_individual_house_is_parsed_and_accepted():
    url = "https://www.pontanegraimoveis.com.br/7659/imoveis/locacao-casa-manaus-am"
    accepted, record, reasons = accept(ponta_page(), url, source="ponta_negra")
    assert accepted and reasons == []
    assert record["external_id"] == "7659"
    assert record["rent_price"] is not None
    assert record["iptu_period"] == "annual"
    assert "_html" not in record["evidence"]


def test_ponta_negra_without_explicit_fee_period_is_rejected():
    page = ponta_page().replace("R$ 360 / ano", "R$ 360")
    url = "https://www.pontanegraimoveis.com.br/7659/imoveis/locacao-casa-manaus-am"
    accepted, _, reasons = accept(page, url, source="ponta_negra")
    assert not accepted
    assert "iptu_period_unclear" in reasons
