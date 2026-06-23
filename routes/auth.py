from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models.user import User

auth_bp = Blueprint("auth", __name__)

# Allowed email domains for registration
ALLOWED_DOMAINS = {"niti.edu.sa"}

VALID_PROGRAMS = {"academic", "job_skills"}
VALID_LEVELS = {
    "Beginner", "Elementary", "Pre-Intermediate",
    "Intermediate", "Upper-Intermediate", "Advanced"
}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        program  = request.form.get("program", "").strip()
        level    = request.form.get("level", "").strip()

        # ── Validation ────────────────────────────────────────────────────────
        if not username or not email or not password:
            flash("جميع الحقول مطلوبة.", "danger")
            return render_template("auth/register.html")

        # Email domain restriction
        domain = email.split("@")[-1] if "@" in email else ""
        if domain not in ALLOWED_DOMAINS:
            flash(
                "التسجيل مقتصر على بريد NITI الرسمي (@niti.edu.sa) فقط.",
                "danger"
            )
            return render_template("auth/register.html")

        if password != confirm:
            flash("كلمتا المرور غير متطابقتين.", "danger")
            return render_template("auth/register.html")

        if len(password) < 8:
            flash("يجب أن تكون كلمة المرور 8 أحرف على الأقل.", "danger")
            return render_template("auth/register.html")

        if program not in VALID_PROGRAMS:
            flash("يرجى اختيار البرنامج.", "danger")
            return render_template("auth/register.html")

        if level not in VALID_LEVELS:
            flash("يرجى اختيار المستوى.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("هذا البريد الإلكتروني مسجّل مسبقاً.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(username=username).first():
            flash("هذا الاسم مستخدم بالفعل.", "danger")
            return render_template("auth/register.html")

        # ── Create user ───────────────────────────────────────────────────────
        user = User(username=username, email=email, program=program, level=level)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"مرحباً {username}! تم إنشاء حسابك بنجاح.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            flash(f"مرحباً بعودتك، {user.username}!", "success")
            return redirect(next_page or url_for("main.index"))

        flash("البريد الإلكتروني أو كلمة المرور غير صحيحة.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل خروجك بنجاح.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile")
@login_required
def profile():
    videos = current_user.videos
    return render_template("auth/profile.html", videos=videos)
