from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.core.db import db
from app.core.login import login_manager
from app.auth.model import User


auth = Blueprint("auth", import_name=__name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    flash("faz login ae caralho")
    return redirect(url_for("auth.login"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("game"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("preenche os dois ae caralho")
            return render_template("auth/register.html")

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("ja existe esse mano ae tio")
            return render_template("auth/register.html")

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)

        return redirect(url_for("game"))

    return render_template("auth/register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("ta errado esse bagulho ae tio")
            return render_template("auth/login.html")

        login_user(user)

        return redirect(url_for("index"))
    return render_template("auth/login.html")


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("voce deslogo no bagulho")
    return redirect(url_for("auth.login"))
