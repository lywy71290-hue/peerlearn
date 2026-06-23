"""
Admin Blueprint — NITI PeerLearn
Accessible only to users with is_admin=True.
"""
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models.user import User
from models.video import Video
from models.comment import Comment

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ── Decorator: require admin ──────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────────────
@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    total_users   = User.query.count()
    total_videos  = Video.query.count()
    total_comments = Comment.query.count()
    recent_users  = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_videos=total_videos,
        total_comments=total_comments,
        recent_users=recent_users,
        recent_videos=recent_videos,
    )


# ── Users List ────────────────────────────────────────────────────────────────
@admin_bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    return render_template("admin/users.html", pagination=pagination, search=search)


# ── Toggle Admin ──────────────────────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("لا يمكنك تعديل صلاحياتك الخاصة.", "warning")
        return redirect(url_for("admin.users"))
    user.is_admin = not user.is_admin
    db.session.commit()
    status = "مشرفاً" if user.is_admin else "متدرباً عادياً"
    flash(f"تم تغيير دور {user.username} إلى {status}.", "success")
    return redirect(url_for("admin.users"))


# ── Delete User ───────────────────────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("لا يمكنك حذف حسابك الخاص من هنا.", "warning")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    db.session.commit()
    flash(f"تم حذف المستخدم {user.username} بنجاح.", "success")
    return redirect(url_for("admin.users"))


# ── Videos List ───────────────────────────────────────────────────────────────
@admin_bp.route("/videos")
@login_required
@admin_required
def videos():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    query = Video.query
    if search:
        query = query.filter(Video.title.ilike(f"%{search}%"))
    pagination = query.order_by(Video.created_at.desc()).paginate(page=page, per_page=20)
    return render_template("admin/videos.html", pagination=pagination, search=search)


# ── Delete Video (admin) ──────────────────────────────────────────────────────
@admin_bp.route("/videos/<int:video_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_video(video_id):
    from utils.gcs import delete_video as cloud_delete
    video = Video.query.get_or_404(video_id)
    title = video.title
    try:
        cloud_delete(video.gcs_public_id)
    except Exception:
        pass  # Don't block deletion if cloud removal fails
    db.session.delete(video)
    db.session.commit()
    flash(f"تم حذف الفيديو «{title}» بنجاح.", "success")
    return redirect(url_for("admin.videos"))
