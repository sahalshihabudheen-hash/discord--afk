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

    async def send_manual_message(self, user_id: str, content: str) -> bool:
        """Manually send a message to a user or group DM channel from the dashboard."""
        try:
            convo = self.store.get_conversation(user_id)
            channel_id = convo.get("channel_id") if convo else None
            
            channel = None
            if channel_id:
                try:
                    channel = self.get_channel(int(channel_id))
                    if not channel:
                        channel = await self.fetch_channel(int(channel_id))
                except Exception as ce:
                    print(f"[Manual Send] Could not fetch channel {channel_id}: {ce}")
            
            if not channel:
                try:
                    user = self.get_user(int(user_id))
                    if not user:
                        user = await self.fetch_user(int(user_id))
                    if user:
                        channel = await user.create_dm()
                except Exception as ue:
                    print(f"[Manual Send] Could not fetch user or create DM for {user_id}: {ue}")

            if not channel:
                print(f"[Manual Send] Error: Conversation channel or user not found for {user_id}")
                return False

            await channel.send(content)
            print(f"[Manual Send] Sent message to {user_id} in channel {channel}: {content}")

            self.store.add_message(
                user_id=user_id,
                role="assistant",
                content=content,
                user_name=convo.get("user_name") if convo else None,
                channel_id=str(channel.id)
            )

            self.emit(
                "new_message",
                {
                    "user_id": user_id,
                    "user_name": convo.get("user_name") if convo else user_id,
                    "content": content,
                    "role": "assistant",
                    "channel_type": "DM" if isinstance(channel, discord.DMChannel) else "Group DM",
                    "timestamp": datetime.now().isoformat(),
                },
            )
            self.emit("stats_update", self.store.get_stats())
            self.emit("conversations_update", self.store.get_sorted_conversations())
            return True
        except Exception as e:
            print(f"[Manual Send] Failed to send message: {e}")
            return False

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
        
        # Avatar decoration
        avatar_deco = None
        if hasattr(message.author, "avatar_decoration") and message.author.avatar_decoration:
            avatar_deco = str(message.author.avatar_decoration.url)

        # Status & Custom Status
        status_val = str(getattr(message.author, "status", "offline"))
        custom_status = None
        if hasattr(message.author, "activities"):
            for act in message.author.activities:
                if isinstance(act, discord.CustomActivity) and act.name:
                    custom_status = act.name
                    break

        # Attachments & Stickers
        attachment_urls = [a.url for a in message.attachments if a.url]
        sticker_urls = [s.url for s in getattr(message, "stickers", []) if hasattr(s, "url") and s.url]

        # Capture reply-to context (what message the user replied to)
        reply_to = None
        if message.reference and message.reference.resolved:
            ref = message.reference.resolved
            reply_to = {
                "message_id": str(ref.id),
                "author": ref.author.display_name if ref.author else "Unknown",
                "content": ref.content or "[Media]",
            }

        channel_type = "DM" if is_dm else "Group DM"

        print(f"[{channel_type}] 📨 {user_name}: {message.content[:80] if message.content else '[Media/Attachment]'}")

        # Update full user profile in store
        self.store.update_profile(
            user_id,
            {
                "handle": str(message.author),
                "avatar": avatar_url,
                "avatar_decoration": avatar_deco,
                "status": status_val,
                "custom_status": custom_status,
            },
        )

        # Persist incoming message
        self.store.add_message(
            user_id=user_id,
            role="user",
            content=message.content,
            user_name=user_name,
            attachments=attachment_urls,
            stickers=sticker_urls,
            message_id=str(message.id),
            channel_id=str(message.channel.id),
            reply_to=reply_to,
        )

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
                "avatar_decoration": avatar_deco,
                "status": status_val,
                "custom_status": custom_status,
                "attachments": attachment_urls,
                "stickers": sticker_urls,
                "reply_to": reply_to,
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
            self.store.add_message(
                user_id=user_id,
                role="assistant",
                content=reply,
                user_name=user_name,
                channel_id=str(message.channel.id),
            )
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

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        # Ignore own reactions
        if user.id == self.user.id:
            return

        is_dm = isinstance(reaction.message.channel, discord.DMChannel)
        is_group = isinstance(reaction.message.channel, discord.GroupChannel)
        if not (is_dm or is_group):
            return

        user_id = str(reaction.message.author.id)
        emoji_str = str(reaction.emoji)

        self.store.add_reaction(user_id, emoji_str)
        self.emit("stats_update", self.store.get_stats())
        self.emit("conversations_update", self.store.get_sorted_conversations())

    async def on_message_delete(self, message: discord.Message):
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_group = isinstance(message.channel, discord.GroupChannel)
        if not (is_dm or is_group):
            return

        self.store.mark_deleted(str(message.id))
        self.emit("conversations_update", self.store.get_sorted_conversations())

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        is_dm = isinstance(after.channel, discord.DMChannel)
        is_group = isinstance(after.channel, discord.GroupChannel)
        if not (is_dm or is_group):
            return

        if before.content != after.content:
            self.store.mark_edited(str(after.id), after.content)
            self.emit("conversations_update", self.store.get_sorted_conversations())


