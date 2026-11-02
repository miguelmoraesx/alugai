from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import json
import gzip

import httpx
import pytest
from sqlalchemy import select, func

from alugai.collector import execute
from alugai.network import Fetcher, Blocked
from alugai.parser import SEED, LayoutError, money, parse_page
from alugai.store import Store, history

HTML = (Path(__file__).parent / "fixtures/search.html").read_text(encoding="utf-8")


@pytest.fixture
def store():
    instance = Store("sqlite:///:memory:")
    yield instance
    instance.close()


def transport(handler):
    return Fetcher(client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)


def robot_response(request, rules="User-agent: *\nAllow: /\n"):
    return httpx.Response(200, text=rules, headers={"content-type": "text/plain"})


def page_response():
    return httpx.Response(200, text=HTML, headers={"content-type": "text/html"})


@pytest.mark.parametrize("value,expected", [("R$ 1.800,50", "1800.50"), ("1.800", "1800.00"),
    (1800.5, "1800.50"), ("1800.50", "1800.50"), (0, "0.00"), (None, None)])
def test_money(value, expected):
    assert money(value) == (Decimal(expected) if expected is not None else None)


@pytest.mark.parametrize("value", ["a partir de 1000", "-1", "NaN", "1.000 / diária", True])
def test_ambiguous_money_rejected(value):
    with pytest.raises(ValueError):
        money(value)


def test_parse_preserves_unknowns_and_zero():
    rows, next_urls, errors = parse_page(HTML, SEED)
    assert not errors
    assert rows[0].rent_price == Decimal("1800")
    assert rows[0].parking_spaces == 0
    assert rows[0].rental_period == "monthly"
    assert rows[1].condo_fee is None
    assert rows[1].rental_period == "unknown"
    assert next_urls == [SEED + "?o=2"]


@pytest.mark.parametrize("body", ["<html>captcha</html>", '<script id="__NEXT_DATA__">{}</script>',
    '<script id="__NEXT_DATA__">{"props":{"pageProps":{"ads":[]}}}</script>'])
def test_unknown_layout_is_not_empty_success(body):
    with pytest.raises(LayoutError):
        parse_page(body, SEED)


def test_upsert_and_price_history(store):
    row = parse_page(HTML, SEED)[0][0]
    assert store.upsert(row) == "new"
    assert store.upsert(row) == "unchanged"
    assert store.upsert(replace(row, rent_price=Decimal("1900.00"))) == "updated"
    assert len(store.export()) == 1
    with store.engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(history)) == 2
    assert store.export()[0]["rent_price"] == "1900.00"


def test_search_omissions_do_not_erase_details_or_starve_refresh(store):
    row = parse_page(HTML, SEED)[0][0]
    store.upsert(row)
    store.upsert(replace(row, condo_fee=None))
    assert store.export()[0]["condo_fee"] == "350.00"
    assert len(store.due()) == 1
    store.upsert(row, detail=True)
    assert not store.due()


def test_failures_do_not_infer_rental_or_change_price(store):
    row = parse_page(HTML, SEED)[0][0]
    store.upsert(row)
    last_seen = store.export()[0]["last_seen_at"]
    for _ in range(3):
        store.mark_error("olx", row.external_id, "HTTP 503")
    assert store.export()[0]["status"] == "pending_verification"
    assert store.export()[0]["last_seen_at"] == last_seen
    store.mark_error("olx", row.external_id, "HTTP 404", missing=True)
    assert store.export()[0]["status"] == "pending_verification"
    store.mark_error("olx", row.external_id, "HTTP 404", missing=True)
    assert store.export()[0]["status"] == "unavailable"
    store.upsert(row)
    assert store.export()[0]["status"] == "active"


def test_robots_wildcards_block_before_page_request():
    requested = []
    def handler(request):
        requested.append(str(request.url))
        return robot_response(request, "User-agent: *\nDisallow: /*?*o=*\n")
    fetcher = transport(handler)
    with pytest.raises(Blocked, match="robots"):
        fetcher.get(SEED + "?o=2")
    assert requested == ["https://www.olx.com.br/robots.txt"]


