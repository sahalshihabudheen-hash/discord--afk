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


DEFAULT_APP_ID = 1107567406834167859

DEFAULT_ICONS = {
    "competing": "https://cdn-icons-png.flaticon.com/512/3112/3112946.png",  # Trophy
    "playing": "https://cdn-icons-png.flaticon.com/512/3238/3238016.png",    # Assignment/Notebook
    "listening": "https://cdn-icons-png.flaticon.com/512/3845/3845876.png",  # Headphones/Music
    "watching": "https://cdn-icons-png.flaticon.com/512/3074/3074767.png",   # Monitor/Study
    "streaming": "https://cdn-icons-png.flaticon.com/512/5968/5968819.png",  # Twitch/Live
}

DEFAULT_RPC_CONFIG = {
    "enabled": True,
    "activity_type": "playing",  # playing, listening, watching, streaming, competing, custom, none
    "name": "Writing assignment",
    "details": "Chapter 4 Draft",
    "state": "Final Polish",
    "emoji": "📝",
    "application_id": DEFAULT_APP_ID,
    "large_image": "https://cdn-icons-png.flaticon.com/512/3238/3238016.png",
    "large_text": "Writing Assignment",
    "small_image": "",
    "small_text": "",
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
        self.proxy_cache: Dict[str, str] = {}

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

    async def resolve_external_assets(self, client: discord.Client, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Proxy external image URLs through Discord's media proxy so they render properly in Discord clients.
        """
        cfg = dict(config)
        app_id = int(cfg.get("application_id") or DEFAULT_APP_ID)
        act_type = (cfg.get("activity_type") or "playing").lower()

        large_img = (cfg.get("large_image") or "").strip()
        if not large_img and act_type in DEFAULT_ICONS:
            large_img = DEFAULT_ICONS[act_type]

        small_img = (cfg.get("small_image") or "").strip()

        # Check and proxy large_image
        if large_img and (large_img.startswith("http://") or large_img.startswith("https://")):
            if not ("media.discordapp.net" in large_img or "cdn.discordapp.com" in large_img):
                if large_img in self.proxy_cache:
                    cfg["large_image"] = self.proxy_cache[large_img]
                else:
                    try:
                        proxied = await client.proxy_external_application_assets(app_id, large_img)
                        if proxied and len(proxied) > 0:
                            self.proxy_cache[large_img] = proxied[0]
                            cfg["large_image"] = proxied[0]
                            print(f"[RPCManager] Proxied large_image: {proxied[0]}")
                    except Exception as e:
                        print(f"[RPCManager] Failed to proxy large_image '{large_img}': {e}")
            else:
                cfg["large_image"] = large_img

        # Check and proxy small_image
        if small_img and (small_img.startswith("http://") or small_img.startswith("https://")):
            if not ("media.discordapp.net" in small_img or "cdn.discordapp.com" in small_img):
                if small_img in self.proxy_cache:
                    cfg["small_image"] = self.proxy_cache[small_img]
                else:
                    try:
                        proxied = await client.proxy_external_application_assets(app_id, small_img)
                        if proxied and len(proxied) > 0:
                            self.proxy_cache[small_img] = proxied[0]
                            cfg["small_image"] = proxied[0]
                    except Exception as e:
                        print(f"[RPCManager] Failed to proxy small_image: {e}")
            else:
                cfg["small_image"] = small_img

        cfg["application_id"] = app_id
        return cfg

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
        app_id = int(cfg.get("application_id") or DEFAULT_APP_ID)

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
            "application_id": app_id,
        }
        if details:
            kwargs["details"] = details
        if state:
            kwargs["state"] = state
        if timestamps:
            kwargs["timestamps"] = timestamps

        # ── 3. Resolve Assets (Logo / Images) ─────────────────────────
        large_image = (cfg.get("large_image") or "").strip()
        if not large_image and act_type in DEFAULT_ICONS:
            large_image = DEFAULT_ICONS[act_type]

        large_text = (cfg.get("large_text") or name or "Activity").strip()
        small_image = (cfg.get("small_image") or "").strip()
        small_text = (cfg.get("small_text") or "").strip()

        assets_dict = {}
        if large_image:
            assets_dict["large_image"] = large_image
            if large_text:
                assets_dict["large_text"] = large_text
        if small_image:
            assets_dict["small_image"] = small_image
            if small_text:
                assets_dict["small_text"] = small_text

        if assets_dict:
            kwargs["assets"] = assets_dict

        activity = discord.Activity(**kwargs)
        return activity, status
