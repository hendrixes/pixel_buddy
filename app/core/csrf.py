from secrets import token_urlsafe

from flask import abort, request, session


CSRF_SESSION_KEY = "_csrf_token"


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf():
    session_token = session.get(CSRF_SESSION_KEY)
    form_token = request.form.get("csrf_token", "")

    if not session_token or not form_token or session_token != form_token:
        abort(400)


def register_csrf(app):
    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": get_csrf_token}
