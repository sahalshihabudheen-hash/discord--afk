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
        avatar: str = None,
        convo_name: str = None,
        convo_avatar: str = None,
        attachments: List[str] = None,
        stickers: List[str] = None,
        reactions: List[str] = None,
        message_id: str = None,
        channel_id: str = None,
        reply_to: dict = None,
        channel_type: str = "DM",
    ):
        """Add a message with optional attachments, stickers, reactions, and message ID."""
        if user_id not in self._store:
            self._store[user_id] = {
                "user_name": convo_name or user_name or user_id,
                "channel_id": channel_id,
                "channel_type": channel_type,
                "profile": {
                    "avatar": convo_avatar or avatar,
                    "avatar_decoration": None,
                    "profile_effect": None,
                    "nameplate": None,
                    "banner": None,
                    "status": "offline",
                    "custom_status": None,
                    "bio": None,
                    "handle": convo_name or user_name or user_id,
                },
                "messages": [],
                "last_updated": datetime.now().isoformat(),
                "total_messages": 0,
                "ai_replies": 0,
                "ai_disabled": False,
                "chat_mode": "human",
            }

        convo = self._store[user_id]
        if convo_name:
            convo["user_name"] = convo_name
            if "profile" in convo and isinstance(convo["profile"], dict):
                convo["profile"]["handle"] = convo_name
        if convo_avatar:
            if "profile" in convo and isinstance(convo["profile"], dict):
                convo["profile"]["avatar"] = convo_avatar
        if channel_id:
            convo["channel_id"] = channel_id
        if channel_type:
            convo["channel_type"] = channel_type

        # Ensure ai_disabled exists in convo
        if "ai_disabled" not in convo:
            convo["ai_disabled"] = False

        # Ensure chat_mode exists in convo
        if "chat_mode" not in convo:
            convo["chat_mode"] = "human"

        msg_obj = {
            "id": message_id or f"msg_{datetime.now().timestamp()}",
            "role": role,
            "content": content or "",
            "timestamp": datetime.now().isoformat(),
            "user_name": user_name,
            "avatar": avatar,
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

    def add_reaction(self, user_id: str, message_id: str, emoji_str: str):
        """Record reaction added on a specific message. Falls back to last message if ID not found."""
        if user_id not in self._store:
            return
        msgs = self._store[user_id]["messages"]
        target = None
        # Find the specific message by ID first
        for msg in msgs:
            if msg.get("id") == message_id:
                target = msg
                break
        # Fallback: attach to last message if not found
        if target is None and msgs:
            target = msgs[-1]
        if target is not None:
            if "reactions" not in target:
                target["reactions"] = []
            if emoji_str not in target["reactions"]:
                target["reactions"].append(emoji_str)
            self.save_to_file()

    def get_history(self, user_id: str) -> list:
        """Return message history in OpenAI format for Groq API."""
        if user_id not in self._store:
            return []
        
        convo = self._store[user_id]
        is_group = convo.get("channel_type") == "Group DM"
        
        history = []
        for m in convo["messages"]:
            if not m.get("content") or m.get("is_deleted"):
                continue
            
            role = m["role"]
            content = m["content"]
            
            # Prefix user messages with their name in group DMs so Groq has identity context
            if role == "user" and is_group and m.get("user_name"):
                content = f"[{m['user_name']}]: {content}"
                
            history.append({"role": role, "content": content})
            
        return history

    def is_ai_disabled(self, user_id: str) -> bool:
        if user_id in self._store:
            return self._store[user_id].get("ai_disabled", False)
        return False

    def set_ai_disabled(self, user_id: str, disabled: bool):
        if user_id in self._store:
            self._store[user_id]["ai_disabled"] = disabled
            self.save_to_file()

    def get_chat_mode(self, user_id: str) -> str:
        """Return chat mode: 'human', 'ai', 'extreme_ai', or 'romance'. Defaults to 'human'."""
        if user_id in self._store:
            return self._store[user_id].get("chat_mode", "human")
        return "human"

    def set_chat_mode(self, user_id: str, mode: str):
        """Set chat mode for a conversation. Valid: 'human', 'ai', 'extreme_ai', 'romance'."""
        valid_modes = {"human", "ai", "extreme_ai", "romance"}
        if mode not in valid_modes:
            mode = "human"
        if user_id in self._store:
            self._store[user_id]["chat_mode"] = mode
            self.save_to_file()

    def update_disabled_conversations(self, disabled_ids: list):
        """Update the ai_disabled flag for all conversations based on the list from the cloud."""
        changed = False
        disabled_set = set(disabled_ids)
        for uid, convo in self._store.items():
            should_be_disabled = uid in disabled_set
            if convo.get("ai_disabled", False) != should_be_disabled:
                convo["ai_disabled"] = should_be_disabled
                changed = True
        if changed:
            self.save_to_file()

    def update_chat_modes(self, chat_modes: dict):
        """Update chat_mode for conversations based on the dictionary from the cloud."""
        changed = False
        for uid, mode in chat_modes.items():
            if uid in self._store and self._store[uid].get("chat_mode") != mode:
                self._store[uid]["chat_mode"] = mode
                changed = True
        if changed:
            self.save_to_file()

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
                    "channel_type": data.get("channel_type", "DM"),
                    "profile": profile,
                    "avatar": profile.get("avatar"),
                    "last_updated": data["last_updated"],
                    "total_messages": data["total_messages"],
                    "ai_replies": data["ai_replies"],
                    "last_message": last_msg,
                    "messages": data["messages"],
                    "ai_disabled": data.get("ai_disabled", False),
                    "chat_mode": data.get("chat_mode", "human"),
                }
            )
        result.sort(key=lambda x: x["last_updated"], reverse=True)
        return result
