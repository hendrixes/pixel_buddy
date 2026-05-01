from datetime import datetime, timezone

from app.core import db


def utc_now():
    return datetime.now(timezone.utc)


class Pet(db.Model):
    __tablename__ = "pets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(80), nullable=False)
    hunger = db.Column(db.Integer, nullable=False, default=50)
    happiness = db.Column(db.Integer, nullable=False, default=50)
    energy = db.Column(db.Integer, nullable=False, default=50)
    hygiene = db.Column(db.Integer, nullable=False, default=50)
    age_seconds = db.Column(db.Integer, nullable=False, default=0)
    mood = db.Column(db.String(30), nullable=False, default="neutral")

    last_tick_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )
    created_at = db.Column(db.DateTime(timezone=True),
                           nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="pets")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "hunger": self.hunger,
            "happiness": self.happiness,
            "energy": self.energy,
            "hygiene": self.hygiene,
            "age_seconds": self.age_seconds,
            "mood": self.mood,
            "last_tick_at": self.last_tick_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }
