import pytest
from flask import Flask

from app.api import api
from app.auth import auth
from app.auth.model import User
from app.core import db, login_manager
from app.pets import pets
from app.pets.model import Pet


@pytest.fixture()
def app():
    test_app = Flask(__name__)
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret",
    )

    db.init_app(test_app)
    login_manager.init_app(test_app)
    test_app.register_blueprint(pets)
    test_app.register_blueprint(auth)
    test_app.register_blueprint(api)

    @test_app.route("/")
    def index():
        return "ok"

    @test_app.route("/game")
    def game():
        return "game"

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
