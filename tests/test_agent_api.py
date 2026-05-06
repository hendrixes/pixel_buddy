from app.core import db
from app.firewall.model import BlockedIP, FirewallEvent
from app.firewall.service import create_agent_for_user
from tests.conftest import create_user


def post_agent_event(client, token, json):
    return client.post(
        "/api/agent/events",
        headers={"Authorization": f"Bearer {token}"},
        json=json,
    )


def test_agent_event_api_requires_token(client, app):
    response = client.post("/api/agent/events", json={})

    assert response.status_code == 401


def test_agent_event_api_records_blocked_event(client, app):
    user = create_user()
    _agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    response = post_agent_event(
        client,
        token,
        json={
            "event_type": "possible_dos",
            "source_ip": "192.168.56.77",
            "destination_port": 5000,
            "packet_count": 150,
            "action": "blocked",
            "summary": "threshold exceeded",
        },
    )

    assert response.status_code == 201
    assert FirewallEvent.query.count() == 1
    assert BlockedIP.query.filter_by(ip_address="192.168.56.77").first() is not None


def test_agent_event_api_rejects_array_json(client, app):
    user = create_user()
    agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    response = post_agent_event(client, token, json=[])
    db.session.refresh(agent)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_payload",
        "message": "JSON body must be an object",
    }
    assert agent.last_seen_at is None
    assert FirewallEvent.query.count() == 0


def test_agent_event_api_missing_fields_does_not_persist_last_seen(client, app):
    user = create_user()
    agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    response = post_agent_event(client, token, json={"event_type": "possible_dos"})
    db.session.refresh(agent)

    assert response.status_code == 400
    assert response.get_json()["error"] == "missing_fields"
    assert agent.last_seen_at is None
    assert FirewallEvent.query.count() == 0


def test_agent_event_api_rejects_non_string_summary(client, app):
    user = create_user()
    agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    response = post_agent_event(
        client,
        token,
        json={
            "event_type": "possible_dos",
            "source_ip": "192.168.56.78",
            "packet_count": 150,
            "action": "blocked",
            "summary": {"text": "threshold exceeded"},
        },
    )
    db.session.refresh(agent)

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_payload"
    assert agent.last_seen_at is None
    assert FirewallEvent.query.count() == 0
    assert BlockedIP.query.count() == 0


def test_agent_event_api_rejects_long_summary(client, app):
    user = create_user()
    agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    response = post_agent_event(
        client,
        token,
        json={
            "event_type": "possible_dos",
            "source_ip": "192.168.56.79",
            "packet_count": 150,
            "action": "blocked",
            "summary": "x" * 256,
        },
    )
    db.session.refresh(agent)

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_payload"
    assert agent.last_seen_at is None
    assert FirewallEvent.query.count() == 0
    assert BlockedIP.query.count() == 0


def test_agent_blocklist_api_requires_token(client, app):
    response = client.get("/api/agent/blocked-ips")

    assert response.status_code == 401


def test_agent_blocklist_api_returns_only_owner_active_ips(client, app):
    user = create_user(username="alice")
    other_user = create_user(username="bob")
    agent, token = create_agent_for_user(user, name="lab-vm", mode="ufw")
    active_ip = BlockedIP(
        user_id=user.id,
        ip_address="192.168.56.10",
        reason="manual",
        source="manual",
        active=True,
    )
    inactive_ip = BlockedIP(
        user_id=user.id,
        ip_address="192.168.56.11",
        reason="old",
        source="manual",
        active=False,
    )
    other_user_ip = BlockedIP(
        user_id=other_user.id,
        ip_address="192.168.56.12",
        reason="other user",
        source="manual",
        active=True,
    )
    db.session.add_all([active_ip, inactive_ip, other_user_ip])
    db.session.commit()

    response = client.get(
        "/api/agent/blocked-ips",
        headers={"Authorization": f"Bearer {token}"},
    )
    db.session.refresh(agent)

    assert response.status_code == 200
    assert response.get_json() == {
        "blocked_ips": [
            {
                "id": active_ip.id,
                "ip_address": "192.168.56.10",
                "reason": "manual",
                "source": "manual",
            }
        ]
    }
    assert agent.last_seen_at is not None
