"""
Qo'shimcha funksiyalar (alohida Router):
  • Spamdan himoya + /ban /unban /banned
  • Kunlik bonus
  • Promokodlar (foydalanuvchi + admin)
  • Taklif/shikoyat va admin javobi, /msg
  • Donat/VIP uchun stikerlar
  • VIP tugashi eslatmasi va kundalik hisobot (fon vazifalari)
"""

import asyncio
import html
import logging
import math
import re
import secrets
import time
from collections import deque
from datetime import timedelta

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandObject, Filter, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config as cfg
import db
import downloader as dl
from common import IsAdmin, edit_or_send, fmt_row, fmt_user, get_lang, is_admin, kb_back, spawn
from texts import t

log = logging.getLogger("bot")
router = Router()


# ============================================================================
# SPAMDAN HIMOYA VA BAN
# ============================================================================
BANNED: set[int] = set()


async def load_banned() -> None:
    BANNED.clear()
    BANNED.update(await db.banned_ids())


class AntiSpamMiddleware(BaseMiddleware):
    """
    1) Bloklangan (ban) foydalanuvchilarni to'xtatadi.
    2) Juda tez-tez harakat qilganni vaqtincha to'xtatadi; takrorlansa — avtomatik ban.
    Adminlar va to'lov tasdig'i (successful_payment) hech qachon to'silmaydi.
    """

    def __init__(self) -> None:
        self.events: dict[int, deque] = {}
        self.blocked_until: dict[int, float] = {}
        self.strikes: dict[int, list[float]] = {}
        self.notice_at: dict[tuple[int, str], float] = {}

    async def _notify(self, event, user, key: str, every: float, **kw) -> None:
        now = time.monotonic()
        if now - self.notice_at.get((user.id, key), -1e9) < every:
            return
        self.notice_at[(user.id, key)] = now
        row = await db.get_user(user.id)
        lang = row["lang"] if row and row["lang"] else "uz"
        text = t(lang, key, **kw)
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(text)
        except Exception:  # noqa: BLE001
            pass

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if not user or user.is_bot or is_admin(user.id):
            return await handler(event, data)
        if isinstance(event, Message) and event.successful_payment:
            return await handler(event, data)

        if user.id in BANNED:
            await self._notify(event, user, "banned_notice", every=600)
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer()
                except Exception:  # noqa: BLE001
                    pass
            return None

        now = time.monotonic()
        if self.blocked_until.get(user.id, 0) > now:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer()
                except Exception:  # noqa: BLE001
                    pass
            return None

        if cfg.SPAM_LIMIT > 0:
            q = self.events.setdefault(user.id, deque())
            q.append(now)
            while q and now - q[0] > cfg.SPAM_WINDOW:
                q.popleft()
            if len(q) > cfg.SPAM_LIMIT:
                q.clear()
                self.blocked_until[user.id] = now + cfg.SPAM_BLOCK_SECONDS
                await self._notify(event, user, "spam_wait", every=0, sec=cfg.SPAM_BLOCK_SECONDS)
                await self._strike(data["bot"], user)
                return None
            if len(self.events) > 5000:  # xotirani tozalash
                self.events = {k: v for k, v in self.events.items() if v and now - v[-1] <= cfg.SPAM_WINDOW}
        return await handler(event, data)

    async def _strike(self, bot: Bot, user) -> None:
        now = time.monotonic()
        hits = [x for x in self.strikes.get(user.id, []) if now - x < 3600] + [now]
        self.strikes[user.id] = hits
        log.warning("Spam: %s (%s) — %d-marta to'xtatildi", user.id, user.username, len(hits))
        if cfg.SPAM_AUTOBAN_STRIKES and len(hits) >= cfg.SPAM_AUTOBAN_STRIKES:
            await db.set_banned(user.id, True, "spam (avtomatik)")
            BANNED.add(user.id)
            for admin_id in cfg.ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"🚫 <b>Avto-ban (spam)</b>\n{fmt_user(user.id, user.username or '', user.full_name)}\n"
                        f"Qaytarish: <code>/unban {user.id}</code>",
                    )
                except Exception:  # noqa: BLE001
                    pass


