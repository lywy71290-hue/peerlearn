from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models.user import User
from models.otp import OTPCode
from utils.email_notif import send_otp_email
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


# ─── Step 1: Enter National ID ────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        national_id = request.form.get("national_id", "").strip()

        if not national_id or not national_id.isdigit() or len(national_id) != 10:
            flash("Please enter a valid 10-digit National ID.", "danger")
            return render_template("auth/login.html")

        # Find user by national_id
        user = User.query.filter_by(national_id=national_id).first()
        if not user:
            flash("This National ID is not registered in the system. Please contact your administrator.", "danger")
            return render_template("auth/login.html")

        # Invalidate old OTPs for this user
        OTPCode.query.filter_by(user_id=user.id, used=False).update({"used": True})
        db.session.commit()

        # Generate new OTP
        otp = OTPCode(user_id=user.id)
        db.session.add(otp)
        db.session.commit()

        # Send OTP email
        email_sent = send_otp_email(user.email, user.username, otp.code)

        # Store user_id in session for step 2
        session["otp_user_id"] = user.id
        session["otp_email_masked"] = _mask_email(user.email)

        if email_sent:
            flash(f"A 6-digit code has been sent to {_mask_email(user.email)}. It expires in 10 minutes.", "info")
        else:
            # Dev fallback: show code in flash (remove in production)
            flash(f"[DEV] Email not configured. Your OTP is: {otp.code}", "warning")

        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/login.html")


# ─── Step 2: Enter OTP ────────────────────────────────────────────────────────
@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user_id = session.get("otp_user_id")
    if not user_id:
        flash("Session expired. Please start again.", "danger")
        return redirect(url_for("auth.login"))

    email_masked = session.get("otp_email_masked", "your email")

    if request.method == "POST":
        code = request.form.get("otp_code", "").strip()

        # Find latest valid OTP for this user
        otp = OTPCode.query.filter_by(
            user_id=user_id, used=False
        ).order_by(OTPCode.created_at.desc()).first()

        if not otp or not otp.is_valid():
            flash("The code has expired. Please request a new one.", "danger")
            return redirect(url_for("auth.login"))

        if otp.code != code:
            flash("Invalid code. Please try again.", "danger")
            return render_template("auth/verify_otp.html", email_masked=email_masked)

        # Mark OTP as used
        otp.used = True
        db.session.commit()

        # Log in the user
        user = User.query.get(user_id)
        login_user(user, remember=True)
        session.pop("otp_user_id", None)
        session.pop("otp_email_masked", None)

        next_page = request.args.get("next")
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(next_page or url_for("main.index"))

    return render_template("auth/verify_otp.html", email_masked=email_masked)


# ─── Resend OTP ───────────────────────────────────────────────────────────────
@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    user_id = session.get("otp_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("auth.login"))

    # Invalidate old OTPs
    OTPCode.query.filter_by(user_id=user.id, used=False).update({"used": True})
    db.session.commit()

    # Generate new OTP
    otp = OTPCode(user_id=user.id)
    db.session.add(otp)
    db.session.commit()

    email_sent = send_otp_email(user.email, user.username, otp.code)
    if email_sent:
        flash(f"A new code has been sent to {_mask_email(user.email)}.", "info")
    else:
        flash(f"[DEV] Email not configured. Your OTP is: {otp.code}", "warning")

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


# ─── Register (disabled — admin only via import) ──────────────────────────────
@auth_bp.route("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("auth/register_closed.html")


# ─── Helper ───────────────────────────────────────────────────────────────────
def _mask_email(email: str) -> str:
    """Mask email for display: ab***@niti.edu.sa"""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked = local + "***"
    else:
        masked = local[:2] + "***" + local[-1]
    return f"{masked}@{domain}"
