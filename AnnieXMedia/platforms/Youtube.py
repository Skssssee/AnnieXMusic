
import asyncio
import os
import re
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from AnnieXMedia.utils.formatters import time_to_seconds
from AnnieXMedia import LOGGER

try:
    from py_yt import VideosSearch
except ImportError:
    from youtubesearchpython.__future__ import VideosSearch


# =====================================================
# CONFIG
# =====================================================

API_AUDIO_URL = "http://152.42.187.207:8000/audio"

API_URLS = []
FALLBACK_API_URL = "https://shrutibots.site"


# =====================================================
# LOAD API URLS (AS IS)
# =====================================================

async def load_api_urls():
    global API_URLS
    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")

    loaded_urls = []

    for pb_id in ["rLsBhAQa", "FwwmTRED", "nfsHqXH2"]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://pastebin.com/raw/{pb_id}",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        url = (await response.text()).strip()
                        if url:
                            loaded_urls.append(url)
        except Exception:
            continue

    if loaded_urls:
        API_URLS = loaded_urls
        logger.info(f"Loaded {len(API_URLS)} API URLs successfully")
    else:
        API_URLS = [FALLBACK_API_URL]
        logger.info("Using fallback API URL")


try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_api_urls())
    else:
        loop.run_until_complete(load_api_urls())
except RuntimeError:
    pass


# =====================================================
# HELPER
# =====================================================

def normalize_yt_url(link: str) -> str:
    if "youtube.com" in link or "youtu.be" in link:
        return link
    return f"https://www.youtube.com/watch?v={link}"


# =====================================================
# 🔥 NEW: FETCH AUDIO FROM YOUR API
# =====================================================

async def fetch_audio_from_api(link: str) -> str | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            API_AUDIO_URL,
            params={"url": link},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            if data.get("status") == "success":
                return data.get("audio")

    return None


# =====================================================
# ✅ REPLACED: download_song (API BASED)
# =====================================================

async def download_song(link: str) -> str | None:
    link = normalize_yt_url(link)

    audio_url = await fetch_audio_from_api(link)
    if not audio_url:
        return None

    # IMPORTANT:
    # returning googlevideo URL (NOT file path)
    return audio_url


# =====================================================
# VIDEO (UNCHANGED – FILE BASED)
# =====================================================

async def download_video(link: str) -> str | None:
    video_id = link.split("v=")[-1].split("&")[0] if "v=" in link else link

    if not video_id or len(video_id) < 3:
        return None

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")

    if os.path.exists(file_path):
        return file_path

    ytdl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
    }

    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            return f"{DOWNLOAD_DIR}/{info['id']}.mp4"

    try:
        return await loop.run_in_executor(None, _download)
    except Exception:
        return None


# =====================================================
# SHELL CMD (AS IS)
# =====================================================

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in errorz.decode().lower():
            return out.decode()
        return errorz.decode()
    return out.decode()


# =====================================================
# YOUTUBE API CLASS (MOSTLY AS IS)
# =====================================================

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Union[str, None]:
        messages = [message]
        if message.reply_to_message:
            messages.append(message.reply_to_message)

        for msg in messages:
            if msg.entities:
                for ent in msg.entities:
                    if ent.type == MessageEntityType.URL:
                        text = msg.text or msg.caption
                        return text[ent.offset : ent.offset + ent.length]
        return None

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        for r in (await results.next())["result"]:
            return {
                "title": r["title"],
                "link": r["link"],
                "vidid": r["id"],
                "duration_min": r["duration"],
                "thumb": r["thumbnails"][0]["url"].split("?")[0],
            }, r["id"]

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        **_
    ):
        if videoid:
            link = self.base + link

        try:
            if video:
                return await download_video(link), True
            else:
                return await download_song(link), True
        except Exception:
            return None, False
