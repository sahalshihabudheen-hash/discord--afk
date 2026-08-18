"""
In-memory conversation store — tracks rich Discord profiles, messages, deleted/ghost messages, and edits.
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


class ConversationStore:
    def __init__(self):
        # {user_id: {user_name, profile, messages, last_updated, total_messages, ai_replies}}
        self.file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "conversations.json")
        self._store: dict = {}
        self.load_from_file()

    def load_from_file(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._store = json.load(f)
                print(f"[Store] Loaded conversations from {self.file_path}")
            except Exception as e:
                print(f"[Store] Error loading conversations: {e}")
                self._store = {}
        else:
            self._store = {}

    def save_to_file(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._store, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Store] Error saving conversations: {e}")

    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        user_name: str = None,
        attachments: List[str] = None,
        stickers: List[str] = None,
        reactions: List[str] = None,
        message_id: str = None,
        channel_id: str = None,
        reply_to: dict = None,
    ):
        """Add a message with optional attachments, stickers, reactions, and message ID."""
        if user_id not in self._store:
            self._store[user_id] = {
                "user_name": user_name or user_id,
                "channel_id": channel_id,
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
        if channel_id:
            convo["channel_id"] = channel_id

        msg_obj = {
            "id": message_id or f"msg_{datetime.now().timestamp()}",
            "role": role,
            "content": content or "",
            "timestamp": datetime.now().isoformat(),
            "attachments": attachments or [],
            "stickers": stickers or [],
            "reactions": reactions or [],
            "is_deleted": False,
            "deleted_at": None,
            "is_edited": False,
            "original_content": None,
            "reply_to": reply_to or None,
        }

        convo["messages"].append(msg_obj)
        convo["last_updated"] = datetime.now().isoformat()
        convo["total_messages"] += 1

        if role == "assistant":
            convo["ai_replies"] += 1

        # Keep history bounded to last 60 messages
        if len(convo["messages"]) > 60:
            convo["messages"] = convo["messages"][-60:]

        self.save_to_file()

    def mark_deleted(self, message_id: str):
        """Ghost message tracker: when someone deletes a message in Discord, we keep it and flag it."""
        for convo in self._store.values():
            for msg in convo["messages"]:
                if msg.get("id") == str(message_id):
                    msg["is_deleted"] = True
                    msg["deleted_at"] = datetime.now().isoformat()
                    self.save_to_file()
                    return

    def mark_edited(self, message_id: str, new_content: str):
        """Track edited messages while keeping the original text."""
        for convo in self._store.values():
            for msg in convo["messages"]:
                if msg.get("id") == str(message_id):
                    if not msg.get("is_edited"):
                        msg["original_content"] = msg.get("content")
                    msg["content"] = new_content
                    msg["is_edited"] = True
                    msg["edited_at"] = datetime.now().isoformat()
                    self.save_to_file()
                    return

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
        self.save_to_file()

    def add_reaction(self, user_id: str, emoji_str: str):
        """Record reaction added in conversation."""
        if user_id in self._store and self._store[user_id]["messages"]:
            last_msg = self._store[user_id]["messages"][-1]
            if "reactions" not in last_msg:
                last_msg["reactions"] = []
            if emoji_str not in last_msg["reactions"]:
                last_msg["reactions"].append(emoji_str)
            self.save_to_file()

    def get_history(self, user_id: str) -> list:
        """Return message history in OpenAI format for Groq API."""
        if user_id not in self._store:
            return []
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self._store[user_id]["messages"]
            if m.get("content") and not m.get("is_deleted")
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
        """Return all conversations sorted with full profile, media, and ghost messages."""
        result = []
        for uid, data in self._store.items():
            last_msg = ""
            if data["messages"]:
                lm = data["messages"][-1]
                if lm.get("is_deleted"):
                    last_msg = f"🗑️ [Deleted]: {lm.get('content', '')}"
                elif lm.get("attachments"):
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
                    "channel_id": data.get("channel_id"),
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
