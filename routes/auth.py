from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models.user import User
from models.otp import OTPCode
from utils.email_notif import send_otp_email
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


# ─── Step 1: Email + Password ─────────────────────────────────────────────────
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
            # Dev fallback: show code on screen if email not configured
            flash(f"[DEV] Email not configured. Your code is: {otp.code}", "warning")

        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/login.html")


# ─── Step 2: Verify OTP ───────────────────────────────────────────────────────
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

        # Find the latest valid OTP for this user
        otp = OTPCode.query.filter_by(user_id=user_id, used=False)\
                           .order_by(OTPCode.created_at.desc()).first()

        if not otp or not otp.is_valid():
            flash("Your code has expired. Please sign in again to get a new code.", "danger")
            session.pop("pending_user_id", None)
            return redirect(url_for("auth.login"))

        if otp.code != entered_code:
            flash("Incorrect code. Please try again.", "danger")
            return render_template("auth/verify_otp.html", email=user.email)

        # ✅ OTP correct — mark as used and log in
        otp.used = True
        db.session.commit()

        session.pop("pending_user_id", None)
        next_page = session.pop("next_page", "") or url_for("main.dashboard")

        login_user(user, remember=True)
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(next_page)

    return render_template("auth/verify_otp.html", email=user.email)


# ─── Resend OTP ───────────────────────────────────────────────────────────────
@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    user_id = session.get("pending_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("auth.login"))

    # Invalidate old OTPs
    OTPCode.query.filter_by(user_id=user_id, used=False).update({"used": True})
    db.session.commit()

    # Generate new OTP
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


# ─── Register (disabled — admin only via import) ──────────────────────────────
@auth_bp.route("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("auth/register_closed.html")
