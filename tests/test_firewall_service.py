import pytest

from app.core import db
from app.display.faces import get_face
from app.firewall.model import Agent, BlockedIP, FirewallEvent
from app.firewall.service import (
    authenticate_agent_token,
    create_agent_for_user,
    record_firewall_event,
)
from tests.conftest import create_user


def test_create_agent_returns_plain_token_once(app):
    user = create_user()

    agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    assert agent.id is not None
    assert token
    assert agent.token_hash != token
    assert authenticate_agent_token(token) == agent


def test_authenticate_agent_token_does_not_commit_last_seen(app):
    user = create_user()
    agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    assert authenticate_agent_token(token) == agent
    assert agent.last_seen_at is not None

    db.session.rollback()
    db.session.refresh(agent)

    assert agent.last_seen_at is None


def test_record_firewall_event_updates_pet_and_creates_records(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    event = record_firewall_event(
        agent=agent,
        payload={
            "event_type": "possible_dos",
            "source_ip": "192.168.56.20",
            "destination_port": 5000,
            "packet_count": 120,
            "action": "blocked",
            "summary": "120 packets in 5 seconds",
        },
    )

    blocked_ip = BlockedIP.query.filter_by(
        user_id=user.id,
        ip_address="192.168.56.20",
    ).first()

    assert isinstance(event, FirewallEvent)
    assert event.user_id == user.id
    assert blocked_ip is not None
    assert blocked_ip.reason == "possible_dos"
    assert user.pet.mood == "angry"
    assert user.pet.network_xp > 0


def test_record_firewall_event_without_block_only_logs_event(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    record_firewall_event(
        agent=agent,
        payload={
            "event_type": "port_pressure",
            "source_ip": "192.168.56.30",
            "destination_port": 22,
            "packet_count": 30,
            "action": "reported",
            "summary": "30 packets to port 22",
        },
    )

    assert FirewallEvent.query.count() == 1
    assert BlockedIP.query.count() == 0
    assert user.pet.mood == "alert"
    assert user.pet.curiosity > 50


def test_reported_agent_event_does_not_create_blocked_ip(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    record_firewall_event(
        agent=agent,
        payload={
            "event_type": "possible_dos",
            "source_ip": "192.168.56.80",
            "destination_port": 80,
            "packet_count": 50,
            "action": "reported",
            "summary": "dry-run detection",
        },
    )

    assert FirewallEvent.query.count() == 1
    assert BlockedIP.query.count() == 0


def test_firewall_moods_have_distinct_faces(app):
    neutral_face = get_face("neutral")

    assert get_face("angry") != neutral_face
    assert get_face("alert") != neutral_face


def test_record_firewall_event_rejects_negative_packet_count(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    with pytest.raises(ValueError):
        record_firewall_event(
            agent=agent,
            payload={
                "event_type": "possible_dos",
                "source_ip": "192.168.56.40",
                "destination_port": 5000,
                "packet_count": -1,
                "action": "reported",
            },
        )

    assert FirewallEvent.query.count() == 0


def test_record_firewall_event_rejects_invalid_port(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    with pytest.raises(ValueError):
        record_firewall_event(
            agent=agent,
            payload={
                "event_type": "possible_dos",
                "source_ip": "192.168.56.41",
                "destination_port": 70000,
                "packet_count": 10,
                "action": "reported",
            },
        )

    assert FirewallEvent.query.count() == 0


def test_record_firewall_event_rejects_invalid_action(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    with pytest.raises(ValueError):
        record_firewall_event(
            agent=agent,
            payload={
                "event_type": "possible_dos",
                "source_ip": "192.168.56.42",
                "destination_port": 22,
                "packet_count": 10,
                "action": "drop",
            },
        )

    assert FirewallEvent.query.count() == 0
