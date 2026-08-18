"""
In-memory conversation store — tracks rich Discord profiles and message history.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class ConversationStore:
    def __init__(self):
        # {user_id: {user_name, profile, messages, last_updated, total_messages, ai_replies}}
        self._store: dict = {}

    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        user_name: str = None,
        attachments: List[str] = None,
        stickers: List[str] = None,
        reactions: List[str] = None,
    ):
        """Add a message with optional attachments, stickers, and reactions."""
        if user_id not in self._store:
            self._store[user_id] = {
                "user_name": user_name or user_id,
                "profile": {
                    "avatar": None,
                    "avatar_decoration": None,
                    "banner": None,
                    "status": "offline",
                    "custom_status": None,
                    "bio": None,
                    "handle": user_name or user_id,
                },
                "messages": [],
                "last_updated": datetime.now().isoformat(),
                "total_messages": 0,
                "ai_replies": 0,
            }

        convo = self._store[user_id]
        if user_name:
            convo["user_name"] = user_name

        convo["messages"].append(
            {
                "role": role,
                "content": content or "",
                "timestamp": datetime.now().isoformat(),
                "attachments": attachments or [],
                "stickers": stickers or [],
                "reactions": reactions or [],
            }
        )
        convo["last_updated"] = datetime.now().isoformat()
        convo["total_messages"] += 1

        if role == "assistant":
            convo["ai_replies"] += 1

        # Keep history bounded to last 50 messages
        if len(convo["messages"]) > 50:
            convo["messages"] = convo["messages"][-50:]

    def update_profile(self, user_id: str, profile_data: Dict[str, Any]):
        """Update Discord profile metadata for a user."""
        if user_id not in self._store:
            self._store[user_id] = {
                "user_name": profile_data.get("handle") or user_id,
                "profile": {},
                "messages": [],
                "last_updated": datetime.now().isoformat(),
                "total_messages": 0,
                "ai_replies": 0,
            }
        
        current_profile = self._store[user_id].setdefault("profile", {})
        for k, v in profile_data.items():
            if v is not None:
                current_profile[k] = v

    def add_reaction(self, user_id: str, emoji_str: str):
        """Record reaction added in conversation."""
        if user_id in self._store and self._store[user_id]["messages"]:
            last_msg = self._store[user_id]["messages"][-1]
            if "reactions" not in last_msg:
                last_msg["reactions"] = []
            if emoji_str not in last_msg["reactions"]:
                last_msg["reactions"].append(emoji_str)

    def get_history(self, user_id: str) -> list:
        """Return message history in OpenAI format for Groq API."""
        if user_id not in self._store:
            return []
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self._store[user_id]["messages"]
            if m["content"]
        ]

    def is_first_message(self, user_id: str) -> bool:
        return user_id not in self._store

    def get_all(self) -> dict:
        return self._store

    def get_conversation(self, user_id: str) -> Optional[dict]:
        return self._store.get(user_id)

    def get_stats(self) -> dict:
        total_msgs = sum(c["total_messages"] for c in self._store.values())
        total_replies = sum(c["ai_replies"] for c in self._store.values())
        return {
            "total_conversations": len(self._store),
            "total_messages": total_msgs,
            "total_ai_replies": total_replies,
        }

    def get_sorted_conversations(self) -> list:
        """Return all conversations sorted with full profile and media data."""
        result = []
        for uid, data in self._store.items():
            last_msg = ""
            if data["messages"]:
                lm = data["messages"][-1]
                if lm.get("attachments"):
                    last_msg = "📷 [Attachment / Media]"
                elif lm.get("stickers"):
                    last_msg = "🎨 [Sticker]"
                else:
                    last_msg = lm.get("content", "")

            profile = data.get("profile", {})
            result.append(
                {
                    "user_id": uid,
                    "user_name": data["user_name"],
                    "profile": profile,
                    "avatar": profile.get("avatar"),
                    "last_updated": data["last_updated"],
                    "total_messages": data["total_messages"],
                    "ai_replies": data["ai_replies"],
                    "last_message": last_msg,
                    "messages": data["messages"],
                }
            )
        result.sort(key=lambda x: x["last_updated"], reverse=True)
        return result
