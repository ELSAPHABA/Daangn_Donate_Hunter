from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from notifications import TelegramNotifier
from scraping import DaangnScraper, iter_subscriptions
from storage import JsonStore


class DonationMonitor:
    def __init__(
        self,
        store: JsonStore,
        scraper: DaangnScraper,
        notifier: TelegramNotifier,
        activity_logger: logging.Logger,
        error_logger: logging.Logger,
    ) -> None:
        self.store = store
        self.scraper = scraper
        self.notifier = notifier
        self.activity_logger = activity_logger
        self.error_logger = error_logger
        self._lock = asyncio.Lock()

    async def run_once(self) -> None:
        if self._lock.locked():
            self.activity_logger.info("[나눔 모니터링] 이전 실행이 진행 중이어서 이번 실행을 건너뜁니다.")
            return
        async with self._lock:
            await self._run_once()

    async def _run_once(self) -> None:
        subscriptions_by_link = defaultdict(list)
        for subscription in iter_subscriptions(self.store.list_active_users()):
            subscriptions_by_link[subscription["detect_link"]].append(subscription)

        for detect_link, subscriptions in subscriptions_by_link.items():
            try:
                item = await asyncio.to_thread(self.scraper.fetch_latest_item, detect_link)
                if not item:
                    continue
                previous = self.store.get_latest_item_url(detect_link)
                self.store.set_latest_item_url(detect_link, item.url)
                if previous and previous != item.url:
                    for subscription in subscriptions:
                        await self.notifier.send_donation_alert(
                            chat_id=subscription["chat_id"],
                            dong_name=subscription["region"]["dong_name"],
                            keyword=subscription["keyword"],
                            product_url=item.url,
                        )
            except Exception as exc:
                self.error_logger.error("[스크래핑 실패] link=%s error=%s", detect_link, exc)
