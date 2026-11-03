import json
from pathlib import Path

from bs4 import BeautifulSoup
import httpx
import pytest

from alugai.firecrawl import API_URL, FirecrawlFetcher, read_api_key
from alugai.network import Blocked, FetchError, Missing
from alugai.parser import SEED, parse_page
from alugai.probe import probe
from alugai.store import Store

HTML = (Path(__file__).parent / "fixtures/search.html").read_text(encoding="utf-8")
ADS = json.loads(BeautifulSoup(HTML, "html.parser").find("script").get_text())["props"]["pageProps"]["ads"]


def envelope(url, html=HTML, status=200):
    return httpx.Response(200, json={"success": True, "data": {
        "rawHtml": html, "metadata": {"statusCode": status, "sourceURL": url}}})


def api_handler(request):
    url = json.loads(request.content)["url"]
    if url.endswith("/robots.txt"):
        return envelope(url, '<html><body><pre>User-agent: *\nDisallow: /*?*o=*\n</pre></body></html>')
    if url == SEED:
        return envelope(url)
    ad = next(ad for ad in ADS if ad["url"] == url)
    detail = '<script id="__NEXT_DATA__">' + json.dumps({"props": {"pageProps": {"ad": ad}}}) + '</script>'
    return envelope(url, detail)


def fetcher(handler=api_handler, **kwargs):
    return FirecrawlFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)),
                            sleep=lambda _: None, **kwargs)


def test_request_auth_and_fresh_raw_html():
    requests = []
    def handler(request):
        requests.append(request)
        return api_handler(request)
    transport = fetcher(handler, api_key="fc-test-not-a-real-secret")
    html, url = transport.get(SEED)
    assert parse_page(html, url)[0][0].rent_price == 1800
    assert len(requests) == 2
    for request in requests:
        assert str(request.url) == API_URL
        assert request.headers["authorization"] == "Bearer fc-test-not-a-real-secret"
        payload = json.loads(request.content)
        assert payload["formats"] == ["rawHtml"]
        assert payload["maxAge"] == 0
        assert payload["storeInCache"] is False
        assert payload["proxy"] == "basic"
        assert "Authorization" not in payload["headers"]
    assert "fc-test" not in json.dumps(transport.metrics())


def test_anonymous_request_has_no_authorization_header():
    def handler(request):
        assert "authorization" not in request.headers
        return api_handler(request)
    assert fetcher(handler).get(SEED)[0] == HTML


@pytest.mark.parametrize("status", [401, 402, 403, 429])
def test_api_denial_stops_without_retry_or_secret_leak(status):
    transport = fetcher(lambda request: httpx.Response(status, json={"error": "fc-private-key"}),
                        api_key="fc-private-key")
    with pytest.raises(Blocked) as error:
        transport.get(SEED)
    assert "fc-private-key" not in str(error.value)
    assert transport.metrics()["api_calls"] == 1


def test_api_404_is_not_a_missing_listing():
    transport = fetcher(lambda request: httpx.Response(404))
    with pytest.raises(FetchError) as error:
        transport.get(SEED)
    assert not isinstance(error.value, Missing)


def test_target_404_is_a_missing_listing():
    def handler(request):
        url = json.loads(request.content)["url"]
        return api_handler(request) if url.endswith("robots.txt") else envelope(url, "", 404)
    with pytest.raises(Missing):
        fetcher(handler).get(SEED)


def test_call_cap_includes_robots_and_never_overruns():
    transport = fetcher(max_calls=1)
    with pytest.raises(Blocked, match="Limite"):
        transport.get(SEED)
    assert transport.metrics()["api_calls"] == 1


def test_remote_robots_disallow_checked_before_paid_page_request():
    transport = fetcher()
    with pytest.raises(Blocked, match="robots"):
        transport.get(SEED + "?o=2")
    assert transport.metrics()["api_calls"] == 1


@pytest.mark.parametrize("payload", [
    {"success": False, "error": "secret echo"},
    {"success": True, "data": {}},
    {"success": True, "data": {"metadata": {"statusCode": 200, "sourceURL": SEED}}},
    {"success": True, "data": {"metadata": {"statusCode": True, "sourceURL": SEED}, "rawHtml": HTML}},
])
def test_invalid_responses_are_not_successful_empty_collections(payload):
    with pytest.raises(FetchError):
        fetcher(lambda request: httpx.Response(200, json=payload)).get(SEED)


def test_unexpected_redirect_rejected():
    with pytest.raises(FetchError, match="redirecionamento"):
        fetcher(lambda request: envelope("https://www.olx.com.br/login", HTML)).get(SEED)


def test_trailing_slash_normalization_is_not_treated_as_redirect():
    transport = fetcher(lambda request: envelope(
        (json.loads(request.content)["url"] + "/") if not
        json.loads(request.content)["url"].endswith("robots.txt") else
        json.loads(request.content)["url"],
        '<pre>User-agent: *\nAllow: /</pre>' if
        json.loads(request.content)["url"].endswith("robots.txt") else HTML))
    assert transport.get(SEED)[1] == SEED


def test_key_file_does_not_execute_or_interpolate(tmp_path, monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    path = tmp_path / ".env.collector"
    path.write_text('IGNORED=abc\nFIRECRAWL_API_KEY="fc-${NOT_EXPANDED}"\n', encoding="utf-8")
    assert read_api_key(path) == "fc-${NOT_EXPANDED}"
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-from-environment")
    assert read_api_key(path) == "fc-from-environment"
    monkeypatch.delenv("FIRECRAWL_API_KEY")
    path.write_text("FIRECRAWL_API_KEY=key with spaces", encoding="utf-8")
    with pytest.raises(FetchError):
        read_api_key(path)


def test_probe_and_repeat_preserve_sample_and_measure_changes():
    store = Store("sqlite:///:memory:")
    first = probe(store, fetcher(), SEED)
    assert first["status"] == "success"
    assert first["valid_details"] == 2
    assert first["transport"]["api_calls"] == 5  # robots x 2 + search + two details
    assert not store.export("olx")
    assert len(store.export("olx-probe")) == 2
    assert first["manual_review"] == "pending"
    assert first["transport"]["actual_billed_credits"] is None
    def changed(request):
        result = api_handler(request)
        data = result.json()
        data["data"]["rawHtml"] = data["data"]["rawHtml"].replace('R$ 1.800,00', 'R$ 1.900,00')
        return httpx.Response(200, json=data)
    second = probe(store, fetcher(changed), SEED, previous=first)
    assert second["status"] == "success"
    assert second["selected"] == first["selected"]
    assert second["transport"]["api_calls"] == 3  # no search on repeat
    assert second["results"][0]["changes_since_previous"]["rent_price"] == {
        "before": "1800.00", "after": "1900.00"}
    assert second["results"][1]["changes_since_previous"] == {}
    store.close()


def test_probe_block_is_recorded_with_zero_valid_details():
    store = Store("sqlite:///:memory:")
    result = probe(store, fetcher(lambda request: httpx.Response(403)), SEED)
    assert result["status"] == "blocked"
    assert result["valid_details"] == 0
    assert result["estimated_base_credits_per_valid_listing"] is None
    assert store.recent_runs()[0]["status"] == "blocked"
    assert not store.export("olx-probe")
    store.close()
