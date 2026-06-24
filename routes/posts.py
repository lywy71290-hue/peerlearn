import os
import cloudinary
import cloudinary.uploader
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models.post import Post, PostComment, PostLike

posts_bp = Blueprint("posts", __name__, url_prefix="/posts")

# ── Cloudinary config ─────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)


@posts_bp.route("/", methods=["GET"])
@login_required
def feed():
    """Show all posts ordered by newest first."""
    page  = request.args.get("page", 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=12)
    return render_template("posts/feed.html", posts=posts)


@posts_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new image post."""
    if request.method == "POST":
        caption = request.form.get("caption", "").strip()
        image   = request.files.get("image")

        if not caption:
            flash("يرجى كتابة شرح للمنشور.", "danger")
            return render_template("posts/create.html")

        image_url       = None
        image_public_id = None

        if image and image.filename:
            try:
                result = cloudinary.uploader.upload(
                    image,
                    folder="niti_learn/posts",
                    resource_type="image",
                    transformation=[{"width": 1200, "crop": "limit", "quality": "auto"}],
                )
                image_url       = result.get("secure_url")
                image_public_id = result.get("public_id")
            except Exception as e:
                flash(f"فشل رفع الصورة: {e}", "danger")
                return render_template("posts/create.html")

        post = Post(
            user_id=current_user.id,
            caption=caption,
            image_url=image_url,
            image_public_id=image_public_id,
        )
        db.session.add(post)
        db.session.commit()
        flash("تم نشر المنشور بنجاح!", "success")
        return redirect(url_for("posts.feed"))

    return render_template("posts/create.html")


@posts_bp.route("/<int:post_id>/delete", methods=["POST"])
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id and not current_user.is_admin:
        flash("غير مصرح لك بحذف هذا المنشور.", "danger")
        return redirect(url_for("posts.feed"))

    # Delete from Cloudinary
    if post.image_public_id:
        try:
            cloudinary.uploader.destroy(post.image_public_id)
        except Exception:
            pass

    db.session.delete(post)
    db.session.commit()
    flash("تم حذف المنشور.", "info")
    return redirect(url_for("posts.feed"))


@posts_bp.route("/<int:post_id>/like", methods=["POST"])
@login_required
def like(post_id):
    post = Post.query.get_or_404(post_id)
    existing = PostLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    if existing:
        db.session.delete(existing)
        liked = False
    else:
        db.session.add(PostLike(post_id=post_id, user_id=current_user.id))
        liked = True
    db.session.commit()
    return jsonify({"liked": liked, "count": post.like_count})


@posts_bp.route("/<int:post_id>/comment", methods=["POST"])
@login_required
def comment(post_id):
    post    = Post.query.get_or_404(post_id)
    content = request.json.get("content", "").strip() if request.is_json else request.form.get("content", "").strip()
    if not content:
        return jsonify({"error": "التعليق فارغ"}), 400

    c = PostComment(post_id=post_id, user_id=current_user.id, content=content)
    db.session.add(c)
    db.session.commit()
    return jsonify({
        "id":         c.id,
        "username":   current_user.username,
        "content":    c.content,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
    })
