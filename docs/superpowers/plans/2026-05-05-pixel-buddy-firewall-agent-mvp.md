# pixel_buddy Firewall Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working MVP of `pixel_buddy` as a gamified firewall SaaS with blocked IP CRUD, agent event ingestion, pet reactions, and a terminal Scapy/UFW agent.

**Architecture:** Flask remains the control panel and source of truth. A new firewall module owns agents, firewall events, and blocked IPs. The terminal agent is a separate Python script that detects suspicious traffic, renders the buddy in the terminal, optionally calls UFW, and reports events to Flask through a token-authenticated API.

**Tech Stack:** Flask, Flask-Login, Flask-SQLAlchemy, SQLite, Jinja templates, Pillow renderer, Scapy for packet monitoring, UFW CLI through `subprocess`, pytest for focused tests.

---

## File Structure

- Modify `pyproject.toml` and `uv.lock`: add `scapy` runtime dependency and `pytest` dev dependency.
- Create `tests/conftest.py`: shared Flask test app, database setup, and user login helpers.
- Create `tests/test_firewall_service.py`: unit tests for agent token auth, event handling, blocked IP creation, and pet mood updates.
- Create `tests/test_firewall_routes.py`: route tests for blocked IP CRUD ownership.
- Create `tests/test_agent_packet_window.py`: unit tests for the terminal agent detector.
- Modify `app/auth/model.py`: add relationships from `User` to firewall records.
- Modify `app/pets/model.py`: keep pet fields and relationships compatible with firewall events.
- Modify `app/pets/service.py`: add firewall-specific pet reaction functions and remove dependence on generic manual actions as the main game loop.
- Modify `app/display/faces.py`: add `angry` and `alert` faces.
- Modify `app/display/renderer.py`: render firewall-oriented labels.
- Create `app/firewall/__init__.py`: exports firewall models first, then blueprints as routes and API are added.
- Create `app/firewall/model.py`: `Agent`, `FirewallEvent`, and `BlockedIP`.
- Create `app/firewall/service.py`: token creation/auth, event ingestion, blocklist creation, and pet updates.
- Create `app/firewall/routes.py`: authenticated HTML CRUD for `BlockedIP` and agent token creation.
- Create `app/firewall/api.py`: token-authenticated API endpoint for `agent.py`.
- Modify `app/main.py`: register firewall blueprints and render recent firewall context on `/game`.
- Modify `init_db.py`: import firewall models before `db.create_all()`.
- Modify `app/templates/base.html`: add navigation links for game, blocked IPs, agents, and leaderboard.
- Modify `app/templates/game.html`: remove generic action buttons and show firewall status links.
- Create `app/templates/firewall/blocked_ips.html`: blocked IP list.
- Create `app/templates/firewall/blocked_ip_form.html`: create/edit form.
- Create `app/templates/firewall/blocked_ip_detail.html`: blocked IP detail.
- Create `app/templates/firewall/agents.html`: agent list and token creation form.
- Create `app/templates/leaderboard.html`: XP ranking.
- Create `agent/pixel_buddy_agent.py`: terminal agent entrypoint.
- Create `agent/packet_window.py`: packet counting and threshold detection.
- Create `agent/ufw.py`: validated UFW block helper.
- Create `agent/README.md`: safe demo instructions.
- Create `docs/IDOR_DEMO.md`: classroom vulnerability demonstration script.

---

## Task 1: Add Test Foundation And Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `tests/conftest.py`

- [ ] **Step 1: Add dependencies**

Run:

```bash
uv add scapy
uv add --dev pytest
```

Expected: `pyproject.toml` contains `scapy` in project dependencies and `pytest` in the dev dependency group. `uv.lock` is updated.

- [ ] **Step 2: Create shared pytest fixtures**

Create `tests/conftest.py`:

```python
import pytest

from app.auth.model import User
from app.core import db
from app.main import app as flask_app
from app.pets.model import Pet


@pytest.fixture()
def app():
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret",
    )

    with flask_app.app_context():
        import app.firewall.model  # noqa: F401

        db.create_all()
        yield flask_app
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
```

- [ ] **Step 3: Run pytest and confirm the expected import failure**

Run:

```bash
uv run pytest -q
```

Expected: FAIL because `app.firewall.model` does not exist yet.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock tests/conftest.py
git commit -m "test: add firewall test foundation"
```

---

## Task 2: Add Firewall Models And Service

**Files:**
- Create: `app/firewall/__init__.py`
- Create: `app/firewall/model.py`
- Create: `app/firewall/service.py`
- Modify: `app/auth/model.py`
- Modify: `init_db.py`
- Create: `tests/test_firewall_service.py`

- [ ] **Step 1: Write service tests**

Create `tests/test_firewall_service.py`:

```python
from app.core import db
from app.firewall.model import Agent, BlockedIP, FirewallEvent
from app.firewall.service import (
    authenticate_agent_token,
    create_agent_for_user,
    record_firewall_event,
)
from tests.conftest import create_user


