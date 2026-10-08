"""
SQLite ma'lumotlar bazasi (aiosqlite).
Eski bot.db fayli bo'lsa, yangi ustunlar avtomatik qo'shiladi (migratsiya).
"""

import time

import aiosqlite

import config as cfg

_db: aiosqlite.Connection | None = None


def _conn() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("DB hali ochilmagan: init_db() ni chaqiring")
    return _db


# Eski bazada yo'q bo'lishi mumkin bo'lgan ustunlar
USER_COLUMNS = {
    "lang": "TEXT NOT NULL DEFAULT ''",
    "bonus": "INTEGER NOT NULL DEFAULT 0",
    "referrer_id": "INTEGER NOT NULL DEFAULT 0",
    "ref_rewarded": "INTEGER NOT NULL DEFAULT 0",
    "ref_count": "INTEGER NOT NULL DEFAULT 0",
    "created_at": "INTEGER NOT NULL DEFAULT 0",
    "last_seen": "INTEGER NOT NULL DEFAULT 0",
    "is_active": "INTEGER NOT NULL DEFAULT 1",
    "username": "TEXT NOT NULL DEFAULT ''",
    "full_name": "TEXT NOT NULL DEFAULT ''",
    "vip_reminded_until": "INTEGER NOT NULL DEFAULT 0",
    "daily_bonus_date": "TEXT NOT NULL DEFAULT ''",
    "bonus_streak": "INTEGER NOT NULL DEFAULT 0",
    "banned": "INTEGER NOT NULL DEFAULT 0",
    "ban_reason": "TEXT NOT NULL DEFAULT ''",
}
DOWNLOAD_COLUMNS = {
    "cached": "INTEGER NOT NULL DEFAULT 0",
}


async def init_db(path: str) -> None:
    global _db
    _db = await aiosqlite.connect(path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS users (
               user_id     INTEGER PRIMARY KEY,
               vip_until   INTEGER NOT NULL DEFAULT 0,
               daily_date  TEXT    NOT NULL DEFAULT '',
               daily_count INTEGER NOT NULL DEFAULT 0
           )"""
    )
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS payments (
               id         INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id    INTEGER NOT NULL,
               kind       TEXT    NOT NULL,
               stars      INTEGER NOT NULL,
               charge_id  TEXT    NOT NULL,
               created_at INTEGER NOT NULL
           )"""
    )
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS downloads (
               id         INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id    INTEGER NOT NULL,
               url        TEXT    NOT NULL,
               platform   TEXT    NOT NULL,
               kind       TEXT    NOT NULL,
               created_at INTEGER NOT NULL
           )"""
    )
    await _db.execute("CREATE INDEX IF NOT EXISTS idx_dl_user ON downloads (user_id, id)")
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS settings (
               key   TEXT PRIMARY KEY,
               value TEXT NOT NULL
           )"""
    )
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS media_cache (
               url_key    TEXT    NOT NULL,
               mode       TEXT    NOT NULL,      -- 'media' yoki 'audio'
               idx        INTEGER NOT NULL,
               media_type TEXT    NOT NULL,
               file_id    TEXT    NOT NULL,
               PRIMARY KEY (url_key, mode, idx)
           )"""
    )
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS promo_codes (
               code       TEXT PRIMARY KEY,
               kind       TEXT    NOT NULL,      -- 'vip' yoki 'bonus'
               amount     INTEGER NOT NULL,
               max_uses   INTEGER NOT NULL DEFAULT 0,   -- 0 = cheksiz
               used       INTEGER NOT NULL DEFAULT 0,
               expires_at INTEGER NOT NULL DEFAULT 0,   -- 0 = muddatsiz
               created_at INTEGER NOT NULL
           )"""
    )
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS promo_uses (
               code    TEXT    NOT NULL,
               user_id INTEGER NOT NULL,
               used_at INTEGER NOT NULL,
               PRIMARY KEY (code, user_id)
           )"""
    )
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS feedback_map (
               admin_chat INTEGER NOT NULL,
               admin_msg  INTEGER NOT NULL,
               user_id    INTEGER NOT NULL,
               PRIMARY KEY (admin_chat, admin_msg)
           )"""
    )

    # --- migratsiya: yetishmayotgan ustunlarni qo'shish ---
    for table, columns in (("users", USER_COLUMNS), ("downloads", DOWNLOAD_COLUMNS)):
        async with _db.execute(f"PRAGMA table_info({table})") as cur:
            existing = {row["name"] for row in await cur.fetchall()}
        for name, ddl in columns.items():
            if name not in existing:
                await _db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
    await _db.commit()


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


