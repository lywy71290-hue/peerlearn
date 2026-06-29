"""
Rewards Blueprint — NITI Learn
نظام النقاط والمكافآت
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models.user import User
from models.rewards import PointTransaction, RewardRequest, PlatformRating
from models.notification import Notification
from utils.email_notif import send_reward_coupon_email
import logging

logger = logging.getLogger(__name__)
rewards_bp = Blueprint("rewards", __name__)

# ── إعدادات المكافآت ──────────────────────────────────────────────────────────
REWARDS = {
    "coffee": {"name": "كوب قهوة ☕", "points": 15},
    "meal":   {"name": "وجبة غداء 🍽️", "points": 30},
}

LOCATIONS = ["المطعم الرئيسي", "كافيه 1", "كافيه 2"]


def admin_required(f):
    from flask import abort
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── صفحة المكافآت للمتدرب ────────────────────────────────────────────────────
@rewards_bp.route("/rewards")
@login_required
def rewards_page():
    transactions = PointTransaction.query.filter_by(user_id=current_user.id)\
                                         .order_by(PointTransaction.created_at.desc()).all()
    my_requests  = RewardRequest.query.filter_by(user_id=current_user.id)\
                                      .order_by(RewardRequest.created_at.desc()).all()
    return render_template(
        "rewards/rewards.html",
        rewards=REWARDS,
        locations=LOCATIONS,
        transactions=transactions,
        my_requests=my_requests,
    )


# ── طلب استبدال النقاط ────────────────────────────────────────────────────────
@rewards_bp.route("/rewards/redeem", methods=["POST"])
@login_required
def redeem():
    reward_type = request.form.get("reward_type", "")
    location    = request.form.get("location", "")

    if reward_type not in REWARDS:
        flash("نوع المكافأة غير صحيح.", "danger")
        return redirect(url_for("rewards.rewards_page"))

    if location not in LOCATIONS:
        flash("الموقع غير صحيح.", "danger")
        return redirect(url_for("rewards.rewards_page"))

    cost = REWARDS[reward_type]["points"]

    if (current_user.total_points or 0) < cost:
        flash(f"نقاطك غير كافية. تحتاج {cost} نقطة.", "danger")
        return redirect(url_for("rewards.rewards_page"))

    # خصم النقاط
    current_user.total_points -= cost
    tx = PointTransaction(
        user_id=current_user.id,
        points=-cost,
        reason=f"استبدال: {REWARDS[reward_type]['name']} من {location}",
    )
    db.session.add(tx)

    # إنشاء طلب المكافأة
    req = RewardRequest(
        user_id=current_user.id,
        reward_type=reward_type,
        location=location,
        points_cost=cost,
        status="pending",
    )
    db.session.add(req)

    # إشعار للأدمن
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            message=f"🎁 {current_user.username} طلب {REWARDS[reward_type]['name']} من {location}",
            link="/admin/rewards",
        )
        db.session.add(notif)

    db.session.commit()
    flash(f"تم إرسال طلبك! ستصلك الموافقة قريباً.", "success")
    return redirect(url_for("rewards.rewards_page"))


# ── لوحة الأدمن: إدارة طلبات المكافآت ───────────────────────────────────────
@rewards_bp.route("/admin/rewards")
@login_required
@admin_required
def admin_rewards():
    pending  = RewardRequest.query.filter_by(status="pending")\
                                  .order_by(RewardRequest.created_at.desc()).all()
    approved = RewardRequest.query.filter_by(status="approved")\
                                  .order_by(RewardRequest.updated_at.desc()).limit(20).all()
    rejected = RewardRequest.query.filter_by(status="rejected")\
                                  .order_by(RewardRequest.updated_at.desc()).limit(20).all()
    return render_template(
        "rewards/admin_rewards.html",
        pending=pending,
        approved=approved,
        rejected=rejected,
        rewards=REWARDS,
    )


# ── الأدمن: موافقة على طلب ────────────────────────────────────────────────────
@rewards_bp.route("/admin/rewards/<int:req_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_reward(req_id):
    req = RewardRequest.query.get_or_404(req_id)
    if req.status != "pending":
        flash("هذا الطلب تمت معالجته مسبقاً.", "warning")
        return redirect(url_for("rewards.admin_rewards"))

    coupon = RewardRequest.generate_coupon()
    req.status      = "approved"
    req.coupon_code = coupon

    # إشعار للمتدرب
    reward_name = REWARDS.get(req.reward_type, {}).get("name", req.reward_type)
    notif = Notification(
        user_id=req.user_id,
        message=f"🎉 تمت الموافقة على طلبك! كوبونك: {coupon} — {reward_name} من {req.location}",
        link="/rewards",
    )
    db.session.add(notif)
    db.session.commit()

    # إرسال الكوبون على الإيميل
    try:
        send_reward_coupon_email(
            to_email=req.user.email,
            username=req.user.username,
            reward_name=reward_name,
            location=req.location,
            coupon_code=coupon,
        )
    except Exception as e:
        logger.warning(f"Coupon email failed: {e}")

    flash(f"تمت الموافقة وأُرسل الكوبون {coupon} للمتدرب.", "success")
    return redirect(url_for("rewards.admin_rewards"))


# ── الأدمن: رفض طلب ───────────────────────────────────────────────────────────
@rewards_bp.route("/admin/rewards/<int:req_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject_reward(req_id):
    req = RewardRequest.query.get_or_404(req_id)
    if req.status != "pending":
        flash("هذا الطلب تمت معالجته مسبقاً.", "warning")
        return redirect(url_for("rewards.admin_rewards"))

    note = request.form.get("note", "").strip()
    req.status     = "rejected"
    req.admin_note = note

    # إعادة النقاط للمتدرب
    user = req.user
    user.total_points = (user.total_points or 0) + req.points_cost
    tx = PointTransaction(
        user_id=user.id,
        points=req.points_cost,
        reason=f"إعادة نقاط: طلب مرفوض ({req.reward_type})",
    )
    db.session.add(tx)

    # إشعار للمتدرب
    msg = f"❌ تم رفض طلب المكافأة."
    if note:
        msg += f" السبب: {note}"
    msg += f" أُعيدت {req.points_cost} نقطة لرصيدك."
    notif = Notification(user_id=user.id, message=msg, link="/rewards")
    db.session.add(notif)
    db.session.commit()

    flash("تم رفض الطلب وإعادة النقاط للمتدرب.", "warning")
    return redirect(url_for("rewards.admin_rewards"))


# ── API: تقييم المنصة ─────────────────────────────────────────────────────────
@rewards_bp.route("/api/rate-platform", methods=["POST"])
@login_required
def rate_platform():
    data   = request.get_json(silent=True) or {}
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"ok": False, "error": "تقييم غير صحيح"}), 400

    pr = PlatformRating(
        user_id=current_user.id,
        rating=rating,
        comment=comment or None,
    )
    db.session.add(pr)
    db.session.commit()
    return jsonify({"ok": True})
