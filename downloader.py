"""
Havolani aniqlash va media yuklash (yt-dlp, zaxira: gallery-dl).
Bu modulning funksiyalari bloklovchi — asyncio.to_thread orqali chaqiriladi.
"""

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import match_filter_func

import config as cfg

log = logging.getLogger("downloader")

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav"}

HAS_FFMPEG = shutil.which("ffmpeg") is not None

PLATFORM_EMOJI = {"instagram": "📸", "pinterest": "📌"}
PLATFORM_TITLE = {"instagram": "Instagram", "pinterest": "Pinterest"}

URL_REGEX = re.compile(
    r"https?://(?:[\w-]+\.)*"
    r"(?:instagram\.com|instagr\.am|pinterest\.[a-z.]+|pin\.it)/\S+",
    re.IGNORECASE,
)


def extract_url(text: str) -> str | None:
    """Matndagi birinchi qo'llab-quvvatlanadigan havolani qaytaradi."""
    m = URL_REGEX.search(text or "")
    if not m:
        return None
    return m.group(0).rstrip(").,;!?>]\"'")


def has_supported_url(text: str | None) -> bool:
    return bool(text and URL_REGEX.search(text))


def detect_platform(url: str) -> str | None:
    """Platforma nomini qaytaradi: instagram yoki pinterest."""
    host = urlparse(url).netloc.lower().split(":")[0]
    if "instagram.com" in host or "instagr.am" in host:
        return "instagram"
    if "pinterest." in host or host.endswith("pin.it"):
        return "pinterest"
    return None


class DownloadFailed(Exception):
    """Yuklab bo'lmaganda: reason — sabab turi, detail — texnik tafsilot (admin uchun)."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(detail or reason)
        self.reason = reason  # too_long | blocked | unavailable | too_big | unknown
        self.detail = detail


class _Collector:
    """yt-dlp xabarlarini yig'adi (sababini aniqlash uchun)."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def _add(self, msg) -> None:
        msg = str(msg).strip()
        if msg and not msg.startswith("[debug]"):
            self.lines.append(msg)
            del self.lines[:-40]

    debug = info = warning = error = _add

    def text(self) -> str:
        return "\n".join(self.lines)

    def detail(self) -> str:
        errors = [x for x in self.lines if "ERROR" in x or "does not pass filter" in x or "max-filesize" in x]
        primary = [x for x in errors if "gallery-dl" not in x]  # yt-dlp xatosi ma'lumotliroq
        return (primary or errors or self.lines or [""])[-1][:400]


def _classify(text: str) -> str:
    low = text.lower()
    if "does not pass filter" in low:
        return "too_long"
    if any(k in low for k in ("sign in to confirm", "not a bot", "login required", "log in", "cookies", "rate-limit")):
        return "blocked"
    if any(k in low for k in ("private video", "video unavailable", "not available", "has been removed", "does not exist", "404")):
        return "unavailable"
    if "max-filesize" in low or "larger than" in low:
        return "too_big"
    return "unknown"


def url_key(url: str) -> str:
    """Kesh uchun havolaning 'tozalangan' kaliti (?igsh=..., oxiridagi / va h.k. e'tiborga olinmaydi)."""
    p = urlparse(url)
    host = p.netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return f"{host}{p.path.rstrip('/')}"


def _collect(folder: Path, exts: set[str]) -> list[Path]:
    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in exts]
    return sorted(files)[: cfg.MAX_FILES_PER_LINK]


def _base_opts(out_dir: str, col: _Collector) -> dict:
    opts = {
        "outtmpl": f"{out_dir}/%(id)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "no_color": True,
        "logger": col,
        "socket_timeout": 30,
        "retries": 3,
        "max_filesize": cfg.MAX_FILE_SIZE,
        # juda uzun videolarni o'tkazib yuboradi (davomiyligi noma'lum bo'lsa — ruxsat)
        "match_filter": match_filter_func(f"duration<=?{cfg.MAX_VIDEO_SECONDS}"),
    }
    if Path(cfg.COOKIES_FILE).exists():
        opts["cookiefile"] = cfg.COOKIES_FILE
    if cfg.PROXY_URL:
        opts["proxy"] = cfg.PROXY_URL
    return opts


def _clear_dir(out_dir: str) -> None:
    for p in Path(out_dir).rglob("*"):
        if p.is_file():
            p.unlink(missing_ok=True)


def _run_ytdlp(opts: dict, url: str, col: _Collector) -> None:
    """yt-dlp'ni ishga tushiradi; xatoni yig'uvchiga yozadi (tashqariga chiqarmaydi)."""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        col.lines.append(msg if msg.startswith("ERROR") else f"ERROR: {msg}")
        log.info("yt-dlp xatosi: %s", msg)


def _ytdlp_video(url: str, out_dir: str, col: _Collector) -> None:
    opts = _base_opts(out_dir, col)
    opts["format"] = "best[ext=mp4]/best"
    _run_ytdlp(opts, url, col)


def _ytdlp_audio(url: str, out_dir: str, col: _Collector) -> None:
    opts = _base_opts(out_dir, col)
    if HAS_FFMPEG:
        # Har qanday manbadan MP3 ajratib oladi
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        # ffmpeg yo'q: faqat tayyor audio oqimi bo'lsa ishlaydi
        opts["format"] = "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio"
    _run_ytdlp(opts, url, col)


def _gallerydl(url: str, out_dir: str, col: _Collector) -> None:
    cmd = [sys.executable, "-m", "gallery_dl", "-q", "-d", out_dir]
    if Path(cfg.COOKIES_FILE).exists():
        cmd += ["--cookies", cfg.COOKIES_FILE]
    if cfg.PROXY_URL:
        cmd += ["--proxy", cfg.PROXY_URL]
    cmd.append(url)
    try:
        subprocess.run(cmd, check=True, timeout=120, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or "").strip().splitlines()[-1:] or [str(e)]
        col.lines.append(f"ERROR: gallery-dl: {tail[0]}")
        log.info("gallery-dl xatosi: %s", tail[0])
    except Exception as e:  # noqa: BLE001
        col.lines.append(f"ERROR: gallery-dl: {e}")
        log.info("gallery-dl xatosi: %s", e)


def download_media(url: str, out_dir: str, platform: str, audio: bool = False) -> list[Path]:
    """
    Havoladan media yuklaydi va fayllar ro'yxatini qaytaradi.
    audio=True bo'lsa, faqat audio (MP3/M4A).
    Hech narsa yuklanmasa — DownloadFailed (sabab bilan) ko'taradi.
    """
    col = _Collector()
    folder = Path(out_dir)

    if audio:
        _ytdlp_audio(url, out_dir, col)
        files = _collect(folder, AUDIO_EXT)
    else:
        _ytdlp_video(url, out_dir, col)
        files = _collect(folder, VIDEO_EXT | IMAGE_EXT)
        # Rasm va karusellar uchun zaxira usul
        if not files and platform in ("instagram", "pinterest"):
            _gallerydl(url, out_dir, col)
            files = _collect(folder, VIDEO_EXT | IMAGE_EXT)

    if files:
        return files
    reason = _classify(col.text())
    detail = col.detail()
    log.warning("Yuklab bo'lmadi [%s] sabab=%s | %s", platform, reason, detail)
    raise DownloadFailed(reason, detail)
