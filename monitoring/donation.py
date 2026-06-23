from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from core import ScrapedItem
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
        concurrency: int = 3,
        max_retries: int = 1,
    ) -> None:
        self.store = store
        self.scraper = scraper
        self.notifier = notifier
        self.activity_logger = activity_logger
        self.error_logger = error_logger
        self.retry_delay_seconds = max(1, retry_delay_seconds)
        self.concurrency = max(1, concurrency)
        self.max_retries = max(1, max_retries)
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

        semaphore = asyncio.Semaphore(self.concurrency)

        async def process_link(detect_link: str, subscriptions: list[dict]) -> None:
            async with semaphore:
                try:
                    item = await self._fetch_latest_item_with_retry(detect_link)
                    if item is None:
                        self.activity_logger.warning("[나눔 모니터링 스킵] link=%s", detect_link)
                        return

                    if self.store.remember_latest_item_url(detect_link, item.url):
                        for subscription in subscriptions:
                            await self.notifier.send_donation_alert(
                                chat_id=subscription["chat_id"],
                                dong_name=subscription["region"]["dong_name"],
                                keyword=subscription["keyword"],
                                product_url=item.url,
                            )
                except Exception as exc:
                    self.error_logger.error("[나눔 모니터링 작업 실패] link=%s error=%s", detect_link, exc)

        await asyncio.gather(
            *(process_link(detect_link, subscriptions) for detect_link, subscriptions in subscriptions_by_link.items())
        )

    async def _fetch_latest_item_with_retry(self, detect_link: str) -> ScrapedItem | None:
        for attempt in range(1, self.max_retries + 1):
            try:
                item = await asyncio.to_thread(self.scraper.fetch_latest_item, detect_link)
            except TimeoutError as exc:
                self.error_logger.error(
                    "[스크래핑 타임아웃] link=%s attempt=%s/%s error=%s",
                    detect_link,
                    attempt,
                    self.max_retries,
                    exc,
                )
            except Exception as exc:
                self.error_logger.error(
                    "[스크래핑 실패] link=%s attempt=%s/%s error=%s",
                    detect_link,
                    attempt,
                    self.max_retries,
                    exc,
                )
            else:
                if item is not None:
                    return item
                self.error_logger.error(
                    "[스크래핑 결과 없음] link=%s attempt=%s/%s error=최신 상품을 찾지 못했습니다.",
                    detect_link,
                    attempt,
                    self.max_retries,
                )

            if attempt < self.max_retries:
                await self._sleep_before_retry(detect_link)

        return None

    async def _sleep_before_retry(self, detect_link: str) -> None:
        self.activity_logger.info(
            "[나눔 모니터링 재시도 대기] link=%s retry_after_seconds=%s",
            detect_link,
            self.retry_delay_seconds,
        )
        await asyncio.sleep(self.retry_delay_seconds)
