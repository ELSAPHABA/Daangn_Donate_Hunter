from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.models import ALL_KEYWORD, Region, Subscription
from core.query import build_detect_link, normalize_user_query_text

RECENT_ITEM_URL_LIMIT = 100


class JsonStore:
    def __init__(
        self,
        users_path: Path,
        areas_path: Path,
        state_path: Path,
        recent_item_url_limit: int = RECENT_ITEM_URL_LIMIT,
    ) -> None:
        self.users_path = users_path
        self.areas_path = areas_path
        self.state_path = state_path
        self.recent_item_url_limit = max(1, recent_item_url_limit)
        self._lock = threading.RLock()
        for path, default in (
            (self.users_path, {"users": []}),
            (self.areas_path, {}),
            (self.state_path, {"latest_items": {}, "last_area_number": 0}),
        ):
            self._ensure_file(path, default)

    def list_areas(self) -> dict[str, str]:
        with self._lock:
            return dict(self._read_json(self.areas_path, {}))

    def find_region(self, user_input: str) -> Region | None:
        matches = self.find_regions(user_input)
        if len(matches) == 1:
            return matches[0]
        return None

    def find_regions(self, user_input: str) -> list[Region]:
        needle = normalize_user_query_text(user_input)
        if needle is None:
            return []
        areas = self.list_areas()
        if needle.isdecimal():
            normalized_code = needle.lstrip("0") or "0"
            return [
                Region(name, str(code))
                for name, code in areas.items()
                if str(code) in {needle, normalized_code}
            ]
        if needle in areas:
            return [Region(needle, str(areas[needle]))]
        compact_needle = "".join(needle.split())
        return [
            Region(name, str(code))
            for name, code in areas.items()
            if needle in name or compact_needle in "".join(name.split())
        ]

    def upsert_areas(self, areas: dict[str, str], last_area_number: int | None = None) -> None:
        with self._lock:
            current = self._read_json(self.areas_path, {})
            current.update({name: str(code) for name, code in areas.items()})
            self._write_json(self.areas_path, current)
            if last_area_number is not None:
                state = self._read_json(self.state_path, {})
                state["last_area_number"] = int(last_area_number)
                self._write_json(self.state_path, state)

    def get_last_area_number(self) -> int:
        with self._lock:
            return int(self._read_json(self.state_path, {}).get("last_area_number", 0))

    def set_last_area_number(self, last_area_number: int) -> None:
        with self._lock:
            state = self._read_json(self.state_path, {})
            state["last_area_number"] = max(0, int(last_area_number))
            self._write_json(self.state_path, state)

    def ensure_user(self, chat_id: int | str) -> dict[str, Any]:
        with self._lock:
            data = self._read_users()
            user = self._find_user(data, str(chat_id))
            if user is None:
                user = {
                    "chat_id": str(chat_id),
                    "notification": True,
                    "regions": [],
                    "keywords": [],
                    "subscriptions": [],
                }
                data["users"].append(user)
                self._write_json(self.users_path, data)
            return dict(user)

    def get_user(self, chat_id: int | str) -> dict[str, Any] | None:
        with self._lock:
            user = self._find_user(self._read_users(), str(chat_id))
            return dict(user) if user else None

    def list_active_users(self) -> list[dict[str, Any]]:
        with self._lock:
            users = self._read_users()["users"]
            return [dict(user) for user in users if user.get("notification", True)]

    def add_region(self, chat_id: int | str, region: Region) -> bool:
        with self._lock:
            data = self._read_users()
            user = self._require_user(data, str(chat_id))
            regions = user.setdefault("regions", [])
            if any(item["code"] == region.code for item in regions):
                return False
            regions.append({"full_name": region.full_name, "dong_name": region.dong_name, "code": region.code})
            self._refresh_subscriptions(user)
            self._write_json(self.users_path, data)
            return True

    def remove_region(self, chat_id: int | str, code: str) -> Region | None:
        with self._lock:
            data = self._read_users()
            user = self._require_user(data, str(chat_id))
            regions = user.setdefault("regions", [])
            removed = next((item for item in regions if str(item["code"]) == str(code)), None)
            if not removed:
                return None
            user["regions"] = [item for item in regions if str(item["code"]) != str(code)]
            self._refresh_subscriptions(user)
            self._write_json(self.users_path, data)
            return Region(removed["full_name"], str(removed["code"]))

    def add_keyword(self, chat_id: int | str, keyword: str) -> bool:
        normalized_keyword = normalize_user_query_text(keyword)
        if normalized_keyword is None:
            return False
        with self._lock:
            data = self._read_users()
            user = self._require_user(data, str(chat_id))
            keywords = user.setdefault("keywords", [])
            if normalized_keyword in keywords:
                return False
            keywords.append(normalized_keyword)
            self._refresh_subscriptions(user)
            self._write_json(self.users_path, data)
            return True

    def remove_keyword(self, chat_id: int | str, keyword: str) -> bool:
        normalized_keyword = normalize_user_query_text(keyword)
        if normalized_keyword is None:
            return False
        with self._lock:
            data = self._read_users()
            user = self._require_user(data, str(chat_id))
            keywords = user.setdefault("keywords", [])
            if normalized_keyword not in keywords:
                return False
            user["keywords"] = [item for item in keywords if item != normalized_keyword]
            self._refresh_subscriptions(user)
            self._write_json(self.users_path, data)
            return True

    def set_notification(self, chat_id: int | str, enabled: bool) -> None:
        with self._lock:
            data = self._read_users()
            user = self._require_user(data, str(chat_id))
            user["notification"] = enabled
            self._write_json(self.users_path, data)

    def get_latest_item_url(self, detect_link: str) -> str | None:
        with self._lock:
            item_urls = self._coerce_item_urls(
                self._read_json(self.state_path, {}).get("latest_items", {}).get(detect_link)
            )
            return item_urls[0] if item_urls else None

    def set_latest_item_url(self, detect_link: str, item_url: str) -> None:
        self.remember_latest_item_url(detect_link, item_url)

    def remember_latest_item_url(self, detect_link: str, item_url: str) -> bool:
        with self._lock:
            state = self._read_json(self.state_path, {})
            latest = state.setdefault("latest_items", {})
            seen_urls = self._coerce_item_urls(latest.get(detect_link))
            is_new = item_url not in seen_urls
            latest[detect_link] = [item_url, *(url for url in seen_urls if url != item_url)][
                : self.recent_item_url_limit
            ]
            self._write_json(self.state_path, state)
            return is_new

    def _refresh_subscriptions(self, user: dict[str, Any]) -> None:
        saved_keywords = user.get("keywords") or []
        keywords = [ALL_KEYWORD] if ALL_KEYWORD in saved_keywords else saved_keywords or [ALL_KEYWORD]
        subscriptions: list[dict[str, Any]] = []
        for region_data in user.get("regions", []):
            region = Region(region_data["full_name"], str(region_data["code"]))
            for keyword in keywords:
                subscriptions.append(
                    {
                        "region": {
                            "full_name": region.full_name,
                            "dong_name": region.dong_name,
                            "code": region.code,
                        },
                        "keyword": keyword,
                        "detect_link": build_detect_link(region, keyword),
                    }
                )
        user["subscriptions"] = subscriptions

    def subscriptions_for_user(self, chat_id: int | str) -> list[Subscription]:
        user = self.get_user(chat_id)
        if not user:
            return []
        return [_subscription_from_dict(item) for item in user.get("subscriptions", [])]

    def _read_users(self) -> dict[str, Any]:
        data = self._read_json(self.users_path, {"users": []})
        data.setdefault("users", [])
        return data

    def _find_user(self, data: dict[str, Any], chat_id: str) -> dict[str, Any] | None:
        return next((user for user in data["users"] if str(user.get("chat_id")) == chat_id), None)

    def _require_user(self, data: dict[str, Any], chat_id: str) -> dict[str, Any]:
        user = self._find_user(data, chat_id)
        if user is None:
            user = {
                "chat_id": chat_id,
                "notification": True,
                "regions": [],
                "keywords": [],
                "subscriptions": [],
            }
            data["users"].append(user)
        return user

    def _ensure_file(self, path: Path, default: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self._write_json(path, default)

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            return default
        except json.JSONDecodeError as exc:
            backup_path = path.with_suffix(path.suffix + ".corrupt")
            shutil.copy2(path, backup_path)
            raise RuntimeError(f"JSON 파일이 손상되어 백업했습니다: {backup_path}") from exc

    def _write_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as tmp:
            json.dump(value, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    def _coerce_item_urls(self, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value] if value else []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str) and item]
        return []


def _subscription_from_dict(item: dict[str, Any]) -> Subscription:
    region_data = item["region"]
    region = Region(region_data["full_name"], str(region_data["code"]))
    return Subscription(region=region, keyword=item["keyword"], detect_link=item["detect_link"])