def test_create_agent_returns_plain_token_once(app):
    user = create_user()

    agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    assert agent.id is not None
    assert token
    assert agent.token_hash != token
    assert authenticate_agent_token(token) == agent


def test_record_firewall_event_updates_pet_and_creates_records(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    event = record_firewall_event(
        agent=agent,
        payload={
            "event_type": "possible_dos",
            "source_ip": "192.168.56.20",
            "destination_port": 5000,
            "packet_count": 120,
            "action": "blocked",
            "summary": "120 packets in 5 seconds",
        },
    )

    blocked_ip = BlockedIP.query.filter_by(
        user_id=user.id,
        ip_address="192.168.56.20",
    ).first()

    assert isinstance(event, FirewallEvent)
    assert event.user_id == user.id
    assert blocked_ip is not None
    assert blocked_ip.reason == "possible_dos"
    assert user.pet.mood == "angry"
    assert user.pet.network_xp > 0


def test_record_firewall_event_without_block_only_logs_event(app):
    user = create_user()
    agent, _token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    record_firewall_event(
        agent=agent,
        payload={
            "event_type": "port_pressure",
            "source_ip": "192.168.56.30",
            "destination_port": 22,
            "packet_count": 30,
            "action": "reported",
            "summary": "30 packets to port 22",
        },
    )

    assert FirewallEvent.query.count() == 1
    assert BlockedIP.query.count() == 0
    assert user.pet.mood == "alert"
    assert user.pet.curiosity > 50
```

- [ ] **Step 2: Run the tests and confirm failure**

Run:

```bash
uv run pytest tests/test_firewall_service.py -q
```

Expected: FAIL because firewall models and service do not exist yet.

- [ ] **Step 3: Create firewall package exports**

Create `app/firewall/__init__.py`:

```python
from app.firewall.model import Agent, BlockedIP, FirewallEvent

__all__ = [
    "Agent",
    "BlockedIP",
    "FirewallEvent",
]
```

- [ ] **Step 4: Create models**

Create `app/firewall/model.py`:

```python
from datetime import datetime, timezone

from app.core import db


def utc_now():
    return datetime.now(timezone.utc)


class Agent(db.Model):
    __tablename__ = "agents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    mode = db.Column(db.String(20), nullable=False, default="dry-run")
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="agents")
    events = db.relationship(
        "FirewallEvent",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    blocked_ips = db.relationship("BlockedIP", back_populates="agent")


class FirewallEvent(db.Model):
    __tablename__ = "firewall_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    event_type = db.Column(db.String(40), nullable=False)
    source_ip = db.Column(db.String(45), nullable=False)
    destination_port = db.Column(db.Integer, nullable=True)
    packet_count = db.Column(db.Integer, nullable=False, default=0)
    action = db.Column(db.String(40), nullable=False, default="reported")
    summary = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="firewall_events")
    agent = db.relationship("Agent", back_populates="events")


class BlockedIP(db.Model):
    __tablename__ = "blocked_ips"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=True)
    ip_address = db.Column(db.String(45), nullable=False)
    reason = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.String(255), nullable=False, default="")
    source = db.Column(db.String(20), nullable=False, default="manual")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="blocked_ips")
    agent = db.relationship("Agent", back_populates="blocked_ips")
