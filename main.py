"""
Media yuklovchi Telegram bot (aiogram 3.x)

Imkoniyatlar:
  • Instagram va Pinterest yuklash (+ MP3)
  • Kunlik limit, VIP tariflar (7/30/90 kun) — Telegram Stars
  • Donat, referal tizimi, yuklash tarixi
  • Majburiy obuna, 3 tilli interfeys (uz/ru/en)
  • Admin panel: /stats, /users, /ban, /msg, /broadcast, /give_vip, /promo_add, /report ...
  • Kesh (file_id), kunlik bonus, promokodlar, taklif/shikoyat, stikerlar, VIP eslatmasi

Ishga tushirish:  python main.py
"""

import asyncio
import html
import logging
import shutil
import socket
import sys
import tempfile
import time
from urllib.parse import quote

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    ErrorEvent,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    User,
)
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config as cfg
import db
import downloader as dl
import features
from common import (
    IsAdmin,
    detect_lang,
    edit_or_send,
    fmt_row,
    fmt_user,
    get_lang,
    is_admin,
    kb_back,
    spawn,
)
from texts import LANGS, t

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bot")

router = Router()

ACTIVE: set[int] = set()                      # hozir yuklayotgan foydalanuvchilar
DL_SEM = asyncio.Semaphore(cfg.MAX_PARALLEL)  # bir vaqtdagi yuklashlar soni
PENDING_BROADCAST: dict[int, dict] = {}       # admin_id -> tasdiq kutayotgan xabar


# ============================================================================
# BARQAROR TARMOQ SESSIYASI (ulanish uzilsa qayta urinadi)
# ============================================================================
class RetrySession(AiohttpSession):
    RETRIES = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connector_init.update(family=socket.AF_INET, force_close=True)

    async def make_request(self, bot, method, timeout=None):
        last_error = None
        for attempt in range(1, self.RETRIES + 1):
            try:
                return await super().make_request(bot, method, timeout)
            except TelegramNetworkError as e:
                last_error = e
                log.warning("Tarmoq xatosi (%d/%d): %s", attempt, self.RETRIES, e)
                await asyncio.sleep(1.5 * attempt)
        raise last_error


# ============================================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================================
class UserMiddleware(BaseMiddleware):
    """Har bir xabarda foydalanuvchini bazaga yozadi va 'oxirgi faollik'ni yangilaydi."""

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not user.is_bot:
            try:
                # Menyu tugmasi bosilsa, kutilayotgan holat (promokod, taklif...) bekor qilinadi
                if isinstance(event, CallbackQuery) and (event.data or "").startswith("menu:") and data.get("state"):
                    await data["state"].clear()
                is_start = isinstance(event, Message) and (event.text or "").startswith("/start")
                uname, fname = user.username or "", user.full_name
                if not is_start:  # /start da referal bilan alohida ro'yxatdan o'tadi
                    await db.register_user(user.id, 0, detect_lang(user.language_code), uname, fname)
                await db.touch_user(user.id, uname, fname)
            except Exception as e:  # noqa: BLE001
                log.warning("UserMiddleware xatosi: %s", e)
        return await handler(event, data)




