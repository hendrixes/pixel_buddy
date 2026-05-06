from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from scapy.all import sniff

from agent.analyzer import PacketAnalyzer
from agent.ufw import block_ip


FACES = {
    "neutral": "(•‿•)",
    "alert": "(⊙_⊙)",
    "angry": "(ಠ_ಠ)",
}


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
        print(f"packets: {event['packet_count']}")
        print(f"action: {event['action']}")


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


def handle_event(config, event, reporter=post_event, renderer=render_terminal):
    handled_event = dict(event)

    try:
        handled_event["action"] = block_ip(handled_event["source_ip"], config.mode)
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
    )

    def handle_packet(packet):
        event = packet_analyzer.observe_packet(packet)
        if not event:
            return None

        return event_handler(config, event)

    return handle_packet


def run_live_monitor(config, event_handler=handle_event):
    sniff(
        iface=config.interface,
        prn=build_packet_handler(config, event_handler=event_handler),
        store=False,
    )
