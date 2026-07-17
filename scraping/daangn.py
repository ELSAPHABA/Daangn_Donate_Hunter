from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from bs4 import BeautifulSoup

from core.models import ScrapedItem
from core.query import BASE_SEARCH_URL, DAANGN_ORIGIN, normalize_daangn_url
from .proxy import ProxyRotator
from .user_agents import UserAgentManager


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
        user_agent = self.user_agent_manager.get_user_agent()
        html = self._decode_html(self._request_with_retry(detect_link, user_agent=user_agent))
        route_data = self._extract_buy_sell_route_data(html)
        articles = self._fetch_fleamarket_articles(route_data, user_agent)
        if not articles:
            return None
        latest = articles[0]
        url = normalize_daangn_url(str(latest.get("href") or latest.get("id") or ""))
        if not url:
            return None
        title = " ".join(str(latest.get("title") or "나눔 상품").split())
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

    def _request_with_retry(
        self,
        url: str,
        extra_headers: dict[str, str] | None = None,
        user_agent: str | None = None,
    ) -> requests.Response:
        deadline = time.monotonic() + self.timeout_seconds
        last_error: Exception | None = None
        headers = {
            "User-Agent": user_agent or self.user_agent_manager.get_user_agent(),
            **(extra_headers or {}),
        }
        for attempt in range(2):
            try:
                timeout = max(1, min(10, int(deadline - time.monotonic())))
                with NoCookieSession() as session:
                    response = session.get(
                        url,
                        headers=headers,
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

    def _extract_buy_sell_route_data(self, html: str) -> dict[str, Any]:
        script = self._find_remix_context_script(html)
        context = json.loads(self._extract_json_object(script, "window.__remixContext = "))
        loader_data = context.get("state", {}).get("loaderData", {})
        for route_name, route_data in loader_data.items():
            if route_name.endswith("buy-sell.s") and isinstance(route_data, dict):
                return route_data
        raise RuntimeError("당근 중고거래 검색 route 데이터를 찾지 못했습니다.")

    def _find_remix_context_script(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.get_text()
            if "window.__remixContext" in text:
                return text
        raise RuntimeError("당근 Remix context를 찾지 못했습니다.")

    def _extract_json_object(self, script: str, assignment: str) -> str:
        start = script.index(assignment) + len(assignment)
        brace_start = script.index("{", start)
        depth = 0
        in_string: str | None = None
        escaped = False
        for index, char in enumerate(script[brace_start:], brace_start):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == in_string:
                    in_string = None
                continue
            if char in {'"', "'"}:
                in_string = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return script[brace_start : index + 1]
        raise RuntimeError("당근 Remix context JSON 범위를 찾지 못했습니다.")

    def _fetch_fleamarket_articles(self, route_data: dict[str, Any], user_agent: str) -> list[dict[str, Any]]:
        pow_data = route_data.get("pow") or {}
        current_filters = route_data.get("currentFilters") or {}
        challenge = str(pow_data["challenge"])
        difficulty = int(pow_data["difficulty"])
        nonce = self._solve_pow_nonce(challenge, difficulty)
        params = self._build_fleamarket_search_params(current_filters, pow_data, nonce)
        url = f"{DAANGN_ORIGIN}/kr/api/v1/fleamarket/search?{urlencode(params)}"
        response = self._request_with_retry(
            url,
            extra_headers={"Accept": "application/json"},
            user_agent=user_agent,
        )
        data = response.json()
        articles = data.get("fleamarketArticles", [])
        return articles if isinstance(articles, list) else []

    def _build_fleamarket_search_params(
        self,
        current_filters: dict[str, Any],
        pow_data: dict[str, Any],
        nonce: int,
    ) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "region_id": str(current_filters["regionId"]),
            "uri": str(pow_data["uri"]),
            "nonce": nonce,
            "expires_at": int(pow_data["expiresAt"]),
        }
        optional_filters = {
            "search": "search",
            "categoryId": "category_id",
            "price": "price",
            "onlyOnSale": "only_on_sale",
        }
        for source_key, target_key in optional_filters.items():
            value = current_filters.get(source_key)
            if value not in (None, ""):
                params[target_key] = str(value).lower() if isinstance(value, bool) else str(value)
        return params

    def _solve_pow_nonce(self, challenge: str, difficulty: int) -> int:
        prefix = "0" * difficulty
        nonce = 0
        while True:
            digest = hashlib.sha256(f"{challenge}:{nonce}".encode("utf-8")).hexdigest()
            if digest.startswith(prefix):
                return nonce
            nonce += 1

    def _response_matches_area_number(self, response_url: str, number: int) -> bool:
        parsed = urlparse(response_url)
        values = parse_qs(parsed.query).get("in", [])
        if str(number) in values:
            return True
        return bool(re.search(rf"(?:^|[-_/]){number}(?:$|[/?#])", response_url))


def iter_subscriptions(users: list[dict]) -> Iterator[dict]:
    for user in users:
        for subscription in user.get("subscriptions", []):
            yield {"chat_id": user["chat_id"], "skip_keywords": user.get("skip_keywords", []), **subscription}
