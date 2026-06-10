from __future__ import annotations

import asyncio
import logging

from scraping import AreaNumberMismatch, DaangnScraper
from storage import JsonStore


class AreaDatabaseCollector:
    def __init__(
        self,
        store: JsonStore,
        scraper: DaangnScraper,
        activity_logger: logging.Logger,
        error_logger: logging.Logger,
        initial_start_number: int = 11,
        delay_seconds: int = 10,
        mismatch_stop_threshold: int = 30,
    ) -> None:
        self.store = store
        self.scraper = scraper
        self.activity_logger = activity_logger
        self.error_logger = error_logger
        self.initial_start_number = max(1, initial_start_number)
        self.delay_seconds = delay_seconds
        self.mismatch_stop_threshold = max(1, mismatch_stop_threshold)
        self._lock = asyncio.Lock()

    async def collect_from_next_number(self) -> None:
        if self._lock.locked():
            self.activity_logger.info("[동네DB 수집] 이미 실행 중이어서 이번 실행을 건너뜁니다.")
            return
        async with self._lock:
            last_area_number = self.store.get_last_area_number()
            start_number = (
                last_area_number + 1
                if last_area_number > 0
                else self.initial_start_number
            )
            self.activity_logger.info(
                (
                    "[동네DB 수집 준비] last_area_number=%s start_number=%s "
                    "initial_start_number=%s mismatch_stop_threshold=%s"
                ),
                last_area_number,
                start_number,
                self.initial_start_number,
                self.mismatch_stop_threshold,
            )
            await self._collect_until_mismatch(start_number)

    async def _collect_until_mismatch(self, start_number: int) -> None:
        number = start_number
        collected_count = 0
        consecutive_mismatch_count = 0
        self.activity_logger.info("[동네DB 수집 시작] start_number=%s", start_number)
        while True:
            try:
                area_name = await asyncio.to_thread(self.scraper.fetch_area_name, number)
            except AreaNumberMismatch as exc:
                consecutive_mismatch_count += 1
                self.activity_logger.info(
                    "[동네DB 수집 불일치] number=%s consecutive_mismatch_count=%s threshold=%s reason=%s",
                    number,
                    consecutive_mismatch_count,
                    self.mismatch_stop_threshold,
                    exc,
                )
                if consecutive_mismatch_count >= self.mismatch_stop_threshold:
                    self.store.set_last_area_number(number)
                    self.activity_logger.info(
                        (
                            "[동네DB 수집 종료] stop_number=%s collected=%s "
                            "consecutive_mismatch_count=%s"
                        ),
                        number,
                        collected_count,
                        consecutive_mismatch_count,
                    )
                    return
            except Exception as exc:
                self.error_logger.error("[동네DB 수집 실패] number=%s error=%s", number, exc)
                return
            else:
                if not area_name:
                    self.error_logger.error("[동네DB 수집 실패] number=%s error=동네 이름을 찾지 못했습니다.", number)
                    return
                consecutive_mismatch_count = 0
                self.store.upsert_areas({area_name: str(number)}, number)
                collected_count += 1
                self.activity_logger.info("[동네DB 수집] %s:%s", area_name, number)
            number += 1
            await asyncio.sleep(self.delay_seconds)