# ============================================================================
# KLAVIATURALAR
# ============================================================================
def kb_main(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_download"), callback_data="menu:download")
    kb.button(text=t(lang, "btn_vip"), callback_data="menu:vip")
    kb.button(text=t(lang, "btn_donate"), callback_data="menu:donate")
    kb.button(text=t(lang, "btn_daily"), callback_data="menu:daily")
    kb.button(text=t(lang, "btn_promo"), callback_data="menu:promo")
    kb.button(text=t(lang, "btn_invite"), callback_data="menu:invite")
    kb.button(text=t(lang, "btn_history"), callback_data="menu:history")
    kb.button(text=t(lang, "btn_feedback"), callback_data="menu:feedback")
    kb.button(text=t(lang, "btn_lang"), callback_data="menu:lang")
    kb.adjust(1, 2, 2, 2, 2)
    return kb.as_markup()


def kb_vip(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for days, price in cfg.VIP_PLANS.items():
        kb.button(text=f"⭐ {price} — {days} {t(lang, 'days_word')}", callback_data=f"buyvip:{days}")
    kb.button(text=t(lang, "btn_back"), callback_data="menu:back")
    kb.adjust(1)
    return kb.as_markup()


def kb_donate(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for amount in cfg.DONATE_PRESETS:
        kb.button(text=f"⭐ {amount}", callback_data=f"donate:{amount}")
    kb.button(text=t(lang, "btn_other"), callback_data="donate:custom")
    kb.button(text=t(lang, "btn_back"), callback_data="menu:back")
    kb.adjust(len(cfg.DONATE_PRESETS), 1, 1)
    return kb.as_markup()


def kb_lang(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, title in LANGS.items():
        kb.button(text=title, callback_data=f"lang:{code}")
    kb.button(text=t(lang, "btn_back"), callback_data="menu:back")
    kb.adjust(1)
    return kb.as_markup()


def kb_limit(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_buy_vip"), callback_data="menu:vip")
    kb.button(text=t(lang, "btn_invite"), callback_data="menu:invite")
    kb.adjust(1)
    return kb.as_markup()


def kb_mp3(lang: str, download_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_mp3"), callback_data=f"mp3:{download_id}")
    return kb.as_markup()


def kb_sub(lang: str, channels: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        if ch["link"]:
            kb.button(text=f"📢 {ch['title']}", url=ch["link"])
    kb.button(text=t(lang, "btn_check_sub"), callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()


# ============================================================================
# MAJBURIY OBUNA
# ============================================================================
async def get_missing_channels(bot: Bot, user_id: int) -> list[dict]:
    missing = []
    for ch in cfg.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(ch["chat"], user_id)
            if member.status in ("left", "kicked"):
                missing.append(ch)
            elif member.status == "restricted" and not getattr(member, "is_member", True):
                missing.append(ch)
        except Exception as e:  # noqa: BLE001
            # Bot kanalda admin emas yoki kanal noto'g'ri: foydalanuvchini to'smaymiz
            log.warning("Obunani tekshirib bo'lmadi (%s): %s", ch["chat"], e)
    return missing


async def ensure_subscribed(bot: Bot, user: User, chat_id: int, lang: str) -> bool:
    if not cfg.REQUIRED_CHANNELS or is_admin(user.id):
        return True
    missing = await get_missing_channels(bot, user.id)
    if not missing:
        return True
    await bot.send_message(chat_id, t(lang, "sub_required"), reply_markup=kb_sub(lang, missing))
    return False


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery, bot: Bot) -> None:
    lang = await get_lang(call.from_user)
    missing = await get_missing_channels(bot, call.from_user.id)
    if missing:
        await call.answer(t(lang, "sub_not_yet"), show_alert=True)
        return
    await call.answer(t(lang, "sub_ok"))
    await edit_or_send(call, await welcome_text(call.from_user, lang), kb_main(lang))


# ============================================================================
# /start VA ASOSIY MENYU
# ============================================================================
async def welcome_text(user: User, lang: str) -> str:
    return t(lang, "welcome", name=html.escape(user.full_name), limit=cfg.DAILY_LIMIT)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    user = message.from_user

    # Referal: /start ref_<id>
    ref_id = 0
    if command.args and command.args.startswith("ref_"):
        try:
            ref_id = int(command.args[4:])
        except ValueError:
            ref_id = 0
    if ref_id == user.id or (ref_id and not await db.user_exists(ref_id)):
        ref_id = 0

    await db.register_user(
        user.id, ref_id, detect_lang(user.language_code), user.username or "", user.full_name
    )
    await db.touch_user(user.id, user.username or "", user.full_name)

    lang = await get_lang(user)

    # Majburiy obuna: kanalga a'zo bo'lmasa, menyu o'rniga obuna so'raladi
    if not await ensure_subscribed(bot, user, message.chat.id, lang):
        return

    text = await welcome_text(user, lang)
    try:
        if cfg.START_PHOTO:
            await message.answer_photo(cfg.START_PHOTO, caption=text, reply_markup=kb_main(lang))
            return
    except Exception as e:  # noqa: BLE001
        log.warning("Start rasmini yuborib bo'lmadi: %s", e)
    await message.answer(text, reply_markup=kb_main(lang))


@router.callback_query(F.data == "menu:back")
async def cb_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await get_lang(call.from_user)
    await edit_or_send(call, await welcome_text(call.from_user, lang), kb_main(lang))
    await call.answer()


@router.callback_query(F.data == "menu:download")
async def cb_download(call: CallbackQuery) -> None:
    lang = await get_lang(call.from_user)
    q = await db.get_quota(call.from_user.id, cfg.DAILY_LIMIT)
    if q["vip"]:
        status = t(lang, "status_vip")
    else:
        status = t(lang, "status_free", used=q["used"], limit=q["limit"], bonus=q["bonus"])
    await edit_or_send(call, t(lang, "download_info", status=status), kb_back(lang))
    await call.answer()


# ---------------------------------------------------------------- Til
@router.callback_query(F.data == "menu:lang")
async def cb_lang_menu(call: CallbackQuery) -> None:
    lang = await get_lang(call.from_user)
    await edit_or_send(call, t(lang, "lang_choose"), kb_lang(lang))
    await call.answer()


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_lang(call: CallbackQuery) -> None:
    code = call.data.split(":", 1)[1]
    if code not in LANGS:
        await call.answer()
        return
    await db.set_lang(call.from_user.id, code)
    await edit_or_send(call, await welcome_text(call.from_user, code), kb_main(code))
    await call.answer(t(code, "lang_changed"))


# ---------------------------------------------------------------- Tarix
@router.callback_query(F.data == "menu:history")
async def cb_history(call: CallbackQuery) -> None:
    lang = await get_lang(call.from_user)
    rows = await db.get_history(call.from_user.id, 10)
    if not rows:
        text = t(lang, "history_empty")
    else:
        kind_icon = {"video": "🎬", "image": "🖼", "audio": "🎵"}
        lines = []
        for r in rows:
            emoji = dl.PLATFORM_EMOJI.get(r["platform"], "🔗")
            title = dl.PLATFORM_TITLE.get(r["platform"], r["platform"])
            url = html.escape(r["url"], quote=True)
            date = cfg.fmt_date(r["created_at"], "%d.%m %H:%M")
            lines.append(f'{emoji} <a href="{url}">{title}</a> {kind_icon.get(r["kind"], "")} · {date}')
        text = t(lang, "history_title", items="\n".join(lines))
    await edit_or_send(call, text, kb_back(lang))
    await call.answer()


# ---------------------------------------------------------------- Referal
@router.callback_query(F.data == "menu:invite")
async def cb_invite(call: CallbackQuery, bot: Bot) -> None:
    lang = await get_lang(call.from_user)
    uid = call.from_user.id
    link = await create_start_link(bot, f"ref_{uid}")
    stats = await db.get_ref_stats(uid)
    text = t(
        lang,
        "ref_info",
        link=link,
        bonus=cfg.REF_BONUS_DOWNLOADS,
        milestone=cfg.REF_MILESTONE,
        vip_days=cfg.REF_MILESTONE_VIP_DAYS,
        count=stats["count"],
        pending=stats["pending"],
        balance=stats["balance"],
    )
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(t(lang, 'ref_share_text'))}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "btn_share"), url=share_url))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:back"))
    await edit_or_send(call, text, kb.as_markup())
    await call.answer()


async def reward_referrer(bot: Bot, invitee_id: int) -> None:
    """Taklif qilingan do'st birinchi yuklaganda taklif qilganga bonus beradi."""
    res = await db.confirm_referral(invitee_id)
    if not res:
        return
    referrer_id, count = res
    await db.add_bonus(referrer_id, cfg.REF_BONUS_DOWNLOADS)
    row = await db.get_user(referrer_id)
    lang = (row["lang"] if row and row["lang"] else "uz")
    text = t(lang, "ref_reward", n=cfg.REF_BONUS_DOWNLOADS)
    if cfg.REF_MILESTONE and count % cfg.REF_MILESTONE == 0:
        await db.grant_vip(referrer_id, cfg.REF_MILESTONE_VIP_DAYS)
        text += "\n\n" + t(lang, "ref_milestone", count=count, days=cfg.REF_MILESTONE_VIP_DAYS)
    try:
        await bot.send_message(referrer_id, text)
    except Exception as e:  # noqa: BLE001
        log.info("Referrerga xabar yuborib bo'lmadi: %s", e)


# ============================================================================
# YUKLASH
# ============================================================================
ADMIN_HINTS = {
    "blocked": "Instagram login so'rayapti: <code>cookies.txt</code> qo'shing (DEPLOY.md, 8-bo'lim) "
               "va yt-dlp ni yangilang.",
    "unavailable": "Havola noto'g'ri, video o'chirilgan yoki yopiq bo'lishi mumkin.",
    "too_long": ".env da MAX_VIDEO_SECONDS ni oshirishingiz mumkin (lekin 50 MB limit bor).",
}


def extract_file(msg: Message) -> tuple[str, str] | None:
    """Yuborilgan xabardan (media_turi, file_id) ni oladi — keshga yozish uchun."""
    if msg.video:
        return "video", msg.video.file_id
    if msg.animation:
        return "animation", msg.animation.file_id
    if msg.photo:
        return "photo", msg.photo[-1].file_id
    if msg.audio:
        return "audio", msg.audio.file_id
    if msg.document:
        return "document", msg.document.file_id
    return None


KIND_BY_TYPE = {"video": "video", "animation": "video", "photo": "image", "audio": "audio", "document": "image"}


async def send_cached(
    bot: Bot, chat_id: int, entries: list[tuple[str, str]], caption: str, lang: str, download_id: int, platform: str
) -> bool:
    """Keshdagi file_id lar bilan yuboradi (qayta yuklamasdan). Muvaffaqiyatli bo'lsa True."""
    sent = 0
    for media_type, file_id in entries:
        try:
            if media_type == "video":
                markup = kb_mp3(lang, download_id) if (sent == 0 and platform != "pinterest") else None
                await bot.send_video(chat_id, file_id, caption=caption, reply_markup=markup, supports_streaming=True)
            elif media_type == "animation":
                await bot.send_animation(chat_id, file_id, caption=caption)
            elif media_type == "photo":
                await bot.send_photo(chat_id, file_id, caption=caption)
            elif media_type == "audio":
                await bot.send_audio(chat_id, file_id, caption=caption)
            else:
                await bot.send_document(chat_id, file_id, caption=caption)
            sent += 1
        except Exception as e:  # noqa: BLE001
            log.warning("Keshdagi fayl yuborilmadi (%s)", e)
            if sent == 0:
                return False
            break
    return sent > 0


async def finish_download(bot: Bot, chat_id: int, uid: int, lang: str, status: Message | None = None) -> None:
    """Muvaffaqiyatli yuklashdan keyin: limitdan ayirish, referal bonusi, qolgan limit xabari."""
    await db.consume_download(uid, cfg.DAILY_LIMIT)
    await reward_referrer(bot, uid)
    if status:
        try:
            await status.delete()
        except Exception:  # noqa: BLE001
            pass
    after = await db.get_quota(uid, cfg.DAILY_LIMIT)
    if not after["vip"]:
        await bot.send_message(chat_id, t(lang, "left", left=after["left"]))


async def run_download(
    bot: Bot, chat_id: int, user: User, url: str, platform: str, lang: str, audio: bool = False
) -> None:
    uid = user.id
    if uid in ACTIVE:
        await bot.send_message(chat_id, t(lang, "busy"))
        return

    quota = await db.get_quota(uid, cfg.DAILY_LIMIT)
    if not quota["allowed"]:
        await bot.send_message(
            chat_id, t(lang, "limit_reached", limit=cfg.DAILY_LIMIT), reply_markup=kb_limit(lang)
        )
        return

    ACTIVE.add(uid)
    tmp_dir: str | None = None
    status: Message | None = None
    mode = "audio" if audio else "media"
    key = dl.url_key(url)
    try:
        bot_username = (await bot.me()).username
        caption = t(lang, "done_audio" if audio else "done", bot=bot_username)

        # --- 1) Keshdan: avval yuborilgan fayl bo'lsa, qayta yuklamaymiz (tez va xavfsiz)
        cached = await db.cache_get(key, mode)
        if cached:
            kind = KIND_BY_TYPE.get(cached[0][0], "image")
            download_id = await db.log_download(uid, url, platform, kind, cached=True)
            if await send_cached(bot, chat_id, cached, caption, lang, download_id, platform):
                await finish_download(bot, chat_id, uid, lang)
                return
            await db.delete_download(download_id)
            await db.cache_delete(key, mode)  # file_id yaroqsiz bo'lib qolgan

        # --- 2) Yuklash
        tmp_dir = tempfile.mkdtemp(prefix="dl_")
        status = await bot.send_message(chat_id, t(lang, "audio_processing" if audio else "processing"))

        try:
            async with DL_SEM:
                files = await asyncio.wait_for(
                    asyncio.to_thread(dl.download_media, url, tmp_dir, platform, audio),
                    timeout=cfg.DOWNLOAD_TIMEOUT,
                )
        except dl.DownloadFailed as e:
            msg = t(lang, f"fail_{e.reason}", minutes=cfg.MAX_VIDEO_SECONDS // 60)
            if is_admin(uid):  # admin sababni aniq ko'radi
                msg += f"\n\n🛠 <b>{e.reason}</b>\n<code>{html.escape(e.detail or '-')}</code>"
                hint = ADMIN_HINTS.get(e.reason)
                if hint:
                    msg += f"\n💡 {hint}"
            await status.edit_text(msg)
            return

        if not files:
            key_name = "audio_fail" if audio else "not_found"
            await status.edit_text(t(lang, key_name, minutes=cfg.MAX_VIDEO_SECONDS // 60))
            return

        first_ext = files[0].suffix.lower()
        kind = "audio" if audio else ("video" if first_ext in dl.VIDEO_EXT else "image")
        download_id = await db.log_download(uid, url, platform, kind)

        sent = 0
        entries: list[tuple[str, str]] = []
        for f in files:
            if f.stat().st_size > cfg.MAX_FILE_SIZE:
                await bot.send_message(chat_id, t(lang, "too_big"))
                continue
            ext = f.suffix.lower()
            try:
                if audio:
                    result = await bot.send_audio(chat_id, FSInputFile(f), caption=caption)
                elif ext in dl.VIDEO_EXT:
                    # MP3 tugmasi faqat birinchi videoga (Pinterest'da audio ma'nosiz)
                    markup = kb_mp3(lang, download_id) if (sent == 0 and platform != "pinterest") else None
                    result = await bot.send_video(
                        chat_id, FSInputFile(f), caption=caption, reply_markup=markup,
                        supports_streaming=True,
                    )
                else:
                    result = await bot.send_photo(chat_id, FSInputFile(f), caption=caption)
                sent += 1
            except Exception as e:  # noqa: BLE001
                log.warning("Fayl yuborishda xato (%s), hujjat sifatida urinamiz", e)
                try:
                    result = await bot.send_document(chat_id, FSInputFile(f), caption=caption)
                    sent += 1
                except Exception as e2:  # noqa: BLE001
                    log.error("Hujjat sifatida ham yuborilmadi: %s", e2)
                    continue
            info = extract_file(result) if isinstance(result, Message) else None
            if info:
                entries.append(info)

        if not sent:
            await status.edit_text(t(lang, "send_failed"))
            return

        # Keshga yozamiz (faqat hamma fayl muvaffaqiyatli yuborilgan bo'lsa)
        if entries and len(entries) == sent == len(files):
            try:
                await db.cache_put(key, mode, entries)
            except Exception as e:  # noqa: BLE001
                log.warning("Keshga yozib bo'lmadi: %s", e)

        await finish_download(bot, chat_id, uid, lang, status)

    except Exception as e:  # noqa: BLE001
        log.exception("run_download xatosi: %s", e)
        try:
            msg = t(lang, "error_generic")
            if status:
                await status.edit_text(msg)
            else:
                await bot.send_message(chat_id, msg)
        except Exception:  # noqa: BLE001
            pass
    finally:
        ACTIVE.discard(uid)
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


@router.message(F.text.func(dl.has_supported_url))
async def handle_link(message: Message, bot: Bot) -> None:
    user = message.from_user
    lang = await get_lang(user)
    url = dl.extract_url(message.text)
    platform = dl.detect_platform(url) if url else None
    if not platform:
        await message.answer(t(lang, "unsupported"))
        return
    if not await ensure_subscribed(bot, user, message.chat.id, lang):
        return
    await run_download(bot, message.chat.id, user, url, platform, lang)


@router.callback_query(F.data.startswith("mp3:"))
async def cb_mp3(call: CallbackQuery, bot: Bot) -> None:
    user = call.from_user
    lang = await get_lang(user)
    try:
        download_id = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer()
        return
    row = await db.get_download(download_id)
    if not row or row["user_id"] != user.id:
        await call.answer(t(lang, "audio_expired"), show_alert=True)
        return
    await call.answer()
    if not await ensure_subscribed(bot, user, call.message.chat.id, lang):
        return
    await run_download(bot, call.message.chat.id, user, row["url"], row["platform"], lang, audio=True)


# ============================================================================
# VIP OBUNA (Telegram Stars)
# ============================================================================
@router.callback_query(F.data == "menu:vip")
async def cb_vip(call: CallbackQuery) -> None:
    lang = await get_lang(call.from_user)
    q = await db.get_quota(call.from_user.id, cfg.DAILY_LIMIT)
    if q["vip"]:
        status = t(lang, "vip_active", date=cfg.fmt_date(q["vip_until"]))
    else:
        status = t(lang, "vip_inactive")
    await edit_or_send(call, t(lang, "vip_info", status=status), kb_vip(lang))
    await call.answer()


@router.callback_query(F.data.startswith("buyvip:"))
async def cb_buy_vip(call: CallbackQuery) -> None:
    lang = await get_lang(call.from_user)
    try:
        days = int(call.data.split(":", 1)[1])
        price = cfg.VIP_PLANS[days]
        await call.message.answer_invoice(
            title=t(lang, "inv_vip_title"),
            description=t(lang, "inv_vip_desc", days=days),
            payload=f"vip:{days}",
            currency="XTR",  # Telegram Stars
            prices=[LabeledPrice(label=t(lang, "inv_vip_label", days=days), amount=price)],
        )
        await call.answer()
    except Exception as e:  # noqa: BLE001
        log.exception("VIP invoice xatosi: %s", e)
        await call.answer(t(lang, "invoice_error"), show_alert=True)


# ============================================================================
# DONAT (Telegram Stars)
# ============================================================================
class DonateState(StatesGroup):
    waiting_amount = State()


async def send_donate_invoice(message: Message, lang: str, amount: int) -> None:
    await message.answer_invoice(
        title=t(lang, "inv_donate_title"),
        description=t(lang, "inv_donate_desc"),
        payload=f"donate:{amount}",
        currency="XTR",
        prices=[LabeledPrice(label=t(lang, "inv_donate_label"), amount=amount)],
    )


@router.callback_query(F.data == "menu:donate")
async def cb_donate(call: CallbackQuery) -> None:
    lang = await get_lang(call.from_user)
    await edit_or_send(call, t(lang, "donate_info"), kb_donate(lang))
    await call.answer()


@router.callback_query(F.data.startswith("donate:"))
async def cb_donate_amount(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user)
    value = call.data.split(":", 1)[1]
    try:
        if value == "custom":
            await state.set_state(DonateState.waiting_amount)
            await call.message.answer(t(lang, "donate_prompt", min=cfg.MIN_DONATE, max=cfg.MAX_DONATE))
        else:
            await send_donate_invoice(call.message, lang, int(value))
        await call.answer()
    except Exception as e:  # noqa: BLE001
        log.exception("Donat xatosi: %s", e)
        await call.answer(t(lang, "invoice_error"), show_alert=True)


@router.message(StateFilter(DonateState.waiting_amount), F.text, ~F.text.startswith("/"))
async def donate_custom_amount(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user)
    text = (message.text or "").strip()
    if not text.isdigit() or not (cfg.MIN_DONATE <= int(text) <= cfg.MAX_DONATE):
        await message.answer(t(lang, "donate_invalid", min=cfg.MIN_DONATE, max=cfg.MAX_DONATE))
        return
    try:
        await state.clear()
        await send_donate_invoice(message, lang, int(text))
    except Exception as e:  # noqa: BLE001
        log.exception("Donat invoice xatosi: %s", e)
        await message.answer(t(lang, "invoice_error"))


# ============================================================================
# TO'LOVNI TASDIQLASH
# ============================================================================
@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    """To'lovdan oldin 10 soniya ichida javob berish SHART. Summani ham tekshiramiz."""
    ok = False
    try:
        kind, _, value = query.invoice_payload.partition(":")
        if kind == "vip" and value.isdigit():
            ok = cfg.VIP_PLANS.get(int(value)) == query.total_amount
        elif kind == "donate" and value.isdigit():
            ok = int(value) == query.total_amount and cfg.MIN_DONATE <= query.total_amount <= cfg.MAX_DONATE
    except Exception as e:  # noqa: BLE001
        log.exception("pre_checkout tekshiruv xatosi: %s", e)
    try:
        if ok:
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="Invalid payment / Noto'g'ri to'lov")
    except Exception as e:  # noqa: BLE001
        log.exception("pre_checkout javob xatosi: %s", e)


@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot) -> None:
    pay = message.successful_payment
    user = message.from_user
    lang = await get_lang(user)
    payload, stars, charge_id = pay.invoice_payload, pay.total_amount, pay.telegram_payment_charge_id
    kind = "unknown"

    try:
        if payload.startswith("vip:"):
            kind = "vip"
            days = int(payload.split(":")[1])
            until = await db.grant_vip(user.id, days)
            await db.save_payment(user.id, kind, stars, charge_id)
            await features.celebrate(bot, message.chat.id, "vip")  # stiker (sozlangan bo'lsa)
            await message.answer(t(lang, "pay_vip_ok", date=cfg.fmt_date(until)))
        elif payload.startswith("donate:"):
            kind = "donate"
            await db.save_payment(user.id, kind, stars, charge_id)
            await features.celebrate(bot, message.chat.id, "donate")  # stiker (sozlangan bo'lsa)
            await message.answer(t(lang, "pay_donate_ok", stars=stars))
        else:
            await db.save_payment(user.id, kind, stars, charge_id)
            await message.answer(t(lang, "pay_unknown"))
    except Exception as e:  # noqa: BLE001
        log.exception("successful_payment xatosi: %s", e)
        await message.answer(t(lang, "pay_error", charge=charge_id))

    # Adminlarga bildirishnoma
    for admin_id in cfg.ADMIN_IDS:
        try:
            if kind in ("vip", "donate"):
                await features.celebrate(bot, admin_id, kind)  # adminga ham stiker + matn
            await bot.send_message(
                admin_id,
                f"💰 Yangi to'lov: <b>{stars} ⭐</b> ({kind})\n"
                f"👤 {fmt_user(user.id, user.username or '', user.full_name)}\n"
                f"🧾 <code>{charge_id}</code>",
            )
        except Exception:  # noqa: BLE001
            pass


@router.message(Command("paysupport"))
async def cmd_paysupport(message: Message) -> None:
    """Telegram qoidasi: Stars qabul qiladigan bot /paysupport'ni qo'llashi kerak."""
    lang = await get_lang(message.from_user)
    await message.answer(t(lang, "paysupport"))


# ============================================================================
# ADMIN PANEL
# ============================================================================
ADMIN_HELP = (
    "🛠 <b>Admin buyruqlar</b>\n\n"
    "<b>Statistika</b>\n"
    "/stats — umumiy statistika\n"
    "/report — bugungi hisobot (har kuni avtomatik ham keladi)\n"
    "/users — foydalanuvchilar (ism · @username · ID)\n"
    "/vips — faol VIP'lar\n"
    "/user &lt;ID yoki @username&gt; — foydalanuvchi ma'lumoti\n\n"
    "<b>Boshqaruv</b>\n"
    "/give_vip &lt;ID yoki @username&gt; &lt;kun&gt; — VIP berish\n"
    "/remove_vip &lt;ID yoki @username&gt; — VIP olib tashlash\n"
    "/ban &lt;ID yoki @username&gt; [sabab] · /unban · /banned\n"
    "/msg &lt;ID yoki @username&gt; matn — foydalanuvchiga xabar\n"
    "/broadcast &lt;matn&gt; — hammaga (yoki xabarga reply qilib)\n"
    "/refund &lt;user_id&gt; &lt;charge_id&gt; — Stars qaytarish\n\n"
    "<b>Promokodlar</b>\n"
    "/promo_add · /promo_list · /promo_del\n\n"
    "<b>Boshqa</b>\n"
    "/stickers — donat/VIP stikerlari (o'rnatish: botga stiker yuboring)\n"
    "/checksub — majburiy obuna sozlamasini tekshirish\n"
    "Taklif/shikoyatga javob: xabarga <i>reply</i> qiling"
)


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(message: Message) -> None:
    await message.answer(ADMIN_HELP)


@router.message(Command("stats"), IsAdmin())
async def cmd_stats(message: Message) -> None:
    s = await db.get_stats()
    platforms = "\n".join(
        f"   {dl.PLATFORM_EMOJI.get(p, '🔗')} {dl.PLATFORM_TITLE.get(p, p)}: {c}" for p, c in s["platforms"]
    ) or "   —"
    vip_cnt, vip_stars = s["income"].get("vip", (0, 0))
    don_cnt, don_stars = s["income"].get("donate", (0, 0))

    top_dl = await db.top_downloaders(5)
    top_ref = await db.top_referrers(5)
    top_dl_txt = "\n".join(f"   {i}. {fmt_user(u, un, fn)} — <b>{c}</b>" for i, (u, un, fn, c) in enumerate(top_dl, 1)) or "   —"
    top_ref_txt = "\n".join(f"   {i}. {fmt_user(u, un, fn)} — <b>{c}</b>" for i, (u, un, fn, c) in enumerate(top_ref, 1)) or "   —"

    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b> (botni bloklagan: {s['blocked']})\n"
        f"🆕 Bugun yangi: <b>{s['new_today']}</b>\n"
        f"🔥 Bugun faol: <b>{s['active_today']}</b>\n"
        f"💎 Faol VIP: <b>{s['vip']}</b>\n\n"
        f"📥 Yuklashlar: jami <b>{s['dl_total']}</b>, bugun <b>{s['dl_today']}</b> (⚡ keshdan: {s['dl_cached']})\n{platforms}\n\n"
        f"💰 Daromad:\n"
        f"   💎 VIP: <b>{vip_stars} ⭐</b> ({vip_cnt} ta)\n"
        f"   ❤️ Donat: <b>{don_stars} ⭐</b> ({don_cnt} ta)\n"
        f"   Jami: <b>{vip_stars + don_stars} ⭐</b>\n\n"
        f"🏆 <b>Eng ko'p yuklaganlar</b>\n{top_dl_txt}\n\n"
        f"🤝 <b>Eng ko'p do'st taklif qilganlar</b>\n{top_ref_txt}"
    )


# ---------------------------------------------------------------- Foydalanuvchilar ro'yxati
USERS_PER_PAGE = 15


async def users_page(page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    total = await db.count_users()
    pages = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = min(max(1, page), pages)
    rows = await db.list_users((page - 1) * USERS_PER_PAGE, USERS_PER_PAGE)
    start = (page - 1) * USERS_PER_PAGE
    lines = [f"{start + i}. {fmt_row(r)}" for i, r in enumerate(rows, 1)]
    text = (
        f"👥 <b>Foydalanuvchilar</b>: {total} ta — sahifa {page}/{pages}\n"
        "<i>(💎 VIP, 🚫 botni bloklagan; yangilari birinchi)</i>\n\n" + ("\n".join(lines) or "—")
    )
    kb = InlineKeyboardBuilder()
    if page > 1:
        kb.button(text="⬅️", callback_data=f"users:{page - 1}")
    if page < pages:
        kb.button(text="➡️", callback_data=f"users:{page + 1}")
    kb.adjust(2)
    return text, (kb.as_markup() if (page > 1 or page < pages) else None)


@router.message(Command("users"), IsAdmin())
async def cmd_users(message: Message, command: CommandObject) -> None:
    page = int(command.args) if command.args and command.args.strip().isdigit() else 1
    text, markup = await users_page(page)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("users:"), IsAdmin())
async def cb_users(call: CallbackQuery) -> None:
    try:
        page = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer()
        return
    text, markup = await users_page(page)
    try:
        await call.message.edit_text(text, reply_markup=markup)
    except Exception:  # noqa: BLE001
        pass
    await call.answer()


@router.message(Command("vips"), IsAdmin())
async def cmd_vips(message: Message) -> None:
    rows = await db.list_vips()
    if not rows:
        await message.answer("💎 Hozircha faol VIP yo'q.")
        return
    lines = [f"{i}. {fmt_row(r)} — {cfg.fmt_date(r['vip_until'])} gacha" for i, r in enumerate(rows[:50], 1)]
    extra = f"\n\n… va yana {len(rows) - 50} ta" if len(rows) > 50 else ""
    await message.answer(f"💎 <b>Faol VIP'lar</b>: {len(rows)} ta\n\n" + "\n".join(lines) + extra)


# ---------------------------------------------------------------- VIP boshqaruvi
@router.message(Command("give_vip"), IsAdmin())
async def cmd_give_vip(message: Message, command: CommandObject, bot: Bot) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[1].isdigit() or int(parts[1]) <= 0:
        await message.answer("Format: /give_vip &lt;ID yoki @username&gt; &lt;kun&gt;")
        return
    row = await db.find_user(parts[0])
    if not row:
        await message.answer("❌ Bunday foydalanuvchi bazada yo'q (u botga kamida bir marta /start bosgan bo'lishi kerak).")
        return
    uid, days = row["user_id"], int(parts[1])
    until = await db.grant_vip(uid, days)
    await message.answer(
        f"✅ {fmt_row(row)}\n💎 {days} kun VIP berildi (tugashi: {cfg.fmt_date(until)})."
    )
    try:
        await bot.send_message(uid, t(row["lang"] or "uz", "vip_gift", days=days, date=cfg.fmt_date(until)))
    except Exception:  # noqa: BLE001
        pass


@router.message(Command("remove_vip"), IsAdmin())
async def cmd_remove_vip(message: Message, command: CommandObject) -> None:
    row = await db.find_user(command.args or "")
    if not row:
        await message.answer("Format: /remove_vip &lt;ID yoki @username&gt; (foydalanuvchi bazada bo'lishi kerak)")
        return
    await db.remove_vip(row["user_id"])
    await message.answer(f"✅ {fmt_row(row)}\nVIP olib tashlandi.")


@router.message(Command("user"), IsAdmin())
async def cmd_user(message: Message, command: CommandObject) -> None:
    row = await db.find_user(command.args or "")
    if not row:
        await message.answer("Format: /user &lt;ID yoki @username&gt; (foydalanuvchi bazada bo'lishi kerak)")
        return
    uid = row["user_id"]
    q = await db.get_quota(uid, cfg.DAILY_LIMIT)
    hist = await db.get_history(uid, 1000)
    vip = f"✅ {cfg.fmt_date(q['vip_until'])} gacha" if q["vip"] else "❌"
    inviter = "—"
    if row["referrer_id"]:
        ref = await db.get_user(row["referrer_id"])
        inviter = fmt_row(ref) if ref else f"<code>{row['referrer_id']}</code>"
    await message.answer(
        f"👤 {fmt_row(row)}\n"
        f"🌐 Til: {row['lang'] or '—'}\n"
        f"💎 VIP: {vip}\n"
        f"📥 Bugun: {q['used']}/{q['limit']}, bonus: {q['bonus']}\n"
        f"📚 Jami yuklashlar: {len(hist)}\n"
        f"👥 Taklif qilgan do'stlar: {row['ref_count']}\n"
        f"🔗 Kim taklif qilgan: {inviter}\n"
        f"📅 Ro'yxatdan o'tgan: {cfg.fmt_date(row['created_at']) if row['created_at'] else '—'}"
    )


@router.message(Command("checksub"), IsAdmin())
async def cmd_checksub(message: Message, bot: Bot) -> None:
    """
    Majburiy obuna to'g'ri sozlanganini tekshiradi va foydalanuvchi ko'radigan
    xabarni adminga ham ko'rsatadi (adminlar obunadan ozod bo'lgani uchun).
    """
    if not cfg.REQUIRED_CHANNELS:
        await message.answer(
            "ℹ️ Majburiy obuna <b>o'chiq</b>.\n"
            ".env da <code>REQUIRED_CHANNELS=@kanalingiz</code> yozilganini tekshiring "
            "(fayl nomi aynan <code>.env</code> bo'lsin) va botni qayta ishga tushiring."
        )
        return
    me = await bot.me()
    lines = []
    for ch in cfg.REQUIRED_CHANNELS:
        title = html.escape(str(ch["title"]))
        try:
            chat = await bot.get_chat(ch["chat"])
            member = await bot.get_chat_member(ch["chat"], me.id)
            if member.status in ("administrator", "creator"):
                lines.append(f"✅ {title} («{html.escape(chat.title or '')}»): bot admin, tekshiruv ishlaydi")
            else:
                lines.append(f"⚠️ {title}: bot kanalda admin emas (holat: {member.status}). Botni admin qiling!")
        except Exception as e:  # noqa: BLE001
            lines.append(f"❌ {title}: {html.escape(str(e))}")
    await message.answer(
        "🔎 <b>Majburiy obuna tekshiruvi</b>\n\n" + "\n".join(lines)
        + "\n\nObuna bo'lmagan foydalanuvchi quyidagini ko'radi 👇"
    )
    lang = await get_lang(message.from_user)
    await bot.send_message(
        message.chat.id, t(lang, "sub_required"), reply_markup=kb_sub(lang, cfg.REQUIRED_CHANNELS)
    )


@router.message(Command("refund"), IsAdmin())
async def cmd_refund(message: Message, command: CommandObject, bot: Bot) -> None:
    try:
        user_id, charge_id = (command.args or "").split()
        await bot.refund_star_payment(user_id=int(user_id), telegram_payment_charge_id=charge_id)
        await message.answer("✅ Qaytarildi.")
    except Exception as e:  # noqa: BLE001
        await message.answer(f"Xato: {html.escape(str(e))}\nFormat: /refund &lt;user_id&gt; &lt;charge_id&gt;")


# ---------------------------------------------------------------- Broadcast
@router.message(Command("broadcast"), IsAdmin())
async def cmd_broadcast(message: Message, command: CommandObject) -> None:
    admin_id = message.from_user.id
    if message.reply_to_message:
        src = message.reply_to_message
        PENDING_BROADCAST[admin_id] = {"mode": "copy", "chat_id": src.chat.id, "message_id": src.message_id}
    elif command.args:
        PENDING_BROADCAST[admin_id] = {"mode": "text", "text": command.args}
    else:
        await message.answer("Format: /broadcast &lt;matn&gt; yoki biror xabarga reply qilib /broadcast")
        return
    total = len(await db.get_all_user_ids(active_only=True))
    kb = InlineKeyboardBuilder()
    kb.button(text=f"✅ Yuborish ({total})", callback_data="bc:yes")
    kb.button(text="❌ Bekor qilish", callback_data="bc:no")
    kb.adjust(2)
    await message.answer(f"📣 Xabar <b>{total}</b> ta faol foydalanuvchiga yuboriladi. Tasdiqlaysizmi?", reply_markup=kb.as_markup())


@router.callback_query(F.data.in_({"bc:yes", "bc:no"}), IsAdmin())
async def cb_broadcast_confirm(call: CallbackQuery, bot: Bot) -> None:
    admin_id = call.from_user.id
    job = PENDING_BROADCAST.pop(admin_id, None)
    if call.data == "bc:no" or not job:
        await call.message.edit_text("❌ Bekor qilindi." if call.data == "bc:no" else "⚠️ Xabar topilmadi, qayta urinib ko'ring.")
        await call.answer()
        return
    await call.message.edit_text("🚀 Yuborish boshlandi...")
    await call.answer()
    spawn(run_broadcast(bot, admin_id, job))


async def run_broadcast(bot: Bot, admin_id: int, job: dict) -> None:
    ids = await db.get_all_user_ids(active_only=True)
    sent = blocked = failed = 0

    async def send_one(uid: int) -> None:
        if job["mode"] == "copy":
            await bot.copy_message(uid, job["chat_id"], job["message_id"])
        else:
            await bot.send_message(uid, job["text"])

    for uid in ids:
        try:
            try:
                await send_one(uid)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
                await send_one(uid)
            sent += 1
        except TelegramForbiddenError:
            blocked += 1
            await db.mark_inactive(uid)
        except Exception as e:  # noqa: BLE001
            failed += 1
            log.info("Broadcast xatosi (%s): %s", uid, e)
        await asyncio.sleep(0.05)  # ~20 xabar/soniya (Telegram limitidan past)

    try:
        await bot.send_message(
            admin_id,
            f"✅ <b>Broadcast tugadi</b>\n\n📨 Yuborildi: {sent}\n🚫 Bloklagan: {blocked}\n⚠️ Xato: {failed}",
        )
    except Exception:  # noqa: BLE001
        pass


# ============================================================================
# QOLGAN XABARLAR VA XATOLAR
# ============================================================================
@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    if isinstance(event.exception, TelegramNetworkError):
        log.error("Tarmoq xatosi (Telegram bilan aloqa yo'q). VPN/internetni tekshiring.")
    else:
        log.exception("Handler xatosi: %s", event.exception)
    return True


fallback_router = Router()  # eng oxirida tekshiriladi


@fallback_router.message(F.text)
async def fallback(message: Message) -> None:
    lang = await get_lang(message.from_user)
    await message.answer(t(lang, "fallback"))


# ============================================================================
# ISHGA TUSHIRISH
# ============================================================================
async def setup_commands(bot: Bot) -> None:
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Menu / Меню / Bosh menyu"),
            BotCommand(command="promo", description="Promo code / Промокод / Promokod"),
            BotCommand(command="paysupport", description="Payment help / Помощь с оплатой"),
        ])
        for admin_id in cfg.ADMIN_IDS:
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Bosh menyu"),
                    BotCommand(command="admin", description="Admin buyruqlar"),
                    BotCommand(command="stats", description="Statistika"),
                    BotCommand(command="users", description="Foydalanuvchilar ro'yxati"),
                    BotCommand(command="vips", description="Faol VIP'lar"),
                    BotCommand(command="broadcast", description="Hammaga xabar"),
                    BotCommand(command="give_vip", description="VIP berish"),
                    BotCommand(command="checksub", description="Majburiy obunani tekshirish"),
                    BotCommand(command="report", description="Bugungi hisobot"),
                    BotCommand(command="ban", description="Foydalanuvchini bloklash"),
                    BotCommand(command="msg", description="Foydalanuvchiga xabar"),
                    BotCommand(command="promo_add", description="Promokod yaratish"),
                    BotCommand(command="stickers", description="Donat/VIP stikerlari"),
                ],
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
    except Exception as e:  # noqa: BLE001
        log.warning("Buyruqlarni o'rnatib bo'lmadi: %s", e)