@router.message(Command("ban"), IsAdmin())
async def cmd_ban(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").split(maxsplit=1)
    row = await db.find_user(parts[0]) if parts else None
    if not row:
        await message.answer("Format: /ban &lt;ID yoki @username&gt; [sabab]\n(foydalanuvchi bazada bo'lishi kerak)")
        return
    if is_admin(row["user_id"]):
        await message.answer("❌ Adminni bloklab bo'lmaydi.")
        return
    reason = parts[1] if len(parts) > 1 else "admin"
    await db.set_banned(row["user_id"], True, reason)
    BANNED.add(row["user_id"])
    await message.answer(f"🚫 Bloklandi: {fmt_user(row['user_id'], row['username'], row['full_name'])}\nSabab: {html.escape(reason)}")


@router.message(Command("unban"), IsAdmin())
async def cmd_unban(message: Message, command: CommandObject) -> None:
    row = await db.find_user(command.args or "")
    if not row:
        await message.answer("Format: /unban &lt;ID yoki @username&gt;")
        return
    await db.set_banned(row["user_id"], False)
    BANNED.discard(row["user_id"])
    AntiSpamInstance.reset(row["user_id"])
    await message.answer(f"✅ Blokdan chiqarildi: {fmt_user(row['user_id'], row['username'], row['full_name'])}")


@router.message(Command("banned"), IsAdmin())
async def cmd_banned(message: Message) -> None:
    rows = await db.list_banned()
    if not rows:
        await message.answer("🚫 Bloklanganlar yo'q.")
        return
    lines = [f"{i}. {fmt_row(r)} — {html.escape(r['ban_reason'] or '-')}" for i, r in enumerate(rows[:50], 1)]
    await message.answer(f"🚫 <b>Bloklanganlar</b>: {len(rows)} ta\n\n" + "\n".join(lines))


def _make_antispam() -> AntiSpamMiddleware:
    mw = AntiSpamMiddleware()

    def reset(user_id: int) -> None:
        mw.blocked_until.pop(user_id, None)
        mw.strikes.pop(user_id, None)
        mw.events.pop(user_id, None)

    mw.reset = reset  # type: ignore[attr-defined]
    return mw


AntiSpamInstance = _make_antispam()   # main.build_dispatcher() shuni ulaydi


# ============================================================================
# KUNLIK BONUS
# ============================================================================
@router.callback_query(F.data == "menu:daily")
async def cb_daily(call: CallbackQuery) -> None:
    lang = await get_lang(call.from_user)
    res = await db.claim_daily_bonus(
        call.from_user.id, cfg.today_str(), cfg.yesterday_str(),
        cfg.DAILY_BONUS, cfg.DAILY_BONUS_STREAK_EVERY, cfg.DAILY_BONUS_STREAK_EXTRA,
    )
    if res is None:
        text = t(lang, "daily_already")
    else:
        text = t(
            lang, "daily_ok", n=res[0], streak=res[1],
            every=cfg.DAILY_BONUS_STREAK_EVERY, extra=cfg.DAILY_BONUS_STREAK_EXTRA,
        )
    await edit_or_send(call, text, kb_back(lang))
    await call.answer()


# ============================================================================
# PROMOKODLAR
# ============================================================================
class PromoState(StatesGroup):
    waiting = State()


PROMO_FAILS: dict[int, list[float]] = {}


def _promo_blocked(uid: int) -> bool:
    now = time.monotonic()
    fails = [x for x in PROMO_FAILS.get(uid, []) if now - x < 600]
    PROMO_FAILS[uid] = fails
    return len(fails) >= cfg.PROMO_MAX_FAILS


async def redeem_and_reply(message: Message, lang: str, code: str) -> str:
    """Promokodni ishlatadi va natijani yuboradi. Status qaytaradi."""
    uid = message.from_user.id
    if _promo_blocked(uid):
        await message.answer(t(lang, "promo_too_many"))
        return "blocked"
    status, kind, amount = await db.redeem_promo(code, uid)
    if status == "ok":
        if kind == "vip":
            until = await db.grant_vip(uid, amount)
            await message.answer(t(lang, "promo_ok_vip", days=amount, date=cfg.fmt_date(until)))
        else:
            await db.add_bonus(uid, amount)
            await message.answer(t(lang, "promo_ok_bonus", n=amount))
    else:
        if status == "not_found":
            PROMO_FAILS.setdefault(uid, []).append(time.monotonic())
        await message.answer(t(lang, f"promo_{status}"))
    return status


@router.callback_query(F.data == "menu:promo")
async def cb_promo(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user)
    await state.set_state(PromoState.waiting)
    await edit_or_send(call, t(lang, "promo_prompt"), kb_back(lang))
    await call.answer()


@router.message(StateFilter(PromoState.waiting), F.text, ~F.text.startswith("/"))
async def promo_text(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user)
    status = await redeem_and_reply(message, lang, message.text)
    if status != "not_found":  # xato yozgan bo'lsa, qayta urinib ko'rishi mumkin
        await state.clear()


@router.message(Command("promo"))
async def cmd_promo(message: Message, command: CommandObject, state: FSMContext) -> None:
    lang = await get_lang(message.from_user)
    if command.args:
        await redeem_and_reply(message, lang, command.args.split()[0])
    else:
        await state.set_state(PromoState.waiting)
        await message.answer(t(lang, "promo_prompt"))


@router.message(Command("promo_add"), IsAdmin())
async def cmd_promo_add(message: Message, command: CommandObject) -> None:
    usage = (
        "Format:\n<code>/promo_add &lt;KOD|auto&gt; &lt;vip|bonus&gt; &lt;miqdor&gt; &lt;necha kishi&gt; [necha kun amal qiladi]</code>\n\n"
        "Masalan:\n<code>/promo_add auto vip 7 50</code> — 7 kun VIP, 50 kishiga\n"
        "<code>/promo_add YANGI10 bonus 10 0 30</code> — 10 bonus yuklash, cheksiz kishiga, 30 kun amal qiladi"
    )
    parts = (command.args or "").split()
    if len(parts) not in (4, 5):
        await message.answer(usage)
        return
    code_arg, kind = parts[0], parts[1].lower()
    if kind not in ("vip", "bonus") or not all(p.isdigit() for p in parts[2:]):
        await message.answer(usage)
        return
    amount, max_uses = int(parts[2]), int(parts[3])
    days_valid = int(parts[4]) if len(parts) == 5 else 0
    if amount <= 0:
        await message.answer(usage)
        return
    expires_at = int(time.time()) + days_valid * 86400 if days_valid else 0

    if code_arg.lower() == "auto":
        code = ""
        for _ in range(10):
            candidate = secrets.token_hex(3).upper()
            if await db.create_promo(candidate, kind, amount, max_uses, expires_at):
                code = candidate
                break
        if not code:
            await message.answer("❌ Kod yaratib bo'lmadi, qayta urinib ko'ring.")
            return
    else:
        code = code_arg.upper()
        if not re.fullmatch(r"[A-Z0-9_-]{3,32}", code):
            await message.answer("❌ Kod faqat lotin harflari, raqam, _ va - dan iborat bo'lsin (3–32 belgi).")
            return
        if not await db.create_promo(code, kind, amount, max_uses, expires_at):
            await message.answer("❌ Bunday kod allaqachon mavjud.")
            return

    what = f"💎 {amount} kun VIP" if kind == "vip" else f"🎁 {amount} bonus yuklash"
    who = f"{max_uses} kishiga" if max_uses else "cheksiz kishiga"
    until = f", {cfg.fmt_date(expires_at)} gacha" if expires_at else ""
    await message.answer(
        f"✅ <b>Promokod yaratildi</b>: <code>{code}</code>\n{what} · {who}{until}\n\n"
        f"Foydalanuvchi: menyuda 🎟 Promokod tugmasi yoki <code>/promo {code}</code>"
    )


@router.message(Command("promo_list"), IsAdmin())
async def cmd_promo_list(message: Message) -> None:
    rows = await db.list_promos()
    if not rows:
        await message.answer("🎟 Promokodlar yo'q. Yaratish: /promo_add")
        return
    lines = []
    for r in rows[:50]:
        what = f"💎 {r['amount']} kun" if r["kind"] == "vip" else f"🎁 +{r['amount']}"
        limit = r["max_uses"] or "∞"
        exp = ""
        if r["expires_at"]:
            exp = " · ⌛ tugagan" if r["expires_at"] <= time.time() else f" · {cfg.fmt_date(r['expires_at'])} gacha"
        lines.append(f"<code>{r['code']}</code> — {what} · {r['used']}/{limit}{exp}")
    await message.answer(f"🎟 <b>Promokodlar</b> ({len(rows)} ta)\n\n" + "\n".join(lines))


@router.message(Command("promo_del"), IsAdmin())
async def cmd_promo_del(message: Message, command: CommandObject) -> None:
    code = (command.args or "").strip()
    if not code:
        await message.answer("Format: /promo_del &lt;KOD&gt;")
        return
    ok = await db.delete_promo(code)
    await message.answer("✅ O'chirildi." if ok else "❌ Bunday kod yo'q.")


# ============================================================================
# TAKLIF / SHIKOYAT va /msg
# ============================================================================
class FeedbackState(StatesGroup):
    waiting = State()


FEEDBACK_TIMES: dict[int, list[float]] = {}


@router.callback_query(F.data == "menu:feedback")
async def cb_feedback(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user)
    await state.set_state(FeedbackState.waiting)
    await edit_or_send(call, t(lang, "feedback_prompt"), kb_back(lang))
    await call.answer()


@router.message(StateFilter(FeedbackState.waiting), F.func(lambda m: not (m.text or "").startswith("/")))
async def got_feedback(message: Message, state: FSMContext, bot: Bot) -> None:
    user = message.from_user
    lang = await get_lang(user)

    now = time.monotonic()
    times = [x for x in FEEDBACK_TIMES.get(user.id, []) if now - x < 3600]
    if len(times) >= cfg.FEEDBACK_PER_HOUR:
        await message.answer(t(lang, "feedback_limit", n=cfg.FEEDBACK_PER_HOUR))
        await state.clear()
        return
    FEEDBACK_TIMES[user.id] = times + [now]

    info = f"📩 <b>Yangi xabar</b>\n👤 {fmt_user(user.id, user.username or '', user.full_name)}\n🌐 {lang}"
    hint = "\n\n<i>Javob berish uchun shu xabarga reply qiling.</i>"
    delivered = 0
    for admin_id in cfg.ADMIN_IDS:
        try:
            if message.text:
                m1 = await bot.send_message(admin_id, f"{info}\n\n{html.escape(message.text)}{hint}")
                await db.fb_map_put(admin_id, m1.message_id, user.id)
            else:
                m1 = await bot.send_message(admin_id, info + hint)
                m2 = await bot.copy_message(admin_id, message.chat.id, message.message_id)
                await db.fb_map_put(admin_id, m1.message_id, user.id)
                await db.fb_map_put(admin_id, m2.message_id, user.id)
            delivered += 1
        except Exception as e:  # noqa: BLE001
            log.warning("Taklifni adminga (%s) yuborib bo'lmadi: %s", admin_id, e)
    await state.clear()
    await message.answer(t(lang, "feedback_sent" if delivered else "error_generic"))


class FeedbackReply(Filter):
    """Admin taklif/shikoyat xabariga reply qilsa — foydalanuvchi ID sini beradi."""

    async def __call__(self, message: Message):
        if not message.from_user or not is_admin(message.from_user.id) or not message.reply_to_message:
            return False
        if (message.text or "").startswith("/"):
            return False
        uid = await db.fb_map_get(message.chat.id, message.reply_to_message.message_id)
        return {"fb_user_id": uid} if uid else False


@router.message(FeedbackReply())
async def admin_reply(message: Message, bot: Bot, fb_user_id: int) -> None:
    row = await db.get_user(fb_user_id)
    lang = row["lang"] if row and row["lang"] else "uz"
    header = t(lang, "admin_reply_header")
    try:
        if message.text:
            await bot.send_message(fb_user_id, f"{header}\n\n{message.html_text}")
        else:
            await bot.send_message(fb_user_id, header)
            await bot.copy_message(fb_user_id, message.chat.id, message.message_id)
        await message.answer("✅ Javob foydalanuvchiga yuborildi.")
    except TelegramForbiddenError:
        await message.answer("❌ Foydalanuvchi botni bloklagan.")
    except Exception as e:  # noqa: BLE001
        await message.answer(f"❌ Yuborib bo'lmadi: {html.escape(str(e))}")


@router.message(Command("msg"), IsAdmin())
async def cmd_msg(message: Message, command: CommandObject, bot: Bot) -> None:
    usage = (
        "Format: <code>/msg &lt;ID yoki @username&gt; matn</code>\n"
        "yoki biror xabarga reply qilib: <code>/msg &lt;ID yoki @username&gt;</code> (rasm/video ham mumkin)"
    )
    args = (command.args or "").split(maxsplit=1)
    row = await db.find_user(args[0]) if args else None
    if not row:
        await message.answer(usage)
        return
    uid, lang = row["user_id"], row["lang"] or "uz"
    header = t(lang, "admin_msg_header")
    try:
        if len(args) == 2:
            await bot.send_message(uid, f"{header}\n\n{args[1]}")
        elif message.reply_to_message:
            await bot.send_message(uid, header)
            await bot.copy_message(uid, message.chat.id, message.reply_to_message.message_id)
        else:
            await message.answer(usage)
            return
        await message.answer(f"✅ Yuborildi: {fmt_row(row)}")
    except TelegramForbiddenError:
        await message.answer("❌ Foydalanuvchi botni bloklagan.")
    except Exception as e:  # noqa: BLE001
        await message.answer(f"❌ Yuborib bo'lmadi: {html.escape(str(e))}")


# ============================================================================
# STIKERLAR (donat / VIP olinganda stiker + matn)
# ============================================================================
STICKER_KINDS = {"donate": "❤️ Donat", "vip": "💎 VIP"}
PENDING_STICKER: dict[int, str] = {}


DEFAULT_EMOJI = {"donate": "❤️", "vip": "🎉"}   # stiker o'rnatilmagan bo'lsa — katta animatsion emoji


async def celebrate(bot: Bot, chat_id: int, kind: str) -> bool:
    """
    Donat/VIP olinganda matndan oldin yuboriladi:
      1) admin o'rnatgan stiker bo'lsa — o'sha stiker;
      2) bo'lmasa — katta animatsion emoji (❤️ / 🎉), CELEBRATE_EMOJI=0 bo'lsa hech narsa.
    """
    file_id = await db.get_setting(f"sticker_{kind}")
    if file_id:
        try:
            await bot.send_sticker(chat_id, file_id)
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("Stiker yuborib bo'lmadi (%s): %s", kind, e)
    if cfg.CELEBRATE_EMOJI and kind in DEFAULT_EMOJI:
        try:
            await bot.send_message(chat_id, DEFAULT_EMOJI[kind])
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("Emoji yuborib bo'lmadi (%s): %s", kind, e)
    return False


@router.message(F.sticker, IsAdmin())
async def admin_sticker(message: Message) -> None:
    PENDING_STICKER[message.from_user.id] = message.sticker.file_id
    kb = InlineKeyboardBuilder()
    kb.button(text="❤️ Donat uchun", callback_data="setst:donate")
    kb.button(text="💎 VIP uchun", callback_data="setst:vip")
    kb.button(text="❌ Bekor", callback_data="setst:no")
    kb.adjust(2, 1)
    await message.answer(
        "🎨 Bu stikerni qaysi holat uchun o'rnatay?\n"
        "Kimdir donat qilganda yoki VIP olganda shu stiker + matn yuboriladi.",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("setst:"), IsAdmin())
async def cb_setst(call: CallbackQuery) -> None:
    kind = call.data.split(":", 1)[1]
    file_id = PENDING_STICKER.pop(call.from_user.id, None)
    if kind == "no":
        text = "❌ Bekor qilindi."
    elif kind not in STICKER_KINDS or not file_id:
        text = "⚠️ Stiker topilmadi. Stikerni qaytadan yuboring."
    else:
        await db.set_setting(f"sticker_{kind}", file_id)
        text = f"✅ {STICKER_KINDS[kind]} uchun stiker o'rnatildi. Ko'rish: /stickers"
    try:
        await call.message.edit_text(text)
    except Exception:  # noqa: BLE001
        await call.message.answer(text)
    await call.answer()


@router.message(Command("stickers"), IsAdmin())
async def cmd_stickers(message: Message, bot: Bot) -> None:
    lines = []
    for kind, title in STICKER_KINDS.items():
        fid = await db.get_setting(f"sticker_{kind}")
        default = f"standart: {DEFAULT_EMOJI[kind]} katta emoji" if cfg.CELEBRATE_EMOJI else "hech narsa yuborilmaydi"
        state = "✅ o'z stikeringiz o'rnatilgan" if fid else f"❌ yo'q ({default})"
        lines.append(f"{title}: {state}")
    await message.answer(
        "🎨 <b>Stikerlar</b>\n" + "\n".join(lines)
        + "\n\nO'rnatish: botga istalgan stikerni yuboring.\nO'chirish: <code>/delsticker donate</code> yoki <code>/delsticker vip</code>"
        + "\n\n👇 Donat/VIP olinganda shunday ko'rinadi (stiker/emoji, keyin matn):"
    )
    for kind in STICKER_KINDS:
        await celebrate(bot, message.chat.id, kind)


@router.message(Command("delsticker"), IsAdmin())
async def cmd_delsticker(message: Message, command: CommandObject) -> None:
    kind = (command.args or "").strip().lower()
    if kind not in STICKER_KINDS:
        await message.answer("Format: /delsticker donate | vip")
        return
    await db.del_setting(f"sticker_{kind}")
    await message.answer(f"✅ {STICKER_KINDS[kind]} stikeri o'chirildi.")


# ============================================================================
# VIP TUGASHI ESLATMASI (fon vazifasi)
# ============================================================================
async def send_vip_reminders(bot: Bot) -> int:
    rows = await db.vip_expiring(cfg.VIP_REMIND_DAYS)
    sent = 0
    for r in rows:
        lang = r["lang"] or "uz"
        days_left = max(1, math.ceil((r["vip_until"] - time.time()) / 86400))
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "btn_renew"), callback_data="menu:vip")
        try:
            await bot.send_message(
                r["user_id"],
                t(lang, "vip_expiring", date=cfg.fmt_date(r["vip_until"]), days=days_left),
                reply_markup=kb.as_markup(),
            )
            sent += 1
        except TelegramForbiddenError:
            await db.mark_inactive(r["user_id"])
        except Exception as e:  # noqa: BLE001
            log.info("VIP eslatmasi yuborilmadi (%s): %s", r["user_id"], e)
        await db.mark_vip_reminded(r["user_id"], r["vip_until"])  # qayta-qayta yubormaslik uchun
        await asyncio.sleep(0.05)
    return sent