```

- [ ] **Step 5: Add user relationships**

Modify `app/auth/model.py` inside `User`:

```python
    agents = db.relationship(
        "Agent",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    firewall_events = db.relationship(
        "FirewallEvent",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    blocked_ips = db.relationship(
        "BlockedIP",
        back_populates="user",
        cascade="all, delete-orphan",
    )
```

- [ ] **Step 6: Create service functions**

Create `app/firewall/service.py`:

```python
from hashlib import sha256
from ipaddress import ip_address
from secrets import token_urlsafe

from app.core import db
from app.firewall.model import Agent, BlockedIP, FirewallEvent, utc_now
from app.pets.service import clamp, update_mood


def hash_agent_token(token):
    return sha256(token.encode("utf-8")).hexdigest()


def create_agent_for_user(user, name, mode="dry-run"):
    token = token_urlsafe(32)
    agent = Agent(
        user=user,
        name=name.strip(),
        mode=mode,
        token_hash=hash_agent_token(token),
    )
    db.session.add(agent)
    db.session.commit()
    return agent, token


def authenticate_agent_token(token):
    if not token:
        return None

    token_hash = hash_agent_token(token)
    agent = Agent.query.filter_by(token_hash=token_hash).first()

    if agent:
        agent.last_seen_at = utc_now()
        db.session.commit()

    return agent


def validate_ip(value):
    return str(ip_address(value))


def update_pet_from_firewall_event(pet, event):
    if not pet:
        return

    xp_gain = max(1, min(10, event.packet_count // 20))
    pet.network_xp += xp_gain
    pet.curiosity = clamp(pet.curiosity + 8)
    pet.energy = clamp(pet.energy - 5)

    if event.action == "blocked":
        pet.mood = "angry"
        pet.happiness = clamp(pet.happiness + 4)
    else:
        pet.mood = "alert"

    update_mood(pet)
    if event.action == "blocked":
        pet.mood = "angry"
    elif event.event_type:
        pet.mood = "alert"


def record_firewall_event(agent, payload):
    source_ip = validate_ip(payload["source_ip"])
    action = payload.get("action", "reported")
    event = FirewallEvent(
        user_id=agent.user_id,
        agent_id=agent.id,
        event_type=payload.get("event_type", "network_event"),
        source_ip=source_ip,
        destination_port=payload.get("destination_port"),
        packet_count=int(payload.get("packet_count", 0)),
        action=action,
        summary=payload.get("summary", ""),
    )
    db.session.add(event)

    if action == "blocked":
        existing_block = BlockedIP.query.filter_by(
            user_id=agent.user_id,
            ip_address=source_ip,
            active=True,
        ).first()

        if not existing_block:
            db.session.add(
                BlockedIP(
                    user_id=agent.user_id,
                    agent_id=agent.id,
                    ip_address=source_ip,
                    reason=event.event_type,
                    notes=event.summary,
                    source="agent",
                    active=True,
                )
            )

    update_pet_from_firewall_event(agent.user.pet, event)
    db.session.commit()
    return event
```

- [ ] **Step 7: Import firewall models in init_db**

Modify `init_db.py`:

```python
    import_module("app.firewall.model")
```

Place it after the existing model imports.

- [ ] **Step 8: Run service tests**

Run:

```bash
uv run pytest tests/test_firewall_service.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add app/auth/model.py app/firewall app/pets/service.py init_db.py tests/test_firewall_service.py
git commit -m "feat: add firewall models and event service"
```

---

## Task 3: Add Blocked IP CRUD

**Files:**
- Create: `app/firewall/routes.py`
- Create: `app/templates/firewall/blocked_ips.html`
- Create: `app/templates/firewall/blocked_ip_form.html`
- Create: `app/templates/firewall/blocked_ip_detail.html`
- Modify: `app/main.py`
- Create: `tests/test_firewall_routes.py`

- [ ] **Step 1: Write route tests**

Create `tests/test_firewall_routes.py`:

```python
from app.core import db
from app.firewall.model import BlockedIP
from tests.conftest import create_user, login


def test_blocked_ip_crud_for_current_user(client, app):
    create_user()
    login(client)

    response = client.post(
        "/blocked-ips",
        data={
            "ip_address": "192.168.56.44",
            "reason": "manual test",
            "notes": "created from pytest",
        },
        follow_redirects=False,
    )

    blocked_ip = BlockedIP.query.filter_by(ip_address="192.168.56.44").first()

    assert response.status_code == 302
    assert blocked_ip is not None
    assert blocked_ip.user.username == "alice"


def test_blocked_ip_idor_is_blocked(client, app):
    user_a = create_user(username="alice")
    blocked_ip = BlockedIP(
        user_id=user_a.id,
        ip_address="192.168.56.55",
        reason="belongs to alice",
        notes="private record",
    )
    db.session.add(blocked_ip)
    db.session.commit()

    create_user(username="bob")
    login(client, username="bob")

    response = client.get(f"/blocked-ips/{blocked_ip.id}")

    assert response.status_code == 404
```

- [ ] **Step 2: Run route tests and confirm failure**

Run:

```bash
uv run pytest tests/test_firewall_routes.py -q
```

Expected: FAIL because blocked IP routes do not exist yet.

- [ ] **Step 3: Create CRUD routes**

Create `app/firewall/routes.py`:

```python
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core import db
from app.firewall.model import BlockedIP
from app.firewall.service import validate_ip


firewall = Blueprint("firewall", __name__)


def get_owned_blocked_ip(blocked_ip_id):
    return BlockedIP.query.filter_by(
        id=blocked_ip_id,
        user_id=current_user.id,
    ).first_or_404()


@firewall.route("/blocked-ips")
@login_required
def blocked_ips():
    records = (
        BlockedIP.query.filter_by(user_id=current_user.id)
        .order_by(BlockedIP.created_at.desc())
        .all()
    )
    return render_template("firewall/blocked_ips.html", blocked_ips=records)


@firewall.route("/blocked-ips/new")
@login_required
def new_blocked_ip():
    return render_template("firewall/blocked_ip_form.html", blocked_ip=None)


@firewall.route("/blocked-ips", methods=["POST"])
@login_required
def create_blocked_ip():
    try:
        ip_address = validate_ip(request.form.get("ip_address", "").strip())
    except ValueError:
        flash("IP invalido")
        return redirect(url_for("firewall.new_blocked_ip"))

    blocked_ip = BlockedIP(
        user_id=current_user.id,
        ip_address=ip_address,
        reason=request.form.get("reason", "").strip() or "manual",
        notes=request.form.get("notes", "").strip(),
        source="manual",
        active=True,
    )
    db.session.add(blocked_ip)
    db.session.commit()
    flash("IP bloqueado cadastrado")
    return redirect(url_for("firewall.blocked_ip_detail", blocked_ip_id=blocked_ip.id))


@firewall.route("/blocked-ips/<int:blocked_ip_id>")
@login_required
def blocked_ip_detail(blocked_ip_id):
    blocked_ip = get_owned_blocked_ip(blocked_ip_id)
    return render_template("firewall/blocked_ip_detail.html", blocked_ip=blocked_ip)


@firewall.route("/blocked-ips/<int:blocked_ip_id>/edit")
@login_required
def edit_blocked_ip(blocked_ip_id):
    blocked_ip = get_owned_blocked_ip(blocked_ip_id)
    return render_template("firewall/blocked_ip_form.html", blocked_ip=blocked_ip)


@firewall.route("/blocked-ips/<int:blocked_ip_id>/edit", methods=["POST"])
@login_required
def update_blocked_ip(blocked_ip_id):
    blocked_ip = get_owned_blocked_ip(blocked_ip_id)

    try:
        blocked_ip.ip_address = validate_ip(request.form.get("ip_address", "").strip())
    except ValueError:
        flash("IP invalido")
        return redirect(url_for("firewall.edit_blocked_ip", blocked_ip_id=blocked_ip.id))

    blocked_ip.reason = request.form.get("reason", "").strip() or "manual"
    blocked_ip.notes = request.form.get("notes", "").strip()
    blocked_ip.active = request.form.get("active") == "on"
    db.session.commit()
    flash("IP bloqueado atualizado")
    return redirect(url_for("firewall.blocked_ip_detail", blocked_ip_id=blocked_ip.id))


@firewall.route("/blocked-ips/<int:blocked_ip_id>/delete", methods=["POST"])
@login_required
def delete_blocked_ip(blocked_ip_id):
    blocked_ip = get_owned_blocked_ip(blocked_ip_id)
    db.session.delete(blocked_ip)
    db.session.commit()
    flash("IP bloqueado removido")
    return redirect(url_for("firewall.blocked_ips"))
```

- [ ] **Step 4: Register blueprint**

Modify `app/firewall/__init__.py`:

```python
from app.firewall.model import Agent, BlockedIP, FirewallEvent
from app.firewall.routes import firewall

__all__ = [
    "Agent",
    "BlockedIP",
    "FirewallEvent",
    "firewall",
]
```

Modify `app/main.py`:

```python
from app.firewall import firewall
```

Register it after the existing blueprints:

```python
app.register_blueprint(firewall)
```

- [ ] **Step 5: Create templates**

Create `app/templates/firewall/blocked_ips.html`:

```html
{% extends "base.html" %}
{% block title %}Blocked IPs - pixel_buddy{% endblock %}
{% block content %}
  <section class="game-panel">
    <h1>blocked ips</h1>
    <p class="muted">IPs registrados pelo agente ou manualmente.</p>
    <p><a class="button-link" href="/blocked-ips/new">Novo bloqueio</a></p>
    <table>
      <thead>
        <tr>
          <th>IP</th>
          <th>Motivo</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for blocked_ip in blocked_ips %}
          <tr>
            <td>{{ blocked_ip.ip_address }}</td>
            <td>{{ blocked_ip.reason }}</td>
            <td>{{ "ativo" if blocked_ip.active else "inativo" }}</td>
            <td><a href="/blocked-ips/{{ blocked_ip.id }}">Ver</a></td>
          </tr>
        {% else %}
          <tr><td colspan="4">Nenhum IP bloqueado.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
{% endblock %}
```

Create `app/templates/firewall/blocked_ip_form.html`:

```html
{% extends "base.html" %}
{% block title %}Blocked IP - pixel_buddy{% endblock %}
{% block content %}
  <section class="auth-panel">
    <h1>{{ "editar" if blocked_ip else "novo" }} bloqueio</h1>
    <form method="post" action="{{ '/blocked-ips/' ~ blocked_ip.id ~ '/edit' if blocked_ip else '/blocked-ips' }}">
      <label>
        IP
        <input name="ip_address" value="{{ blocked_ip.ip_address if blocked_ip else '' }}" required>
      </label>
      <label>
        Motivo
        <input name="reason" value="{{ blocked_ip.reason if blocked_ip else '' }}" required>
      </label>
      <label>
        Observacoes
        <input name="notes" value="{{ blocked_ip.notes if blocked_ip else '' }}">
      </label>
      {% if blocked_ip %}
        <label>
          Ativo
          <input type="checkbox" name="active" {% if blocked_ip.active %}checked{% endif %}>
        </label>
      {% endif %}
      <button type="submit">Salvar</button>
    </form>
  </section>
{% endblock %}
```

Create `app/templates/firewall/blocked_ip_detail.html`:

```html
{% extends "base.html" %}
{% block title %}{{ blocked_ip.ip_address }} - pixel_buddy{% endblock %}
{% block content %}
  <section class="game-panel">
    <h1>{{ blocked_ip.ip_address }}</h1>
    <p>Motivo: {{ blocked_ip.reason }}</p>
    <p>Origem: {{ blocked_ip.source }}</p>
    <p>Status: {{ "ativo" if blocked_ip.active else "inativo" }}</p>
    <p>{{ blocked_ip.notes }}</p>
    <p><a class="button-link" href="/blocked-ips/{{ blocked_ip.id }}/edit">Editar</a></p>
    <form method="post" action="/blocked-ips/{{ blocked_ip.id }}/delete">
      <button type="submit">Remover</button>
    </form>
  </section>
{% endblock %}
```

- [ ] **Step 6: Add table styles**

Modify `app/templates/base.html` inside the `<style>` block:

```css
      table {
        border-collapse: collapse;
        width: 100%;
      }

      th,
      td {
        border: 3px solid #000;
        padding: 10px;
        text-align: left;
      }

      th {
        background: #000;
        color: #fff;
        text-transform: uppercase;
      }
```

- [ ] **Step 7: Run route tests**

Run:

```bash
uv run pytest tests/test_firewall_routes.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/firewall/routes.py app/main.py app/templates/base.html app/templates/firewall tests/test_firewall_routes.py
git commit -m "feat: add blocked ip crud"
```

---

## Task 4: Add Agent UI And Event API

**Files:**
- Create: `app/firewall/api.py`
- Modify: `app/firewall/routes.py`
- Create: `app/templates/firewall/agents.html`
- Create: `tests/test_agent_api.py`

- [ ] **Step 1: Write API tests**

Create `tests/test_agent_api.py`:

```python
from app.firewall.model import BlockedIP, FirewallEvent
from app.firewall.service import create_agent_for_user
from tests.conftest import create_user


def test_agent_event_api_requires_token(client, app):
    response = client.post("/api/agent/events", json={})

    assert response.status_code == 401


def test_agent_event_api_records_blocked_event(client, app):
    user = create_user()
    _agent, token = create_agent_for_user(user, name="lab-vm", mode="dry-run")

    response = client.post(
        "/api/agent/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "possible_dos",
            "source_ip": "192.168.56.77",
            "destination_port": 5000,
            "packet_count": 150,
            "action": "blocked",
            "summary": "threshold exceeded",
        },
    )

    assert response.status_code == 201
    assert FirewallEvent.query.count() == 1
    assert BlockedIP.query.filter_by(ip_address="192.168.56.77").first() is not None
```

- [ ] **Step 2: Run API tests and confirm failure**

Run:

```bash
uv run pytest tests/test_agent_api.py -q
```

Expected: FAIL because `/api/agent/events` does not exist yet.

- [ ] **Step 3: Create API blueprint**

Create `app/firewall/api.py`:

```python
from flask import Blueprint, jsonify, request

from app.firewall.service import authenticate_agent_token, record_firewall_event


agent_api = Blueprint("agent_api", __name__, url_prefix="/api/agent")


def get_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.removeprefix("Bearer ").strip()


@agent_api.route("/events", methods=["POST"])
def create_agent_event():
    agent = authenticate_agent_token(get_bearer_token())
    if not agent:
        return jsonify({"error": "invalid_agent_token"}), 401

    payload = request.get_json(silent=True) or {}
    required_fields = ["event_type", "source_ip", "packet_count", "action"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    event = record_firewall_event(agent, payload)
    return jsonify({"id": event.id, "status": "recorded"}), 201
```

- [ ] **Step 4: Register API blueprint**

Modify `app/firewall/__init__.py`:

```python
from app.firewall.api import agent_api
from app.firewall.model import Agent, BlockedIP, FirewallEvent
from app.firewall.routes import firewall

__all__ = [
    "Agent",
    "BlockedIP",
    "FirewallEvent",
    "agent_api",
    "firewall",
]
```

Modify `app/main.py`:

```python
from app.firewall import agent_api, firewall
```

Register both:

```python
app.register_blueprint(firewall)
app.register_blueprint(agent_api)
```

- [ ] **Step 5: Add agent management routes**

Append to `app/firewall/routes.py`:

```python
from app.firewall.model import Agent
from app.firewall.service import create_agent_for_user


@firewall.route("/agents")
@login_required
def agents():
    records = (
        Agent.query.filter_by(user_id=current_user.id)
        .order_by(Agent.created_at.desc())
        .all()
    )
    return render_template("firewall/agents.html", agents=records, created_token=None)


@firewall.route("/agents", methods=["POST"])
@login_required
def create_agent():
    name = request.form.get("name", "").strip()
    mode = request.form.get("mode", "dry-run")

    if not name:
        flash("Nome do agente obrigatorio")
        return redirect(url_for("firewall.agents"))

    if mode not in {"dry-run", "ufw"}:
        flash("Modo invalido")
        return redirect(url_for("firewall.agents"))

    _agent, token = create_agent_for_user(current_user, name=name, mode=mode)
    records = (
        Agent.query.filter_by(user_id=current_user.id)
        .order_by(Agent.created_at.desc())
        .all()
    )
    return render_template("firewall/agents.html", agents=records, created_token=token)
```

- [ ] **Step 6: Create agents template**

Create `app/templates/firewall/agents.html`:

```html
{% extends "base.html" %}
{% block title %}Agents - pixel_buddy{% endblock %}
{% block content %}
  <section class="game-panel">
    <h1>agents</h1>
    {% if created_token %}
      <div class="flash-list">
        <li>Novo token: <strong>{{ created_token }}</strong></li>
      </div>
    {% endif %}
    <form method="post" action="/agents">
      <label>
        Nome
        <input name="name" required>
      </label>
      <label>
        Modo
        <select name="mode">
          <option value="dry-run">dry-run</option>
          <option value="ufw">ufw</option>
        </select>
      </label>
      <button type="submit">Criar agente</button>
    </form>
    <table>
      <thead>
        <tr>
          <th>Nome</th>
          <th>Modo</th>
          <th>Ultimo contato</th>
        </tr>
      </thead>
      <tbody>
        {% for agent in agents %}
          <tr>
            <td>{{ agent.name }}</td>
            <td>{{ agent.mode }}</td>
            <td>{{ agent.last_seen_at or "-" }}</td>
          </tr>
        {% else %}
          <tr><td colspan="3">Nenhum agente cadastrado.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
{% endblock %}
```

- [ ] **Step 7: Add select styles**

Modify `app/templates/base.html`:

```css
      select {
        width: 100%;
        background: #fff;
        border: 3px solid #000;
        border-radius: 0;
        color: #000;
        font: inherit;
        padding: 10px 12px;
      }
```

- [ ] **Step 8: Run API tests**

Run:

```bash
uv run pytest tests/test_agent_api.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add app/firewall/api.py app/firewall/routes.py app/main.py app/templates/base.html app/templates/firewall/agents.html tests/test_agent_api.py
git commit -m "feat: add agent event api"
```

---

## Task 5: Update Game UI, Pet Reactions, Faces, And Leaderboard

**Files:**
- Modify: `app/display/faces.py`
- Modify: `app/display/renderer.py`
- Modify: `app/templates/game.html`
- Modify: `app/templates/base.html`
- Modify: `app/main.py`
- Create: `app/templates/leaderboard.html`

- [ ] **Step 1: Add mood faces**

Modify `app/display/faces.py`:

```python
FACES = {
    "neutral": "(•‿•)",
    "happy": "(^‿^)",
    "curious": "(◕‿◕)",
    "tired": "(⇀‿↼)",
    "hungry": "(•︿•)",
    "confused": "(#__#)",
    "cool": "(⌐■_■)",
    "alert": "(⊙_⊙)",
    "angry": "(ಠ_ಠ)",
}
```

- [ ] **Step 2: Render firewall labels**

Modify the bottom labels in `app/display/renderer.py`:

```python
    draw.text((12, 146), f"ENG {pet.energy}", font=medium_font, fill=BLACK)
    draw.text((88, 146), f"XP {pet.network_xp}", font=medium_font, fill=BLACK)
    draw.text((156, 146), f"CUR {pet.curiosity}", font=medium_font, fill=BLACK)
    draw.text((240, 146), f"MOOD {pet.mood[:5].upper()}", font=medium_font, fill=BLACK)
```

- [ ] **Step 3: Replace generic game buttons**

Modify `app/templates/game.html` so the action area becomes:

```html
    <div class="game-actions">
      <a class="button-link" href="/agents">Agents</a>
      <a class="button-link" href="/blocked-ips">Blocklist</a>
      <a class="button-link" href="/leaderboard">Ranking</a>
    </div>
```

Keep the existing `refreshScreen()` interval.

- [ ] **Step 4: Add leaderboard route**

Modify `app/main.py` imports:

```python
from app.auth import User
```

Add route:

```python
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
```

- [ ] **Step 5: Create leaderboard template**

Create `app/templates/leaderboard.html`:

```html
{% extends "base.html" %}
{% block title %}Leaderboard - pixel_buddy{% endblock %}
{% block content %}
  <section class="game-panel">
    <h1>leaderboard</h1>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>User</th>
          <th>Buddy</th>
          <th>XP</th>
        </tr>
      </thead>
      <tbody>
        {% for user in users %}
          <tr>
            <td>{{ loop.index }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.pet.name }}</td>
            <td>{{ user.pet.network_xp }}</td>
          </tr>
        {% else %}
          <tr><td colspan="4">Nenhum buddy ranqueado.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
{% endblock %}
```

- [ ] **Step 6: Add header navigation**

Modify authenticated block in `app/templates/base.html`:

```html
          <div class="site-user">
            <a href="/game">Game</a>
            <a href="/agents">Agents</a>
            <a href="/blocked-ips">Blocklist</a>
            <a href="/leaderboard">Ranking</a>
            <span>Logado como {{ current_user.username }}</span>
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
uv run pytest tests/test_firewall_service.py tests/test_firewall_routes.py tests/test_agent_api.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/display/faces.py app/display/renderer.py app/main.py app/templates/base.html app/templates/game.html app/templates/leaderboard.html
git commit -m "feat: show firewall buddy dashboard"
```

---

## Task 6: Add Terminal Agent Detector And UFW Helper

**Files:**
- Create: `agent/packet_window.py`
- Create: `agent/ufw.py`
- Create: `agent/pixel_buddy_agent.py`
- Create: `agent/README.md`
- Create: `tests/test_agent_packet_window.py`

- [ ] **Step 1: Write detector tests**

Create `tests/test_agent_packet_window.py`:

```python
from agent.packet_window import PacketWindow


def test_packet_window_detects_threshold_for_source_ip():
    window = PacketWindow(threshold=3, window_seconds=5)

    assert window.observe("192.168.56.10", 5000, now=100.0) is None
    assert window.observe("192.168.56.10", 5000, now=101.0) is None
    event = window.observe("192.168.56.10", 5000, now=102.0)

    assert event == {
        "event_type": "possible_dos",
        "source_ip": "192.168.56.10",
        "destination_port": 5000,
        "packet_count": 3,
        "action": "reported",
        "summary": "3 packets from 192.168.56.10 in 5s",
    }


def test_packet_window_expires_old_packets():
    window = PacketWindow(threshold=2, window_seconds=5)

    assert window.observe("192.168.56.10", 5000, now=100.0) is None
    assert window.observe("192.168.56.10", 5000, now=110.0) is None
```

- [ ] **Step 2: Run detector tests and confirm failure**

Run:

```bash
uv run pytest tests/test_agent_packet_window.py -q
```

Expected: FAIL because `agent.packet_window` does not exist yet.

- [ ] **Step 3: Create packet window detector**

Create `agent/packet_window.py`:

```python
from collections import defaultdict, deque


class PacketWindow:
    def __init__(self, threshold=50, window_seconds=5):
        self.threshold = threshold
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)

    def observe(self, source_ip, destination_port, now):
        key = (source_ip, destination_port)
        events = self._events[key]
        events.append(now)

        while events and now - events[0] > self.window_seconds:
            events.popleft()

        if len(events) < self.threshold:
            return None

        events.clear()
        return {
            "event_type": "possible_dos",
            "source_ip": source_ip,
            "destination_port": destination_port,
            "packet_count": self.threshold,
            "action": "reported",
            "summary": (
                f"{self.threshold} packets from {source_ip} "
                f"in {self.window_seconds}s"
            ),
        }
```

- [ ] **Step 4: Create UFW helper**

Create `agent/ufw.py`:

```python
import subprocess
from ipaddress import ip_address


def normalize_ip(value):
    return str(ip_address(value))


def block_ip(source_ip, mode):
    normalized_ip = normalize_ip(source_ip)

    if mode == "dry-run":
        return "reported"

    if mode != "ufw":
        raise ValueError(f"unsupported mode: {mode}")

    subprocess.run(
        ["ufw", "deny", "from", normalized_ip],
        check=True,
        capture_output=True,
        text=True,
    )
    return "blocked"
```

- [ ] **Step 5: Create terminal agent**

Create `agent/pixel_buddy_agent.py`:

```python
import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scapy.all import IP, TCP, sniff

from agent.packet_window import PacketWindow
from agent.ufw import block_ip


FACES = {
    "neutral": "(•‿•)",
    "alert": "(⊙_⊙)",
    "angry": "(ಠ_ಠ)",
}


def render_terminal(status, event=None):
    face = FACES.get(status, FACES["neutral"])
    print("\033c", end="")
    print("pixel_buddy agent")
    print()
    print(f"  {face}")
    print()
    print(f"status: {status.upper()}")
    if event:
        print(f"event: {event['event_type']}")
        print(f"source: {event['source_ip']}")
        print(f"packets: {event['packet_count']}")
        print(f"action: {event['action']}")


def post_event(server, token, event):
    body = json.dumps(event).encode("utf-8")
    request = Request(
        f"{server.rstrip('/')}/api/agent/events",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return response.status


def build_packet_handler(args, packet_window):
    def handle_packet(packet):
        if IP not in packet:
            return

        source_ip = packet[IP].src
        destination_port = packet[TCP].dport if TCP in packet else 0
        event = packet_window.observe(source_ip, destination_port, time.time())
        if not event:
            return

        try:
            event["action"] = block_ip(source_ip, args.mode)
        except Exception as exc:
            event["action"] = "block_failed"
            event["summary"] = f"{event['summary']} | block failed: {exc}"

        render_terminal("angry" if event["action"] == "blocked" else "alert", event)

        try:
            post_event(args.server, args.token, event)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"report failed: {exc}")

    return handle_packet


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--mode", choices=["dry-run", "ufw"], default="dry-run")
    parser.add_argument("--threshold", type=int, default=50)
    parser.add_argument("--window", type=int, default=5)
    return parser.parse_args()


def main():
    args = parse_args()
    render_terminal("neutral")
    packet_window = PacketWindow(
        threshold=args.threshold,
        window_seconds=args.window,
    )
    sniff(
        iface=args.interface,
        prn=build_packet_handler(args, packet_window),
        store=False,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Create agent README**

Create `agent/README.md`:

```markdown
# pixel_buddy agent

The agent runs on a protected Ubuntu/Debian lab machine. It watches packets with
Scapy, renders the buddy in the terminal, and reports firewall events to the
Flask app.

Development mode:

```bash
uv run python agent/pixel_buddy_agent.py \
  --server http://127.0.0.1:5000 \
  --token TOKEN_FROM_WEB_UI \
  --interface eth0 \
  --mode dry-run \
  --threshold 20 \
  --window 5
```

Demo mode with UFW:

```bash
sudo uv run python agent/pixel_buddy_agent.py \
  --server http://FLASK_HOST:5000 \
  --token TOKEN_FROM_WEB_UI \
  --interface eth0 \
  --mode ufw \
  --threshold 20 \
  --window 5
```

Use `dry-run` for normal development. Use `ufw` only inside a controlled lab VM.
```

- [ ] **Step 7: Run agent tests**

Run:

```bash
uv run pytest tests/test_agent_packet_window.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add agent tests/test_agent_packet_window.py
git commit -m "feat: add terminal firewall agent"
```

---

## Task 7: Add IDOR Demo Documentation

**Files:**
- Create: `docs/IDOR_DEMO.md`

- [ ] **Step 1: Create demonstration guide**

Create `docs/IDOR_DEMO.md`:

```markdown
# IDOR Demonstration

The vulnerable pattern is a blocked IP lookup that trusts only the URL ID:

```python
blocked_ip = BlockedIP.query.get_or_404(blocked_ip_id)
```

This allows user B to access user A's blocked IP record by manually changing the
URL to `/blocked-ips/<id_from_user_a>`.

The fixed pattern includes ownership:

```python
blocked_ip = BlockedIP.query.filter_by(
    id=blocked_ip_id,
    user_id=current_user.id,
).first_or_404()
```

Presentation flow:

1. Create user A.
2. Create a blocked IP as user A.
3. Note the blocked IP ID.
4. Log out.
5. Create user B.
6. Try to access `/blocked-ips/<id_from_user_a>` as user B.
7. Show the vulnerable version allows access.
8. Apply the fixed query.
9. Repeat the request and show Flask returns 404.

Final code must keep the ownership-filtered query.
```

- [ ] **Step 2: Commit**

```bash
git add docs/IDOR_DEMO.md
git commit -m "docs: add idor demo guide"
```

---

## Task 8: Final Verification

**Files:**
- Verify: full repository state

- [ ] **Step 1: Initialize database**

Run:

```bash
uv run python init_db.py
```

Expected: output includes `agents`, `blocked_ips`, and `firewall_events`.

- [ ] **Step 2: Run tests**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run Flask locally**

Run:

```bash
uv run flask --app app.main run
```

Expected: Flask starts on `http://127.0.0.1:5000`.

- [ ] **Step 4: Manual browser smoke test**

Check:

- Register user.
- Create buddy.
- Open `/agents`.
- Create dry-run agent token.
- Open `/blocked-ips`.
- Create blocked IP manually.
- Open `/leaderboard`.
- Confirm `/game/screen.png` still renders.

- [ ] **Step 5: API smoke test**

Run with a real token from `/agents`:

```bash
curl -X POST http://127.0.0.1:5000/api/agent/events \
  -H "Authorization: Bearer TOKEN_FROM_WEB_UI" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"possible_dos","source_ip":"192.168.56.99","destination_port":5000,"packet_count":120,"action":"blocked","summary":"manual smoke test"}'
```

Expected: JSON response contains `"status":"recorded"`.

- [ ] **Step 6: Commit remaining verified changes**

```bash
git status --short
git add .
git commit -m "chore: verify firewall agent mvp"
```

Skip this commit if `git status --short` is clean.

---

## Self-Review

- Spec coverage: product direction, agent, Scapy monitoring, UFW mode, blocked IP CRUD, IDOR, leaderboard, and terminal rendering are covered by tasks.
- Unresolved marker scan: no task uses incomplete implementation markers. `TOKEN_FROM_WEB_UI` and `FLASK_HOST` are explicit runtime values for manual demo commands.
- Type consistency: `Agent`, `FirewallEvent`, `BlockedIP`, `create_agent_for_user`, `authenticate_agent_token`, and `record_firewall_event` are named consistently across model, service, tests, routes, and agent API.
