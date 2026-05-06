import os

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.auth import User, auth
from app.core import db, login_manager, register_csrf, validate_csrf
from app.display import render_pet_screen
from app.firewall import agent_api, firewall
from app.pets import Pet
from app.pets.service import tick_pet

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///database.db",
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "1"

app.register_blueprint(auth)
app.register_blueprint(firewall)
app.register_blueprint(agent_api)

db.init_app(app)
login_manager.init_app(app)
register_csrf(app)


@app.route("/")
def index():
    return redirect(url_for("game"))


@app.route("/game/setup", methods=["POST"])
@login_required
def game_setup():
    validate_csrf()
    pet_name = request.form.get("pet_name", "").strip()

    if not pet_name:
        flash("Informe o nome do buddy.")
        return redirect(url_for("game"))

    if current_user.pet:
        return redirect(url_for("game"))

    current_user.pet = Pet(name=pet_name)
    db.session.commit()

    return redirect(url_for("game"))


@app.route("/game/screen.png")
@login_required
def render_screen():
    if not current_user.pet:
        return redirect(url_for("game"))

    if tick_pet(current_user.pet):
        db.session.commit()

    image = render_pet_screen(current_user.pet)

    return send_file(image, mimetype="image/png", max_age=0)


@app.route("/game")
@login_required
def game():
    if not current_user.pet:
        return render_template("game_setup.html")

    if tick_pet(current_user.pet):
        db.session.commit()

    return render_template("game.html")


@app.route("/leaderboard")
@login_required
def leaderboard():
    users = (
        User.query.join(Pet)
        .order_by(Pet.network_xp.desc())
        .limit(20)
        .all()
    )
    return render_template("leaderboard.html", users=users)
