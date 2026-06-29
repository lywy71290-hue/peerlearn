from app import db
from datetime import datetime
import random
import string


class PointTransaction(db.Model):
    """سجل النقاط — كل عملية كسب أو خصم نقاط"""
    __tablename__ = "point_transactions"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    points      = db.Column(db.Integer, nullable=False)          # موجب = كسب، سالب = خصم
    reason      = db.Column(db.String(200), nullable=False)      # سبب النقاط
    video_id    = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user  = db.relationship("User",  backref="point_transactions")
    video = db.relationship("Video", backref="point_transactions")


class RewardRequest(db.Model):
    """طلب استبدال النقاط بمكافأة"""
    __tablename__ = "reward_requests"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reward_type  = db.Column(db.String(50),  nullable=False)   # 'coffee' أو 'meal'
    location     = db.Column(db.String(100), nullable=False)   # اسم المطعم/الكافيه
    points_cost  = db.Column(db.Integer,     nullable=False)   # عدد النقاط المخصومة
    status       = db.Column(db.String(20),  default="pending")  # pending / approved / rejected
    coupon_code  = db.Column(db.String(20),  nullable=True)    # الكود الفريد بعد الموافقة
    admin_note   = db.Column(db.String(300), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="reward_requests")

    @staticmethod
    def generate_coupon():
        """توليد كود كوبون فريد"""
        chars = string.ascii_uppercase + string.digits
        return "NITI-" + ''.join(random.choices(chars, k=8))


class PlatformRating(db.Model):
    """تقييمات المنصة من المتدربين"""
    __tablename__ = "platform_ratings"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    rating     = db.Column(db.Integer, nullable=False)          # 1-5
    comment    = db.Column(db.Text,    nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="platform_ratings")
