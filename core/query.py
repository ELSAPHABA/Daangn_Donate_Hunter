from __future__ import annotations

from urllib.parse import quote_plus, urlparse

from .models import ALL_KEYWORD, Region


BASE_SEARCH_URL = "https://www.daangn.com/kr/buy-sell/s/"
DAANGN_ORIGIN = "https://www.daangn.com"
BLOCKED_QUERY_CHARS = str.maketrans({char: " " for char in "&?=+"})


def sanitize_query_text(value: str) -> str:
    return " ".join(value.translate(BLOCKED_QUERY_CHARS).split())


def normalize_keyword(value: str | None) -> str:
    cleaned = sanitize_query_text(value or "")
    return cleaned if cleaned else ALL_KEYWORD


def build_detect_link(region: Region, keyword: str) -> str:
    query = f"price=0__0&in={quote_plus(region.code)}"
    if keyword != ALL_KEYWORD:
        query += f"&search={quote_plus(keyword)}"
    return f"{BASE_SEARCH_URL}?{query}"


def normalize_daangn_url(href: str) -> str | None:
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https"} and parsed.netloc == "www.daangn.com":
        return href
    if href.startswith("/"):
        return f"{DAANGN_ORIGIN}{href}"
    return None
