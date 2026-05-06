from flask import Blueprint, jsonify, request

from app.core import db
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

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": "invalid_payload",
                    "message": "JSON body must be an object",
                }
            ),
            400,
        )

    required_fields = ["event_type", "source_ip", "packet_count", "action"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        db.session.rollback()
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    try:
        event = record_firewall_event(agent, payload)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": "invalid_payload", "message": str(exc)}), 400

    return jsonify({"id": event.id, "status": "recorded"}), 201
