"""
Discord RPC & Activity Status Manager — handles building custom Discord activities,
status modes (online/idle/dnd/invisible), timestamps, and JSON persistence.
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import discord


DEFAULT_RPC_CONFIG = {
    "enabled": True,
    "activity_type": "playing",  # playing, listening, watching, streaming, competing, custom, none
    "name": "Writing assignment",
    "details": "Chapter 4 Draft",
    "state": "Final Polish",
    "emoji": "📝",
    "stream_url": "",
    "status": "dnd",  # online, idle, dnd, invisible
    "show_timestamp": True,
    "start_time": None,
}


class RPCManager:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "rpc_config.json"
            )
        self.config_path = config_path
        self.current_config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load RPC config from JSON file, or fallback to defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    config = {**DEFAULT_RPC_CONFIG, **data}
                    return config
            except Exception as e:
                print(f"[RPCManager] Error loading {self.config_path}: {e}")
        return dict(DEFAULT_RPC_CONFIG)

    def save_config(self, config: Dict[str, Any]):
        """Save RPC config to JSON file."""
        self.current_config = {**self.current_config, **config}
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.current_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[RPCManager] Error saving {self.config_path}: {e}")

    def build_presence(self, config: Optional[Dict[str, Any]] = None) -> Tuple[Optional[discord.BaseActivity], discord.Status]:
        """
        Build discord.Activity and discord.Status from config dict.
        Returns (activity, status).
        """
        cfg = config if config is not None else self.current_config

        # ── 1. Resolve Status ─────────────────────────────────────────
        status_str = (cfg.get("status") or "online").lower()
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "busy": discord.Status.dnd,
            "do_not_disturb": discord.Status.dnd,
            "invisible": discord.Status.invisible,
            "offline": discord.Status.invisible,
        }
        status = status_map.get(status_str, discord.Status.online)

        if not cfg.get("enabled", True):
            return None, status

        # ── 2. Resolve Activity Type ──────────────────────────────────
        act_type = (cfg.get("activity_type") or "playing").lower()
        name = (cfg.get("name") or "").strip()
        details = (cfg.get("details") or "").strip() or None
        state = (cfg.get("state") or "").strip() or None
        emoji = (cfg.get("emoji") or "").strip() or None
        stream_url = (cfg.get("stream_url") or "").strip() or None
        show_timestamp = cfg.get("show_timestamp", False)

        timestamps = None
        if show_timestamp:
            start_t = cfg.get("start_time")
            if not start_t:
                start_t = int(time.time() * 1000)
                cfg["start_time"] = start_t
            elif int(start_t) < 10000000000:
                start_t = int(start_t) * 1000
            timestamps = {"start": int(start_t)}

        if act_type == "none" or (not name and act_type != "custom"):
            return None, status

        # Custom status (Emoji + text)
        if act_type == "custom":
            custom_name = name or state or details or "Busy"
            try:
                activity = discord.CustomActivity(name=custom_name, emoji=emoji)
            except Exception:
                activity = discord.Activity(
                    type=discord.ActivityType.custom,
                    name="Custom Status",
                    state=custom_name,
                )
            return activity, status

        # Streaming
        if act_type == "streaming":
            valid_url = stream_url if (stream_url and ("twitch.tv" in stream_url or "youtube.com" in stream_url)) else "https://twitch.tv/discord"
            activity = discord.Streaming(
                name=name or "Streaming Live",
                url=valid_url,
                details=details,
                state=state,
            )
            return activity, status

        # ActivityType mappings
        type_mapping = {
            "playing": discord.ActivityType.playing,
            "listening": discord.ActivityType.listening,
            "watching": discord.ActivityType.watching,
            "competing": discord.ActivityType.competing,
        }

        discord_act_type = type_mapping.get(act_type, discord.ActivityType.playing)

        kwargs: Dict[str, Any] = {
            "type": discord_act_type,
            "name": name,
        }
        if details:
            kwargs["details"] = details
        if state:
            kwargs["state"] = state
        if timestamps:
            kwargs["timestamps"] = timestamps

        activity = discord.Activity(**kwargs)
        return activity, status