async def check_channels_on_start(bot: Bot) -> None:
    """Ishga tushganda majburiy obuna holatini logga yozadi va botning kanalda adminligini tekshiradi."""
    if not cfg.REQUIRED_CHANNELS:
        log.info("Majburiy obuna: O'CHIQ (.env da REQUIRED_CHANNELS bo'sh yoki yo'q)")
        return
    log.info("Majburiy obuna: YOQILGAN → %s", ", ".join(str(c["chat"]) for c in cfg.REQUIRED_CHANNELS))
    try:
        me = await bot.me()
    except Exception as e:  # noqa: BLE001
        log.warning("Kanallarni tekshirib bo'lmadi: %s", e)
        return
    for ch in cfg.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(ch["chat"], me.id)
            if member.status in ("administrator", "creator"):
                log.info("   ✅ %s: bot admin, tekshiruv ishlaydi", ch["chat"])
            else:
                log.warning("   ⚠️ %s: bot kanalda ADMIN EMAS (%s) — obuna tekshirilmaydi!", ch["chat"], member.status)
        except Exception as e:  # noqa: BLE001
            log.warning("   ❌ %s: %s", ch["chat"], e)


def build_dispatcher() -> Dispatcher:
    """Routerlar tartibi: asosiy → qo'shimcha funksiyalar → fallback (oxirida)."""
    dp = Dispatcher()
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(features.AntiSpamInstance)  # spam / ban
        observer.outer_middleware(UserMiddleware())            # ism, @username, faollik
    dp.include_router(router)
    dp.include_router(features.router)
    dp.include_router(fallback_router)
    return dp


