from io import BytesIO
import logging

from scapy.all import IP, TCP, wrpcap

from app.core.csrf import CSRF_SESSION_KEY
from app.firewall.model import FirewallEvent
from tests.conftest import create_user, login


def csrf_form(client, **data):
    token = "known-test-csrf-token"
    with client.session_transaction() as session:
        session[CSRF_SESSION_KEY] = token

    return {**data, "csrf_token": token}


def pcap_bytes(tmp_path):
    path = tmp_path / "traffic.pcap"
    packets = [
        IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000),
        IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000),
        IP(src="192.168.56.11", dst="192.168.56.99") / TCP(dport=5000),
    ]
    wrpcap(str(path), packets)
    return path.read_bytes()


def test_pcap_upload_requires_login(client):
    response = client.get("/pcaps/upload")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_pcap_upload_records_firewall_events(client, app, tmp_path):
    user = create_user()
    login(client)

    response = client.post(
        "/pcaps/upload",
        data=csrf_form(
            client,
            threshold="2",
            window="5",
            pcap_file=(BytesIO(pcap_bytes(tmp_path)), "traffic.pcap"),
        ),
        content_type="multipart/form-data",
    )

    event = FirewallEvent.query.one()

    assert response.status_code == 200
    assert b"possible_dos" in response.data
    assert event.user_id == user.id
    assert event.agent_id is None
    assert event.source == "pcap_upload"
    assert event.source_ip == "192.168.56.10"
    assert event.destination_port == 5000
    assert user.pet.mood == "alert"
    assert user.pet.network_xp > 0


def test_pcap_upload_without_csrf_is_rejected(client, app, tmp_path):
    create_user()
    login(client)

    response = client.post(
        "/pcaps/upload",
        data={
            "threshold": "2",
            "window": "5",
            "pcap_file": (BytesIO(pcap_bytes(tmp_path)), "traffic.pcap"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert FirewallEvent.query.count() == 0


def test_invalid_pcap_upload_is_logged(client, app, caplog):
    create_user()
    login(client)
    caplog.set_level(logging.ERROR)

    response = client.post(
        "/pcaps/upload",
        data=csrf_form(
            client,
            threshold="2",
            window="5",
            pcap_file=(BytesIO(b"not a pcap"), "traffic.pcap"),
        ),
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert "PCAP upload analysis failed" in caplog.text
    assert FirewallEvent.query.count() == 0


def test_pcap_upload_form_does_not_ask_for_protected_ip(client, app):
    create_user()
    login(client)

    response = client.get("/pcaps/upload")

    assert response.status_code == 200
    assert b'name="protected_ip"' not in response.data