@pytest.mark.parametrize("status", [401, 403, 429])
def test_block_has_no_retry(status):
    requested = []
    def handler(request):
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return robot_response(request)
        return httpx.Response(status)
    with pytest.raises(Blocked):
        transport(handler).get(SEED)
    assert len(requested) == 2


def test_block_with_corrupt_compression_still_reported_as_block():
    def handler(request):
        return httpx.Response(403, stream=httpx.ByteStream(b"not gzip"),
                              headers={"content-encoding": "gzip"})
    with pytest.raises(Blocked, match="403"):
        transport(handler).get(SEED)


def test_crawl_delay_is_respected():
    waits = []
    def handler(request):
        if request.url.path == "/robots.txt":
            return robot_response(request, "User-agent: *\nCrawl-delay: 10\nAllow: /\n")
        return page_response()
    fetcher = Fetcher(client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=waits.append)
    fetcher.get(SEED)
    assert waits[0] > 9


def test_compressed_html_is_decoded_once():
    def handler(request):
        if request.url.path == "/robots.txt":
            return robot_response(request)
        return httpx.Response(200, stream=httpx.ByteStream(gzip.compress(HTML.encode())),
                              headers={"content-encoding": "gzip", "content-type": "text/html"})
    assert transport(handler).get(SEED)[0] == HTML


@pytest.mark.parametrize("status", [404, 500, 302])
def test_unavailable_robots_fails_closed(status):
    with pytest.raises(Blocked):
        transport(lambda request: httpx.Response(status)).get(SEED)


def test_redirect_rechecks_robots():
    requested = []
    def handler(request):
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return robot_response(request, "User-agent: *\nDisallow: /private\n")
        return httpx.Response(302, headers={"location": "/private"})
    with pytest.raises(Blocked):
        transport(handler).get(SEED)
    assert not any(url.endswith("/private") for url in requested)


def test_external_redirect_not_followed():
    def handler(request):
        if request.url.path == "/robots.txt":
            return robot_response(request)
        return httpx.Response(302, headers={"location": "https://example.com/"})
    with pytest.raises(ValueError):
        transport(handler).get(SEED)


def test_discovery_limits_and_blocked_pagination(store):
    def handler(request):
        if request.url.path == "/robots.txt":
            return robot_response(request, "User-agent: *\nDisallow: /*?*o=*\n")
        return page_response()
    result = execute(store, transport(handler), "discover", seed=SEED, max_pages=2)
    assert result["status"] == "blocked"
    assert result["processed"] == 2  # valid first-page data survives a later block
    assert len(store.export()) == 2
    again = execute(store, transport(handler), "discover", seed=SEED, limit=1)
    assert again["processed"] == 1
    assert again["unchanged"] == 1


def test_refresh_layout_failure_keeps_existing_data(store):
    row = parse_page(HTML, SEED)[0][0]
    store.upsert(row)
    def handler(request):
        if request.url.path == "/robots.txt":
            return robot_response(request)
        return httpx.Response(200, text="<html>changed</html>", headers={"content-type": "text/html"})
    result = execute(store, transport(handler), "refresh", seed=SEED)
    assert result["status"] == "failed"
    assert store.export()[0]["status"] == "pending_verification"
    assert store.export()[0]["rent_price"] == "1800.00"
    assert store.recent_runs()[0]["finished_at"]


def test_fixture_namespace_isolated(store):
    row = parse_page(HTML, SEED)[0][0]
    store.upsert(row, source="olx-fixture")
    assert not store.export()
    assert not store.due()
    assert len(store.export("olx-fixture")) == 1


def test_detail_refresh_matches_id(store):
    row = parse_page(HTML, SEED)[0][0]
    store.upsert(row)
    ad = {"listId": row.external_id, "subject": row.title, "url": row.url, "priceValue": 2000}
    body = '<script id="__NEXT_DATA__">' + json.dumps({"props": {"pageProps": {"ad": ad}}}) + '</script>'
    def handler(request):
        if request.url.path == "/robots.txt":
            return robot_response(request)
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})
    result = execute(store, transport(handler), "refresh", seed=SEED)
    assert result["status"] == "success"
    assert store.export()[0]["rent_price"] == "2000.00"
    assert not store.due()
