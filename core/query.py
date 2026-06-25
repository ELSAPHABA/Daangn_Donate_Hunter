from __future__ import annotations

from urllib.parse import quote_plus, urlparse

from .models import ALL_KEYWORD, Region


BASE_SEARCH_URL = "https://www.daangn.com/kr/buy-sell/s/"
DAANGN_ORIGIN = "https://www.daangn.com"
MAX_USER_QUERY_LENGTH = 80
BLOCKED_QUERY_CHARS = str.maketrans({char: " " for char in "&?=+#;"})


def sanitize_query_text(value: str | None) -> str:
    without_controls = "".join(" " if _is_control_character(char) else char for char in value or "")
    return " ".join(without_controls.translate(BLOCKED_QUERY_CHARS).split())


def normalize_user_query_text(value: str | None) -> str | None:
    cleaned = sanitize_query_text(value)
    if not cleaned or len(cleaned) > MAX_USER_QUERY_LENGTH:
        return None
    return cleaned


def normalize_keyword(value: str | None) -> str:
    cleaned = sanitize_query_text(value)
    return cleaned if cleaned else ALL_KEYWORD


def build_detect_link(region: Region, keyword: str) -> str:
    query = f"price=0__0&in={quote_plus(_normalize_region_code(region.code))}"
    cleaned_keyword = sanitize_query_text(keyword)
    if cleaned_keyword and cleaned_keyword != ALL_KEYWORD:
        query += f"&search={quote_plus(cleaned_keyword)}"
    return f"{BASE_SEARCH_URL}?{query}"


def normalize_daangn_url(href: str) -> str | None:
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https"} and parsed.netloc == "www.daangn.com":
        return href
    if href.startswith("/"):
        return f"{DAANGN_ORIGIN}{href}"
    return None


def shorten_daangn_product_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc != "www.daangn.com":
        return url
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 3 and parts[:2] == ["kr", "buy-sell"]:
        product_id = parts[2].rsplit("-", 1)[-1]
        return f"{DAANGN_ORIGIN}/kr/buy-sell/{product_id}/"
    return url


def _normalize_region_code(value: str) -> str:
    cleaned = sanitize_query_text(value)
    if not cleaned.isdecimal():
        raise ValueError(f"동네 번호는 숫자여야 합니다: {value!r}")
    return cleaned.lstrip("0") or "0"


def _is_control_character(value: str) -> bool:
    return ord(value) < 32 or ord(value) == 127
