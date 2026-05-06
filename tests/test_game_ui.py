from io import BytesIO

from PIL import Image, ImageFont

from app.core import db
from tests.conftest import create_user, login
from tests.conftest import csrf_form


def test_leaderboard_requires_login(client):
    response = client.get("/leaderboard")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_leaderboard_renders_logged_in_users_by_xp(client, app):
    create_user(username="alice").pet.network_xp = 10
    create_user(username="bob").pet.network_xp = 40
    db.session.commit()
    login(client, username="alice")

    response = client.get("/leaderboard")

    assert response.status_code == 200
    assert response.data.find(b"bob-buddy") < response.data.find(b"alice-buddy")
    assert b"bob-buddy" in response.data
    assert b"40" in response.data


def test_game_dashboard_links_replace_pet_action_buttons(client, app):
    create_user()
    login(client)

    response = client.get("/game")

    assert response.status_code == 200
    assert b'href="/agents"' in response.data
    assert b'href="/blocked-ips"' in response.data
    assert b'href="/pcaps/upload"' in response.data
    assert b'href="/leaderboard"' in response.data
    assert b'data-action="feed"' not in response.data
    assert b'data-action="play"' not in response.data
    assert b'data-action="sleep"' not in response.data
    assert b'data-action="observe"' not in response.data
    assert b"fetch(`/pets/action/${action}`" not in response.data


def test_base_template_uses_dark_theme_by_default(client):
    response = client.get("/auth/login")

    assert response.status_code == 200
    assert b'data-theme="dark"' in response.data
    assert b"color-scheme: dark" in response.data


def test_base_template_reads_theme_cookie(client):
    client.set_cookie("pet_theme", "light")

    response = client.get("/auth/login")

    assert response.status_code == 200
    assert b'data-theme="light"' in response.data


def test_theme_route_sets_cookie(client, app):
    create_user()
    login(client)

    response = client.post(
        "/theme",
        data=csrf_form(client, theme="light"),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "pet_theme=light" in response.headers["Set-Cookie"]


def test_screen_renderer_uses_theme_cookie(client, app, monkeypatch):
    create_user()
    login(client)
    client.set_cookie("pet_theme", "dark")
    monkeypatch.setattr(
        "app.display.renderer.load_font",
        lambda _size, bold=False: ImageFont.load_default(),
    )

    response = client.get("/game/screen.png")
    image = Image.open(BytesIO(response.data))

    assert response.status_code == 200
    assert image.getpixel((10, 40)) == 0
    assert image.getpixel((0, 0)) == 255
