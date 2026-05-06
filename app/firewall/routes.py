from pathlib import Path
from tempfile import TemporaryDirectory

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.core import db, validate_csrf
from app.firewall.model import Agent, BlockedIP
from app.firewall.pcap import analyze_pcap_file
from app.firewall.service import (
    create_agent_for_user,
    record_firewall_event_for_user,
    validate_ip,
)


firewall = Blueprint("firewall", __name__)
ALLOWED_PCAP_EXTENSIONS = {".pcap", ".pcapng", ".cap"}
MAX_PCAP_THRESHOLD = 10000
MAX_PCAP_WINDOW_SECONDS = 3600


def get_owned_blocked_ip(blocked_ip_id):

    # codigo vulneravel para demonstracao
    # Correcao: filtrar tambem por user_id=current_user.id
    # return BlockedIP.query.filter_by(
    #     id=blocked_ip_id,
    #     user_id=current_user.id,
    # ).first_or_404()

    return BlockedIP.query.filter_by(id=blocked_ip_id).first_or_404()


def parse_positive_form_int(name, default, max_value=None):
    raw_value = request.form.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        raise ValueError(f"{name} precisa ser inteiro") from None

    if value <= 0:
        raise ValueError(f"{name} precisa ser positivo")

    if max_value is not None and value > max_value:
        raise ValueError(f"{name} precisa ser no maximo {max_value}")

    return value


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
        blocked_ip.ip_address = validate_ip(
            request.form.get("ip_address", "").strip())
    except ValueError:
        flash("IP invalido")
        return redirect(
            url_for("firewall.edit_blocked_ip", blocked_ip_id=blocked_ip.id)
        )

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


@firewall.route("/pcaps/upload")
@login_required
def upload_pcap_form():
    return render_template("firewall/pcap_upload.html", events=None)


@firewall.route("/pcaps/upload", methods=["POST"])
@login_required
def upload_pcap():
    validate_csrf()

    uploaded_file = request.files.get("pcap_file")
    if not uploaded_file or not uploaded_file.filename:
        flash("Arquivo PCAP obrigatorio")
        return redirect(url_for("firewall.upload_pcap_form"))

    filename = secure_filename(uploaded_file.filename)
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_PCAP_EXTENSIONS:
        flash("Formato de arquivo invalido")
        return redirect(url_for("firewall.upload_pcap_form"))

    try:
        threshold = parse_positive_form_int(
            "threshold",
            50,
            max_value=MAX_PCAP_THRESHOLD,
        )
        window = parse_positive_form_int(
            "window",
            5,
            max_value=MAX_PCAP_WINDOW_SECONDS,
        )
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("firewall.upload_pcap_form"))

    with TemporaryDirectory() as tmpdir:
        pcap_path = Path(tmpdir) / filename
        uploaded_file.save(pcap_path)

        try:
            detected_events = analyze_pcap_file(
                pcap_path,
                threshold=threshold,
                window_seconds=window,
            )
        except Exception:
            current_app.logger.exception("PCAP upload analysis failed")
            flash("Nao foi possivel analisar o PCAP")
            return redirect(url_for("firewall.upload_pcap_form"))

    recorded_events = [
        record_firewall_event_for_user(
            current_user,
            event,
            source="pcap_upload",
        )
        for event in detected_events
    ]

    return render_template("firewall/pcap_upload.html", events=recorded_events)
