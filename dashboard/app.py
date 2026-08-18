"""
Flask + SocketIO dashboard — real-time conversation monitor.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app(config: dict):
    """
    Factory that creates the Flask app.
    Returns (app, event_emitter_fn, state_dict).
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "afk-bot-dashboard-secret-2025"

    socketio.init_app(app)

    # ── Shared state (mutated by both bot callbacks and Flask routes) ──
    state = {
        "afk_mode": config.get("afk_mode", True),
        "bot": None,  # Set in run.py after bot creation
        "conversations": [],
        "stats": {
            "total_conversations": 0,
            "total_messages": 0,
            "total_ai_replies": 0,
        },
        "log": [],  # Recent events log (last 200)
    }

    # ── Event emitter called from the bot thread ──────────────────────
    def event_emitter(event: str, data: dict):
        if event == "new_message":
            state["log"].insert(0, {"event": event, **data})
            state["log"] = state["log"][:200]
        elif event == "stats_update":
            state["stats"] = data
        elif event == "conversations_update":
            state["conversations"] = data
        elif event == "afk_toggle":
            state["afk_mode"] = data.get("afk_mode", True)

        socketio.emit(event, data)

    # ── Routes ────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            owner_name=config.get("your_name", "Sahal"),
            afk_mode=state["afk_mode"],
        )

    @app.route("/api/state")
    def get_state():
        return jsonify(
            {
                "afk_mode": state["afk_mode"],
                "conversations": state["conversations"],
                "stats": state["stats"],
            }
        )

    @app.route("/api/toggle-afk", methods=["POST"])
    def toggle_afk():
        data = request.get_json() or {}
        new_mode = data.get("afk_mode", not state["afk_mode"])
        state["afk_mode"] = new_mode

        if state["bot"] is not None:
            state["bot"].toggle_afk(new_mode)
        else:
            socketio.emit("afk_toggle", {"afk_mode": new_mode})

        return jsonify({"success": True, "afk_mode": new_mode})

    @app.route("/api/send-message", methods=["POST"])
    def send_message():
        data = request.get_json() or {}
        user_id = data.get("user_id")
        content = data.get("content")

        if not user_id or not content:
            return jsonify({"success": False, "error": "Missing user_id or content"}), 400

        if state["bot"] is not None:
            import asyncio
            fut = asyncio.run_coroutine_threadsafe(
                state["bot"].send_manual_message(user_id, content),
                state["bot"].loop
            )
            try:
                success = fut.result(timeout=5)
                return jsonify({"success": success})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        else:
            return jsonify({"success": False, "error": "Bot is not active"}), 500

    # ── SocketIO events ───────────────────────────────────────────────

    @socketio.on("connect")
    def handle_connect():
        socketio.emit(
            "initial_state",
            {
                "afk_mode": state["afk_mode"],
                "conversations": state["conversations"],
                "stats": state["stats"],
                "log": state["log"][:50],
            },
        )

    return app, event_emitter, state
