from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from core import ScrapedItem
from core.query import keyword_matches_text
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

        if not subscriptions_by_link:
            return

        self.activity_logger.info(
            "[나눔 모니터링 시작] 대상 링크 수: %s개", len(subscriptions_by_link)
        )

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
                            matched_skip_keyword = next(
                                (
                                    keyword
                                    for keyword in subscription.get("skip_keywords", [])
                                    if keyword_matches_text(keyword, item.title)
                                ),
                                None,
                            )
                            if matched_skip_keyword is not None:
                                self.activity_logger.info(
                                    "[나눔 알림 제외] chat_id=%s skip_keyword=%s title=%s url=%s",
                                    subscription["chat_id"],
                                    matched_skip_keyword,
                                    item.title,
                                    item.url,
                                    )
                                continue
                            if not self.store.remember_notified_item_url(subscription["chat_id"], item.url):
                                continue
                            await self.notifier.send_donation_alert(
                                chat_id=subscription["chat_id"],
                                dong_name=subscription["region"]["dong_name"],
                                keyword=subscription["keyword"],
                                product_title=item.title,
                                product_url=item.url,
                            )
                            self.activity_logger.info(
                                "[나눔 알림 발송] chat_id=%s dong=%s keyword=%s title=%s url=%s",
                                subscription["chat_id"],
                                subscription["region"]["dong_name"],
                                subscription["keyword"],
                                item.title,
                                item.url,
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
            except Exception as exc:
                cause = f" (원인: {exc.__cause__})" if getattr(exc, "__cause__", None) else ""
                self.error_logger.error(
                    "[스크래핑 실패] link=%s attempt=%s/%s error=%s%s",
                    detect_link,
                    attempt,
                    self.max_retries,
                    exc,
                    cause,
                )
            else:
                if item is not None:
                    return item
                self.activity_logger.info(
                    "[스크래핑 결과 없음] link=%s attempt=%s/%s (최신 상품 없음)",
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
