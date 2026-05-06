from pathlib import Path

import pytest
from flask import Flask

from app.auth import auth
from app.auth.model import User
from app.core import db, login_manager, register_csrf
from app.firewall import agent_api, firewall
from app.main import game, leaderboard
from app.pets.model import Pet


@pytest.fixture()
def app():
    template_folder = Path(__file__).resolve().parents[1] / "app" / "templates"
    test_app = Flask(__name__, template_folder=template_folder)
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret",
    )

    db.init_app(test_app)
    login_manager.init_app(test_app)
    register_csrf(test_app)
    test_app.register_blueprint(auth)
    test_app.register_blueprint(firewall)
    test_app.register_blueprint(agent_api)

    @test_app.route("/")
    def index():
        return "ok"

    test_app.add_url_rule("/game", view_func=game)
    test_app.add_url_rule("/leaderboard", view_func=leaderboard)

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_user(username="alice", password="password"):
    user = User(username=username)
    user.set_password(password)
    user.pet = Pet(name=f"{username}-buddy")
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username="alice", password="password"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
