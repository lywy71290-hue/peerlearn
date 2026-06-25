from datetime import datetime, timedelta
from app import db
import random
import string


class OTPCode(db.Model):
    __tablename__ = 'otp_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='otp_codes')

    def __init__(self, user_id):
        self.user_id = user_id
        self.code = ''.join(random.choices(string.digits, k=6))
        self.created_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(minutes=10)
        self.used = False

    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at
