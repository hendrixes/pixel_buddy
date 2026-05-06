import argparse
import json
import time
from ipaddress import ip_address
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scapy.all import IP, TCP, sniff

from agent.packet_window import PacketWindow
from agent.ufw import block_ip


FACES = {
    "neutral": "(•‿•)",
    "alert": "(⊙_⊙)",
    "angry": "(ಠ_ಠ)",
}


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def ip_address_arg(value):
    try:
        return str(ip_address(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


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


def build_packet_handler(args, packet_window):
    def handle_packet(packet):
        if IP not in packet or TCP not in packet:
            return

        if packet[IP].dst != args.protected_ip:
            return

        source_ip = packet[IP].src
        destination_port = packet[TCP].dport
        event = packet_window.observe(source_ip, destination_port, time.time())
        if not event:
            return

        try:
            event["action"] = block_ip(source_ip, args.mode)
        except Exception as exc:
            event["action"] = "block_failed"
            event["summary"] = f"{event['summary']} | block failed: {exc}"

        render_terminal("angry" if event["action"] == "blocked" else "alert", event)

        try:
            post_event(args.server, args.token, event)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"report failed: {exc}")

    return handle_packet


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--protected-ip", type=ip_address_arg, required=True)
    parser.add_argument("--mode", choices=["dry-run", "ufw"], default="dry-run")
    parser.add_argument("--threshold", type=positive_int, default=50)
    parser.add_argument("--window", type=positive_int, default=5)
    return parser.parse_args()


def main():
    args = parse_args()
    render_terminal("neutral")
    packet_window = PacketWindow(
        threshold=args.threshold,
        window_seconds=args.window,
    )
    sniff(
        iface=args.interface,
        prn=build_packet_handler(args, packet_window),
        store=False,
    )


if __name__ == "__main__":
    main()