# ============================================================ FOYDALANUVCHI
async def register_user(
    user_id: int, referrer_id: int = 0, lang: str = "", username: str = "", full_name: str = ""
) -> bool:
    """Foydalanuvchini qo'shadi. Yangi bo'lsa True qaytaradi."""
    now = int(time.time())
    cur = await _conn().execute(
        """INSERT OR IGNORE INTO users (user_id, referrer_id, lang, created_at, last_seen, username, full_name)
           VALUES (?,?,?,?,?,?,?)""",
        (user_id, referrer_id, lang, now, now, username, full_name),
    )
    await _conn().commit()
    return cur.rowcount == 1


async def user_exists(user_id: int) -> bool:
    async with _conn().execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)) as cur:
        return await cur.fetchone() is not None


async def get_user(user_id: int) -> aiosqlite.Row | None:
    async with _conn().execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
        return await cur.fetchone()


async def touch_user(user_id: int, username: str | None = None, full_name: str | None = None) -> None:
    """Oxirgi faollikni yangilaydi; ism va @username berilsa, ularni ham yangilaydi."""
    if username is None and full_name is None:
        await _conn().execute(
            "UPDATE users SET last_seen=?, is_active=1 WHERE user_id=?", (int(time.time()), user_id)
        )
    else:
        await _conn().execute(
            "UPDATE users SET last_seen=?, is_active=1, username=?, full_name=? WHERE user_id=?",
            (int(time.time()), username or "", full_name or "", user_id),
        )
    await _conn().commit()


async def find_user(query: str) -> aiosqlite.Row | None:
    """ID (raqam) yoki @username bo'yicha foydalanuvchini topadi."""
    query = query.strip()
    if query.lstrip("-").isdigit():
        return await get_user(int(query))
    uname = query.lstrip("@").lower()
    if not uname:
        return None
    async with _conn().execute("SELECT * FROM users WHERE LOWER(username)=?", (uname,)) as cur:
        return await cur.fetchone()


async def count_users() -> int:
    async with _conn().execute("SELECT COUNT(*) FROM users") as cur:
        return (await cur.fetchone())[0]


async def list_users(offset: int, limit: int) -> list[aiosqlite.Row]:
    """Eng yangi ro'yxatdan o'tganlar birinchi."""
    async with _conn().execute(
        "SELECT * FROM users ORDER BY created_at DESC, user_id DESC LIMIT ? OFFSET ?", (limit, offset)
    ) as cur:
        return list(await cur.fetchall())


async def list_vips() -> list[aiosqlite.Row]:
    async with _conn().execute(
        "SELECT * FROM users WHERE vip_until>? ORDER BY vip_until ASC", (int(time.time()),)
    ) as cur:
        return list(await cur.fetchall())


async def top_downloaders(limit: int = 5) -> list[tuple]:
    """(user_id, username, full_name, soni) — eng ko'p yuklaganlar."""
    async with _conn().execute(
        """SELECT d.user_id, COALESCE(u.username,''), COALESCE(u.full_name,''), COUNT(*) AS c
           FROM downloads d LEFT JOIN users u ON u.user_id = d.user_id
           GROUP BY d.user_id ORDER BY c DESC LIMIT ?""",
        (limit,),
    ) as cur:
        return [tuple(r) for r in await cur.fetchall()]


async def top_referrers(limit: int = 5) -> list[tuple]:
    """(user_id, username, full_name, do'stlar soni) — eng ko'p taklif qilganlar."""
    async with _conn().execute(
        """SELECT user_id, username, full_name, ref_count FROM users
           WHERE ref_count>0 ORDER BY ref_count DESC LIMIT ?""",
        (limit,),
    ) as cur:
        return [tuple(r) for r in await cur.fetchall()]


