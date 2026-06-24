from app import db
from datetime import datetime


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room       = db.Column(db.String(100), nullable=False, default="general")
    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship("User", backref="chat_messages", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "username":   self.author.username,
            "content":    self.content,
            "room":       self.room,
            "created_at": self.created_at.strftime("%H:%M"),
        }
