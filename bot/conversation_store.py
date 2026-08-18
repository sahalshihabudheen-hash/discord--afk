"""
In-memory conversation store — tracks message history per user.
"""

from datetime import datetime
from typing import Optional


class ConversationStore:
    def __init__(self):
        # {user_id: {user_name, messages, last_updated, total_messages, ai_replies}}
        self._store: dict = {}

    def add_message(self, user_id: str, role: str, content: str, user_name: str = None):
        """Add a message to a user's conversation history."""
        if user_id not in self._store:
            self._store[user_id] = {
                "user_name": user_name or user_id,
                "messages": [],
                "last_updated": datetime.now().isoformat(),
                "total_messages": 0,
                "ai_replies": 0,
                "avatar": None,
            }

        convo = self._store[user_id]

        if user_name:
            convo["user_name"] = user_name

        convo["messages"].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        convo["last_updated"] = datetime.now().isoformat()
        convo["total_messages"] += 1

        if role == "assistant":
            convo["ai_replies"] += 1

        # Keep history bounded to last 40 messages (20 exchanges)
        if len(convo["messages"]) > 40:
            convo["messages"] = convo["messages"][-40:]

    def set_avatar(self, user_id: str, avatar_url: str):
        if user_id in self._store:
            self._store[user_id]["avatar"] = avatar_url

    def get_history(self, user_id: str) -> list:
        """Return message history in OpenAI format for Groq API."""
        if user_id not in self._store:
            return []
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self._store[user_id]["messages"]
        ]

    def is_first_message(self, user_id: str) -> bool:
        """True if this is the first ever message from this user."""
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
        """Return all conversations sorted by last activity (newest first)."""
        result = []
        for uid, data in self._store.items():
            last_msg = data["messages"][-1]["content"] if data["messages"] else ""
            result.append(
                {
                    "user_id": uid,
                    "user_name": data["user_name"],
                    "last_updated": data["last_updated"],
                    "total_messages": data["total_messages"],
                    "ai_replies": data["ai_replies"],
                    "last_message": last_msg,
                    "avatar": data.get("avatar"),
                    "messages": data["messages"],
                }
            )
        result.sort(key=lambda x: x["last_updated"], reverse=True)
        return result