async def mark_inactive(user_id: int) -> None:
    await _conn().execute("UPDATE users SET is_active=0 WHERE user_id=?", (user_id,))
    await _conn().commit()


async def set_lang(user_id: int, lang: str) -> None:
    await _conn().execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
    await _conn().commit()


async def get_all_user_ids(active_only: bool = True) -> list[int]:
    sql = "SELECT user_id FROM users"
    if active_only:
        sql += " WHERE is_active=1"
    async with _conn().execute(sql) as cur:
        return [row[0] for row in await cur.fetchall()]


# ============================================================ LIMIT / VIP
async def get_quota(user_id: int, daily_limit: int) -> dict:
    """Foydalanuvchining yuklash huquqini hisoblaydi."""
    await register_user(user_id)  # mavjud bo'lsa hech narsa qilmaydi
    row = await get_user(user_id)
    now = int(time.time())
    vip = row["vip_until"] > now
    used = row["daily_count"] if row["daily_date"] == cfg.today_str() else 0
    free_left = max(0, daily_limit - used)
    bonus = row["bonus"]
    return {
        "vip": vip,
        "vip_until": row["vip_until"],
        "used": used,
        "limit": daily_limit,
        "free_left": free_left,
        "bonus": bonus,
        "left": free_left + bonus,
        "allowed": vip or free_left > 0 or bonus > 0,
    }


async def consume_download(user_id: int, daily_limit: int) -> None:
    """Muvaffaqiyatli yuklashdan keyin limitdan 1 ta ayiradi (VIP'dan emas)."""
    q = await get_quota(user_id, daily_limit)
    if q["vip"]:
        return
    today = cfg.today_str()
    if q["free_left"] > 0:
        await _conn().execute(
            """UPDATE users SET
                   daily_count = CASE WHEN daily_date = ? THEN daily_count + 1 ELSE 1 END,
                   daily_date  = ?
               WHERE user_id = ?""",
            (today, today, user_id),
        )
    elif q["bonus"] > 0:
        await _conn().execute(
            "UPDATE users SET bonus = bonus - 1 WHERE user_id=? AND bonus > 0", (user_id,)
        )
    await _conn().commit()


async def grant_vip(user_id: int, days: int) -> int:
    """VIP beradi yoki uzaytiradi. Yangi tugash vaqtini (unix) qaytaradi."""
    await register_user(user_id)
    row = await get_user(user_id)
    new_until = max(int(time.time()), row["vip_until"]) + days * 86400
    await _conn().execute("UPDATE users SET vip_until=? WHERE user_id=?", (new_until, user_id))
    await _conn().commit()
    return new_until


async def remove_vip(user_id: int) -> None:
    await _conn().execute("UPDATE users SET vip_until=0 WHERE user_id=?", (user_id,))
    await _conn().commit()


async def add_bonus(user_id: int, n: int) -> None:
    await _conn().execute("UPDATE users SET bonus = bonus + ? WHERE user_id=?", (n, user_id))
    await _conn().commit()


# ============================================================ REFERAL
async def confirm_referral(user_id: int) -> tuple[int, int] | None:
    """
    Taklif qilingan foydalanuvchi birinchi marta muvaffaqiyatli yuklaganda chaqiriladi.
    (referrer_id, referrerning jami tasdiqlangan do'stlari) ni qaytaradi,
    yoki allaqachon hisoblangan/referrer yo'q bo'lsa None.
    """
    db = _conn()
    cur = await db.execute(
        "UPDATE users SET ref_rewarded=1 WHERE user_id=? AND ref_rewarded=0 AND referrer_id>0",
        (user_id,),
    )
    if cur.rowcount != 1:
        await db.commit()
        return None
    async with db.execute("SELECT referrer_id FROM users WHERE user_id=?", (user_id,)) as c:
        referrer_id = (await c.fetchone())["referrer_id"]
    await db.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?", (referrer_id,))
    await db.commit()
    async with db.execute("SELECT ref_count FROM users WHERE user_id=?", (referrer_id,)) as c:
        row = await c.fetchone()
    return referrer_id, (row["ref_count"] if row else 0)


