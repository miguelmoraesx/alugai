"""Firecrawl v2 transport. The API key never goes to the target website."""
import os
from pathlib import Path
import time
from urllib.parse import urlsplit, urldefrag

from bs4 import BeautifulSoup
import httpx

from .network import Fetcher, FetchError, Blocked
from .parser import canonical_url

API_URL = "https://api.firecrawl.dev/v2/scrape"


def read_api_key(path=Path(".env.collector")):
    """Read only this credential; never execute/interpolate environment file content."""
    key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not key and path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "FIRECRAWL_API_KEY":
                key = value.strip()
                if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
                    key = key[1:-1]
                break
    if key and (any(c.isspace() for c in key) or not key.isascii()):
        raise FetchError("Formato de FIRECRAWL_API_KEY inválido; confira o arquivo local")
    return key or None


class FirecrawlFetcher(Fetcher):
    def __init__(self, api_key=None, *, max_calls=13, client=None, sleep=time.sleep):
        super().__init__(client=client or httpx.Client(timeout=55, follow_redirects=False), sleep=sleep)
        self.api_key = api_key
        self.max_calls = max_calls
        self.calls = []

    def metrics(self):
        successes = sum(call.get("api_status") == 200 and call.get("target_status") == 200
                        for call in self.calls)
        return {"provider": "firecrawl", "auth_mode": "api_key" if self.api_key else "anonymous",
                "api_calls": len(self.calls), "max_calls": self.max_calls,
                "successful_scrapes": successes, "estimated_base_credits": successes,
                "actual_billed_credits": None, "calls": self.calls}

    def request(self, url, delay):
        canonical_url(url)
        if len(self.calls) >= self.max_calls:
            raise Blocked("Limite de chamadas Firecrawl atingido; nenhuma chamada extra enviada")
        if self.last_request is not None:
            self.sleep(max(0, delay - (time.monotonic() - self.last_request)))
        is_robots = urlsplit(url).path == "/robots.txt"
        call = {"url": url, "kind": "robots" if is_robots else "page"}
        self.calls.append(call)
        started = time.monotonic()
        payload = {"url": url, "formats": ["rawHtml"], "onlyMainContent": False,
                   "maxAge": 0, "storeInCache": False, "timeout": 45000,
                   "skipTlsVerification": False, "proxy": "basic", "parsers": [],
                   "headers": {"User-Agent": self.user_agent}}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            response = self.client.post(API_URL, json=payload, headers=headers)
            call["api_status"] = response.status_code
            if response.status_code in (401, 402, 403, 429):
                raise Blocked(f"Firecrawl API HTTP {response.status_code}; confira acesso, saldo ou limite")
            if response.status_code != 200:
                # An API 404 is NOT evidence of a removed OLX listing.
                raise FetchError(f"Firecrawl API HTTP {response.status_code}")
            try:
                envelope = response.json()
            except ValueError as exc:
                raise FetchError("Firecrawl retornou resposta não JSON") from exc
            if not isinstance(envelope, dict) or envelope.get("success") is not True:
                raise FetchError("Firecrawl não confirmou sucesso; resposta omitida para proteger credenciais")
            data = envelope.get("data")
            metadata = data.get("metadata") if isinstance(data, dict) else None
            if not isinstance(metadata, dict):
                raise FetchError("Firecrawl sem metadados de origem")
            status = metadata.get("statusCode")
            if type(status) is not int or status < 100 or status > 599:
                raise FetchError("Firecrawl sem status HTTP válido da origem")
            call["target_status"] = status
            final_url = metadata.get("url") or metadata.get("sourceURL")
            if not isinstance(final_url, str):
                raise FetchError("Firecrawl sem URL de origem")
            canonical_url(final_url)
            if urldefrag(final_url)[0] != urldefrag(url)[0]:
                raise FetchError("Firecrawl informou redirecionamento; revisar destino antes de coletar")
            html = data.get("rawHtml")
            if status == 200 and (not isinstance(html, str) or not html.strip()):
                raise FetchError("Firecrawl sem rawHtml; não substituir por texto gerado")
            if not isinstance(html, str):
                html = ""
            if len(html.encode("utf-8")) > 8_000_000:
                raise FetchError("HTML Firecrawl excede 8 MB")
            if is_robots and status == 200:
                # Text files can be returned inside a browser's <pre> wrapper.
                html = BeautifulSoup(html, "html.parser").get_text() if "<" in html else html
            return httpx.Response(status, text=html,
                                  headers={"content-type": "text/plain" if is_robots else "text/html"})
        except httpx.HTTPError as exc:
            raise FetchError(f"Falha de transporte Firecrawl: {type(exc).__name__}") from None
        finally:
            call["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            self.last_request = time.monotonic()
