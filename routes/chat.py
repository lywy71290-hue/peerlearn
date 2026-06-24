from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from models.chat import ChatMessage

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")

ROOMS = {
    "general":  "الغرفة العامة",
    "academic": "الأكاديميون",
    "skills":   "مهارات وظيفية",
}


@chat_bp.route("/")
@login_required
def index():
    """Chat room list."""
    return render_template("chat/index.html", rooms=ROOMS)


@chat_bp.route("/<room>")
@login_required
def room(room):
    if room not in ROOMS:
        room = "general"
    # Load last 50 messages
    messages = (ChatMessage.query
                .filter_by(room=room)
                .order_by(ChatMessage.created_at.asc())
                .limit(50)
                .all())
    return render_template("chat/room.html",
                           room=room,
                           room_name=ROOMS[room],
                           messages=messages,
                           rooms=ROOMS)


@chat_bp.route("/<room>/send", methods=["POST"])
@login_required
def send(room):
    if room not in ROOMS:
        return jsonify({"error": "غرفة غير موجودة"}), 404

    data    = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    if not content or len(content) > 500:
        return jsonify({"error": "الرسالة فارغة أو طويلة جداً"}), 400

    msg = ChatMessage(user_id=current_user.id, room=room, content=content)
    db.session.add(msg)
    db.session.commit()
    return jsonify(msg.to_dict()), 201


@chat_bp.route("/<room>/messages")
@login_required
def messages(room):
    """Polling endpoint — returns messages after a given ID."""
    if room not in ROOMS:
        return jsonify([])

    after_id = request.args.get("after", 0, type=int)
    msgs = (ChatMessage.query
            .filter_by(room=room)
            .filter(ChatMessage.id > after_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(50)
            .all())
    return jsonify([m.to_dict() | {"id": m.id} for m in msgs])
