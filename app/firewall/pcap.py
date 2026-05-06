from collections import defaultdict, deque
import logging
from pathlib import Path

from scapy.all import IP, TCP, PcapReader
from scapy.error import Scapy_Exception


logger = logging.getLogger(__name__)


class PcapPacketWindow:
    def __init__(self, threshold=50, window_seconds=5):
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self.threshold = threshold
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)

    def observe(self, source_ip, destination_ip, destination_port, now):
        key = (source_ip, destination_ip, destination_port)
        events = self._events[key]
        events.append(now)

        while events and now - events[0] > self.window_seconds:
            events.popleft()

        if len(events) < self.threshold:
            return None

        events.clear()
        return {
            "event_type": "possible_dos",
            "source_ip": source_ip,
            "destination_port": destination_port,
            "packet_count": self.threshold,
            "action": "reported",
            "summary": (
                f"{self.threshold} packets from {source_ip} to {destination_ip} "
                f"in {self.window_seconds}s"
            ),
        }


def analyze_pcap_file(path, threshold=50, window_seconds=5):
    window = PcapPacketWindow(
        threshold=threshold,
        window_seconds=window_seconds,
    )
    events = []

    packets_read = 0
    reader = PcapReader(str(Path(path)))
    try:
        while True:
            try:
                packet = reader.read_packet()
            except EOFError:
                break
            except Scapy_Exception:
                if packets_read == 0:
                    raise

                logger.warning(
                    "PCAP parsing stopped after %s packets because a later "
                    "block could not be decoded",
                    packets_read,
                    exc_info=True,
                )
                break

            if packet is None:
                break

            packets_read += 1
            if IP not in packet or TCP not in packet:
                continue

            event = window.observe(
                source_ip=packet[IP].src,
                destination_ip=packet[IP].dst,
                destination_port=packet[TCP].dport,
                now=float(packet.time),
            )
            if event:
                events.append(event)
    finally:
        reader.close()

    return events