async def main() -> None:
    if not cfg.BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN topilmadi! Bot papkasida '.env' fayli bo'lishi kerak "
            "('.env' EMAS) va ichida BOT_TOKEN=... yozilgan bo'lsin."
        )

    await db.init_db(cfg.DB_PATH)
    session = RetrySession(proxy=cfg.PROXY_URL or None, timeout=60)
    bot = Bot(
        token=cfg.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dp = build_dispatcher()
    await features.load_banned()

    log.info("Bot ishga tushdi ✅ | ffmpeg: %s | adminlar: %s", dl.HAS_FFMPEG, sorted(cfg.ADMIN_IDS))
    if not dl.HAS_FFMPEG:
        log.warning("ffmpeg topilmadi: MP3 tugmasi ishlamasligi mumkin (Windows: winget install Gyan.FFmpeg --source winget).")
    tasks = []
    try:
        await check_channels_on_start(bot)
        await setup_commands(bot)
        tasks = features.start_background(bot)  # VIP eslatmasi, kundalik hisobot
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for task in tasks:
            task.cancel()
        await bot.session.close()
        await db.close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot to'xtatildi.")
    except SystemExit as e:
        if e.code not in (None, 0):
            log.error("%s", e.code)  # sabab ko'rinsin (masalan, token topilmadi)
