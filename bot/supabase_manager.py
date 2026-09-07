"""
Supabase Manager — Handles direct cloud database persistence and media storage for the AFK Discord bot.
Provides zero-locking, high-speed cloud synchronization with the Next.js Vercel web app.
"""

import os
import aiohttp
import json
from typing import Optional, Dict, Any, List

class SupabaseManager:
    def __init__(self, url: str = None, key: str = None):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.enabled = bool(self.url and self.key and self.url.startswith("http"))
        if self.enabled:
            print(f"[Supabase] Connected to {self.url}")
        else:
            print("[Supabase] Supabase credentials not found, running with local store only")

    def _headers(self, prefer_upsert: bool = False) -> Dict[str, str]:
        h = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if prefer_upsert:
            h["Prefer"] = "resolution=merge-duplicates"
        return h

    async def save_conversation(self, convo_data: Dict[str, Any]) -> bool:
        """Upsert a single conversation into Supabase conversations table."""
        if not self.enabled:
            return False

        user_id = convo_data.get("user_id")
        if not user_id:
            return False

        payload = {
            "user_id": str(user_id),
            "user_name": convo_data.get("user_name") or str(user_id),
            "channel_id": str(convo_data.get("channel_id") or ""),
            "channel_type": convo_data.get("channel_type", "DM"),
            "profile": convo_data.get("profile", {}),
            "last_updated": convo_data.get("last_updated"),
            "total_messages": convo_data.get("total_messages", 0),
            "ai_replies": convo_data.get("ai_replies", 0),
            "ai_disabled": bool(convo_data.get("ai_disabled", False)),
            "chat_mode": convo_data.get("chat_mode", "human"),
            "busy_notice_sent": bool(convo_data.get("busy_notice_sent", False)),
            "messages": convo_data.get("messages", []),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/rest/v1/conversations",
                    headers=self._headers(prefer_upsert=True),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status in (200, 201):
                        return True
                    else:
                        # Log error once or on failure
                        err_text = await resp.text()
                        if "schema cache" in err_text:
                            # Table not created yet
                            pass
                        else:
                            print(f"[Supabase] Upsert error ({resp.status}): {err_text[:200]}")
        except Exception as e:
            # Silently pass transient network hiccups
            pass
        return False

    async def sync_all_conversations(self, convos: List[Dict[str, Any]]) -> bool:
        """Bulk upsert conversations into Supabase."""
        if not self.enabled or not convos:
            return False

        records = []
        for c in convos:
            records.append({
                "user_id": str(c["user_id"]),
                "user_name": c.get("user_name") or str(c["user_id"]),
                "channel_id": str(c.get("channel_id") or ""),
                "channel_type": c.get("channel_type", "DM"),
                "profile": c.get("profile", {}),
                "last_updated": c.get("last_updated"),
                "total_messages": c.get("total_messages", 0),
                "ai_replies": c.get("ai_replies", 0),
                "ai_disabled": bool(c.get("ai_disabled", False)),
                "chat_mode": c.get("chat_mode", "human"),
                "busy_notice_sent": bool(c.get("busy_notice_sent", False)),
                "messages": c.get("messages", []),
            })

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/rest/v1/conversations",
                    headers=self._headers(prefer_upsert=True),
                    json=records,
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as resp:
                    return resp.status in (200, 201)
        except Exception:
            pass
        return False

    async def set_state(self, key: str, value: Any) -> bool:
        """Upsert a key-value pair in bot_state table."""
        if not self.enabled:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/rest/v1/bot_state",
                    headers=self._headers(prefer_upsert=True),
                    json={"key": key, "value": value},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    return resp.status in (200, 201)
        except Exception:
            pass
        return False

    async def get_state(self, key: str) -> Optional[Any]:
        """Fetch a value from bot_state table."""
        if not self.enabled:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.url}/rest/v1/bot_state?key=eq.{key}&select=value",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            return data[0].get("value")
        except Exception:
            pass
        return None

    async def upload_media(self, data: bytes, filename: str, content_type: str = "image/png") -> Optional[str]:
        """Upload image/video to Supabase Storage 'media' bucket and return public URL."""
        if not self.enabled or not data:
            return None

        clean_name = "".join(c for c in filename if c.isalnum() or c in "._-")
        storage_path = f"{self.url}/storage/v1/object/media/{clean_name}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    storage_path,
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status in (200, 201):
                        public_url = f"{self.url}/storage/v1/object/public/media/{clean_name}"
                        return public_url
                    else:
                        print(f"[Supabase Storage] Upload error ({resp.status}): {await resp.text()[:200]}")
        except Exception as e:
            print(f"[Supabase Storage] Upload exception: {e}")
        return None
