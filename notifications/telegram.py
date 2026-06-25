from __future__ import annotations

import logging

from telegram import Bot

from core.query import shorten_daangn_product_url


class TelegramNotifier:
    def __init__(self, bot: Bot, error_logger: logging.Logger) -> None:
        self.bot = bot
        self.error_logger = error_logger

    async def send_donation_alert(
        self,
        chat_id: str,
        dong_name: str,
        keyword: str,
        product_title: str,
        product_url: str,
    ) -> None:
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"[{dong_name}] [{keyword}] 새 나눔 알림:\n"
                    f"{product_title}\n"
                    f"{shorten_daangn_product_url(product_url)}"
                ),
                disable_web_page_preview=False,
            )
        except Exception as exc:
            self.error_logger.error("[텔레그램 메시지 전송 실패] chat_id=%s error=%s", chat_id, exc)
