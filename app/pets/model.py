from datetime import datetime, timezone

from app.core import db


def utc_now():
    return datetime.now(timezone.utc)


class Pet(db.Model):
    __tablename__ = "pets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    name = db.Column(db.String(80), nullable=False)
    hunger = db.Column(db.Integer, nullable=False, default=50)
    happiness = db.Column(db.Integer, nullable=False, default=50)
    energy = db.Column(db.Integer, nullable=False, default=50)
    curiosity = db.Column(db.Integer, nullable=False, default=50)
    network_xp = db.Column(db.Integer, nullable=False, default=0)
    mood = db.Column(db.String(30), nullable=False, default="neutral")

    last_network_action_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_tick_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )
    created_at = db.Column(db.DateTime(timezone=True),
                           nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="pet")
    network_events = db.relationship(
        "NetworkEvent",
        back_populates="pet",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "hunger": self.hunger,
            "happiness": self.happiness,
            "energy": self.energy,
            "curiosity": self.curiosity,
            "network_xp": self.network_xp,
            "mood": self.mood,
            "last_network_action_at": (
                self.last_network_action_at.isoformat()
                if self.last_network_action_at
                else None
            ),
            "last_tick_at": self.last_tick_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class NetworkEvent(db.Model):
    __tablename__ = "network_events"

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey("pets.id"), nullable=False)

    event_type = db.Column(db.String(40), nullable=False)
    target = db.Column(db.String(120), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=False)
    summary = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    pet = db.relationship("Pet", back_populates="network_events")

    def to_dict(self):
        return {
            "id": self.id,
            "pet_id": self.pet_id,
            "event_type": self.event_type,
            "target": self.target,
            "success": self.success,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
        }
