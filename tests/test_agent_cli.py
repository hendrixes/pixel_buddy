from argparse import Namespace

import pytest
from scapy.all import IP, TCP

from agent import pixel_buddy_agent


class SpyWindow:
    def __init__(self):
        self.observed = []

    def observe(self, source_ip, destination_port, now):
        self.observed.append((source_ip, destination_port))
        return None


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
    args = Namespace(mode="dry-run", protected_ip="192.168.56.20")
    window = SpyWindow()
    handler = pixel_buddy_agent.build_packet_handler(args, window)

    handler(IP(src="192.168.56.20", dst="1.1.1.1") / TCP(dport=5000))

    assert window.observed == []


def test_build_packet_handler_ignores_non_tcp_packet():
    args = Namespace(mode="dry-run", protected_ip="192.168.56.20")
    window = SpyWindow()
    handler = pixel_buddy_agent.build_packet_handler(args, window)

    handler(IP(src="1.1.1.1", dst="192.168.56.20"))

    assert window.observed == []
