from flask import Flask, redirect, render_template, send_file, url_for, request, flash
from flask_login import current_user, login_required

from app.api import api
from app.auth import auth
from app.firewall import agent_api, firewall
from app.display import render_pet_screen
from app.pets import pets
from app.core import db
from app.core import login_manager
from app.core import register_csrf
from app.pets import Pet
from app.pets.service import tick_pet

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "chave-secreta"

app.register_blueprint(pets)
app.register_blueprint(auth)
app.register_blueprint(api)
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
    pet_name = request.form.get("pet_name", "").strip()

    if not pet_name:
        flash("digita o nome do baguio ae carai")
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
