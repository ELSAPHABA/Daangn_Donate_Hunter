from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.models import ALL_KEYWORD
from core.query import normalize_keyword, normalize_user_query_text
from storage import JsonStore


CHOOSING, ADD_REGION, DELETE_REGION, ADD_KEYWORD, DELETE_KEYWORD, ADD_SKIP_KEYWORD, DELETE_SKIP_KEYWORD = range(7)

BTN_REGION_MENU: Final = "탐지 동네 설정"
BTN_REGION_LIST: Final = "탐지 동네 조회"
BTN_REGION_ADD: Final = "탐지 동네 추가"
BTN_REGION_DELETE: Final = "탐지 동네 삭제"
BTN_KEYWORD_MENU: Final = "탐지 키워드 설정"
BTN_KEYWORD_LIST: Final = "탐지 키워드 조회"
BTN_KEYWORD_ADD: Final = "탐지 키워드 추가"
BTN_KEYWORD_DELETE: Final = "탐지 키워드 삭제"
BTN_SKIP_KEYWORD_MENU: Final = "제외 키워드 설정"
BTN_SKIP_KEYWORD_LIST: Final = "제외 키워드 조회"
BTN_SKIP_KEYWORD_ADD: Final = "제외 키워드 추가"
BTN_SKIP_KEYWORD_DELETE: Final = "제외 키워드 삭제"
BTN_NOTIFICATION: Final = "알림 설정"
BTN_BACK: Final = "돌아가기"
BTN_ERROR_LOG: Final = "오류 로그 조회"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_REGION_MENU, BTN_KEYWORD_MENU], [BTN_SKIP_KEYWORD_MENU, BTN_NOTIFICATION]],
        resize_keyboard=True,
    )


def region_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_REGION_LIST, BTN_REGION_ADD], [BTN_REGION_DELETE, BTN_BACK]],
        resize_keyboard=True,
    )


def region_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[BTN_BACK]], resize_keyboard=True)


def keyword_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_KEYWORD_LIST, BTN_KEYWORD_ADD], [BTN_KEYWORD_DELETE, BTN_BACK]],
        resize_keyboard=True,
    )


def keyword_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[ALL_KEYWORD], [BTN_BACK]], resize_keyboard=True)


def skip_keyword_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_SKIP_KEYWORD_LIST, BTN_SKIP_KEYWORD_ADD], [BTN_SKIP_KEYWORD_DELETE, BTN_BACK]],
        resize_keyboard=True,
    )


def skip_keyword_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[BTN_BACK]], resize_keyboard=True)


