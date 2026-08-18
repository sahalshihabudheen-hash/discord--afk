"""
Main Discord self-bot — listens for DMs and Group DMs, replies with Groq AI.
"""

import discord
import asyncio
import random
from datetime import datetime

from bot.groq_client import GroqClient
from bot.conversation_store import ConversationStore
from bot.gif_library import GifLibrary

# Probability of sending a GIF after a normal reply
from bot.cloud_sync import CloudSync

# Probability of sending a GIF after a normal reply
GIF_CHANCE = 0.30
# Typing delay range (seconds) — makes it feel human
TYPING_MIN = 1.8
TYPING_MAX = 4.5


class AFKBot(discord.Client):
    def __init__(self, config: dict, event_callback=None):
        super().__init__()
        self.config = config
        self.owner_name = config.get("your_name", "Sahal")
        self.groq = GroqClient(config["groq_api_key"], self.owner_name)
        self.gif_lib = GifLibrary()
        self.store = ConversationStore()
        self.afk_mode: bool = config.get("afk_mode", True)
        self.event_callback = event_callback
        self.cloud_sync = CloudSync(
            vercel_url=config.get("vercel_dashboard_url", ""),
            owner_name=self.owner_name,
            store=self.store,
            bot_instance=self,
        )

    # ─── Internal helpers ───────────────────────────────────────────

    def emit(self, event: str, data: dict):
        """Forward an event to the dashboard callback (thread-safe)."""
        if self.event_callback:
            try:
                self.event_callback(event, data)
            except Exception as e:
                print(f"[emit error] {e}")

    def toggle_afk(self, mode: bool):
        self.afk_mode = mode
        status = "ON 🟢" if mode else "OFF 🔴"
        print(f"[AFK] Mode toggled → {status}")
        self.emit("afk_toggle", {"afk_mode": mode, "timestamp": datetime.now().isoformat()})

    # ─── Discord events ──────────────────────────────────────────────

    async def on_ready(self):
        print(f"[Discord] ✅ Logged in as {self.user} (ID: {self.user.id})")
        print(f"[Discord] 🤖 AFK Mode: {'ON' if self.afk_mode else 'OFF'}")
        
        # Start background cloud sync if Vercel URL is configured
        if self.cloud_sync.enabled:
            asyncio.create_task(self.cloud_sync.start())

        self.emit(
            "bot_ready",
            {
                "username": str(self.user),
                "user_id": str(self.user.id),
                "afk_mode": self.afk_mode,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def on_message(self, message: discord.Message):
        # Ignore own messages
        if message.author.id == self.user.id:
            return

        # Only handle DMs and Group DMs — skip all server/guild messages
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_group = isinstance(message.channel, discord.GroupChannel)
        if not (is_dm or is_group):
            return

        # Respect AFK toggle
        if not self.afk_mode:
            return

        user_id = str(message.author.id)
        user_name = message.author.display_name
        is_first = self.store.is_first_message(user_id)
        avatar_url = str(message.author.display_avatar.url) if message.author.display_avatar else None
        channel_type = "DM" if is_dm else "Group DM"

        print(f"[{channel_type}] 📨 {user_name}: {message.content[:80]}")

        # Persist incoming message
        self.store.add_message(user_id, "user", message.content, user_name)
        if avatar_url:
            self.store.set_avatar(user_id, avatar_url)

        # Notify dashboard of incoming message
        self.emit(
            "new_message",
            {
                "user_id": user_id,
                "user_name": user_name,
                "content": message.content,
                "role": "user",
                "channel_type": channel_type,
                "timestamp": datetime.now().isoformat(),
                "avatar": avatar_url,
            },
        )

        try:
            # Show typing indicator + delay
            delay = random.uniform(TYPING_MIN, TYPING_MAX) + len(message.content) * 0.012
            delay = min(delay, 5.0)

            try:
                async with message.channel.typing():
                    await asyncio.sleep(delay)
            except Exception as te:
                print(f"[Typing Notice] {te}")
                await asyncio.sleep(delay)

            history = self.store.get_history(user_id)

            # Get reply from Groq
            reply = await self.groq.get_response(history, user_name=user_name)

            if not reply:
                reply = f"hey {user_name}! {self.owner_name} is away rn, he'll reply as soon as he's back 🙌"

            # Store and send reply (directly quoting the user's message)
            self.store.add_message(user_id, "assistant", reply, user_name)
            try:
                await message.reply(reply, mention_author=False)
            except Exception:
                await message.channel.send(reply)

            print(f"[{channel_type}] 🤖 Bot (replied to {user_name}): {reply[:80]}")

            # Notify dashboard of reply
            self.emit(
                "new_message",
                {
                    "user_id": user_id,
                    "user_name": user_name,
                    "content": reply,
                    "role": "assistant",
                    "channel_type": channel_type,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # ── Maybe send a stored GIF ─────────────────────────
            mood = self.gif_lib.detect_mood_from_text(message.content + " " + reply)
            should_send_gif = (mood == "roast" and random.random() < 0.70) or (random.random() < GIF_CHANCE)

            if should_send_gif:
                gif_url = self.gif_lib.get_random_gif(mood)
                if gif_url:
                    await asyncio.sleep(random.uniform(0.8, 1.6))
                    try:
                        await message.channel.send(gif_url)
                    except Exception as ge:
                        print(f"[GIF Error] {ge}")

                    print(f"[{channel_type}] 🎬 GIF ({mood}) → {user_name}: {gif_url}")
                    self.emit(
                        "new_message",
                        {
                            "user_id": user_id,
                            "user_name": user_name,
                            "content": f"[GIF:{mood}]{gif_url}",
                            "role": "assistant",
                            "channel_type": channel_type,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

            # Push updated stats and conversation list to dashboard
            self.emit("stats_update", self.store.get_stats())
            self.emit("conversations_update", self.store.get_sorted_conversations())

        except Exception as e:
            print(f"[Error] Failed to process message from {user_name}: {e}")
            self.emit("error", {"message": str(e), "timestamp": datetime.now().isoformat()})
