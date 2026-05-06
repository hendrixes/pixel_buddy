from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core import db, validate_csrf
from app.firewall.model import Agent, BlockedIP
from app.firewall.service import create_agent_for_user, validate_ip


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
    validate_csrf()

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
    validate_csrf()
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
    validate_csrf()
    blocked_ip = get_owned_blocked_ip(blocked_ip_id)
    db.session.delete(blocked_ip)
    db.session.commit()
    flash("IP bloqueado removido")
    return redirect(url_for("firewall.blocked_ips"))


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
    validate_csrf()
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
