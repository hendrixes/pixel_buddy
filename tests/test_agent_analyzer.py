from scapy.all import IP, TCP

from agent.analyzer import PacketAnalyzer


def test_packet_analyzer_detects_threshold_for_protected_ip():
    analyzer = PacketAnalyzer(
        protected_ip="192.168.56.20",
        threshold=2,
        window_seconds=5,
    )

    packet = IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000)

    assert analyzer.observe_packet(packet) is None
    event = analyzer.observe_packet(packet)

    assert event["event_type"] == "possible_dos"
    assert event["source_ip"] == "192.168.56.10"
    assert event["destination_port"] == 5000
    assert event["packet_count"] == 2


def test_packet_analyzer_ignores_packets_for_other_destinations():
    analyzer = PacketAnalyzer(
        protected_ip="192.168.56.20",
        threshold=1,
        window_seconds=5,
    )

    packet = IP(src="192.168.56.10", dst="192.168.56.99") / TCP(dport=5000)

    assert analyzer.observe_packet(packet) is None


def test_packet_analyzer_ignores_ssh_by_default():
    analyzer = PacketAnalyzer(
        protected_ip="192.168.56.20",
        threshold=1,
        window_seconds=5,
    )

    packet = IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=22)

    assert analyzer.observe_packet(packet) is None
