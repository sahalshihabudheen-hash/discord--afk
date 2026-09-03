"""
VoiceManager module — detects Discord Voice Channel (VC) presence
and streams YouTube audio into the VC using yt-dlp and FFmpeg.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import discord
import imageio_ffmpeg
import yt_dlp

logger = logging.getLogger("VoiceManager")


def format_duration(seconds: Optional[int]) -> str:
    if not seconds or seconds < 0:
        return "Live / Unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current_channel: Optional[discord.VoiceChannel] = None
        self._ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        # Voice state
        self.in_vc: bool = False
        self.channel_id: Optional[str] = None
        self.channel_name: Optional[str] = None
        self.guild_id: Optional[str] = None
        self.guild_name: Optional[str] = None
        self.self_mute: bool = False
        self.self_deaf: bool = False

        # Music playback state
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.volume: int = 80  # 0 to 100
        self.current_track: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock()

    def get_voice_state(self) -> Dict[str, Any]:
        return {
            "in_vc": self.in_vc,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "guild_id": self.guild_id,
            "guild_name": self.guild_name,
            "self_mute": self.self_mute,
            "self_deaf": self.self_deaf,
        }

    def get_music_state(self) -> Dict[str, Any]:
        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "volume": self.volume,
            "current_track": self.current_track,
        }

    def emit_updates(self):
        """Notify local dashboard and callbacks of voice and music state."""
        self.bot.emit("voice_state_update", self.get_voice_state())
        self.bot.emit("music_state_update", self.get_music_state())

    async def on_voice_state_update(self, before: discord.VoiceState, after: discord.VoiceState):
        """Called when self.user joins, switches, or leaves a voice channel."""
        if after.channel is not None:
            # User joined or switched voice channel
            self.in_vc = True
            self.current_channel = after.channel
            self.channel_id = str(after.channel.id)
            self.channel_name = after.channel.name
            self.guild_id = str(after.channel.guild.id) if hasattr(after.channel, "guild") and after.channel.guild else None
            self.guild_name = after.channel.guild.name if hasattr(after.channel, "guild") and after.channel.guild else "Direct Call"
            self.self_mute = bool(after.self_mute)
            self.self_deaf = bool(after.self_deaf)

            print(f"[Voice] 🎙️ Detected in VC: #{self.channel_name} ({self.guild_name})")
            self.emit_updates()

            # If music is already playing and user switched channels, move voice client
            if self.voice_client and self.voice_client.is_connected() and self.voice_client.channel.id != after.channel.id:
                try:
                    await self.voice_client.move_to(after.channel)
                except Exception as e:
                    print(f"[Voice] Failed to move voice client to new channel: {e}")

        else:
            # User left voice channel
            print(f"[Voice] 🚪 Left voice channel: #{self.channel_name or 'unknown'}")
            await self.cleanup()
            self.emit_updates()

    async def connect_to_vc(self) -> Optional[discord.VoiceClient]:
        """Ensure voice client is connected to current channel."""
        if not self.current_channel:
            return None

        # Check existing voice client for this guild/call
        for vc in self.bot.voice_clients:
            if vc.channel and vc.channel.id == self.current_channel.id:
                self.voice_client = vc
                return self.voice_client

        try:
            if self.voice_client and self.voice_client.is_connected():
                if self.voice_client.channel.id != self.current_channel.id:
                    await self.voice_client.move_to(self.current_channel)
                return self.voice_client

            self.voice_client = await self.current_channel.connect(self_deaf=False, self_mute=False)
            return self.voice_client
        except Exception as e:
            print(f"[Voice] Error connecting to voice channel: {e}")
            return None

    def _extract_youtube_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Synchronously extracts stream URL & metadata with yt-dlp."""
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch",
            "extract_flat": False,
            "js_runtimes": {"node": {}},
        }

        search_query = query if query.startswith("http://") or query.startswith("https://") else f"ytsearch1:{query}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
            except Exception as e:
                print(f"[Voice] yt-dlp extract error: {e}")
                return None

            if not info:
                return None

            if "entries" in info:
                entries = info["entries"]
                if not entries:
                    return None
                entry = entries[0]
            else:
                entry = info

            # Find best direct audio stream URL
            stream_url = entry.get("url")
            if not stream_url and "formats" in entry:
                audio_formats = [f for f in entry["formats"] if f.get("acodec") != "none"]
                if audio_formats:
                    stream_url = audio_formats[-1].get("url")

            if not stream_url:
                return None

            return {
                "title": entry.get("title", "Unknown Title"),
                "url": entry.get("webpage_url") or entry.get("url"),
                "stream_url": stream_url,
                "duration": format_duration(entry.get("duration")),
                "thumbnail": entry.get("thumbnail"),
                "channel": entry.get("uploader") or entry.get("channel") or "YouTube",
            }

    async def play(self, query: str) -> Dict[str, Any]:
        """Play YouTube audio from search query or URL into the VC."""
        async with self._lock:
            if not self.in_vc or not self.current_channel:
                return {
                    "success": False,
                    "error": "You are not in a voice channel! Join a Discord VC first.",
                }

            vc = await self.connect_to_vc()
            if not vc:
                return {
                    "success": False,
                    "error": "Could not connect to the voice channel.",
                }

            # Run audio extraction in worker thread
            loop = asyncio.get_running_loop()
            track_data = await loop.run_in_executor(None, self._extract_youtube_info, query)

            if not track_data or not track_data.get("stream_url"):
                return {
                    "success": False,
                    "error": f"No playable audio found on YouTube for: '{query}'",
                }

            try:
                if vc.is_playing() or vc.is_paused():
                    vc.stop()

                # Build FFmpeg audio stream
                ffmpeg_options = {
                    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    "options": "-vn",
                }

                raw_source = discord.FFmpegPCMAudio(
                    track_data["stream_url"],
                    executable=self._ffmpeg_path,
                    **ffmpeg_options,
                )

                volume_source = discord.PCMVolumeTransformer(raw_source, volume=self.volume / 100.0)

                def after_handler(error):
                    if error:
                        print(f"[Voice] Playback error: {error}")
                    self.is_playing = False
                    self.is_paused = False
                    self.current_track = None
                    self.emit_updates()

                vc.play(volume_source, after=after_handler)

                self.is_playing = True
                self.is_paused = False
                self.current_track = {
                    "title": track_data["title"],
                    "url": track_data["url"],
                    "duration": track_data["duration"],
                    "thumbnail": track_data["thumbnail"],
                    "channel": track_data["channel"],
                }

                print(f"[Voice] ▶️ Now Playing: {track_data['title']} in #{self.channel_name}")
                self.emit_updates()

                return {
                    "success": True,
                    "track": self.current_track,
                }
            except Exception as e:
                print(f"[Voice] Playback setup failed: {e}")
                return {"success": False, "error": str(e)}

    def pause(self) -> bool:
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True
            self.emit_updates()
            return True
        return False

    def resume(self) -> bool:
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused = False
            self.emit_updates()
            return True
        return False

    def stop(self) -> bool:
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_track = None
        self.emit_updates()
        return True

    def set_volume(self, volume: int) -> bool:
        self.volume = max(0, min(100, int(volume)))
        if self.voice_client and self.voice_client.source and hasattr(self.voice_client.source, "volume"):
            self.voice_client.source.volume = self.volume / 100.0
        self.emit_updates()
        return True

    async def cleanup(self):
        """Disconnect and reset all states."""
        self.stop()
        if self.voice_client:
            try:
                if self.voice_client.is_connected():
                    await self.voice_client.disconnect(force=True)
            except Exception:
                pass
            self.voice_client = None

        self.in_vc = False
        self.current_channel = None
        self.channel_id = None
        self.channel_name = None
        self.guild_id = None
        self.guild_name = None
        self.self_mute = False
        self.self_deaf = False
        self.current_track = None
        self.is_playing = False
        self.is_paused = False
