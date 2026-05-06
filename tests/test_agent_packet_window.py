import pytest

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


def test_packet_window_rejects_non_positive_threshold():
    with pytest.raises(ValueError, match="threshold must be positive"):
        PacketWindow(threshold=0, window_seconds=5)


def test_packet_window_rejects_non_positive_window():
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        PacketWindow(threshold=2, window_seconds=0)
