"""
Bot sozlamalari. Hamma qiymat .env faylidan o'qiladi.
"""

import os
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time

from dotenv import load_dotenv

load_dotenv()


def _int_list(raw: str) -> list[int]:
    out = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return out


# ---------------------------------------------------------------- Asosiy
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Adminlar: ADMIN_IDS=123,456  (eski ADMIN_ID ham ishlaydi)
ADMIN_IDS: set[int] = set(_int_list(os.getenv("ADMIN_IDS", ""))) | set(
    _int_list(os.getenv("ADMIN_ID", ""))
)

DB_PATH = os.getenv("DB_PATH", "bot.db")
PROXY_URL = os.getenv("PROXY_URL", "")
START_PHOTO = os.getenv("START_PHOTO", "")
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")

# ---------------------------------------------------------------- Vaqt zonasi
try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tashkent"))
except Exception:  # tzdata o'rnatilmagan bo'lsa
    TZ = timezone(timedelta(hours=5))


def now_dt() -> datetime:
    return datetime.now(TZ)


def today_str() -> str:
    return now_dt().date().isoformat()


def today_start_ts() -> int:
    return int(datetime.combine(now_dt().date(), dt_time.min, tzinfo=TZ).timestamp())


def yesterday_str() -> str:
    return (now_dt().date() - timedelta(days=1)).isoformat()


def fmt_date(ts: int, fmt: str = "%d.%m.%Y") -> str:
    return datetime.fromtimestamp(ts, TZ).strftime(fmt)


# ---------------------------------------------------------------- Limitlar
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))
MAX_FILE_SIZE = 50 * 1024 * 1024          # Bot API limiti
MAX_FILES_PER_LINK = 10
MAX_VIDEO_SECONDS = int(os.getenv("MAX_VIDEO_SECONDS", "600"))  # 10 daqiqa
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "3"))              # bir vaqtda nechta yuklash
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "180"))    # soniya

# ---------------------------------------------------------------- VIP tariflar
# VIP_PLANS="7:35,30:100,90:250"  ->  kun:stars
def _parse_plans(raw: str) -> dict[int, int]:
    plans: dict[int, int] = {}
    for item in raw.split(","):
        days, _, price = item.strip().partition(":")
        if days.isdigit() and price.isdigit() and int(days) > 0 and int(price) > 0:
            plans[int(days)] = int(price)
    return plans or {7: 35, 30: 100, 90: 250}


VIP_PLANS: dict[int, int] = _parse_plans(os.getenv("VIP_PLANS", "7:35,30:100,90:250"))

# ---------------------------------------------------------------- Donat
MIN_DONATE = 1
MAX_DONATE = 10000
DONATE_PRESETS = (10, 50, 100, 500)

# ---------------------------------------------------------------- Referal
REF_BONUS_DOWNLOADS = int(os.getenv("REF_BONUS_DOWNLOADS", "3"))   # har do'st uchun
REF_MILESTONE = int(os.getenv("REF_MILESTONE", "5"))               # har N ta do'stga
REF_MILESTONE_VIP_DAYS = int(os.getenv("REF_MILESTONE_VIP_DAYS", "3"))


# ---------------------------------------------------------------- Majburiy obuna
# REQUIRED_CHANNELS=@kanal1,@kanal2
# yoki yopiq kanal: -1001234567890|https://t.me/+AbCdEf
def _parse_channels(raw: str) -> list[dict]:
    out: list[dict] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        chat, _, link = item.partition("|")
        chat, link = chat.strip(), link.strip()
        chat_id: int | str
        if chat.lstrip("-").isdigit():
            chat_id = int(chat)
        else:
            chat_id = chat if chat.startswith("@") else "@" + chat
        if not link and isinstance(chat_id, str):
            link = f"https://t.me/{chat_id[1:]}"
        title = chat_id if isinstance(chat_id, str) else "Kanal"
        out.append({"chat": chat_id, "link": link or None, "title": title})
    return out


REQUIRED_CHANNELS: list[dict] = _parse_channels(os.getenv("REQUIRED_CHANNELS", ""))


# ---------------------------------------------------------------- Kunlik bonus
DAILY_BONUS = int(os.getenv("DAILY_BONUS", "1"))                          # har kuni nechta yuklash
DAILY_BONUS_STREAK_EVERY = int(os.getenv("DAILY_BONUS_STREAK_EVERY", "7"))  # har N-ketma-ket kunda
DAILY_BONUS_STREAK_EXTRA = int(os.getenv("DAILY_BONUS_STREAK_EXTRA", "3"))  # qo'shimcha sovg'a

# ---------------------------------------------------------------- Eslatma, hisobot, boshqalar
VIP_REMIND_DAYS = int(os.getenv("VIP_REMIND_DAYS", "2"))     # VIP tugashiga necha kun qolganda eslatish
REPORT_HOUR = int(os.getenv("REPORT_HOUR", "21"))            # kundalik hisobot soati (-1 = o'chiq)
FEEDBACK_PER_HOUR = int(os.getenv("FEEDBACK_PER_HOUR", "3"))  # soatiga nechta taklif/shikoyat
PROMO_MAX_FAILS = int(os.getenv("PROMO_MAX_FAILS", "5"))      # 10 daqiqada noto'g'ri promokod urinishlari

# ---------------------------------------------------------------- Spamdan himoya
SPAM_LIMIT = int(os.getenv("SPAM_LIMIT", "8"))                  # SPAM_WINDOW soniyada nechta harakat
SPAM_WINDOW = int(os.getenv("SPAM_WINDOW", "10"))
SPAM_BLOCK_SECONDS = int(os.getenv("SPAM_BLOCK_SECONDS", "60"))  # vaqtincha to'xtatish
SPAM_AUTOBAN_STRIKES = int(os.getenv("SPAM_AUTOBAN_STRIKES", "3"))  # 1 soatda shuncha marta to'xtatilsa — avto-ban (0 = o'chiq)

# Donat/VIP olinganda stiker sozlanmagan bo'lsa, shu o'rniga katta animatsion emoji yuboriladi (1 = ha, 0 = yo'q)
CELEBRATE_EMOJI = os.getenv("CELEBRATE_EMOJI", "1") == "1"
