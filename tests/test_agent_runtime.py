from agent.config import AgentConfig
from agent.runtime import build_packet_handler, handle_event, sync_blocklist


class SpyAnalyzer:
    def __init__(self, event):
        self.event = event
        self.packets = []

    def observe_packet(self, packet):
        self.packets.append(packet)
        return self.event


def test_handle_event_reports_dry_run_event():
    reported = []
    rendered = []
    event = {
        "event_type": "possible_dos",
        "source_ip": "192.168.56.10",
        "destination_port": 5000,
        "packet_count": 20,
        "action": "reported",
        "summary": "20 packets from 192.168.56.10 in 5s",
    }

    handled = handle_event(
        config=AgentConfig(
            server="http://127.0.0.1:5000",
            token="token",
            interface="eth0",
            protected_ip="192.168.56.20",
            mode="dry-run",
        ),
        event=event,
        reporter=lambda _server, _token, payload: reported.append(payload) or 201,
        renderer=lambda status, payload: rendered.append((status, payload)),
    )

    assert handled["action"] == "reported"
    assert reported == [handled]
    assert rendered[0][0] == "alert"


def test_handle_event_never_blocks_ignored_ports():
    reported = []
    blocked = []
    event = {
        "event_type": "possible_dos",
        "source_ip": "192.168.56.10",
        "destination_port": 22,
        "packet_count": 20,
        "action": "reported",
        "summary": "20 packets from 192.168.56.10 in 5s",
    }

    handled = handle_event(
        config=AgentConfig(
            server="http://127.0.0.1:5000",
            token="token",
            interface="eth0",
            protected_ip="192.168.56.20",
            mode="ufw",
        ),
        event=event,
        blocker=lambda source_ip, mode: blocked.append((source_ip, mode)) or "blocked",
        reporter=lambda _server, _token, payload: reported.append(payload) or 201,
        renderer=lambda _status, _payload: None,
    )

    assert handled["action"] == "reported"
    assert "ignored management port 22" in handled["summary"]
    assert blocked == []
    assert reported == [handled]


def test_build_packet_handler_uses_analyzer_and_event_pipeline():
    handled = []
    event = {
        "event_type": "possible_dos",
        "source_ip": "192.168.56.10",
        "destination_port": 5000,
        "packet_count": 20,
        "action": "reported",
        "summary": "20 packets from 192.168.56.10 in 5s",
    }
    analyzer = SpyAnalyzer(event)
    config = AgentConfig(
        server="http://127.0.0.1:5000",
        token="token",
        interface="eth0",
        protected_ip="192.168.56.20",
        mode="dry-run",
    )

    handler = build_packet_handler(
        config=config,
        analyzer=analyzer,
        event_handler=lambda _config, payload: handled.append(payload),
    )
    result = handler(object())

    assert analyzer.packets
    assert handled == [event]
    assert result is None


def test_sync_blocklist_applies_and_reports_new_rules():
    blocked = []
    reported = []
    rendered = []
    config = AgentConfig(
        server="http://127.0.0.1:5000",
        token="token",
        interface="eth0",
        protected_ip="192.168.56.20",
        mode="ufw",
    )

    synced = sync_blocklist(
        config,
        applied_ips=set(),
        fetcher=lambda _server, _token: [
            {"id": 7, "ip_address": "192.168.56.10", "reason": "manual"}
        ],
        blocker=lambda source_ip, mode: blocked.append((source_ip, mode)) or "blocked",
        reporter=lambda _server, _token, payload: reported.append(payload) or 201,
        renderer=lambda status, payload: rendered.append((status, payload)),
    )

    assert synced == {"192.168.56.10"}
    assert blocked == [("192.168.56.10", "ufw")]
    assert reported == [
        {
            "event_type": "manual_block_sync",
            "source_ip": "192.168.56.10",
            "destination_port": None,
            "packet_count": 0,
            "action": "blocked",
            "summary": "manual blocklist rule 7 applied",
        }
    ]
    assert rendered[0][0] == "angry"


def test_sync_blocklist_does_not_reapply_synced_rules():
    blocked = []
    reported = []
    config = AgentConfig(
        server="http://127.0.0.1:5000",
        token="token",
        interface="eth0",
        protected_ip="192.168.56.20",
        mode="ufw",
    )

    synced = sync_blocklist(
        config,
        applied_ips={"192.168.56.10"},
        fetcher=lambda _server, _token: [
            {"id": 7, "ip_address": "192.168.56.10", "reason": "manual"}
        ],
        blocker=lambda source_ip, mode: blocked.append((source_ip, mode)) or "blocked",
        reporter=lambda _server, _token, payload: reported.append(payload) or 201,
        renderer=lambda _status, _payload: None,
    )

    assert synced == {"192.168.56.10"}
    assert blocked == []
    assert reported == []


def test_sync_blocklist_removes_rules_missing_from_api():
    unblocked = []
    reported = []
    config = AgentConfig(
        server="http://127.0.0.1:5000",
        token="token",
        interface="eth0",
        protected_ip="192.168.56.20",
        mode="ufw",
    )

    synced = sync_blocklist(
        config,
        applied_ips={"192.168.56.10", "192.168.56.11"},
        fetcher=lambda _server, _token: [
            {"id": 8, "ip_address": "192.168.56.11", "reason": "manual"}
        ],
        blocker=lambda source_ip, mode: "blocked",
        unblocker=lambda source_ip, mode: (
            unblocked.append((source_ip, mode)) or "unblocked"
        ),
        reporter=lambda _server, _token, payload: reported.append(payload) or 201,
        renderer=lambda _status, _payload: None,
    )

    assert synced == {"192.168.56.11"}
    assert unblocked == [("192.168.56.10", "ufw")]
    assert reported == [
        {
            "event_type": "manual_block_removed",
            "source_ip": "192.168.56.10",
            "destination_port": None,
            "packet_count": 0,
            "action": "unblocked",
            "summary": "manual blocklist rule for 192.168.56.10 removed",
        }
    ]
