"""
Flask + SocketIO dashboard — real-time conversation monitor.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from bot.rpc_manager import RPCManager

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app(config: dict):
    """
    Factory that creates the Flask app.
    Returns (app, event_emitter_fn, state_dict).
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "afk-bot-dashboard-secret-2025"

    socketio.init_app(app)
    rpc_mgr = RPCManager()

    # ── Shared state (mutated by both bot callbacks and Flask routes) ──
    state = {
        "afk_mode": config.get("afk_mode", True),
        "bot": None,  # Set in run.py after bot creation
        "rpc_config": rpc_mgr.load_config(),
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
        elif event == "rpc_update":
            state["rpc_config"] = data

        socketio.emit(event, data)

    # ── Routes ────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            owner_name=config.get("your_name", "Sahal"),
            afk_mode=state["afk_mode"],
            rpc_config=state["rpc_config"],
        )

    @app.route("/api/state")
    def get_state():
        return jsonify(
            {
                "afk_mode": state["afk_mode"],
                "rpc_config": state["rpc_config"],
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

    @app.route("/api/toggle-ai", methods=["POST"])
    def toggle_ai():
        data = request.get_json() or {}
        user_id = data.get("user_id")
        ai_disabled = data.get("ai_disabled")

        if not user_id:
            return jsonify({"success": False, "error": "Missing user_id"}), 400

        if state["bot"] is not None:
            if ai_disabled is None:
                ai_disabled = not state["bot"].store.is_ai_disabled(user_id)
            state["bot"].store.set_ai_disabled(user_id, ai_disabled)
            # Emit updated conversations
            state["conversations"] = state["bot"].store.get_sorted_conversations()
            socketio.emit("conversations_update", state["conversations"])
            return jsonify({"success": True, "ai_disabled": ai_disabled})
        else:
            return jsonify({"success": False, "error": "Bot is not active"}), 500

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

    @app.route("/api/get-rpc")
    def get_rpc():
        return jsonify({"success": True, "rpc_config": state["rpc_config"]})

    @app.route("/api/set-rpc", methods=["POST"])
    def set_rpc():
        data = request.get_json() or {}
        rpc_mgr = RPCManager()
        rpc_mgr.save_config(data)
        state["rpc_config"] = rpc_mgr.current_config

        if state["bot"] is not None:
            import asyncio
            fut = asyncio.run_coroutine_threadsafe(
                state["bot"].apply_rpc(data),
                state["bot"].loop
            )
            try:
                success = fut.result(timeout=5)
                return jsonify({"success": success, "rpc_config": state["rpc_config"]})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        else:
            socketio.emit("rpc_update", state["rpc_config"])
            return jsonify({"success": True, "rpc_config": state["rpc_config"]})

    # ── SocketIO events ───────────────────────────────────────────────

    @socketio.on("connect")
    def handle_connect():
        socketio.emit(
            "initial_state",
            {
                "afk_mode": state["afk_mode"],
                "rpc_config": state["rpc_config"],
                "conversations": state["conversations"],
                "stats": state["stats"],
                "log": state["log"][:50],
            },
        )

    return app, event_emitter, state
