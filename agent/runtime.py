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
    sniff(
        iface=config.interface,
        prn=build_packet_handler(config, event_handler=event_handler),
        store=False,
    )
