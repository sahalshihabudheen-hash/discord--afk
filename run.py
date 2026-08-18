"""
run.py — Entry point. Starts the Flask dashboard in a background thread,
then runs the Discord self-bot in the main asyncio event loop.
"""

import os
import sys
import threading

from dotenv import load_dotenv

load_dotenv()

# Fix Windows terminal encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


import socket

# Keep lock socket reference alive
_lock_socket = None

def acquire_single_instance_lock(port=48999):
    global _lock_socket
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(('127.0.0.1', port))
        _lock_socket.listen(1)
        return True
    except socket.error:
        return False


def validate_config(config: dict):
    errors = []
    if not config.get("discord_token") or config["discord_token"] == "your_discord_user_token_here":
        errors.append("❌  DISCORD_TOKEN is not set in your .env file")
    if not config.get("groq_api_key") or config["groq_api_key"] == "your_groq_api_key_here":
        errors.append("❌  GROQ_API_KEY is not set in your .env file")
    return errors


def main():
    if not acquire_single_instance_lock():
        print("\n⚠️  Another instance of the Discord Control Bot is already running!")
        print("   Only 1 instance can run at a time to prevent double replies.\n")
        sys.exit(0)
    config = {
        "discord_token": os.getenv("DISCORD_TOKEN", ""),
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),

        "your_name": os.getenv("YOUR_NAME", "Sahal"),
        "afk_mode": os.getenv("AFK_MODE", "true").lower() == "true",
        "dashboard_port": int(os.getenv("DASHBOARD_PORT", "5000")),
        "vercel_dashboard_url": os.getenv("CLOUD_DASHBOARD_URL", "") or os.getenv("VERCEL_DASHBOARD_URL", ""),
    }

    # ── Validate required keys ────────────────────────────────
    errors = validate_config(config)
    if errors:
        print("\n" + "─" * 50)
        print("  ⚠️  Configuration issues found:")
        for e in errors:
            print(f"     {e}")
        print("  Copy .env.example → .env and fill in your keys.")
        print("─" * 50 + "\n")
        sys.exit(1)

    # ── Lazy imports (after validation) ──────────────────────
    from dashboard.app import create_app, socketio
    from bot.afk_bot import AFKBot

    # Create Flask app + event emitter
    app, event_emitter, state = create_app(config)

    # Create Discord bot and wire it to the dashboard
    bot = AFKBot(config, event_callback=event_emitter)
    state["bot"] = bot  # Allows Flask routes to call bot.toggle_afk()

    # Start Flask-SocketIO dashboard in a daemon background thread
    def run_dashboard():
        print(f"[Dashboard] 🌐  http://localhost:{config['dashboard_port']}")
        socketio.run(
            app,
            host="0.0.0.0",
            port=config["dashboard_port"],
            debug=False,
            use_reloader=False,
            log_output=False,
            allow_unsafe_werkzeug=True,
        )

    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()

    # Run the Discord bot in the main thread (blocking)
    print("[Bot] 🤖  Starting Discord self-bot…")
    print(f"[Bot] 📊  AFK mode: {'ON' if config['afk_mode'] else 'OFF'}")
    print()
    bot.run(config["discord_token"], log_handler=None)


if __name__ == "__main__":
    main()
