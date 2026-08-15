from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    data_dir: Path
    users_path: Path
    areas_path: Path
    state_path: Path
    user_activity_log: Path
    error_log: Path
    admin_chat_ids: set[str]
    scrape_interval_seconds: int = 60
    monitor_misfire_grace_seconds: int = 300
    monitor_retry_delay_seconds: int = 60
    monitor_concurrency: int = 3
    monitor_max_retries: int = 1
    monitor_recent_items_limit: int = 100
    scrape_timeout_seconds: int = 10
    area_collection_start_number: int = 1
    area_collection_delay_seconds: int = 10
    area_collection_retry_delay_seconds: int = 60
    area_collection_mismatch_stop_threshold: int = 30
    proxy_rotate_seconds: int = 30 * 60 # 기본값: 15 * 60
    proxy_enabled: bool = True
    user_agent_file: str = "user-agents.txt"


def load_settings() -> Settings:
    load_dotenv()
    data_dir = Path(os.getenv("DATA_DIR", DATA_DIR)).resolve()
    user_agent_file = Path(os.getenv("USER_AGENT_FILE", "resources/user-agents.txt"))
    if not user_agent_file.is_absolute():
        user_agent_file = ROOT_DIR / user_agent_file
    proxy_enabled_raw = os.getenv("PROXY_ENABLED", "true").strip().lower()
    proxy_enabled = proxy_enabled_raw in {"1", "true", "yes", "on", "t"}
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        data_dir=data_dir,
        users_path=data_dir / "users.json",
        areas_path=data_dir / "areas.json",
        state_path=data_dir / "scrape_state.json",
        user_activity_log=Path(os.getenv("USER_ACTIVITY_LOG", "user_activity.log")).resolve(),
        error_log=Path(os.getenv("ERROR_LOG", "error.log")).resolve(),
        admin_chat_ids={
            item.strip()
            for item in os.getenv("ADMIN_CHAT_IDS", "").split(",")
            if item.strip()
        },
        scrape_interval_seconds=int(os.getenv("SCRAPE_INTERVAL_SECONDS", "60")),
        monitor_misfire_grace_seconds=int(os.getenv("MONITOR_MISFIRE_GRACE_SECONDS", "300")),
        monitor_retry_delay_seconds=int(os.getenv("MONITOR_RETRY_DELAY_SECONDS", "60")),
        monitor_concurrency=int(os.getenv("MONITOR_CONCURRENCY", "3")),
        monitor_max_retries=int(os.getenv("MONITOR_MAX_RETRIES", "1")),
        monitor_recent_items_limit=int(os.getenv("MONITOR_RECENT_ITEMS_LIMIT", "100")),
        scrape_timeout_seconds=int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "10")),
        area_collection_start_number=int(os.getenv("AREA_COLLECTION_START_NUMBER", "11")),
        area_collection_delay_seconds=int(os.getenv("AREA_COLLECTION_DELAY_SECONDS", "10")),
        area_collection_retry_delay_seconds=int(os.getenv("AREA_COLLECTION_RETRY_DELAY_SECONDS", "60")),
        area_collection_mismatch_stop_threshold=int(
            os.getenv("AREA_COLLECTION_MISMATCH_STOP_THRESHOLD", "30")
        ),
        proxy_rotate_seconds=int(os.getenv("PROXY_ROTATE_SECONDS", str(15 * 60))),
        proxy_enabled=proxy_enabled,
        user_agent_file=str(user_agent_file),
    )
