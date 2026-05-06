from collections import defaultdict, deque


class PacketWindow:
    def __init__(self, threshold=50, window_seconds=5):
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self.threshold = threshold
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)

    def observe(self, source_ip, destination_port, now):
        key = (source_ip, destination_port)
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
                f"{self.threshold} packets from {source_ip} "
                f"in {self.window_seconds}s"
            ),
        }
