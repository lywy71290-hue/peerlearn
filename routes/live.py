from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import uuid, json, os

live_bp = Blueprint("live", __name__, url_prefix="/live")

# In-memory room registry (resets on server restart — fine for free tier)
# Structure: { room_id: { "title": str, "host_id": int, "host_name": str,
#                         "created_at": datetime, "peers": {user_id: signal_data} } }
LIVE_ROOMS = {}

# Signaling store: { room_id: [ {from, to, data, ts} ] }
SIGNALS = {}


def clean_old_rooms():
    cutoff = datetime.utcnow() - timedelta(hours=3)
    to_del = [k for k, v in LIVE_ROOMS.items() if v["created_at"] < cutoff]
    for k in to_del:
        LIVE_ROOMS.pop(k, None)
        SIGNALS.pop(k, None)


@live_bp.route("/")
@login_required
def index():
    clean_old_rooms()
    return render_template("live/index.html", rooms=LIVE_ROOMS)


@live_bp.route("/create", methods=["POST"])
@login_required
def create():
    clean_old_rooms()
    title   = request.form.get("title", "").strip() or f"غرفة {current_user.username}"
    room_id = str(uuid.uuid4())[:8]
    LIVE_ROOMS[room_id] = {
        "title":      title,
        "host_id":    current_user.id,
        "host_name":  current_user.username,
        "created_at": datetime.utcnow(),
        "peers":      {},
    }
    SIGNALS[room_id] = []
    return jsonify({"room_id": room_id})


@live_bp.route("/<room_id>")
@login_required
def room(room_id):
    if room_id not in LIVE_ROOMS:
        return render_template("live/not_found.html"), 404
    r = LIVE_ROOMS[room_id]
    is_host = (r["host_id"] == current_user.id)
    return render_template("live/room.html",
                           room_id=room_id,
                           room=r,
                           is_host=is_host)


@live_bp.route("/<room_id>/join", methods=["POST"])
@login_required
def join(room_id):
    if room_id not in LIVE_ROOMS:
        return jsonify({"error": "الغرفة غير موجودة"}), 404
    LIVE_ROOMS[room_id]["peers"][str(current_user.id)] = current_user.username
    peers = [{"id": uid, "name": name}
             for uid, name in LIVE_ROOMS[room_id]["peers"].items()
             if uid != str(current_user.id)]
    return jsonify({"peers": peers, "host_id": LIVE_ROOMS[room_id]["host_id"]})


@live_bp.route("/<room_id>/leave", methods=["POST"])
@login_required
def leave(room_id):
    if room_id in LIVE_ROOMS:
        LIVE_ROOMS[room_id]["peers"].pop(str(current_user.id), None)
        # If host left, close room
        if LIVE_ROOMS[room_id]["host_id"] == current_user.id:
            LIVE_ROOMS.pop(room_id, None)
            SIGNALS.pop(room_id, None)
    return jsonify({"ok": True})


@live_bp.route("/<room_id>/peers")
@login_required
def peers(room_id):
    if room_id not in LIVE_ROOMS:
        return jsonify({"peers": [], "active": False})
    r = LIVE_ROOMS[room_id]
    return jsonify({
        "active": True,
        "peers": [{"id": uid, "name": name} for uid, name in r["peers"].items()],
        "host_id": r["host_id"],
    })


# ── WebRTC Signaling (offer/answer/ice via polling) ───────────────────────────

@live_bp.route("/<room_id>/signal/send", methods=["POST"])
@login_required
def signal_send(room_id):
    if room_id not in SIGNALS:
        return jsonify({"error": "room not found"}), 404
    data = request.get_json(silent=True) or {}
    SIGNALS[room_id].append({
        "from": current_user.id,
        "to":   data.get("to"),
        "type": data.get("type"),
        "data": data.get("data"),
        "ts":   datetime.utcnow().timestamp(),
    })
    # Keep only last 200 signals
    if len(SIGNALS[room_id]) > 200:
        SIGNALS[room_id] = SIGNALS[room_id][-200:]
    return jsonify({"ok": True})


@live_bp.route("/<room_id>/signal/poll")
@login_required
def signal_poll(room_id):
    if room_id not in SIGNALS:
        return jsonify([])
    after = request.args.get("after", 0, type=float)
    msgs  = [s for s in SIGNALS[room_id]
             if s["ts"] > after and (s["to"] is None or s["to"] == current_user.id)]
    return jsonify(msgs)
