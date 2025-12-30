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
from youtubesearchpython import VideosSearch


AUDIO_API = "http://152.42.187.207:8000/audio"


# ---------------- HELPERS ----------------

def normalize_yt_url(link: str) -> str:
    if "youtube.com" in link or "youtu.be" in link:
        return link
    return f"https://www.youtube.com/watch?v={link}"


# ---------------- AUDIO ----------------
# RETURNS: str | None (NO BOOL)

async def download_song(link: str) -> Union[str, None]:
    link = normalize_yt_url(link)

    async with aiohttp.ClientSession() as session:
        async with session.get(
            AUDIO_API,
            params={"url": link},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            if data.get("status") == "success":
                return data.get("audio")

    return None


# ---------------- VIDEO ----------------
# RETURNS: filepath | None

async def download_video(link: str) -> Union[str, None]:
    link = normalize_yt_url(link)
    video_id = link.split("v=")[-1].split("&")[0]

    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{video_id}.mp4"

    if os.path.exists(file_path):
        return file_path

    ytdl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
    }

    loop = asyncio.get_event_loop()

    def _dl():
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            return f"downloads/{info['id']}.mp4"

    try:
        return await loop.run_in_executor(None, _dl)
    except Exception:
        return None


# ---------------- YOUTUBE API ----------------
# 🔥 RETURNS ONLY str | None (NO tuple, NO bool)

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="

    async def url(self, message: Message) -> Union[str, None]:
        msgs = [message]
        if message.reply_to_message:
            msgs.append(message.reply_to_message)

        for msg in msgs:
            if msg.entities:
                for ent in msg.entities:
                    if ent.type == MessageEntityType.URL:
                        text = msg.text or msg.caption
                        return text[ent.offset : ent.offset + ent.length]
        return None

    async def track(self, link: str):
        results = VideosSearch(link, limit=1)
        for r in (await results.next())["result"]:
            return {
                "title": r["title"],
                "vidid": r["id"],
                "duration": r["duration"],
                "thumb": r["thumbnails"][0]["url"],
            }

    async def download(self, link: str, video: bool = False):
        try:
            if video:
                return await download_video(link)
            else:
                return await download_song(link)
        except Exception as e:
            LOGGER("YouTubeAPI").error(e)
            return None
