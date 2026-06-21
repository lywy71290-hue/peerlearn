from datetime import datetime
from app import db


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)   # 1-5
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("video_id", "user_id", name="unique_video_user_rating"),
        db.CheckConstraint("score >= 1 AND score <= 5", name="score_range"),
    )

    def __repr__(self):
        return f"<Rating {self.score} on Video {self.video_id}>"
