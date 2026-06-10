from __future__ import annotations

import argparse
from datetime import time
from zoneinfo import ZoneInfo

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
    store = JsonStore(settings.users_path, settings.areas_path, settings.state_path)
    user_agent_manager = UserAgentManager(settings.user_agent_file)
    proxy_rotator = ProxyRotator.from_env(settings.proxy_rotate_seconds)
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

    application = Application.builder().token(settings.telegram_bot_token).build()
    bot = DaangnBot(store, activity_logger, error_logger, settings.error_log, settings.admin_chat_ids)
    bot.register(application)

    notifier = TelegramNotifier(application.bot, error_logger)
    monitor = DonationMonitor(store, scraper, notifier, error_logger)
    area_collector = AreaDatabaseCollector(
        store=store,
        scraper=scraper,
        activity_logger=activity_logger,
        error_logger=error_logger,
        initial_start_number=settings.area_collection_start_number,
        delay_seconds=settings.area_collection_delay_seconds,
    )

    async def monitor_job(_context):
        await monitor.run_once()

    async def area_collection_job(_context):
        await area_collector.collect_from_next_number()

    application.job_queue.run_repeating(
        monitor_job,
        interval=settings.scrape_interval_seconds,
        first=5,
        name="donation-monitor",
    )
    application.job_queue.run_once(
        area_collection_job,
        when=0,
        name="area-db-collector-on-start",
    )
    application.job_queue.run_monthly(
        area_collection_job,
        when=time(hour=0, minute=0, tzinfo=ZoneInfo("Asia/Seoul")),
        day=1,
        name="area-db-collector-monthly",
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
