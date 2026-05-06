from app.core import db
from app.core.csrf import CSRF_SESSION_KEY
from app.firewall.model import BlockedIP
from tests.conftest import create_user, login


def csrf_form(client, **data):
    token = "known-test-csrf-token"
    with client.session_transaction() as session:
        session[CSRF_SESSION_KEY] = token

    return {**data, "csrf_token": token}


def test_blocked_ip_crud_for_current_user(client, app):
    create_user()
    login(client)

    response = client.post(
        "/blocked-ips",
        data=csrf_form(
            client,
            ip_address="192.168.56.44",
            reason="manual test",
            notes="created from pytest",
        ),
        follow_redirects=False,
    )

    blocked_ip = BlockedIP.query.filter_by(ip_address="192.168.56.44").first()

    assert response.status_code == 302
    assert blocked_ip is not None
    assert blocked_ip.user.username == "alice"

    update_response = client.post(
        f"/blocked-ips/{blocked_ip.id}/edit",
        data=csrf_form(
            client,
            ip_address="192.168.56.46",
            reason="updated manual test",
            notes="updated from pytest",
            active="on",
        ),
        follow_redirects=False,
    )
    db.session.refresh(blocked_ip)

    assert update_response.status_code == 302
    assert blocked_ip.ip_address == "192.168.56.46"
    assert blocked_ip.reason == "updated manual test"
    assert blocked_ip.notes == "updated from pytest"

    blocked_ip_id = blocked_ip.id
    delete_response = client.post(
        f"/blocked-ips/{blocked_ip_id}/delete",
        data=csrf_form(client),
        follow_redirects=False,
    )

    assert delete_response.status_code == 302
    assert db.session.get(BlockedIP, blocked_ip_id) is None


def test_blocked_ip_create_without_csrf_is_rejected(client, app):
    create_user()
    login(client)

    response = client.post(
        "/blocked-ips",
        data={
            "ip_address": "192.168.56.45",
            "reason": "manual test",
            "notes": "missing csrf",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert BlockedIP.query.filter_by(ip_address="192.168.56.45").first() is None


def test_blocked_ip_detail_idor_is_blocked(client, app):
    user_a = create_user(username="alice")
    blocked_ip = BlockedIP(
        user_id=user_a.id,
        ip_address="192.168.56.55",
        reason="belongs to alice",
        notes="private record",
    )
    db.session.add(blocked_ip)
    db.session.commit()

    create_user(username="bob")
    login(client, username="bob")

    response = client.get(f"/blocked-ips/{blocked_ip.id}")

    assert response.status_code == 404


def test_blocked_ip_edit_idor_is_blocked(client, app):
    user_a = create_user(username="alice")
    blocked_ip = BlockedIP(
        user_id=user_a.id,
        ip_address="192.168.56.56",
        reason="belongs to alice",
        notes="private record",
    )
    db.session.add(blocked_ip)
    db.session.commit()

    create_user(username="bob")
    login(client, username="bob")

    response = client.get(f"/blocked-ips/{blocked_ip.id}/edit")

    assert response.status_code == 404


def test_blocked_ip_update_idor_is_blocked(client, app):
    user_a = create_user(username="alice")
    blocked_ip = BlockedIP(
        user_id=user_a.id,
        ip_address="192.168.56.57",
        reason="belongs to alice",
        notes="private record",
        active=True,
    )
    db.session.add(blocked_ip)
    db.session.commit()

    create_user(username="bob")
    login(client, username="bob")

    response = client.post(
        f"/blocked-ips/{blocked_ip.id}/edit",
        data=csrf_form(
            client,
            ip_address="192.168.56.99",
            reason="bob update",
            notes="changed",
            active="on",
        ),
        follow_redirects=False,
    )
    db.session.refresh(blocked_ip)

    assert response.status_code == 404
    assert blocked_ip.ip_address == "192.168.56.57"
    assert blocked_ip.reason == "belongs to alice"
    assert blocked_ip.notes == "private record"


def test_blocked_ip_delete_idor_is_blocked(client, app):
    user_a = create_user(username="alice")
    blocked_ip = BlockedIP(
        user_id=user_a.id,
        ip_address="192.168.56.58",
        reason="belongs to alice",
        notes="private record",
    )
    db.session.add(blocked_ip)
    db.session.commit()
    blocked_ip_id = blocked_ip.id

    create_user(username="bob")
    login(client, username="bob")

    response = client.post(
        f"/blocked-ips/{blocked_ip_id}/delete",
        data=csrf_form(client),
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert db.session.get(BlockedIP, blocked_ip_id) is not None
