from app import db
from datetime import datetime


class Post(db.Model):
    __tablename__ = "posts"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    caption     = db.Column(db.Text, nullable=False)
    image_url   = db.Column(db.String(500), nullable=True)   # Cloudinary URL
    image_public_id = db.Column(db.String(300), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    author   = db.relationship("User", backref="posts", lazy=True)
    comments = db.relationship("PostComment", backref="post", lazy=True,
                               cascade="all, delete-orphan",
                               order_by="PostComment.created_at")
    likes    = db.relationship("PostLike", backref="post", lazy=True,
                               cascade="all, delete-orphan")

    @property
    def like_count(self):
        return len(self.likes)

    def __repr__(self):
        return f"<Post {self.id} by user {self.user_id}>"


class PostComment(db.Model):
    __tablename__ = "post_comments"

    id         = db.Column(db.Integer, primary_key=True)
    post_id    = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship("User", backref="post_comments", lazy=True)


class PostLike(db.Model):
    __tablename__ = "post_likes"

    id      = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("post_id", "user_id"),)
