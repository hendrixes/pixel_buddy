from hashlib import sha256
from ipaddress import ip_address
from secrets import token_urlsafe

from app.core import db
from app.firewall.model import Agent, BlockedIP, FirewallEvent, utc_now
from app.pets.service import clamp


VALID_ACTIONS = {"reported", "blocked", "block_failed"}
VALID_EVENT_SOURCES = {"agent", "pcap_upload"}


def hash_agent_token(token):
    return sha256(token.encode("utf-8")).hexdigest()


def create_agent_for_user(user, name, mode="dry-run"):
    token = token_urlsafe(32)
    agent = Agent(
        user=user,
        name=name.strip(),
        mode=mode,
        token_hash=hash_agent_token(token),
    )
    db.session.add(agent)
    db.session.commit()
    return agent, token


def authenticate_agent_token(token):
    if not token:
        return None

    token_hash = hash_agent_token(token)
    agent = Agent.query.filter_by(token_hash=token_hash).first()

    if agent:
        agent.last_seen_at = utc_now()

    return agent


def validate_ip(value):
    return str(ip_address(value))


def validate_packet_count(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("packet_count must be an integer")

    if value < 0:
        raise ValueError("packet_count must be greater than or equal to 0")

    return value


def validate_destination_port(value):
    if value is None or value == "":
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("destination_port must be an integer")

    if value < 0 or value > 65535:
        raise ValueError("destination_port must be between 0 and 65535")

    return value


def validate_action(value):
    if value not in VALID_ACTIONS:
        raise ValueError("action is not supported")

    return value


def validate_event_type(value):
    if not isinstance(value, str):
        raise ValueError("event_type must be a string")

    event_type = value.strip()
    if not event_type:
        raise ValueError("event_type is required")

    if len(event_type) > 40:
        raise ValueError("event_type must be 40 characters or fewer")

    return event_type


def validate_summary(value):
    if value is None:
        return ""

    if not isinstance(value, str):
        raise ValueError("summary must be a string")

    if len(value) > 255:
        raise ValueError("summary must be 255 characters or fewer")

    return value


def validate_event_source(value):
    if value not in VALID_EVENT_SOURCES:
        raise ValueError("event source is not supported")

    return value


def update_pet_from_firewall_event(pet, event):
    if not pet:
        return

    xp_gain = max(1, min(10, event.packet_count // 20))
    pet.network_xp += xp_gain
    pet.curiosity = clamp(pet.curiosity + 8)
    pet.energy = clamp(pet.energy - 5)

    if event.action == "blocked":
        pet.mood = "angry"
    else:
        pet.mood = "alert"


def record_firewall_event_for_user(user, payload, source="agent", agent=None):
    source_ip = validate_ip(payload["source_ip"])
    action = validate_action(payload.get("action", "reported"))
    packet_count = validate_packet_count(payload.get("packet_count", 0))
    destination_port = validate_destination_port(payload.get("destination_port"))
    event_type = validate_event_type(payload.get("event_type"))
    summary = validate_summary(payload.get("summary", ""))
    event_source = validate_event_source(source)
    event = FirewallEvent(
        user_id=user.id,
        agent_id=agent.id if agent else None,
        source=event_source,
        event_type=event_type,
        source_ip=source_ip,
        destination_port=destination_port,
        packet_count=packet_count,
        action=action,
        summary=summary,
    )
    db.session.add(event)

    if action == "blocked":
        existing_block = BlockedIP.query.filter_by(
            user_id=user.id,
            ip_address=source_ip,
            active=True,
        ).first()

        if not existing_block:
            db.session.add(
                BlockedIP(
                    user_id=user.id,
                    agent_id=agent.id if agent else None,
                    ip_address=source_ip,
                    reason=event.event_type,
                    notes=event.summary,
                    source=event_source,
                    active=True,
                )
            )

    update_pet_from_firewall_event(user.pet, event)
    db.session.commit()
    return event


def record_firewall_event(agent, payload):
    return record_firewall_event_for_user(
        user=agent.user,
        payload=payload,
        source="agent",
        agent=agent,
    )
