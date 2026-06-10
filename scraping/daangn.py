from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from core.models import ScrapedItem
from core.query import BASE_SEARCH_URL, normalize_daangn_url
from .proxy import ProxyRotator
from .user_agents import UserAgentManager


PRODUCT_SELECTOR = (
    "#main-content > div._1j555bm0.sprinkles_paddingLeft_4_base__1byufe8g6."
    "sprinkles_paddingLeft_10_small__1byufe8gr.sprinkles_paddingLeft_16_medium__1byufe8h4."
    "sprinkles_paddingLeft_20_large__1byufe8h9.sprinkles_paddingRight_4_base__1byufe8e2."
    "sprinkles_paddingRight_10_small__1byufe8en.sprinkles_paddingRight_16_medium__1byufe8f0."
    "sprinkles_paddingRight_20_large__1byufe8f5.sprinkles_backgroundColor_layerDefault__1byufe8n."
    "sprinkles_width_full_base__1byufe84q > div > section > div > div._12b29ll0."
    "sprinkles_width_full_base__1byufe84q._12b29ll1 > a:nth-child(1)"
)
AREA_TITLE_SELECTOR = (
    "#main-content > div._1j555bm0.sprinkles_paddingLeft_4_base__1byufe8g6."
    "sprinkles_paddingLeft_10_small__1byufe8gr.sprinkles_paddingLeft_16_medium__1byufe8h4."
    "sprinkles_paddingLeft_20_large__1byufe8h9.sprinkles_paddingRight_4_base__1byufe8e2."
    "sprinkles_paddingRight_10_small__1byufe8en.sprinkles_paddingRight_16_medium__1byufe8f0."
    "sprinkles_paddingRight_20_large__1byufe8f5.sprinkles_backgroundColor_layerDefault__1byufe8n."
    "sprinkles_width_full_base__1byufe84q > div > div > h1"
)


class AreaNumberMismatch(Exception):
    pass


class NoCookieSession(requests.Session):
    def prepare_request(self, request: requests.Request) -> requests.PreparedRequest:
        request.cookies = {}
        prepared = super().prepare_request(request)
        prepared.headers.pop("Cookie", None)
        return prepared

    def send(self, request: requests.PreparedRequest, **kwargs) -> requests.Response:
        request.headers.pop("Cookie", None)
        return super().send(request, **kwargs)


class DaangnScraper:
    def __init__(
        self,
        user_agent_manager: UserAgentManager,
        proxy_rotator: ProxyRotator | None,
        error_logger: logging.Logger,
        timeout_seconds: int = 10,
    ) -> None:
        self.user_agent_manager = user_agent_manager
        self.proxy_rotator = proxy_rotator
        self.error_logger = error_logger
        self.timeout_seconds = timeout_seconds

    def fetch_latest_item(self, detect_link: str) -> ScrapedItem | None:
        html = self._get_html(detect_link)
        time.sleep(0.5)
        soup = BeautifulSoup(html, "html.parser")
        link = soup.select_one(PRODUCT_SELECTOR) or self._fallback_product_link(soup)
        if not link or not link.get("href"):
            return None
        url = normalize_daangn_url(link["href"])
        if not url:
            return None
        title = " ".join(link.get_text(" ", strip=True).split()) or "나눔 상품"
        return ScrapedItem(title=title, url=url)

    def fetch_area_name(self, number: int) -> str | None:
        url = f"{BASE_SEARCH_URL}?in={number}"
        response = self._request_with_retry(url)
        if not self._response_matches_area_number(response.url, number):
            raise AreaNumberMismatch(f"요청 번호 {number}와 응답 URL이 일치하지 않습니다: {response.url}")
        soup = BeautifulSoup(self._decode_html(response), "html.parser")
        heading = soup.select_one(AREA_TITLE_SELECTOR) or soup.find("h1")
        if not heading:
            return None
        text = heading.get_text(" ", strip=True).replace("중고거래", "")
        area_name = " ".join(text.split())
        return area_name or None

    def _get_html(self, url: str) -> str:
        return self._decode_html(self._request_with_retry(url))

    def _decode_html(self, response: requests.Response) -> str:
        encoding = response.encoding
        if not encoding or encoding.lower() in {"iso-8859-1", "latin-1"}:
            encoding = "utf-8"
        return response.content.decode(encoding, errors="replace")

    def _request_with_retry(self, url: str) -> requests.Response:
        deadline = time.monotonic() + self.timeout_seconds
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                timeout = max(1, min(10, int(deadline - time.monotonic())))
                with NoCookieSession() as session:
                    response = session.get(
                        url,
                        headers={"User-Agent": self.user_agent_manager.get_user_agent()},
                        proxies=self.proxy_rotator.requests_proxy() if self.proxy_rotator else None,
                        timeout=timeout,
                        allow_redirects=True,
                    )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 0 and time.monotonic() < deadline:
                    time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
                    continue
        raise TimeoutError(f"{url} 요청이 {self.timeout_seconds}초 내 완료되지 않았습니다.") from last_error

    def _fallback_product_link(self, soup: BeautifulSoup):
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if (
                "/kr/buy-sell/" in href
                and "/kr/buy-sell/s/" not in href
                and "?" not in href
                and not href.rstrip("/").endswith("/kr/buy-sell")
            ):
                return link
            if "/articles/" in href:
                return link
        return None

    def _response_matches_area_number(self, response_url: str, number: int) -> bool:
        parsed = urlparse(response_url)
        values = parse_qs(parsed.query).get("in", [])
        if str(number) in values:
            return True
        return bool(re.search(rf"(?:^|[-_/]){number}(?:$|[/?#])", response_url))


def iter_subscriptions(users: list[dict]) -> Iterator[dict]:
    for user in users:
        for subscription in user.get("subscriptions", []):
            yield {"chat_id": user["chat_id"], **subscription}
