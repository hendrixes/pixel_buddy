import time
from ipaddress import ip_address

from scapy.all import IP, TCP

from agent.packet_window import PacketWindow


class PacketAnalyzer:
    def __init__(self, protected_ip, threshold=50, window_seconds=5):
        self.protected_ip = str(ip_address(protected_ip))
        self.packet_window = PacketWindow(
            threshold=threshold,
            window_seconds=window_seconds,
        )

    def observe_packet(self, packet):
        if IP not in packet or TCP not in packet:
            return None

        if packet[IP].dst != self.protected_ip:
            return None

        packet_time = float(getattr(packet, "time", time.time()))
        return self.packet_window.observe(
            source_ip=packet[IP].src,
            destination_port=packet[TCP].dport,
            now=packet_time,
        )
