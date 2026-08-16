from __future__ import annotations

import argparse
import asyncio
from datetime import time
from zoneinfo import ZoneInfo

from telegram import BotCommand
from telegram.ext import Application

from bot import DaangnBot
from core import load_settings
from monitoring import AreaDatabaseCollector, DonationMonitor
from notifications import TelegramNotifier
from scraping import DaangnScraper, ProxyRotator, UserAgentManager
from storage import JsonStore
from utils import configure_logging, configure_process_encoding


def build_components():
    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    activity_logger, error_logger = configure_logging(settings.user_activity_log, settings.error_log)
    store = JsonStore(
        settings.users_path,
        settings.areas_path,
        settings.state_path,
        recent_item_url_limit=settings.monitor_recent_items_limit,
    )
    user_agent_manager = UserAgentManager(settings.user_agent_file)
    proxy_rotator = ProxyRotator.from_env(settings.proxy_rotate_seconds, enabled=settings.proxy_enabled)
    scraper = DaangnScraper(
        user_agent_manager=user_agent_manager,
        proxy_rotator=proxy_rotator,
        error_logger=error_logger,
        timeout_seconds=settings.scrape_timeout_seconds,
    )
    return settings, activity_logger, error_logger, store, scraper


def run_bot() -> None:
    settings, activity_logger, error_logger, store, scraper = build_components()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN 환경 변수를 설정해야 합니다.")

    area_collector = AreaDatabaseCollector(
        store=store,
        scraper=scraper,
        activity_logger=activity_logger,
        error_logger=error_logger,
        initial_start_number=settings.area_collection_start_number,
        delay_seconds=settings.area_collection_delay_seconds,
        retry_delay_seconds=settings.area_collection_retry_delay_seconds,
        mismatch_stop_threshold=settings.area_collection_mismatch_stop_threshold,
    )

    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands(
            [
                BotCommand("start", "봇 시작"),
                BotCommand("settings", "탐지 및 알림 설정"),
                BotCommand("areasetting", "탐지 동네 설정"),
                BotCommand("areaview", "탐지 동네 조회"),
                BotCommand("areaadd", "탐지 동네 추가"),
                BotCommand("areadelete", "탐지 동네 삭제"),
                BotCommand("kwdsetting", "탐지 키워드 설정"),
                BotCommand("kwdview", "탐지 키워드 조회"),
                BotCommand("kwdadd", "탐지 키워드 추가"),
                BotCommand("kwddelete", "탐지 키워드 삭제"),
                BotCommand("skipkwdsetting", "제외 키워드 설정"),
                BotCommand("skipkwdview", "제외 키워드 조회"),
                BotCommand("skipkwdadd", "제외 키워드 추가"),
                BotCommand("skipkwddelete", "제외 키워드 삭제"),
                BotCommand("arlam", "알림 설정"),
                BotCommand("help", "도움말"),
            ]
        )

    application = Application.builder().token(settings.telegram_bot_token).post_init(post_init).build()
    bot = DaangnBot(store, activity_logger, error_logger, settings.error_log, settings.admin_chat_ids)
    bot.register(application)

    notifier = TelegramNotifier(application.bot, error_logger)
    monitor = DonationMonitor(
        store,
        scraper,
        notifier,
        activity_logger,
        error_logger,
        retry_delay_seconds=settings.monitor_retry_delay_seconds,
        concurrency=settings.monitor_concurrency,
        max_retries=settings.monitor_max_retries,
    )

    async def monitor_job(_context):
        await monitor.run_once()

    async def area_collection_full_job(_context):
        await area_collector.collect_from_start(1)

    async def area_collection_incremental_job(_context):
        await area_collector.collect_from_next_number()

    try:
        schedule_tz = ZoneInfo(settings.tz)
    except Exception:
        error_logger.warning("[시간대 설정 오류] 잘못된 시간대 '%s', 기본값 'UTC'로 대체합니다.", settings.tz)
        schedule_tz = ZoneInfo("UTC")

    application.job_queue.run_repeating(
        monitor_job,
        interval=settings.scrape_interval_seconds,
        first=5,
        name="donation-monitor",
        job_kwargs={
            "misfire_grace_time": settings.monitor_misfire_grace_seconds,
            "coalesce": True,
            "max_instances": 1,
        },
    )
    application.job_queue.run_monthly(
        area_collection_full_job,
        when=time(hour=0, minute=0, tzinfo=schedule_tz),
        day=1,
        name="area-db-collector-monthly-full",
        job_kwargs={
            "misfire_grace_time": 3600,
            "coalesce": True,
            "max_instances": 1,
        },
    )
    application.job_queue.run_monthly(
        area_collection_incremental_job,
        when=time(hour=0, minute=0, tzinfo=schedule_tz),
        day=10,
        name="area-db-collector-monthly-day10",
        job_kwargs={
            "misfire_grace_time": 3600,
            "coalesce": True,
            "max_instances": 1,
        },
    )
    application.job_queue.run_monthly(
        area_collection_incremental_job,
        when=time(hour=0, minute=0, tzinfo=schedule_tz),
        day=20,
        name="area-db-collector-monthly-day20",
        job_kwargs={
            "misfire_grace_time": 3600,
            "coalesce": True,
            "max_instances": 1,
        },
    )
    application.run_polling()


def main() -> None:
    configure_process_encoding()
    parser = argparse.ArgumentParser(description="Daangn donation hunter Telegram bot")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("bot", help="텔레그램 봇을 실행합니다.")
    args = parser.parse_args()

    run_bot()


if __name__ == "__main__":
    main()