class DaangnBot:
    def __init__(
        self,
        store: JsonStore,
        activity_logger: logging.Logger,
        error_logger: logging.Logger,
        error_log_path: Path | None = None,
        admin_chat_ids: set[str] | None = None,
    ) -> None:
        self.store = store
        self.activity_logger = activity_logger
        self.error_logger = error_logger
        self.error_log_path = error_log_path
        self.admin_chat_ids = admin_chat_ids or set()

    def register(self, application: Application) -> None:
        conversation = ConversationHandler(
            entry_points=[
                CommandHandler("settings", self.settings),
                CommandHandler("areasetting", self.area_setting),
                CommandHandler("areaview", self.area_view),
                CommandHandler("areaadd", self.area_add),
                CommandHandler("areadelete", self.area_delete),
                CommandHandler("kwdsetting", self.keyword_setting),
                CommandHandler("kwdview", self.keyword_view),
                CommandHandler("kwdadd", self.keyword_add),
                CommandHandler("kwddelete", self.keyword_delete),
                CommandHandler("skipkwdsetting", self.skip_keyword_setting),
                CommandHandler("skipkwdview", self.skip_keyword_view),
                CommandHandler("skipkwdadd", self.skip_keyword_add),
                CommandHandler("skipkwddelete", self.skip_keyword_delete),
                CommandHandler("arlam", self.notification_setting),
                MessageHandler(
                    filters.Regex(f"^{BTN_REGION_MENU}$|^{BTN_KEYWORD_MENU}$|^{BTN_SKIP_KEYWORD_MENU}$|^{BTN_NOTIFICATION}$"),
                    self.handle_choice,
                ),
            ],
            states={
                CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_choice)],
                ADD_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_region)],
                DELETE_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.delete_region)],
                ADD_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_keyword)],
                DELETE_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.delete_keyword)],
                ADD_SKIP_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_skip_keyword)],
                DELETE_SKIP_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.delete_skip_keyword)],
            },
            fallbacks=[
                CommandHandler("start", self.start),
                CommandHandler("help", self.help),
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), self.settings),
            ],
            allow_reentry=True,
        )
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("manage", self.manage))
        application.add_handler(conversation)
        application.add_handler(MessageHandler(filters.Regex(f"^{BTN_ERROR_LOG}$"), self.reply_error_log))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id = update.effective_chat.id
        self.store.ensure_user(chat_id)
        await update.message.reply_text(
            "당근마켓에서 동네의 나눔 상품을 탐지합니다. 탐지 동네 및 키워드, 알림을 설정하시려면 /settings를, 도움말은 /help를 입력해 주세요.",
            reply_markup=main_keyboard(),
        )
        return CHOOSING

    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await update.message.reply_text("설정할 항목을 선택하세요.", reply_markup=main_keyboard())
        return CHOOSING

    async def area_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await update.message.reply_text("탐지 동네 설정을 선택하세요.", reply_markup=region_keyboard())
        return CHOOSING

    async def area_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await self._reply_region_list(update)
        return CHOOSING

    async def area_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await update.message.reply_text(
            "추가하실 동네 주소 또는 동네 번호를 입력해 주세요.",
            reply_markup=region_input_keyboard(),
        )
        return ADD_REGION

    async def area_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        user = self.store.get_user(update.effective_chat.id) or {}
        regions = user.get("regions", [])
        if not regions:
            await update.message.reply_text("탐지중인 동네가 없습니다.", reply_markup=region_keyboard())
            return CHOOSING
        await update.message.reply_text(
            "삭제하실 동네를 선택하세요.",
            reply_markup=ReplyKeyboardMarkup([[item["full_name"]] for item in regions] + [[BTN_BACK]], resize_keyboard=True),
        )
        return DELETE_REGION

    async def keyword_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await update.message.reply_text("탐지 키워드 설정을 선택하세요.", reply_markup=keyword_keyboard())
        return CHOOSING

    async def keyword_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await self._reply_keyword_list(update)
        return CHOOSING

    async def keyword_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await update.message.reply_text(
            "추가하실 키워드를 입력해 주세요. 전체 탐지는 전체를 선택하세요.",
            reply_markup=keyword_input_keyboard(),
        )
        return ADD_KEYWORD

    async def keyword_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        user = self.store.get_user(update.effective_chat.id) or {}
        keywords = user.get("keywords", [])
        if not keywords:
            await update.message.reply_text("탐지중인 키워드가 없습니다.", reply_markup=keyword_keyboard())
            return CHOOSING
        await update.message.reply_text(
            "삭제하실 키워드를 선택하세요.",
            reply_markup=ReplyKeyboardMarkup([[item] for item in keywords] + [[BTN_BACK]], resize_keyboard=True),
        )
        return DELETE_KEYWORD

    async def skip_keyword_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await update.message.reply_text("제외 키워드 설정을 선택하세요.", reply_markup=skip_keyword_keyboard())
        return CHOOSING

    async def skip_keyword_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await self._reply_skip_keyword_list(update)
        return CHOOSING

    async def skip_keyword_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        await update.message.reply_text(
            "추가하실 제외 키워드를 입력해 주세요.",
            reply_markup=skip_keyword_input_keyboard(),
        )
        return ADD_SKIP_KEYWORD

    async def skip_keyword_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.store.ensure_user(update.effective_chat.id)
        user = self.store.get_user(update.effective_chat.id) or {}
        skip_keywords = user.get("skip_keywords", [])
        if not skip_keywords:
            await update.message.reply_text("제외 키워드가 없습니다.", reply_markup=skip_keyword_keyboard())
            return CHOOSING
        await update.message.reply_text(
            "삭제하실 제외 키워드를 선택하세요.",
            reply_markup=ReplyKeyboardMarkup([[item] for item in skip_keywords] + [[BTN_BACK]], resize_keyboard=True),
        )
        return DELETE_SKIP_KEYWORD

    async def notification_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        chat_id = update.effective_chat.id
        user = self.store.get_user(chat_id) or self.store.ensure_user(chat_id)
        enabled = not bool(user.get("notification", True))
        self.store.set_notification(chat_id, enabled)
        self.activity_logger.info("[%s] [알림 설정 변경] %s", chat_id, "시작" if enabled else "중지")
        await update.message.reply_text(f"알림을 {'시작' if enabled else '중지'}했습니다.", reply_markup=main_keyboard())
        return CHOOSING

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "/settings: 탐지 및 알림 설정\n"
            "/help: 도움말"
        )

    async def manage(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await update.message.reply_text("관리자만 사용할 수 있는 메뉴입니다.", reply_markup=main_keyboard())
            return
        await update.message.reply_text("관리 메뉴입니다.", reply_markup=ReplyKeyboardMarkup([[BTN_ERROR_LOG]], resize_keyboard=True))

    async def reply_error_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await update.message.reply_text("관리자만 사용할 수 있는 메뉴입니다.", reply_markup=main_keyboard())
            return
        if not self.error_log_path or not self.error_log_path.exists():
            await update.message.reply_text("기록된 오류 로그가 없습니다.", reply_markup=main_keyboard())
            return
        lines = self.error_log_path.read_text(encoding="utf-8").splitlines()[-20:]
        await update.message.reply_text("\n".join(lines) if lines else "기록된 오류 로그가 없습니다.", reply_markup=main_keyboard())

    async def handle_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text
        chat_id = update.effective_chat.id
        self.store.ensure_user(chat_id)
        if text == BTN_REGION_MENU:
            return await self.area_setting(update, context)
        if text == BTN_REGION_LIST:
            return await self.area_view(update, context)
        if text == BTN_REGION_ADD:
            return await self.area_add(update, context)
        if text == BTN_REGION_DELETE:
            return await self.area_delete(update, context)
        if text == BTN_KEYWORD_MENU:
            return await self.keyword_setting(update, context)
        if text == BTN_KEYWORD_LIST:
            return await self.keyword_view(update, context)
        if text == BTN_KEYWORD_ADD:
            return await self.keyword_add(update, context)
        if text == BTN_KEYWORD_DELETE:
            return await self.keyword_delete(update, context)
        if text == BTN_SKIP_KEYWORD_MENU:
            return await self.skip_keyword_setting(update, context)
        if text == BTN_SKIP_KEYWORD_LIST:
            return await self.skip_keyword_view(update, context)
        if text == BTN_SKIP_KEYWORD_ADD:
            return await self.skip_keyword_add(update, context)
        if text == BTN_SKIP_KEYWORD_DELETE:
            return await self.skip_keyword_delete(update, context)
        if text == BTN_NOTIFICATION:
            return await self.notification_setting(update, context)
        if text == BTN_ERROR_LOG:
            await self.reply_error_log(update, context)
            return CHOOSING
        if text == BTN_BACK:
            await update.message.reply_text("설정 메뉴로 돌아갑니다.", reply_markup=main_keyboard())
            return CHOOSING
        await update.message.reply_text("메뉴에서 항목을 선택해 주세요.", reply_markup=main_keyboard())
        return CHOOSING

    async def add_region(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == BTN_BACK:
            return await self.settings(update, context)
        chat_id = update.effective_chat.id
        cleaned = normalize_user_query_text(update.message.text)
        if cleaned is None:
            await update.message.reply_text(
                "동네 입력이 비어 있거나 너무 깁니다. 다시 입력해 주세요.",
                reply_markup=region_input_keyboard(),
            )
            return ADD_REGION
        matches = self.store.find_regions(cleaned)
        if not matches:
            await update.message.reply_text(
                "해당되는 동네 주소 또는 번호가 없습니다. 다시 입력해 주세요.",
                reply_markup=region_input_keyboard(),
            )
            return ADD_REGION
        if len(matches) > 1:
            display_limit = 20
            displayed_matches = matches[:display_limit]
            lines = "\n".join(f"- {region.full_name}" for region in displayed_matches)
            if len(matches) > display_limit:
                lines += f"\n외 {len(matches) - display_limit}개"
            await update.message.reply_text(
                (
                    f"해당되는 동네가 {len(matches)}개 있습니다:\n"
                    f"{lines}\n"
                    "추가하실 동네를 입력해 주세요."
                ),
                reply_markup=region_input_keyboard(),
            )
            return ADD_REGION
        region = matches[0]
        if not self.store.add_region(chat_id, region):
            await update.message.reply_text("이미 탐지중인 동네입니다. 다시 입력해 주세요.", reply_markup=region_input_keyboard())
            return ADD_REGION
        self.activity_logger.info("[%s] [탐지 동네 추가] %s", chat_id, region.full_name)
        await update.message.reply_text(f"{region.full_name}이 추가되었습니다.", reply_markup=region_keyboard())
        return CHOOSING

    async def delete_region(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == BTN_BACK:
            return await self.settings(update, context)
        chat_id = update.effective_chat.id
        user = self.store.get_user(chat_id) or {}
        region = next((item for item in user.get("regions", []) if item["full_name"] == update.message.text), None)
        if not region:
            await update.message.reply_text("해당되는 동네가 없습니다. 다시 입력해주세요.", reply_markup=region_keyboard())
            return CHOOSING
        removed = self.store.remove_region(chat_id, str(region["code"]))
        if removed:
            self.activity_logger.info("[%s] [탐지 동네 삭제] %s", chat_id, removed.full_name)
            await update.message.reply_text(f"{removed.full_name}이 삭제되었습니다.", reply_markup=region_keyboard())
        return CHOOSING

    async def add_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == BTN_BACK:
            return await self.settings(update, context)
        chat_id = update.effective_chat.id
        cleaned = normalize_user_query_text(update.message.text)
        if cleaned is None:
            await update.message.reply_text(
                "키워드 입력이 비어 있거나 너무 깁니다. 다시 입력해 주세요.",
                reply_markup=keyword_input_keyboard(),
            )
            return ADD_KEYWORD
        keyword = normalize_keyword(cleaned)
        if not self.store.add_keyword(chat_id, keyword):
            await update.message.reply_text("이미 탐지중인 키워드입니다. 다시 입력해 주세요.", reply_markup=keyword_input_keyboard())
            return ADD_KEYWORD
        self.activity_logger.info("[%s] [탐지 키워드 추가] %s", chat_id, keyword)
        message = "전체를 탐지합니다." if keyword == ALL_KEYWORD else f"{keyword}가 추가되었습니다."
        await update.message.reply_text(message, reply_markup=keyword_keyboard())
        return CHOOSING

    def _is_admin(self, update: Update) -> bool:
        return bool(self.admin_chat_ids and str(update.effective_chat.id) in self.admin_chat_ids)

    async def delete_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == BTN_BACK:
            return await self.settings(update, context)
        chat_id = update.effective_chat.id
        keyword = normalize_user_query_text(update.message.text)
        if keyword is None:
            await update.message.reply_text("키워드를 다시 입력해 주세요.", reply_markup=keyword_keyboard())
            return CHOOSING
        if not self.store.remove_keyword(chat_id, keyword):
            await update.message.reply_text("해당 키워드는 탐지중이지 않습니다.", reply_markup=keyword_keyboard())
            return CHOOSING
        self.activity_logger.info("[%s] [탐지 키워드 삭제] %s", chat_id, keyword)
        message = "전체 탐지가 해제되었습니다." if keyword == ALL_KEYWORD else f"{keyword}가 삭제되었습니다."
        await update.message.reply_text(message, reply_markup=keyword_keyboard())
        return CHOOSING

    async def add_skip_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == BTN_BACK:
            return await self.settings(update, context)
        chat_id = update.effective_chat.id
        keyword = normalize_user_query_text(update.message.text)
        if keyword is None:
            await update.message.reply_text("제외 키워드를 다시 입력해 주세요.", reply_markup=skip_keyword_input_keyboard())
            return ADD_SKIP_KEYWORD
        if not self.store.add_skip_keyword(chat_id, keyword):
            await update.message.reply_text("이미 등록된 제외 키워드입니다. 다시 입력해 주세요.", reply_markup=skip_keyword_input_keyboard())
            return ADD_SKIP_KEYWORD
        self.activity_logger.info("[%s] [제외 키워드 추가] %s", chat_id, keyword)
        await update.message.reply_text(f"{keyword}가 추가되었습니다.", reply_markup=skip_keyword_keyboard())
        return CHOOSING

    async def delete_skip_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == BTN_BACK:
            return await self.settings(update, context)
        chat_id = update.effective_chat.id
        keyword = normalize_user_query_text(update.message.text)
        if keyword is None:
            await update.message.reply_text("제외 키워드를 다시 입력해 주세요.", reply_markup=skip_keyword_keyboard())
            return CHOOSING
        if not self.store.remove_skip_keyword(chat_id, keyword):
            await update.message.reply_text("해당 제외 키워드는 등록되어 있지 않습니다.", reply_markup=skip_keyword_keyboard())
            return CHOOSING
        self.activity_logger.info("[%s] [제외 키워드 삭제] %s", chat_id, keyword)
        await update.message.reply_text(f"{keyword}가 삭제되었습니다.", reply_markup=skip_keyword_keyboard())
        return CHOOSING

    async def _reply_region_list(self, update: Update) -> None:
        user = self.store.get_user(update.effective_chat.id) or {}
        regions = user.get("regions", [])
        if not regions:
            await update.message.reply_text("현재 탐지중인 동네가 없습니다.", reply_markup=region_keyboard())
            return
        lines = "\n".join(f"- {item['full_name']}" for item in regions)
        await update.message.reply_text(f"현재 탐지중인 동네입니다:\n{lines}", reply_markup=region_keyboard())

    async def _reply_keyword_list(self, update: Update) -> None:
        user = self.store.get_user(update.effective_chat.id) or {}
        keywords = user.get("keywords", [])
        if not keywords:
            await update.message.reply_text("현재 탐지중인 키워드가 없습니다.", reply_markup=keyword_keyboard())
            return
        lines = "\n".join(f"- {item}" for item in keywords)
        await update.message.reply_text(f"현재 탐지중인 키워드입니다:\n{lines}", reply_markup=keyword_keyboard())

    async def _reply_skip_keyword_list(self, update: Update) -> None:
        user = self.store.get_user(update.effective_chat.id) or {}
        skip_keywords = user.get("skip_keywords", [])
        if not skip_keywords:
            await update.message.reply_text("현재 제외 키워드가 없습니다.", reply_markup=skip_keyword_keyboard())
            return
        lines = "\n".join(f"- {item}" for item in skip_keywords)
        await update.message.reply_text(f"현재 제외 키워드입니다:\n{lines}", reply_markup=skip_keyword_keyboard())
