import pytest
from scapy.all import IP, TCP

from agent.config import AgentConfig
from agent import pixel_buddy_agent


def test_parse_args_rejects_non_positive_threshold(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "pixel_buddy_agent",
            "--server",
            "http://127.0.0.1:5000",
            "--token",
            "token",
            "--interface",
            "eth0",
            "--protected-ip",
            "192.168.56.20",
            "--threshold",
            "0",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        pixel_buddy_agent.parse_args()

    assert exc_info.value.code == 2
    assert "must be a positive integer" in capsys.readouterr().err


def test_parse_args_allows_tui_without_required_flags(monkeypatch):
    monkeypatch.setattr("sys.argv", ["pixel_buddy_agent"])

    args = pixel_buddy_agent.parse_args()

    assert args.server is None
    assert args.token is None
    assert args.interface is None
    assert args.protected_ip is None


def test_parse_args_rejects_non_positive_window(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "pixel_buddy_agent",
            "--server",
            "http://127.0.0.1:5000",
            "--token",
            "token",
            "--interface",
            "eth0",
            "--protected-ip",
            "192.168.56.20",
            "--window",
            "0",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        pixel_buddy_agent.parse_args()

    assert exc_info.value.code == 2
    assert "must be a positive integer" in capsys.readouterr().err


def test_build_packet_handler_ignores_outbound_packet():
    handled = []
    config = AgentConfig(
        server="http://127.0.0.1:5000",
        token="token",
        interface="eth0",
        protected_ip="192.168.56.20",
        mode="dry-run",
        threshold=1,
        window=5,
    )
    handler = pixel_buddy_agent.build_packet_handler(
        config,
        event_handler=lambda _config, event: handled.append(event),
    )

    handler(IP(src="192.168.56.20", dst="1.1.1.1") / TCP(dport=5000))

    assert handled == []


def test_build_packet_handler_ignores_non_tcp_packet():
    handled = []
    config = AgentConfig(
        server="http://127.0.0.1:5000",
        token="token",
        interface="eth0",
        protected_ip="192.168.56.20",
        mode="dry-run",
        threshold=1,
        window=5,
    )
    handler = pixel_buddy_agent.build_packet_handler(
        config,
        event_handler=lambda _config, event: handled.append(event),
    )

    handler(IP(src="1.1.1.1", dst="192.168.56.20"))

    assert handled == []
