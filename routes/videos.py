from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app
)
from flask_login import login_required, current_user
from app import db
from models.video import Video
from models.comment import Comment
from models.rating import Rating
from models.notification import Notification
from models.user import User
from utils.gcs import upload_video_to_gcs, delete_blob_from_gcs

TERMS = ["Term 1", "Term 2", "Term 3", "Term 4"]
LEVELS = ["Beginner", "Elementary", "Pre-Intermediate", "Intermediate", "Upper-Intermediate", "Advanced"]
UNITS = [f"Unit {i}" for i in range(1, 13)]

videos_bp = Blueprint("videos", __name__, url_prefix="/videos")

ALLOWED_EXTENSIONS = {"mp4", "webm", "mov", "avi"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _notify_admins_new_video(video):
    """Create in-app notifications for all admins and send email."""
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            message=f"📹 فيديو جديد ينتظر مراجعتك: «{video.title}» — رفعه {video.author.username}",
            link="/admin/pending",
        )
        db.session.add(notif)
    db.session.commit()

    # Send email notification
    try:
        from utils.email_notif import notify_admin_new_video
        notify_admin_new_video(
            video_title=video.title,
            uploader_name=video.author.username,
            uploader_email=video.author.email,
            video_id=video.id,
            term=video.term,
            level=video.level,
            unit=video.unit,
        )
    except Exception as e:
        current_app.logger.warning(f"Email notification failed: {e}")


# ─── Upload ───────────────────────────────────────────────────────────────────

@videos_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        term = request.form.get("term", "")
        level = request.form.get("level", "")
        unit = request.form.get("unit", "")
        file = request.files.get("video_file")

        if not all([title, term, level, unit, file]):
            flash("يرجى ملء جميع الحقول المطلوبة واختيار ملف الفيديو.", "danger")
            return render_template("videos/upload.html", terms=TERMS, levels=LEVELS, units=UNITS)

        if not allowed_file(file.filename):
            flash("نوع الملف غير مدعوم. الأنواع المقبولة: mp4, webm, mov, avi", "danger")
            return render_template("videos/upload.html", terms=TERMS, levels=LEVELS, units=UNITS)

        try:
            gcs_url = upload_video_to_gcs(file.stream, file.filename)
        except Exception as e:
            current_app.logger.error(f"GCS upload error: {e}")
            flash("فشل رفع الفيديو. يرجى المحاولة مرة أخرى.", "danger")
            return render_template("videos/upload.html", terms=TERMS, levels=LEVELS, units=UNITS)

        video = Video(
            title=title,
            description=description,
            gcs_url=gcs_url,
            term=term,
            level=level,
            unit=unit,
            user_id=current_user.id,
            is_approved=False,  # Requires admin approval
        )
        db.session.add(video)
        db.session.commit()

        # Notify admins (in-app + email)
        _notify_admins_new_video(video)

        flash("✅ تم رفع فيديوك بنجاح! سيظهر للجميع بعد مراجعة المشرف وموافقته.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("videos/upload.html", terms=TERMS, levels=LEVELS, units=UNITS)


# ─── Detail / Watch ───────────────────────────────────────────────────────────

@videos_bp.route("/<int:video_id>")
def detail(video_id):
    video = Video.query.get_or_404(video_id)

    # Block unapproved videos from public view (allow owner and admins)
    if not video.is_approved:
        if not current_user.is_authenticated or (
            current_user.id != video.user_id and not current_user.is_admin
        ):
            flash("هذا الفيديو قيد المراجعة ولم يُنشر بعد.", "warning")
            return redirect(url_for("main.browse"))

    comments = Comment.query.filter_by(video_id=video_id).order_by(Comment.created_at.desc()).all()
    user_rating = None
    if current_user.is_authenticated:
        r = Rating.query.filter_by(video_id=video_id, user_id=current_user.id).first()
        user_rating = r.score if r else None
    related = (
        Video.query.filter(
            Video.term == video.term,
            Video.level == video.level,
            Video.id != video.id,
            Video.is_approved == True,
        )
        .order_by(Video.created_at.desc())
        .limit(4)
        .all()
    )
    return render_template(
        "videos/detail.html",
        video=video,
        comments=comments,
        user_rating=user_rating,
        related=related,
    )


# ─── Comment (AJAX) ───────────────────────────────────────────────────────────

@videos_bp.route("/<int:video_id>/comment", methods=["POST"])
@login_required
def add_comment(video_id):
    video = Video.query.get_or_404(video_id)
    content = request.json.get("content", "").strip() if request.is_json else request.form.get("content", "").strip()
    if not content:
        return jsonify({"error": "التعليق لا يمكن أن يكون فارغاً."}), 400
    comment = Comment(content=content, video_id=video.id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()
    return jsonify({
        "id": comment.id,
        "content": comment.content,
        "username": current_user.username,
        "created_at": comment.created_at.strftime("%Y-%m-%d"),
    })


# ─── Rating (AJAX) ────────────────────────────────────────────────────────────

@videos_bp.route("/<int:video_id>/rate", methods=["POST"])
@login_required
def rate_video(video_id):
    video = Video.query.get_or_404(video_id)
    score = int(request.json.get("score", 0))
    if score < 1 or score > 5:
        return jsonify({"error": "التقييم يجب أن يكون بين 1 و 5."}), 400

    existing = Rating.query.filter_by(video_id=video_id, user_id=current_user.id).first()
    if existing:
        existing.score = score
    else:
        rating = Rating(score=score, video_id=video_id, user_id=current_user.id)
        db.session.add(rating)
    db.session.commit()

    return jsonify({
        "avg_rating": video.avg_rating,
        "rating_count": video.rating_count,
    })


# ─── Delete ───────────────────────────────────────────────────────────────────

@videos_bp.route("/<int:video_id>/delete", methods=["POST"])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    if video.user_id != current_user.id and not current_user.is_admin:
        flash("غير مصرح لك بحذف هذا الفيديو.", "danger")
        return redirect(url_for("videos.detail", video_id=video_id))
    try:
        delete_blob_from_gcs(video.gcs_url)
    except Exception:
        pass
    db.session.delete(video)
    db.session.commit()
    flash("تم حذف الفيديو بنجاح.", "success")
    return redirect(url_for("main.browse"))
