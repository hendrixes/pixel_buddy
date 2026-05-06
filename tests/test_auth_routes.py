from app.auth.model import User
from tests.conftest import create_user, csrf_form, login


def test_register_without_csrf_is_rejected(client, app):
    response = client.post(
        "/auth/register",
        data={"username": "mallory", "password": "password"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert User.query.filter_by(username="mallory").first() is None


def test_login_without_csrf_is_rejected(client, app):
    create_user()

    response = client.post(
        "/auth/login",
        data={"username": "alice", "password": "password"},
        follow_redirects=False,
    )

    assert response.status_code == 400


def test_register_with_csrf_creates_user(client, app):
    response = client.post(
        "/auth/register",
        data=csrf_form(client, username="mallory", password="password"),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert User.query.filter_by(username="mallory").first() is not None


def test_register_rejects_short_password(client, app):
    response = client.post(
        "/auth/register",
        data=csrf_form(client, username="mallory", password="12345"),
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert User.query.filter_by(username="mallory").first() is None


def test_register_rejects_long_username(client, app):
    long_username = "a" * 81

    response = client.post(
        "/auth/register",
        data=csrf_form(client, username=long_username, password="password"),
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert User.query.filter_by(username=long_username).first() is None


def test_logout_without_csrf_is_rejected(client, app):
    create_user()
    login(client)

    response = client.post("/auth/logout", follow_redirects=False)

    assert response.status_code == 400


def test_game_setup_without_csrf_is_rejected(client, app):
    create_user()
    login(client)

    response = client.post(
        "/game/setup",
        data={"pet_name": "new-name"},
        follow_redirects=False,
    )

    assert response.status_code == 400
