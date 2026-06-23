"""
Admin Blueprint — NITI Learn
Accessible only to users with is_admin=True.
"""
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models.user import User
from models.video import Video
from models.comment import Comment
from models.notification import Notification

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ── Decorator: require admin ──────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _notify_admins(message, link=""):
    """Send an in-app notification to all admins."""
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        notif = Notification(user_id=admin.id, message=message, link=link)
        db.session.add(notif)
    db.session.commit()


# ── Dashboard ─────────────────────────────────────────────────────────────────
@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    total_users    = User.query.count()
    total_videos   = Video.query.filter_by(is_approved=True).count()
    pending_count  = Video.query.filter_by(is_approved=False).count()
    total_comments = Comment.query.count()
    recent_users   = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_videos  = Video.query.filter_by(is_approved=True).order_by(Video.created_at.desc()).limit(10).all()
    pending_videos = Video.query.filter_by(is_approved=False).order_by(Video.created_at.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_videos=total_videos,
        pending_count=pending_count,
        total_comments=total_comments,
        recent_users=recent_users,
        recent_videos=recent_videos,
        pending_videos=pending_videos,
    )


# ── Pending Videos (Review Queue) ─────────────────────────────────────────────
@admin_bp.route("/pending")
@login_required
@admin_required
def pending():
    page = request.args.get("page", 1, type=int)
    pagination = (
        Video.query.filter_by(is_approved=False)
        .order_by(Video.created_at.desc())
        .paginate(page=page, per_page=15)
    )
    # Mark all admin notifications as read when visiting review page
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return render_template("admin/pending.html", pagination=pagination)


# ── Approve Video ─────────────────────────────────────────────────────────────
@admin_bp.route("/videos/<int:video_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_video(video_id):
    video = Video.query.get_or_404(video_id)
    video.is_approved = True
    # Notify the uploader
    notif = Notification(
        user_id=video.user_id,
        message=f"✅ تمت الموافقة على فيديوك «{video.title}» ونُشر للجميع.",
        link=f"/videos/{video.id}",
    )
    db.session.add(notif)
    db.session.commit()
    # Send email to uploader
    try:
        from utils.email_notif import notify_uploader_approved
        notify_uploader_approved(
            uploader_email=video.author.email,
            uploader_name=video.author.username,
            video_title=video.title,
            video_id=video.id,
        )
    except Exception as e:
        import logging; logging.getLogger(__name__).warning(f"Approve email failed: {e}")
    flash(f"تمت الموافقة على «{video.title}» ونُشر.", "success")
    return redirect(request.referrer or url_for("admin.pending"))


# ── Reject Video ──────────────────────────────────────────────────────────────
@admin_bp.route("/videos/<int:video_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject_video(video_id):
    video = Video.query.get_or_404(video_id)
    reason = request.form.get("reason", "").strip()
    # Notify the uploader
    msg = f"❌ تم رفض فيديوك «{video.title}»."
    if reason:
        msg += f" السبب: {reason}"
    notif = Notification(user_id=video.user_id, message=msg, link="")
    db.session.add(notif)
    # Send email to uploader
    try:
        from utils.email_notif import notify_uploader_rejected
        notify_uploader_rejected(
            uploader_email=video.author.email,
            uploader_name=video.author.username,
            video_title=video.title,
            reason=reason,
        )
    except Exception as e:
        import logging; logging.getLogger(__name__).warning(f"Reject email failed: {e}")
    # Delete the video record (and optionally from cloud)
    try:
        from utils.gcs import delete_blob_from_gcs
        delete_blob_from_gcs(video.gcs_url)
    except Exception:
        pass
    db.session.delete(video)
    db.session.commit()
    flash(f"تم رفض وحذف الفيديو «{video.title}».", "warning")
    return redirect(request.referrer or url_for("admin.pending"))


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
    video = Video.query.get_or_404(video_id)
    title = video.title
    try:
        from utils.gcs import delete_blob_from_gcs
        delete_blob_from_gcs(video.gcs_url)
    except Exception:
        pass
    db.session.delete(video)
    db.session.commit()
    flash(f"تم حذف الفيديو «{title}» بنجاح.", "success")
    return redirect(url_for("admin.videos"))
