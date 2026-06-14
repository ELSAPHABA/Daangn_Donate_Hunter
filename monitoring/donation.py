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
        retry_delay_seconds: int = 60,
    ) -> None:
        self.store = store
        self.scraper = scraper
        self.notifier = notifier
        self.activity_logger = activity_logger
        self.error_logger = error_logger
        self.retry_delay_seconds = max(1, retry_delay_seconds)
        self._is_first_scan = True
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

        is_first_scan = self._is_first_scan
        for detect_link, subscriptions in subscriptions_by_link.items():
            item = await self._fetch_latest_item_with_retry(detect_link)
            previous = self.store.get_latest_item_url(detect_link)
            self.store.set_latest_item_url(detect_link, item.url)
            if is_first_scan or previous is None or previous != item.url:
                for subscription in subscriptions:
                    await self.notifier.send_donation_alert(
                        chat_id=subscription["chat_id"],
                        dong_name=subscription["region"]["dong_name"],
                        keyword=subscription["keyword"],
                        product_url=item.url,
                    )
        self._is_first_scan = False

    async def _fetch_latest_item_with_retry(self, detect_link: str):
        while True:
            try:
                item = await asyncio.to_thread(self.scraper.fetch_latest_item, detect_link)
            except TimeoutError as exc:
                self.error_logger.error("[스크래핑 타임아웃] link=%s error=%s", detect_link, exc)
                await self._sleep_before_retry(detect_link)
                continue
            except Exception as exc:
                self.error_logger.error("[스크래핑 실패] link=%s error=%s", detect_link, exc)
                await self._sleep_before_retry(detect_link)
                continue
            if item is not None:
                return item
            self.error_logger.error("[스크래핑 결과 없음] link=%s error=최신 상품을 찾지 못했습니다.", detect_link)
            await self._sleep_before_retry(detect_link)

    async def _sleep_before_retry(self, detect_link: str) -> None:
        self.activity_logger.info(
            "[나눔 모니터링 재시도 대기] link=%s retry_after_seconds=%s",
            detect_link,
            self.retry_delay_seconds,
        )
        await asyncio.sleep(self.retry_delay_seconds)