async def reminders_loop(bot: Bot) -> None:
    await asyncio.sleep(30)
    while True:
        try:
            n = await send_vip_reminders(bot)
            if n:
                log.info("VIP eslatmalari yuborildi: %d ta", n)
        except Exception as e:  # noqa: BLE001
            log.exception("reminders_loop xatosi: %s", e)
        await asyncio.sleep(3600)


# ============================================================================
# KUNDALIK HISOBOT (fon vazifasi)
# ============================================================================
def seconds_until(hour: int) -> float:
    now = cfg.now_dt()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def build_report_text() -> str:
    r = await db.get_day_report()
    platforms = "\n".join(
        f"   {dl.PLATFORM_EMOJI.get(p, '🔗')} {dl.PLATFORM_TITLE.get(p, p)}: {c}" for p, c in r["platforms"]
    ) or "   —"
    vip_cnt, vip_stars = r["income"].get("vip", (0, 0))
    don_cnt, don_stars = r["income"].get("donate", (0, 0))
    return (
        f"📅 <b>Kunlik hisobot</b> — {cfg.now_dt().strftime('%d.%m.%Y')}\n\n"
        f"👥 Jami: <b>{r['users']}</b> · 🆕 bugun yangi: <b>{r['new']}</b> · 🔥 faol: <b>{r['active']}</b>\n"
        f"📥 Yuklashlar: <b>{r['dl']}</b> (⚡ keshdan: {r['dl_cached']})\n{platforms}\n\n"
        f"💰 Bugungi daromad: <b>{vip_stars + don_stars} ⭐</b>\n"
        f"   💎 VIP: {vip_stars} ⭐ ({vip_cnt} ta) · ❤️ Donat: {don_stars} ⭐ ({don_cnt} ta)\n"
        f"💎 Faol VIP: <b>{r['vip_active']}</b> (2 kun ichida tugaydi: {r['vip_expiring']})\n"
        f"🎁 Kunlik bonus olganlar: <b>{r['daily_bonus']}</b>"
    )


async def send_report(bot: Bot) -> None:
    text = await build_report_text()
    for admin_id in cfg.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:  # noqa: BLE001
            log.info("Hisobotni adminga (%s) yuborib bo'lmadi: %s", admin_id, e)


async def report_loop(bot: Bot) -> None:
    if cfg.REPORT_HOUR < 0 or not cfg.ADMIN_IDS:
        return
    while True:
        await asyncio.sleep(seconds_until(cfg.REPORT_HOUR))
        try:
            await send_report(bot)
        except Exception as e:  # noqa: BLE001
            log.exception("report_loop xatosi: %s", e)
        await asyncio.sleep(61)


@router.message(Command("report"), IsAdmin())
async def cmd_report(message: Message) -> None:
    await message.answer(await build_report_text())


def start_background(bot: Bot) -> list[asyncio.Task]:
    """Fon vazifalarini ishga tushiradi (VIP eslatmasi, kundalik hisobot)."""
    return [spawn(reminders_loop(bot)), spawn(report_loop(bot))]
