"""
Umumiy yordamchilar: main.py va features.py ikkalasi ham shu yerdan foydalanadi.
"""

import asyncio
import html
import logging
import time

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config as cfg
import db
from texts import t

log = logging.getLogger("bot")

BG_TASKS: set[asyncio.Task] = set()  # fon vazifalari (GC dan himoya)


def spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    BG_TASKS.add(task)
    task.add_done_callback(BG_TASKS.discard)
    return task


def detect_lang(code: str | None) -> str:
    code = (code or "").lower()
    if code.startswith("ru"):
        return "ru"
    if code.startswith("en"):
        return "en"
    return "uz"


async def get_lang(user: User) -> str:
    row = await db.get_user(user.id)
    if row and row["lang"]:
        return row["lang"]
    return detect_lang(user.language_code)


def is_admin(user_id: int) -> bool:
    return user_id in cfg.ADMIN_IDS


class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return bool(event.from_user and is_admin(event.from_user.id))


def fmt_user(user_id: int, username: str = "", full_name: str = "") -> str:
    """Admin uchun: bosiladigan ism · @username · chat ID."""
    name = html.escape(full_name or "—")
    uname = f"@{html.escape(username)}" if username else "—"
    return f'<a href="tg://user?id={user_id}">{name}</a> · {uname} · <code>{user_id}</code>'


def fmt_row(row) -> str:
    """Bazadagi qator uchun: fmt_user + belgilar (💎 VIP, 🚫 bloklagan/ban)."""
    marks = ""
    if row["vip_until"] > time.time():
        marks += " 💎"
    if not row["is_active"]:
        marks += " 📴"
    if row["banned"]:
        marks += " 🚫"
    return fmt_user(row["user_id"], row["username"], row["full_name"]) + marks


def kb_back(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_back"), callback_data="menu:back")
    return kb.as_markup()


async def edit_or_send(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    """Xabarni tahrirlaydi (rasmli bo'lsa caption), bo'lmasa yangisini yuboradi."""
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text, reply_markup=markup)
        else:
            await call.message.edit_text(text, reply_markup=markup)
    except Exception:  # noqa: BLE001
        await call.message.answer(text, reply_markup=markup)
