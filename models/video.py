from datetime import datetime
from app import db


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    gcs_url = db.Column(db.String(512), nullable=False)
    thumbnail_url = db.Column(db.String(512), default="")
    duration = db.Column(db.Integer, default=0)   # seconds

    # Classification
    term = db.Column(db.String(50), nullable=False)    # e.g. "Term 1"
    level = db.Column(db.String(50), nullable=False)   # e.g. "Beginner"
    unit = db.Column(db.String(50), nullable=False)    # e.g. "Unit 3 - Lesson 2"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Moderation
    is_approved = db.Column(db.Boolean, default=False, nullable=False)  # False = pending review

    comments = db.relationship(
        "Comment", backref="video", lazy=True, cascade="all, delete-orphan"
    )
    ratings = db.relationship(
        "Rating", backref="video", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def avg_rating(self):
        if not self.ratings:
            return 0
        return round(sum(r.score for r in self.ratings) / len(self.ratings), 1)

    @property
    def rating_count(self):
        return len(self.ratings)

    def __repr__(self):
        return f"<Video {self.title}>"
