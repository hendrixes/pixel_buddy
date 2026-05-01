from flask import Flask, redirect, render_template, url_for
from flask_login import login_required

from app.api import api
from app.auth import auth
from app.pets import pets
from app.core import db
from app.core import login_manager

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "chave-secreta"

app.register_blueprint(pets)
app.register_blueprint(auth)
app.register_blueprint(api)

db.init_app(app)
login_manager.init_app(app)


@app.route("/")
def index():
    return redirect(url_for("game"))


@app.route("/game")
@login_required
def game():
    return render_template("game.html")
