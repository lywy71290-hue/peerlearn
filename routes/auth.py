from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import timedelta
from app import db
from models.user import User
from models.otp import OTPCode
from utils.email_notif import send_otp_email, send_register_otp_email
import logging
import random
import string

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


# ─── Step 1: Email + Password (Login) ────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Please enter your email and password.", "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Incorrect email or password. Please try again.", "danger")
            return render_template("auth/login.html")

        # ✅ Credentials correct — generate OTP and send to email
        otp = OTPCode(user_id=user.id)
        db.session.add(otp)
        db.session.commit()

        email_sent = send_otp_email(user.email, user.username, otp.code)

        # Store user_id in session for the verify step
        session["pending_user_id"] = user.id
        session["next_page"] = request.args.get("next", "")

        if email_sent:
            flash(f"A 6-digit code has been sent to {user.email}. Enter it below.", "info")
        else:
            flash(f"[DEV] Email not configured. Your code is: {otp.code}", "warning")

        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/login.html")


# ─── Step 2: Verify OTP (Login) ───────────────────────────────────────────────
@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user_id = session.get("pending_user_id")
    if not user_id:
        flash("Session expired. Please sign in again.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        session.pop("pending_user_id", None)
        flash("User not found. Please sign in again.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        entered_code = request.form.get("otp_code", "").strip()

        otp = OTPCode.query.filter_by(user_id=user_id, used=False)\
                           .order_by(OTPCode.created_at.desc()).first()

        if not otp or not otp.is_valid():
            flash("Your code has expired. Please sign in again to get a new code.", "danger")
            session.pop("pending_user_id", None)
            return redirect(url_for("auth.login"))

        if otp.code != entered_code:
            flash("Incorrect code. Please try again.", "danger")
            return render_template("auth/verify_otp.html", email=user.email)

        # ✅ OTP correct — mark as used and log in (remember for 1 year)
        otp.used = True
        db.session.commit()

        session.pop("pending_user_id", None)
        next_page = session.pop("next_page", "") or url_for("main.dashboard")

        login_user(user, remember=True, duration=timedelta(hours=1))
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(next_page)

    return render_template("auth/verify_otp.html", email=user.email)


# ─── Resend OTP (Login) ───────────────────────────────────────────────────────
@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    user_id = session.get("pending_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("auth.login"))

    OTPCode.query.filter_by(user_id=user_id, used=False).update({"used": True})
    db.session.commit()

    otp = OTPCode(user_id=user.id)
    db.session.add(otp)
    db.session.commit()

    email_sent = send_otp_email(user.email, user.username, otp.code)

    if email_sent:
        flash(f"A new code has been sent to {user.email}.", "info")
    else:
        flash(f"[DEV] Your new code is: {otp.code}", "warning")

    return redirect(url_for("auth.verify_otp"))


# ─── Logout ───────────────────────────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


# ─── Profile ──────────────────────────────────────────────────────────────────
@auth_bp.route("/profile")
@login_required
def profile():
    videos = current_user.videos
    return render_template("auth/profile.html", videos=videos)


# ─── Register: Step 1 — Enter name, email, password ──────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username         = request.form.get("username", "").strip()
        email            = request.form.get("email", "").strip().lower()
        password         = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Validate fields
        if not username or not email or not password:
            flash("يرجى تعبئة جميع الحقول المطلوبة.", "danger")
            return render_template("auth/register.html")

        if not email.endswith("@niti.edu.sa"):
            flash("يُسمح فقط بالبريد المؤسسي @niti.edu.sa", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("كلمة المرور يجب أن تكون 6 أحرف على الأقل.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("كلمتا المرور غير متطابقتين.", "danger")
            return render_template("auth/register.html")

        # Check duplicate email
        if User.query.filter_by(email=email).first():
            flash("يوجد حساب بهذا البريد الإلكتروني بالفعل.", "danger")
            return render_template("auth/register.html")

        # Generate OTP code (6 digits)
        otp_code = ''.join(random.choices(string.digits, k=6))

        # Store pending registration data in session
        session["pending_register"] = {
            "username": username,
            "email": email,
            "password": password,
            "otp_code": otp_code,
        }

        # Send OTP to email
        email_sent = send_register_otp_email(email, username, otp_code)

        if email_sent:
            flash(f"أُرسل رمز التحقق إلى {email}. أدخله أدناه.", "info")
        else:
            flash(f"[DEV] الرمز هو: {otp_code}", "warning")

        return redirect(url_for("auth.verify_register_otp"))

    return render_template("auth/register.html")


# ─── Register: Step 2 — Verify OTP ───────────────────────────────────────────
@auth_bp.route("/verify-register-otp", methods=["GET", "POST"])
def verify_register_otp():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    pending = session.get("pending_register")
    if not pending:
        flash("انتهت الجلسة. يرجى إعادة التسجيل.", "danger")
        return redirect(url_for("auth.register"))

    email = pending.get("email", "")

    if request.method == "POST":
        entered_code = request.form.get("otp_code", "").strip()

        if entered_code != pending.get("otp_code"):
            flash("الرمز غير صحيح. يرجى المحاولة مرة أخرى.", "danger")
            return render_template("auth/verify_register_otp.html", email=email)

        # ✅ OTP correct — create the user account
        # Re-check email not taken (race condition guard)
        if User.query.filter_by(email=email).first():
            session.pop("pending_register", None)
            flash("يوجد حساب بهذا البريد الإلكتروني بالفعل.", "danger")
            return redirect(url_for("auth.register"))

        user = User(
            username=pending["username"],
            email=pending["email"],
        )
        user.set_password(pending["password"])
        db.session.add(user)
        db.session.commit()

        session.pop("pending_register", None)

        # Log in immediately with 1-year session
        login_user(user, remember=True, duration=timedelta(hours=1))
        flash(f"مرحباً {user.username}! تم إنشاء حسابك بنجاح.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/verify_register_otp.html", email=email)


# ─── Resend Register OTP ──────────────────────────────────────────────────────
@auth_bp.route("/resend-register-otp", methods=["POST"])
def resend_register_otp():
    pending = session.get("pending_register")
    if not pending:
        return redirect(url_for("auth.register"))

    # Generate new OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    pending["otp_code"] = otp_code
    session["pending_register"] = pending

    email_sent = send_register_otp_email(pending["email"], pending["username"], otp_code)

    if email_sent:
        flash(f"تم إرسال رمز جديد إلى {pending['email']}.", "info")
    else:
        flash(f"[DEV] الرمز الجديد هو: {otp_code}", "warning")

    return redirect(url_for("auth.verify_register_otp"))
