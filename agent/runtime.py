from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import time

from scapy.all import sniff

from agent.analyzer import PacketAnalyzer
from agent.ufw import block_ip, unblock_ip


FACES = {
    "neutral": "(•‿•)",
    "alert": "(⊙_⊙)",
    "angry": "(ಠ_ಠ)",
}
BLOCKLIST_SYNC_INTERVAL_SECONDS = 10


def render_terminal(status, event=None):
    face = FACES.get(status, FACES["neutral"])
    print("\033c", end="")
    print("pixel_buddy agent")
    print()
    print(f"  {face}")
    print()
    print(f"status: {status.upper()}")
    if event:
        print(f"event: {event['event_type']}")
        print(f"source: {event['source_ip']}")
        print(f"port: {event.get('destination_port') or '-'}")
        print(f"packets: {event['packet_count']}")
        print(f"action: {event['action']}")
        print(f"summary: {event['summary']}")


def post_event(server, token, event):
    body = json.dumps(event).encode("utf-8")
    request = Request(
        f"{server.rstrip('/')}/api/agent/events",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return response.status


def fetch_blocked_ips(server, token):
    request = Request(
        f"{server.rstrip('/')}/api/agent/blocked-ips",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return payload.get("blocked_ips", [])


def blocklist_event(rule, action, summary):
    return {
        "event_type": "manual_block_sync",
        "source_ip": rule["ip_address"],
        "destination_port": None,
        "packet_count": 0,
        "action": action,
        "summary": summary,
    }


def removed_blocklist_event(source_ip, action, summary):
    return {
        "event_type": "manual_block_removed",
        "source_ip": source_ip,
        "destination_port": None,
        "packet_count": 0,
        "action": action,
        "summary": summary,
    }


def sync_blocklist(
    config,
    applied_ips=None,
    fetcher=fetch_blocked_ips,
    blocker=block_ip,
    unblocker=unblock_ip,
    reporter=post_event,
    renderer=render_terminal,
):
    synced_ips = set(applied_ips or set())

    try:
        rules = fetcher(config.server, config.token)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"blocklist sync failed: {exc}")
        return synced_ips

    for rule in rules:
        source_ip = rule["ip_address"]
        if source_ip in synced_ips:
            continue

        try:
            action = blocker(source_ip, config.mode)
            summary = f"manual blocklist rule {rule['id']} applied"
        except Exception as exc:
            action = "block_failed"
            summary = f"manual blocklist rule {rule['id']} failed: {exc}"

        event = blocklist_event(rule, action, summary)
        status = "angry" if action == "blocked" else "alert"
        renderer(status, event)

        try:
            reporter(config.server, config.token, event)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"report failed: {exc}")

        if action in {"blocked", "reported"}:
            synced_ips.add(source_ip)

    active_ips = {rule["ip_address"] for rule in rules}
    for source_ip in sorted(synced_ips - active_ips):
        try:
            action = unblocker(source_ip, config.mode)
            summary = f"manual blocklist rule for {source_ip} removed"
        except Exception as exc:
            action = "block_failed"
            summary = f"manual blocklist rule for {source_ip} remove failed: {exc}"

        event = removed_blocklist_event(source_ip, action, summary)
        renderer("alert", event)

        try:
            reporter(config.server, config.token, event)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"report failed: {exc}")

        if action in {"reported", "unblocked"}:
            synced_ips.remove(source_ip)

    return synced_ips


def should_ignore_event(config, event):
    destination_port = event.get("destination_port")
    return destination_port in set(config.ignored_ports)


def handle_event(
    config,
    event,
    reporter=post_event,
    renderer=render_terminal,
    blocker=block_ip,
):
    handled_event = dict(event)

    if should_ignore_event(config, handled_event):
        handled_event["action"] = "reported"
        handled_event["summary"] = (
            f"{handled_event['summary']} | ignored management port "
            f"{handled_event['destination_port']}"
        )
    else:
        try:
            handled_event["action"] = blocker(handled_event["source_ip"], config.mode)
        except Exception as exc:
            handled_event["action"] = "block_failed"
            handled_event["summary"] = (
                f"{handled_event['summary']} | block failed: {exc}"
            )

    status = "angry" if handled_event["action"] == "blocked" else "alert"
    renderer(status, handled_event)

    try:
        reporter(config.server, config.token, handled_event)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"report failed: {exc}")

    return handled_event


def build_packet_handler(config, analyzer=None, event_handler=handle_event):
    packet_analyzer = analyzer or PacketAnalyzer(
        protected_ip=config.protected_ip,
        threshold=config.threshold,
        window_seconds=config.window,
        ignored_ports=config.ignored_ports,
    )

    def handle_packet(packet):
        event = packet_analyzer.observe_packet(packet)
        if not event:
            return None

        event_handler(config, event)
        return None

    return handle_packet


def run_live_monitor(config, event_handler=handle_event):
    synced_blocklist_ips = set()
    last_blocklist_sync = 0
    handler = build_packet_handler(config, event_handler=event_handler)

    while True:
        now = time.monotonic()
        if now - last_blocklist_sync >= BLOCKLIST_SYNC_INTERVAL_SECONDS:
            synced_blocklist_ips = sync_blocklist(config, synced_blocklist_ips)
            last_blocklist_sync = now

        sniff(iface=config.interface, prn=handler, store=False, timeout=1)
