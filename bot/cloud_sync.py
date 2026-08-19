"""
Cloud sync module — synchronizes conversation state with Vercel web app.
"""

import asyncio
import aiohttp
from datetime import datetime


class CloudSync:
    def __init__(self, vercel_url: str, owner_name: str, store, bot_instance=None):
        self.vercel_url = vercel_url.rstrip("/") if vercel_url else ""
        self.owner_name = owner_name
        self.store = store
        self.bot = bot_instance
        self._running = False
        self._sync_interval = 4.0  # sync every 4 seconds

    @property
    def enabled(self) -> bool:
        return bool(self.vercel_url and self.vercel_url.startswith("http"))

    async def start(self):
        """Background loop to periodically sync state with Vercel and check for remote AFK toggles."""
        if not self.enabled:
            return

        self._running = True
        print(f"[Cloud Sync] ☁️  Syncing with Vercel: {self.vercel_url}")

        while self._running:
            try:
                await self.sync_once()
            except Exception as e:
                # Silently catch transient network errors
                pass
            await asyncio.sleep(self._sync_interval)

    def stop(self):
        self._running = False

    async def sync_once(self):
        """Push full state to Vercel and apply any remote AFK toggle."""
        if not self.enabled:
            return

        payload = {
            "owner_name": self.owner_name,
            "stats": self.store.get_stats(),
            "conversations": self.store.get_sorted_conversations(),
            "timestamp": datetime.now().isoformat(),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.vercel_url}/api/sync",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    cloud_afk = data.get("afk_mode")

                    # If user toggled AFK on the Vercel mobile web app, update local bot!
                    if self.bot and cloud_afk is not None and cloud_afk != self.bot.afk_mode:
                        self.bot.toggle_afk(cloud_afk)

                    # Process blocked conversations / disabled AI replies from cloud
                    disabled_convo_ids = data.get("disabled_convo_ids", [])
                    if self.bot and hasattr(self.bot, "store"):
                        self.bot.store.update_disabled_conversations(disabled_convo_ids)

                    # Process pending manual messages sent from Vercel web app
                    pending_msgs = data.get("pending_messages", [])
                    if pending_msgs and self.bot:
                        for msg in pending_msgs:
                            user_id = msg.get("user_id")
                            content = msg.get("content")
                            if user_id and content:
                                asyncio.create_task(self.bot.send_manual_message(user_id, content))
