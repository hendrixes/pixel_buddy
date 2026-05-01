from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.core import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    pets = db.relationship(
        "Pet",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str):
        return check_password_hash(self.password_hash, password)
