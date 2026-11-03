"""Conservative HTTP transport with per-origin robots rules and no evasion."""
import time
from urllib.parse import urlsplit, urljoin

import httpx
from protego import Protego

from .parser import canonical_url


class FetchError(RuntimeError):
    pass


class Blocked(FetchError):
    pass


class Missing(FetchError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"HTTP {status}")


class Fetcher:
    def __init__(self, user_agent="AlugaiCollector/0.1", delay=5.0, client=None, sleep=time.sleep,
                 allowed_domains=("olx.com.br",)):
        self.user_agent = user_agent
        self.delay = max(2.0, delay)
        self.client = client or httpx.Client(timeout=30, follow_redirects=False,
                                             headers={"User-Agent": user_agent})
        self.sleep = sleep
        self.allowed_domains = tuple(allowed_domains)
        self.policies = {}
        self.last_request = None

    def close(self):
        self.client.close()

    def request(self, url, delay):
        if self.last_request is not None:
            self.sleep(max(0, delay - (time.monotonic() - self.last_request)))
        try:
            # No automatic redirects: every redirect target must pass robots too.
            with self.client.stream("GET", url, headers={"User-Agent": self.user_agent,
                                                          "Accept-Encoding": "identity"}) as response:
                # A denial/redirect does not require decoding its (possibly broken) body.
                if response.status_code != 200:
                    headers = dict(response.headers)
                    headers.pop("content-encoding", None)
                    return httpx.Response(response.status_code, headers=headers,
                                          content=b"", request=response.request)
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > 8_000_000:
                        raise FetchError("Resposta maior que o limite de 8 MB")
                headers = dict(response.headers)
                # iter_bytes already decoded compression. Do not decode it a second time.
                headers.pop("content-encoding", None)
                headers.pop("content-length", None)
                return httpx.Response(response.status_code, headers=headers,
                                      content=bytes(content), request=response.request)
        except httpx.HTTPError as exc:
            raise FetchError(f"Falha HTTP: {type(exc).__name__}") from exc
        finally:
            self.last_request = time.monotonic()

    @staticmethod
    def check_block(response):
        if response.status_code in (401, 403, 429):
            retry = response.headers.get("retry-after", "não informado")
            raise Blocked(f"HTTP {response.status_code}; execução interrompida; Retry-After: {retry}")
        body = response.text.lower()
        # Match challenge pages, not a mere CAPTCHA script in a normal page.
        if "__next_data__" not in body and any(marker in body for marker in (
            "verify you are human", "verifique que você é humano", "access denied",
            "<title>just a moment", "<title>captcha", "cf-chl-", "captcha-delivery.com")):
            raise Blocked("Página de desafio/bloqueio; execução interrompida")

    def rules(self, url):
        canonical_url(url, self.allowed_domains)
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.policies:
            response = self.request(origin + "/robots.txt", self.delay)
            self.check_block(response)
            if response.status_code != 200:
                raise Blocked(f"robots.txt indisponível (HTTP {response.status_code}); coleta suspensa")
            if "<html" in response.text.lower() or "user-agent:" not in response.text.lower():
                raise Blocked("robots.txt não reconhecido; coleta suspensa")
            self.policies[origin] = Protego.parse(response.text)
        return self.policies[origin]

    def get(self, url):
        for _ in range(6):
            rules = self.rules(url)
            if not rules.can_fetch(url, self.user_agent):
                raise Blocked("URL desautorizada pelo robots.txt")
            delay = max(self.delay, float(rules.crawl_delay(self.user_agent) or 0))
            rate = rules.request_rate(self.user_agent)
            if rate and rate.requests:
                delay = max(delay, rate.seconds / rate.requests)
            response = self.request(url, delay)
            self.check_block(response)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise FetchError("Redirecionamento sem destino")
                url = urljoin(url, location)
                canonical_url(url, self.allowed_domains)
                continue
            if response.status_code in (404, 410):
                raise Missing(response.status_code)
            if response.status_code != 200:
                raise FetchError(f"HTTP {response.status_code}")
            if "text/html" not in response.headers.get("content-type", ""):
                raise FetchError("Resposta não é HTML")
            return response.text, url
        raise FetchError("Excesso de redirecionamentos")
