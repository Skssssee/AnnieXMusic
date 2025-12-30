import os
import re
import asyncio
import aiohttp
import aiofiles
from typing import Union
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
# Corrected Import for youtube-search-python
from youtubesearchpython.__future__ import VideosSearch, Playlist
from AnnieXMedia.utils.formatters import time_to_seconds

# --- HELPER FUNCTIONS ---

async def download_song(link: str):
    """Downloads audio using custom API and saves to local storage"""
    if "?si=" in link:
        link = link.split("?si=")[0]
    
    # Extract ID for filename
    video_id = link.split('v=')[-1].split('/')[-1]
    download_folder = "downloads"
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        
    file_path = os.path.join(download_folder, f"{video_id}.mp3")

    if os.path.exists(file_path):
        return file_path
        
    # Your Custom API Endpoint
    api_url = f"http://152.42.187.207:8000/audio?url={link}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if data.get("status") == "success":
                    download_link = data.get("audio")
                    
                    # Async download of the binary file
                    async with session.get(download_link) as file_res:
                        if file_res.status == 200:
                            async with aiofiles.open(file_path, mode='wb') as f:
                                await f.write(await file_res.read())
                            return file_path
        except Exception as e:
            print(f"Error in download_song: {e}")
    return None

# --- MAIN YOUTUBE API CLASS ---

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        url = text[entity.offset : entity.offset + entity.length]
                        return url.split("?si=")[0] if "?si=" in url else url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        search = VideosSearch(link, limit=1)
        resp = await search.next()
        res = resp["result"][0]
        
        title = res["title"]
        duration_min = res["duration"]
        thumbnail = res["thumbnails"][0]["url"].split("?")[0]
        vidid = res["id"]
        duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        
        return title, duration_min, duration_sec, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link

        # Trigger for Audio/Music
        if songaudio or songvideo:
            await mystic.edit_text("📥 **Fetching audio via Custom API...**")
            file_path = await download_song(link)
            if file_path:
                return file_path
            else:
                await mystic.edit_text("❌ **API Download Failed. Falling back to internal...**")
                # Fallback logic could go here
                return None
        return None

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid: link = self.listbase + link
        try:
            plist = Playlist(link)
            # Playlist initialization in this library is slightly different
            while plist.hasMoreVideos:
                await plist.getNextVideos()
                if len(plist.videos) >= limit:
                    break
            return [v['id'] for v in plist.videos[:limit]]
        except:
            return []
            
