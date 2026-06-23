from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from models.notification import Notification

notif_bp = Blueprint("notif", __name__, url_prefix="/notifications")


@notif_bp.route("/count")
@login_required
def count():
    """Return unread notification count for the bell badge."""
    n = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": n})


@notif_bp.route("/list")
@login_required
def list_notifications():
    """Return last 20 notifications for the dropdown."""
    notifs = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify([n.to_dict() for n in notifs])


@notif_bp.route("/mark-read", methods=["POST"])
@login_required
def mark_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})


@notif_bp.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_one_read(notif_id):
    """Mark a single notification as read."""
    n = Notification.query.get_or_404(notif_id)
    if n.user_id == current_user.id:
        n.is_read = True
        db.session.commit()
    return jsonify({"ok": True})
