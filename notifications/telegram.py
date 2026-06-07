from __future__ import annotations

import logging

from telegram import Bot


class TelegramNotifier:
    def __init__(self, bot: Bot, error_logger: logging.Logger) -> None:
        self.bot = bot
        self.error_logger = error_logger

    async def send_donation_alert(self, chat_id: str, dong_name: str, keyword: str, product_url: str) -> None:
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "[당근마켓 나눔 탐지 알림]\n"
                    f"{dong_name}에서 {keyword} 관련 나눔 상품이 올라왔습니다!\n"
                    f"링크: {product_url}"
                ),
                disable_web_page_preview=False,
            )
        except Exception as exc:
            self.error_logger.error("[텔레그램 메시지 전송 실패] chat_id=%s error=%s", chat_id, exc)
