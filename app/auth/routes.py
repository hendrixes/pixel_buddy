from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.model import User
from app.core import validate_csrf
from app.core.db import db
from app.core.login import login_manager


auth = Blueprint("auth", import_name=__name__, url_prefix="/auth")
MAX_USERNAME_LENGTH = 80
MIN_PASSWORD_LENGTH = 6


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    flash("Faca login para continuar.")
    return redirect(url_for("auth.login"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("game"))

    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Preencha usuario e senha.")
            return render_template("auth/register.html")

        if len(username) > MAX_USERNAME_LENGTH:
            flash("Usuario deve ter no maximo 80 caracteres.")
            return render_template("auth/register.html")

        if len(password) < MIN_PASSWORD_LENGTH:
            flash("Senha deve ter pelo menos 6 caracteres.")
            return render_template("auth/register.html")

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("Usuario ja existe.")
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
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Usuario ou senha invalidos.")
            return render_template("auth/login.html")

        login_user(user)

        return redirect(url_for("index"))
    return render_template("auth/login.html")


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    validate_csrf()
    logout_user()
    flash("Sessao encerrada.")
    return redirect(url_for("auth.login"))
