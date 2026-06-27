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
import re

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


def normalize_otp(code: str) -> str:
    """Remove spaces, dashes, and keep digits only."""
    return re.sub(r'\D', '', code.strip())


# ─── Step 1: Email + Password (Login) ────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("يرجى إدخال البريد الإلكتروني وكلمة المرور.", "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("البريد الإلكتروني أو كلمة المرور غير صحيحة.", "danger")
            return render_template("auth/login.html")

        # ✅ Credentials correct — generate OTP and send to email
        otp = OTPCode(user_id=user.id)
        db.session.add(otp)
        db.session.commit()

        email_sent = send_otp_email(user.email, user.username, otp.code)

        session["pending_user_id"] = user.id
        session["next_page"] = request.args.get("next", "")

        if email_sent:
            flash(f"أُرسل رمز التحقق إلى {user.email}. أدخله أدناه.", "info")
        else:
            flash(f"[DEV] الرمز هو: {otp.code}", "warning")

        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/login.html")


# ─── Step 2: Verify OTP (Login) ───────────────────────────────────────────────
@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user_id = session.get("pending_user_id")
    if not user_id:
        flash("انتهت الجلسة. يرجى تسجيل الدخول مجدداً.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        session.pop("pending_user_id", None)
        flash("المستخدم غير موجود.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        entered_code = normalize_otp(request.form.get("otp_code", ""))

        otp = OTPCode.query.filter_by(user_id=user_id, used=False)\
                           .order_by(OTPCode.created_at.desc()).first()

        if not otp or not otp.is_valid():
            flash("انتهت صلاحية الرمز. يرجى تسجيل الدخول مجدداً.", "danger")
            session.pop("pending_user_id", None)
            return redirect(url_for("auth.login"))

        if normalize_otp(otp.code) != entered_code:
            flash("الرمز غير صحيح. يرجى المحاولة مرة أخرى.", "danger")
            return render_template("auth/verify_otp.html", email=user.email)

        # ✅ OTP correct
        otp.used = True
        db.session.commit()

        session.pop("pending_user_id", None)
        next_page = session.pop("next_page", "") or url_for("main.dashboard")

        login_user(user, remember=True, duration=timedelta(hours=1))
        flash(f"مرحباً {user.username}!", "success")
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
        flash(f"تم إرسال رمز جديد إلى {user.email}.", "info")
    else:
        flash(f"[DEV] الرمز الجديد هو: {otp.code}", "warning")

    return redirect(url_for("auth.verify_otp"))


# ─── Logout ───────────────────────────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل خروجك بنجاح.", "info")
    return redirect(url_for("auth.register"))


# ─── Profile ──────────────────────────────────────────────────────────────────
@auth_bp.route("/profile")
@login_required
def profile():
    videos = current_user.videos
    return render_template("auth/profile.html", videos=videos)


# ─── Register: Step 1 — Enter name, email, national ID ───────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username    = request.form.get("username", "").strip()
        email       = request.form.get("email", "").strip().lower()
        national_id = request.form.get("national_id", "").strip()

        # Validate fields
        if not username or not email or not national_id:
            flash("يرجى تعبئة جميع الحقول المطلوبة.", "danger")
            return render_template("auth/register.html")

        if not email.endswith("@niti.edu.sa"):
            flash("يُسمح فقط بالبريد المؤسسي @niti.edu.sa", "danger")
            return render_template("auth/register.html")

        if not re.match(r'^\d{4,10}$', national_id):
            flash("رقم الهوية يجب أن يكون أرقاماً فقط (4-10 أرقام).", "danger")
            return render_template("auth/register.html")

        # Check duplicate email
        if User.query.filter_by(email=email).first():
            flash("يوجد حساب بهذا البريد الإلكتروني بالفعل.", "danger")
            return render_template("auth/register.html")

        # Password = Niti + national_id
        password = f"Niti{national_id}"

        # Generate OTP code (6 digits)
        otp_code = ''.join(random.choices(string.digits, k=6))

        # Store pending registration data in session
        session["pending_register"] = {
            "username": username,
            "email": email,
            "password": password,
            "national_id": national_id,
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
        entered_code = normalize_otp(request.form.get("otp_code", ""))
        stored_code  = normalize_otp(pending.get("otp_code", ""))

        if entered_code != stored_code:
            flash("الرمز غير صحيح. يرجى المحاولة مرة أخرى.", "danger")
            return render_template("auth/verify_register_otp.html", email=email)

        # ✅ OTP correct — create the user account
        if User.query.filter_by(email=email).first():
            session.pop("pending_register", None)
            flash("يوجد حساب بهذا البريد الإلكتروني بالفعل.", "danger")
            return redirect(url_for("auth.register"))

        user = User(
            username=pending["username"],
            email=pending["email"],
            national_id=pending.get("national_id"),
        )
        user.set_password(pending["password"])
        db.session.add(user)
        db.session.commit()

        session.pop("pending_register", None)

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

    otp_code = ''.join(random.choices(string.digits, k=6))
    pending["otp_code"] = otp_code
    session["pending_register"] = pending

    email_sent = send_register_otp_email(pending["email"], pending["username"], otp_code)

    if email_sent:
        flash(f"تم إرسال رمز جديد إلى {pending['email']}.", "info")
    else:
        flash(f"[DEV] الرمز الجديد هو: {otp_code}", "warning")

    return redirect(url_for("auth.verify_register_otp"))