async def get_ref_stats(user_id: int) -> dict:
    row = await get_user(user_id)
    async with _conn().execute(
        "SELECT COUNT(*) FROM users WHERE referrer_id=? AND ref_rewarded=0", (user_id,)
    ) as cur:
        pending = (await cur.fetchone())[0]
    return {
        "count": row["ref_count"] if row else 0,
        "pending": pending,
        "balance": row["bonus"] if row else 0,
    }


# ============================================================ YUKLASHLAR / TARIX
async def log_download(user_id: int, url: str, platform: str, kind: str, cached: bool = False) -> int:
    cur = await _conn().execute(
        "INSERT INTO downloads (user_id, url, platform, kind, created_at, cached) VALUES (?,?,?,?,?,?)",
        (user_id, url, platform, kind, int(time.time()), 1 if cached else 0),
    )
    await _conn().commit()
    return cur.lastrowid


async def get_download(download_id: int) -> aiosqlite.Row | None:
    async with _conn().execute("SELECT * FROM downloads WHERE id=?", (download_id,)) as cur:
        return await cur.fetchone()


async def delete_download(download_id: int) -> None:
    await _conn().execute("DELETE FROM downloads WHERE id=?", (download_id,))
    await _conn().commit()


async def get_history(user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
    async with _conn().execute(
        "SELECT * FROM downloads WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
    ) as cur:
        return list(await cur.fetchall())


# ============================================================ TO'LOVLAR
async def save_payment(user_id: int, kind: str, stars: int, charge_id: str) -> None:
    await _conn().execute(
        "INSERT INTO payments (user_id, kind, stars, charge_id, created_at) VALUES (?,?,?,?,?)",
        (user_id, kind, stars, charge_id, int(time.time())),
    )
    await _conn().commit()


# ============================================================ STATISTIKA
async def get_stats() -> dict:
    db = _conn()
    day_start = cfg.today_start_ts()
    now = int(time.time())

    async def scalar(sql: str, params: tuple = ()) -> int:
        async with db.execute(sql, params) as cur:
            row = await cur.fetchone()
            return row[0] or 0

    stats = {
        "users": await scalar("SELECT COUNT(*) FROM users"),
        "blocked": await scalar("SELECT COUNT(*) FROM users WHERE is_active=0"),
        "new_today": await scalar("SELECT COUNT(*) FROM users WHERE created_at>=?", (day_start,)),
        "active_today": await scalar("SELECT COUNT(*) FROM users WHERE last_seen>=?", (day_start,)),
        "vip": await scalar("SELECT COUNT(*) FROM users WHERE vip_until>?", (now,)),
        "dl_total": await scalar("SELECT COUNT(*) FROM downloads"),
        "dl_today": await scalar("SELECT COUNT(*) FROM downloads WHERE created_at>=?", (day_start,)),
        "dl_cached": await scalar("SELECT COUNT(*) FROM downloads WHERE cached=1"),
    }
    async with db.execute("SELECT platform, COUNT(*) AS c FROM downloads GROUP BY platform ORDER BY c DESC") as cur:
        stats["platforms"] = [(r["platform"], r["c"]) for r in await cur.fetchall()]
    async with db.execute("SELECT kind, COUNT(*) AS c, SUM(stars) AS s FROM payments GROUP BY kind") as cur:
        stats["income"] = {r["kind"]: (r["c"], r["s"] or 0) for r in await cur.fetchall()}
    return stats


# ============================================================ SOZLAMALAR (stikerlar va h.k.)
async def get_setting(key: str, default: str = "") -> str:
    async with _conn().execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
        row = await cur.fetchone()
    return row["value"] if row else default


async def set_setting(key: str, value: str) -> None:
    await _conn().execute(
        "INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    await _conn().commit()


async def del_setting(key: str) -> None:
    await _conn().execute("DELETE FROM settings WHERE key=?", (key,))
    await _conn().commit()


# ============================================================ KESH (Telegram file_id)
async def cache_get(url_key: str, mode: str) -> list[tuple[str, str]]:
    """[(media_type, file_id), ...] tartib bilan."""
    async with _conn().execute(
        "SELECT media_type, file_id FROM media_cache WHERE url_key=? AND mode=? ORDER BY idx",
        (url_key, mode),
    ) as cur:
        return [(r["media_type"], r["file_id"]) for r in await cur.fetchall()]


async def cache_put(url_key: str, mode: str, items: list[tuple[str, str]]) -> None:
    db = _conn()
    await db.execute("DELETE FROM media_cache WHERE url_key=? AND mode=?", (url_key, mode))
    await db.executemany(
        "INSERT INTO media_cache (url_key, mode, idx, media_type, file_id) VALUES (?,?,?,?,?)",
        [(url_key, mode, i, mt, fid) for i, (mt, fid) in enumerate(items)],
    )
    await db.commit()


async def cache_delete(url_key: str, mode: str) -> None:
    await _conn().execute("DELETE FROM media_cache WHERE url_key=? AND mode=?", (url_key, mode))
    await _conn().commit()


# ============================================================ PROMOKODLAR
async def create_promo(code: str, kind: str, amount: int, max_uses: int, expires_at: int) -> bool:
    cur = await _conn().execute(
        """INSERT OR IGNORE INTO promo_codes (code, kind, amount, max_uses, expires_at, created_at)
           VALUES (?,?,?,?,?,?)""",
        (code.upper(), kind, amount, max_uses, expires_at, int(time.time())),
    )
    await _conn().commit()
    return cur.rowcount == 1


async def list_promos() -> list[aiosqlite.Row]:
    async with _conn().execute("SELECT * FROM promo_codes ORDER BY created_at DESC") as cur:
        return list(await cur.fetchall())


async def delete_promo(code: str) -> bool:
    db = _conn()
    cur = await db.execute("DELETE FROM promo_codes WHERE code=?", (code.strip().upper(),))
    await db.execute("DELETE FROM promo_uses WHERE code=?", (code.strip().upper(),))
    await db.commit()
    return cur.rowcount == 1


async def redeem_promo(code: str, user_id: int) -> tuple[str, str | None, int]:
    """
    Promokodni ishlatadi. (status, kind, amount) qaytaradi.
    status: ok | not_found | expired | used | exhausted
    """
    code = code.strip().upper()
    db = _conn()
    async with db.execute("SELECT * FROM promo_codes WHERE code=?", (code,)) as cur:
        row = await cur.fetchone()
    if not row:
        return "not_found", None, 0
    now = int(time.time())
    if row["expires_at"] and row["expires_at"] <= now:
        return "expired", None, 0
    cur = await db.execute(
        "INSERT OR IGNORE INTO promo_uses (code, user_id, used_at) VALUES (?,?,?)", (code, user_id, now)
    )
    if cur.rowcount != 1:
        await db.commit()
        return "used", None, 0
    cur = await db.execute(
        "UPDATE promo_codes SET used = used + 1 WHERE code=? AND (max_uses=0 OR used < max_uses)", (code,)
    )
    if cur.rowcount != 1:
        await db.execute("DELETE FROM promo_uses WHERE code=? AND user_id=?", (code, user_id))
        await db.commit()
        return "exhausted", None, 0
    await db.commit()
    return "ok", row["kind"], row["amount"]


# ============================================================ TAKLIF/SHIKOYAT (admin javobi uchun)
async def fb_map_put(admin_chat: int, admin_msg: int, user_id: int) -> None:
    await _conn().execute(
        "INSERT OR REPLACE INTO feedback_map (admin_chat, admin_msg, user_id) VALUES (?,?,?)",
        (admin_chat, admin_msg, user_id),
    )
    await _conn().commit()


async def fb_map_get(admin_chat: int, admin_msg: int) -> int | None:
    async with _conn().execute(
        "SELECT user_id FROM feedback_map WHERE admin_chat=? AND admin_msg=?", (admin_chat, admin_msg)
    ) as cur:
        row = await cur.fetchone()
    return row["user_id"] if row else None


# ============================================================ KUNLIK BONUS
async def claim_daily_bonus(
    user_id: int, today: str, yesterday: str, base: int, streak_every: int, streak_extra: int
) -> tuple[int, int] | None:
    """Bugun olinmagan bo'lsa bonus beradi: (qo'shilgan soni, ketma-ket kunlar). Aks holda None."""
    await register_user(user_id)
    row = await get_user(user_id)
    if row["daily_bonus_date"] == today:
        return None
    streak = row["bonus_streak"] + 1 if row["daily_bonus_date"] == yesterday else 1
    amount = base
    if streak_every > 0 and streak % streak_every == 0:
        amount += streak_extra
    cur = await _conn().execute(
        """UPDATE users SET daily_bonus_date=?, bonus_streak=?, bonus = bonus + ?
           WHERE user_id=? AND daily_bonus_date != ?""",
        (today, streak, amount, user_id, today),
    )
    await _conn().commit()
    return (amount, streak) if cur.rowcount == 1 else None


# ============================================================ VIP ESLATMASI
async def vip_expiring(days: int) -> list[aiosqlite.Row]:
    """Tez orada tugaydigan va hali eslatma yuborilmagan VIP'lar."""
    now = int(time.time())
    async with _conn().execute(
        """SELECT * FROM users
           WHERE vip_until > ? AND vip_until <= ? AND vip_reminded_until != vip_until AND is_active = 1""",
        (now, now + days * 86400),
    ) as cur:
        return list(await cur.fetchall())


async def mark_vip_reminded(user_id: int, vip_until: int) -> None:
    await _conn().execute("UPDATE users SET vip_reminded_until=? WHERE user_id=?", (vip_until, user_id))
    await _conn().commit()


# ============================================================ KUNDALIK HISOBOT
async def get_day_report() -> dict:
    db = _conn()
    day_start = cfg.today_start_ts()
    now = int(time.time())

    async def scalar(sql: str, params: tuple = ()) -> int:
        async with db.execute(sql, params) as cur:
            row = await cur.fetchone()
            return row[0] or 0

    report = {
        "users": await scalar("SELECT COUNT(*) FROM users"),
        "new": await scalar("SELECT COUNT(*) FROM users WHERE created_at>=?", (day_start,)),
        "active": await scalar("SELECT COUNT(*) FROM users WHERE last_seen>=?", (day_start,)),
        "dl": await scalar("SELECT COUNT(*) FROM downloads WHERE created_at>=?", (day_start,)),
        "dl_cached": await scalar("SELECT COUNT(*) FROM downloads WHERE created_at>=? AND cached=1", (day_start,)),
        "vip_active": await scalar("SELECT COUNT(*) FROM users WHERE vip_until>?", (now,)),
        "vip_expiring": await scalar(
            "SELECT COUNT(*) FROM users WHERE vip_until>? AND vip_until<=?", (now, now + 2 * 86400)
        ),
        "daily_bonus": await scalar("SELECT COUNT(*) FROM users WHERE daily_bonus_date=?", (cfg.today_str(),)),
    }
    async with db.execute(
        "SELECT platform, COUNT(*) AS c FROM downloads WHERE created_at>=? GROUP BY platform ORDER BY c DESC",
        (day_start,),
    ) as cur:
        report["platforms"] = [(r["platform"], r["c"]) for r in await cur.fetchall()]
    async with db.execute(
        "SELECT kind, COUNT(*) AS c, SUM(stars) AS s FROM payments WHERE created_at>=? GROUP BY kind",
        (day_start,),
    ) as cur:
        report["income"] = {r["kind"]: (r["c"], r["s"] or 0) for r in await cur.fetchall()}
    return report


# ============================================================ BAN
async def set_banned(user_id: int, banned: bool, reason: str = "") -> None:
    await register_user(user_id)
    await _conn().execute(
        "UPDATE users SET banned=?, ban_reason=? WHERE user_id=?",
        (1 if banned else 0, reason if banned else "", user_id),
    )
    await _conn().commit()


async def banned_ids() -> set[int]:
    async with _conn().execute("SELECT user_id FROM users WHERE banned=1") as cur:
        return {r[0] for r in await cur.fetchall()}


async def list_banned() -> list[aiosqlite.Row]:
    async with _conn().execute("SELECT * FROM users WHERE banned=1 ORDER BY user_id") as cur:
        return list(await cur.fetchall())
