from scapy.all import IP, TCP, PcapNgWriter, wrpcap

from app.firewall.pcap import analyze_pcap_file


def test_pcap_analyzer_detects_repeated_packets_without_protected_ip(tmp_path):
    path = tmp_path / "traffic.pcap"
    packets = [
        IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000),
        IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000),
        IP(src="192.168.56.10", dst="192.168.56.99") / TCP(dport=5000),
    ]
    wrpcap(str(path), packets)

    events = analyze_pcap_file(path, threshold=2, window_seconds=5)

    assert len(events) == 1
    assert events[0]["source_ip"] == "192.168.56.10"
    assert events[0]["destination_port"] == 5000
    assert "192.168.56.20" in events[0]["summary"]


def test_pcap_analyzer_supports_pcapng_files(tmp_path):
    path = tmp_path / "traffic.pcapng"
    writer = PcapNgWriter(str(path))
    writer.write(IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000))
    writer.write(IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000))
    writer.close()

    events = analyze_pcap_file(path, threshold=2, window_seconds=5)

    assert len(events) == 1
    assert events[0]["source_ip"] == "192.168.56.10"


def test_pcap_analyzer_uses_packets_before_truncated_pcapng_block(tmp_path):
    complete_path = tmp_path / "complete.pcapng"
    truncated_path = tmp_path / "truncated.pcapng"
    writer = PcapNgWriter(str(complete_path))
    writer.write(IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000))
    writer.write(IP(src="192.168.56.10", dst="192.168.56.20") / TCP(dport=5000))
    writer.close()
    data = complete_path.read_bytes()
    truncated_path.write_bytes(data[:-8])

    events = analyze_pcap_file(truncated_path, threshold=1, window_seconds=5)

    assert len(events) == 1
    assert events[0]["source_ip"] == "192.168.56.10"
