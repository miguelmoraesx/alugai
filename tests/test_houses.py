"""Collection-flow tests: discovery via cards, verification via detail pages."""
from alugai.houses import collect_houses
from alugai.store import Store


def _escape_json(value):
    return value.replace("&", "&amp;").replace('"', "&quot;")


def _fixture(ad):
    import json
    payload = json.dumps({"ad": ad}, ensure_ascii=False)
    return ('<html><body><script id="initial-data" type="text/plain" '
            'data-json="' + _escape_json(payload) + '"></script></body></html>')


def _house_ad():
    return {
        "listId": 100000001,
        "adId": 500000001,
        "subject": "Casa 3 quartos com quintal no Alvorada",
        "priceLabel": "Aluguel",
        "categoryName": "Casas",
        "canonicalUrl": "https://am.olx.com.br/regiao-de-manaus/imoveis/casa-alvorada-100000001",
        "location": {"municipality": "Manaus", "neighbourhood": "Alvorada", "address": "Rua das Flores, 12"},
        "properties": [
            {"name": "real_estate_type", "value": "Aluguel - casa em rua pública"},
            {"name": "size", "value": "120m²"},
            {"name": "rooms", "value": "3"},
            {"name": "bathrooms", "value": "2"},
            {"name": "garage_spaces", "value": "2"},
        ],
        "realEstatePriceInfo": [
            {"name": "Aluguel", "value": "R$ 2.500", "period": "mês"},
            {"name": "condominio", "value": "Não informado", "period": None},
            {"name": "iptu", "value": "R$ 350", "period": "anual"},
        ],
        "description": "Casa espaçosa com três quartos, sendo uma suíte, sala ampla, cozinha planejada e quintal com área gourmet. Próxima a escolas, mercado e ponto de ônibus. Bairro tranquilo e seguro.",
    }


SEARCH = (
    '<section class="olx-adcard">'
    '<a data-testid="adcard-link" href="https://am.olx.com.br/regiao-de-manaus/imoveis/casa-alvorada-100000001">Casa Alvorada</a>'
    '<h3 class="olx-adcard__price">R$ 2.500</h3>'
    '<p class="olx-adcard__location">Manaus, Alvorada</p>'
    '<div class="olx-adcard__detail" aria-label="120 metros quadrados"></div>'
    '<div class="olx-adcard__detail" aria-label="3 quartos"></div>'
    '</section>'
)


class MockFetcher:
    def __init__(self, detail_html):
        self.detail_html = detail_html
        self.calls = []

    def get(self, url):
        self.calls.append({"url": url, "scrape_id": "s-0001"})
        if "casas" in url:
            return SEARCH, url
        return self.detail_html, url

    def metrics(self):
        return {"provider": "firecrawl", "api_calls": len(self.calls), "calls": self.calls}

    def close(self):
        pass


def test_collect_houses_accepts_and_stages_house(tmp_path):
    store = Store("sqlite:///" + (tmp_path / "db.sqlite").as_posix())
    report = collect_houses(store, MockFetcher(_fixture(_house_ad())),
                            "https://www.olx.com.br/imoveis/aluguel/casas/estado-am/regiao-de-manaus/manaus",
                            max_details=5, max_accepted=20)
    assert report["accepted"] == 1
    assert report["inspected"] == 1
    assert report["accepted_ids"] == ["100000001"]
    assert store.count_review_items("olx") == 1
    store.close()


def test_collect_houses_rejects_apartment_and_stages_nothing(tmp_path):
    store = Store("sqlite:///" + (tmp_path / "db.sqlite").as_posix())
    ad = _house_ad()
    ad["properties"] = [
        {"name": "real_estate_type", "value": "Aluguel - apartamento padrão"},
        {"name": "size", "value": "57m²"},
        {"name": "rooms", "value": "1"},
    ]
    ad["categoryName"] = "Apartamentos"
    report = collect_houses(store, MockFetcher(_fixture(ad)),
                            "https://www.olx.com.br/imoveis/aluguel/casas/estado-am/regiao-de-manaus/manaus",
                            max_details=5, max_accepted=20)
    assert report["accepted"] == 0
    assert report["rejected"].get("not_house", 0) == 1
    assert store.count_review_items("olx") == 0
    store.close()


def test_collect_houses_rejects_card_detail_id_mismatch(tmp_path):
    store = Store("sqlite:///" + (tmp_path / "db.sqlite").as_posix())
    ad = _house_ad()
    ad["listId"] = 100000002
    report = collect_houses(store, MockFetcher(_fixture(ad)),
                            "https://www.olx.com.br/imoveis/aluguel/casas/estado-am/regiao-de-manaus/manaus")
    assert report["accepted"] == 0
    assert report["rejected"]["external_id_mismatch"] == 1
    assert store.count_review_items("olx") == 0
    store.close()


def test_unexpected_failure_finishes_run_as_failed(tmp_path):
    store = Store("sqlite:///" + (tmp_path / "db.sqlite").as_posix())
    store.upsert_review_item = lambda *args: (_ for _ in ()).throw(RuntimeError("boom"))
    report = collect_houses(store, MockFetcher(_fixture(_house_ad())),
                            "https://www.olx.com.br/imoveis/aluguel/casas/estado-am/regiao-de-manaus/manaus")
    assert report["status"] == "failed"
    run = store.recent_runs()[0]
    assert run["status"] == "failed"
    assert run["finished_at"] is not None
    store.close()


def test_review_item_upsert_is_idempotent(tmp_path):
    store = Store("sqlite:///" + (tmp_path / "db.sqlite").as_posix())
    assert store.upsert_review_item("olx", "1", {"value": 1}) == "new"
    assert store.upsert_review_item("olx", "1", {"value": 2}) == "updated"
    assert store.count_review_items("olx") == 1
    assert store.review_data()[0]["value"] == 2
    store.close()
