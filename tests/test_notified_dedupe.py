from __future__ import annotations

import asyncio
import logging
import tempfile
import unittest
from pathlib import Path

from core import Region, ScrapedItem
from monitoring import DonationMonitor
from storage import JsonStore


class FakeScraper:
    def fetch_latest_item(self, detect_link: str) -> ScrapedItem:
        return ScrapedItem(title="free chair", url="https://www.daangn.com/articles/12345")


class FakeNotifier:
    def __init__(self) -> None:
        self.alerts: list[dict[str, str]] = []

    async def send_donation_alert(self, chat_id: str, dong_name: str, keyword: str, product_url: str) -> None:
        self.alerts.append(
            {"chat_id": chat_id, "dong_name": dong_name, "keyword": keyword, "product_url": product_url}
        )


class NotifiedDedupeTest(unittest.TestCase):
    def test_same_user_same_product_from_overlapping_regions_sends_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = JsonStore(root / "users.json", root / "areas.json", root / "scrape_state.json")
            store.ensure_user("42")
            store.add_region("42", Region("서울 금천구 독산동", "295"))
            store.add_region("42", Region("서울 금천구 독산제1동", "296"))

            notifier = FakeNotifier()
            monitor = DonationMonitor(
                store=store,
                scraper=FakeScraper(),
                notifier=notifier,
                activity_logger=logging.getLogger("test.activity"),
                error_logger=logging.getLogger("test.error"),
                max_retries=1,
            )

            asyncio.run(monitor.run_once())

            self.assertEqual(1, len(notifier.alerts))
            self.assertEqual("42", notifier.alerts[0]["chat_id"])
            self.assertEqual("https://www.daangn.com/articles/12345", notifier.alerts[0]["product_url"])


if __name__ == "__main__":
    unittest.main()
