from datetime import datetime, timezone

from app.core import db


def utc_now():
    return datetime.now(timezone.utc)


class Agent(db.Model):
    __tablename__ = "agents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    mode = db.Column(db.String(20), nullable=False, default="dry-run")
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="agents")
    events = db.relationship(
        "FirewallEvent",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    blocked_ips = db.relationship("BlockedIP", back_populates="agent")


class FirewallEvent(db.Model):
    __tablename__ = "firewall_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    event_type = db.Column(db.String(40), nullable=False)
    source_ip = db.Column(db.String(45), nullable=False)
    destination_port = db.Column(db.Integer, nullable=True)
    packet_count = db.Column(db.Integer, nullable=False, default=0)
    action = db.Column(db.String(40), nullable=False, default="reported")
    summary = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="firewall_events")
    agent = db.relationship("Agent", back_populates="events")


class BlockedIP(db.Model):
    __tablename__ = "blocked_ips"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=True)
    ip_address = db.Column(db.String(45), nullable=False)
    reason = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.String(255), nullable=False, default="")
    source = db.Column(db.String(20), nullable=False, default="manual")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="blocked_ips")
    agent = db.relationship("Agent", back_populates="blocked_ips")
