"""
Main Discord self-bot — listens for DMs and Group DMs, replies with Groq AI.
"""

import discord
import asyncio
import random
from datetime import datetime

from bot.groq_client import GroqClient
from bot.conversation_store import ConversationStore
from bot.cloud_sync import CloudSync
from bot.image_generator import ImageGenerator
from bot.rpc_manager import RPCManager
from bot.voice_manager import VoiceManager

# Typing delay range (seconds) — lightning fast replies
TYPING_MIN = 0.2
TYPING_MAX = 0.5


class AFKBot(discord.Client):
    def __init__(self, config: dict, event_callback=None):
        intents = discord.Intents.default()
        intents.guild_voice_states = True   # REQUIRED: receive on_voice_state_update
        intents.guilds = True               # REQUIRED: guild/channel objects resolve properly
        intents.members = True              # Needed to resolve member objects in guilds
        super().__init__(intents=intents)
        self.config = config
        self.owner_name = config.get("your_name", "Sahal")
        self.groq = GroqClient(config["groq_api_key"], self.owner_name)
        self.image_gen = ImageGenerator()
        self.store = ConversationStore()
        self.rpc_manager = RPCManager()
        self.voice_manager = VoiceManager(self)
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

    async def _send_content_chunks(self, channel, content: str, reply_to=None):
        """Send message to Discord, splitting cleanly into chunks <= 1900 chars to avoid Discord 2000 char limit."""
        if not content:
            return

        if len(content) <= 1900:
            if reply_to:
                try:
                    await reply_to.reply(content, mention_author=False)
                    return
                except Exception:
                    pass
            await channel.send(content)
            return

        # Split into chunks around newlines/spaces
        chunks = []
        rem = content
        while len(rem) > 1900:
            split_at = rem[:1900].rfind("\n")
            if split_at == -1 or split_at < 800:
                split_at = rem[:1900].rfind(" ")
            if split_at == -1:
                split_at = 1900
            chunks.append(rem[:split_at].strip())
            rem = rem[split_at:].strip()
        if rem:
            chunks.append(rem)

        for i, chunk in enumerate(chunks):
            if not chunk:
                continue
            if i == 0 and reply_to:
                try:
                    await reply_to.reply(chunk, mention_author=False)
                except Exception:
                    await channel.send(chunk)
            else:
                await channel.send(chunk)
            await asyncio.sleep(0.6)

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

            await self._send_content_chunks(channel, content)
            print(f"[Manual Send] Sent message to {user_id} in channel {channel}: {content[:80]}")

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

    async def aify_and_process_message(self, user_id: str, prompt: str, should_send: bool = True) -> dict:
        """AI-fy a user-typed draft/intent into persona style and optionally send it.
        Works regardless of whether AI auto-replies or AFK mode are turned ON or OFF."""
        try:
            convo = self.store.get_conversation(user_id)
            user_name = convo.get("user_name") if convo else "Friend"
            chat_mode = self.store.get_chat_mode(user_id)
            history = self.store.get_history(user_id)

            aified_text = await self.groq.aify_message(
                user_intent=prompt,
                user_name=user_name,
                chat_mode=chat_mode,
                history=history,
            )
            if not aified_text:
                aified_text = prompt

            if should_send:
                success = await self.send_manual_message(user_id, aified_text)
                return {"success": success, "aified_content": aified_text}
            else:
                return {"success": True, "aified_content": aified_text}
        except Exception as e:
            print(f"[AI-fy Send] Failed: {e}")
            return {"success": False, "error": str(e)}

    # ─── Discord events ──────────────────────────────────────────────

    async def on_ready(self):
        print(f"[Discord] ✅ Logged in as {self.user} (ID: {self.user.id})")
        print(f"[Discord] 🤖 AFK Mode: {'ON' if self.afk_mode else 'OFF'}")
        
        # Start background cloud sync if Vercel URL is configured
        if self.cloud_sync.enabled:
            asyncio.create_task(self.cloud_sync.start())

        # Apply saved custom Discord RPC / status
        await self.apply_rpc()

        self.emit(
            "bot_ready",
            {
                "username": str(self.user),
                "user_id": str(self.user.id),
                "afk_mode": self.afk_mode,
                "rpc_config": self.rpc_manager.current_config,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def apply_rpc(self, config: dict = None) -> bool:
        """Apply custom presence/activity and online status to Discord."""
        try:
            target_config = config if config is not None else self.rpc_manager.current_config
            # Resolve image assets through Discord Media Proxy
            resolved_config = await self.rpc_manager.resolve_external_assets(self, target_config)
            self.rpc_manager.save_config(resolved_config)
            activity, status = self.rpc_manager.build_presence(resolved_config)
            await self.change_presence(activity=activity, status=status)
            cfg = self.rpc_manager.current_config
            print(f"[RPC] Presence updated: {cfg.get('activity_type', 'none')} | {cfg.get('name', 'Custom')} (Status: {status})")
            self.emit("rpc_update", cfg)
            return True
        except Exception as e:
            print(f"[RPC] Failed to update presence: {e}")
            return False

    async def on_voice_state_update(self, member, before: discord.VoiceState, after: discord.VoiceState):
        # Works for both guild Members and User objects (self-bot user accounts)
        member_id = getattr(member, "id", None)
        if self.user and member_id == self.user.id:
            await self.voice_manager.on_voice_state_update(before, after)

    async def execute_music_command(self, action: str, data: dict = None) -> dict:
        data = data or {}
        if action == "play":
            return await self.voice_manager.play(data.get("query", ""))
        elif action == "pause":
            success = self.voice_manager.pause()
            return {"success": success}
        elif action == "resume":
            success = self.voice_manager.resume()
            return {"success": success}
        elif action == "stop":
            success = self.voice_manager.stop()
            return {"success": success}
        elif action == "volume":
            success = self.voice_manager.set_volume(data.get("volume", 80))
            return {"success": success}
        return {"success": False, "error": f"Unknown action: {action}"}

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

        # Resolve conversation ID, name, avatar and type
        channel_type = "DM" if is_dm else "Group DM"
        if is_group:
            convo_id = str(message.channel.id)
            if message.channel.name:
                convo_name = message.channel.name
            else:
                convo_name = ", ".join(u.display_name for u in message.channel.recipients)
            convo_avatar = str(message.channel.icon.url) if message.channel.icon else None
        else:
            convo_id = str(message.author.id)
            convo_name = message.author.display_name
            convo_avatar = str(message.author.display_avatar.url) if message.author.display_avatar else None

        user_name = message.author.display_name
        is_first = self.store.is_first_message(convo_id)
        avatar_url = str(message.author.display_avatar.url) if message.author.display_avatar else None

        # Avatar decoration
        avatar_deco = None
        if hasattr(message.author, "avatar_decoration") and message.author.avatar_decoration:
            avatar_deco = str(message.author.avatar_decoration.url)

        # Profile Effect (animated background overlay)
        profile_effect = None
        try:
            if hasattr(message.author, "profile_effect") and message.author.profile_effect:
                pe = message.author.profile_effect
                if hasattr(pe, "url"):
                    profile_effect = str(pe.url)
                elif hasattr(pe, "id"):
                    # Construct CDN URL from the effect ID
                    profile_effect = f"https://cdn.discordapp.com/profile-effects/{pe.id}/effect.png"
        except Exception:
            pass

        # Nameplate (collectibles badge strip)
        nameplate = None
        try:
            if hasattr(message.author, "collectibles") and message.author.collectibles:
                coll = message.author.collectibles
                if hasattr(coll, "nameplate") and coll.nameplate:
                    np = coll.nameplate
                    if hasattr(np, "asset"):
                        nameplate = str(np.asset)
                    elif hasattr(np, "url"):
                        nameplate = str(np.url)
        except Exception:
            pass

        # Banner
        banner_url = None
        try:
            if hasattr(message.author, "banner") and message.author.banner:
                banner_url = str(message.author.banner.url)
        except Exception:
            pass

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

        print(f"[{channel_type}] 📨 {user_name} in {convo_name}: {message.content[:80] if message.content else '[Media/Attachment]'}")

        # Update full conversation/user profile in store
        if is_group:
            profile_to_update = {
                "handle": convo_name,
                "avatar": convo_avatar,
            }
        else:
            profile_to_update = {
                "handle": str(message.author),
                "avatar": avatar_url,
                "avatar_decoration": avatar_deco,
                "profile_effect": profile_effect,
                "nameplate": nameplate,
                "banner": banner_url,
                "status": status_val,
                "custom_status": custom_status,
            }
        self.store.update_profile(convo_id, profile_to_update)

        # Persist incoming message
        self.store.add_message(
            user_id=convo_id,
            role="user",
            content=message.content,
            user_name=user_name,
            avatar=avatar_url,
            convo_name=convo_name,
            convo_avatar=convo_avatar,
            attachments=attachment_urls,
            stickers=sticker_urls,
            message_id=str(message.id),
            channel_id=str(message.channel.id),
            reply_to=reply_to,
            channel_type=channel_type,
        )

        # Notify dashboard of incoming message
        self.emit(
            "new_message",
            {
                "user_id": convo_id,
                "user_name": user_name,
                "convo_name": convo_name,
                "convo_avatar": convo_avatar,
                "content": message.content,
                "role": "user",
                "channel_type": channel_type,
                "timestamp": datetime.now().isoformat(),
                "avatar": avatar_url,
                "avatar_decoration": avatar_deco if not is_group else None,
                "profile_effect": profile_effect if not is_group else None,
                "nameplate": nameplate if not is_group else None,
                "banner": banner_url if not is_group else None,
                "status": status_val if not is_group else "online",
                "custom_status": custom_status if not is_group else None,
                "attachments": attachment_urls,
                "stickers": sticker_urls,
                "reply_to": reply_to,
            },
        )

        if self.store.is_ai_disabled(convo_id):
            print(f"[AFK] 🚫 AI replies are disabled for {convo_name} ({convo_id}). Skipping auto-reply.")
            return

        try:
            # Collect image URLs from attachments for vision analysis
            image_urls = [
                a.url for a in message.attachments
                if a.content_type and a.content_type.startswith("image/")
            ]

            # Show typing indicator + delay (lightning fast)
            delay = random.uniform(TYPING_MIN, TYPING_MAX)

            try:
                async with message.channel.typing():
                    await asyncio.sleep(delay)
            except Exception as te:
                print(f"[Typing Notice] {te}")
                await asyncio.sleep(delay)

            history = self.store.get_history(convo_id)
            chat_mode = self.store.get_chat_mode(convo_id)

            # ── Check if user is requesting image generation ──────────────
            image_prompt = self.image_gen.extract_image_prompt(message.content or "")
            if not image_prompt and message.content and any(w in message.content.lower() for w in ["image", "draw", "picture", "photo", "pic", "paint", "render", "artwork"]):
                image_prompt = await self.groq.extract_image_prompt_ai(message.content)

            if image_prompt:
                print(f"[{channel_type}] 🎨 Generating image for prompt: '{image_prompt}' in mode [{chat_mode}]")
                try:
                    img_buffer, direct_url = await self.image_gen.generate_image(image_prompt)
                except Exception as ige:
                    print(f"[ImageGen Error] {ige}")
                    img_buffer, direct_url = None, ""

                if img_buffer:
                    if chat_mode == "extreme_ai":
                        caption = f"🚀 Generated your custom AI artwork! 🎨✨\n**Prompt:** *{image_prompt}*\nRendered with FLUX AI! 🔥"
                    elif chat_mode == "ai":
                        caption = f"Here's the image you requested! 🎨✨ ({image_prompt})"
                    elif chat_mode == "romance":
                        caption = f"Made this lovely artwork specially for you, sweetie ❤️✨\n*{image_prompt}* 🌹💫"
                    else:
                        caption = random.choice(["here bro", "made this for u", "there u go", "done bro"])

                    d_file = discord.File(fp=img_buffer, filename="generated_artwork.png")
                    sent_msg = None
                    try:
                        sent_msg = await message.reply(caption, file=d_file, mention_author=False)
                    except Exception:
                        sent_msg = await message.channel.send(caption, file=d_file)

                    attached_urls = []
                    if sent_msg and getattr(sent_msg, "attachments", None):
                        attached_urls = [a.url for a in sent_msg.attachments if a.url]
                    if not attached_urls and direct_url:
                        attached_urls = [direct_url]

                    self.store.add_message(
                        user_id=convo_id,
                        role="assistant",
                        content=caption,
                        user_name=user_name,
                        convo_name=convo_name,
                        convo_avatar=convo_avatar,
                        attachments=attached_urls,
                        channel_id=str(message.channel.id),
                        channel_type=channel_type,
                    )
                    self.emit(
                        "new_message",
                        {
                            "user_id": convo_id,
                            "user_name": user_name,
                            "convo_name": convo_name,
                            "convo_avatar": convo_avatar,
                            "content": caption,
                            "role": "assistant",
                            "attachments": attached_urls,
                            "channel_type": channel_type,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                    self.emit("stats_update", self.store.get_stats())
                    self.emit("conversations_update", self.store.get_sorted_conversations())
                    return

            # Get reply from Groq based on conversation chat_mode
            reply = await self.groq.get_response(
                history,
                user_name=user_name,
                image_urls=image_urls if image_urls else None,
                chat_mode=chat_mode,
            )

            if not reply:
                if chat_mode == "extreme_ai":
                    reply = f"Hey {user_name}! 🤖 I'm on it! {self.owner_name} is away right now but your message is logged! 💬✨"
                elif chat_mode == "ai":
                    reply = f"Hey {user_name}! {self.owner_name} is AFK right now, but I'll make sure he sees this 🙌"
                elif chat_mode == "romance":
                    reply = f"Aww {user_name}, I'm right here with you~ sending you sweet hugs and kisses! 💖💋"
                else:
                    reply = f"yo {user_name}! been kinda tied up rn, hit me up later"

            # Store and send reply (directly quoting the user's message)
            self.store.add_message(
                user_id=convo_id,
                role="assistant",
                content=reply,
                user_name=user_name,
                convo_name=convo_name,
                convo_avatar=convo_avatar,
                channel_id=str(message.channel.id),
                channel_type=channel_type,
            )
            # Send reply safely, splitting into parts if exceeding Discord's 2000 character limit
            await self._send_content_chunks(message.channel, reply, reply_to=message)

            print(f"[{channel_type}] 🤖 Bot [{chat_mode}] (replied in {convo_name}): {reply[:80]}")

            # Notify dashboard of reply
            self.emit(
                "new_message",
                {
                    "user_id": convo_id,
                    "user_name": user_name,
                    "convo_name": convo_name,
                    "convo_avatar": convo_avatar,
                    "content": reply,
                    "role": "assistant",
                    "channel_type": channel_type,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Push updated stats and conversation list to dashboard
            self.emit("stats_update", self.store.get_stats())
            self.emit("conversations_update", self.store.get_sorted_conversations())

        except Exception as e:
            print(f"[Error] Failed to process message from {user_name} in {convo_name}: {e}")
            self.emit("error", {"message": str(e), "timestamp": datetime.now().isoformat()})

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        # Ignore own reactions
        if user.id == self.user.id:
            return

        is_dm = isinstance(reaction.message.channel, discord.DMChannel)
        is_group = isinstance(reaction.message.channel, discord.GroupChannel)
        if not (is_dm or is_group):
            return

        # Determine the conversation owner: the channel ID for Group DM or user ID for DM
        if is_group:
            convo_id = str(reaction.message.channel.id)
        else:
            if reaction.message.author.id == self.user.id:
                convo_id = str(user.id)
            else:
                convo_id = str(reaction.message.author.id)

        message_id = str(reaction.message.id)
        emoji_str = str(reaction.emoji)

        print(f"[Reaction] {user.display_name} reacted {emoji_str} to message {message_id} in conversation {convo_id}")
        self.store.add_reaction(convo_id, message_id, emoji_str)
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


