import curses
from pathlib import Path
from textwrap import wrap

from scapy.all import sniff

from agent.analyzer import PacketAnalyzer
from agent.config import AgentConfig, default_config_path, load_config, save_config
from agent.runtime import FACES, build_packet_handler, handle_event


def draw_lines(stdscr, lines):
    stdscr.erase()
    max_width = max(1, curses.COLS - 1)
    for y, line in enumerate(lines):
        if y >= curses.LINES - 1:
            break
        stdscr.addstr(y, 0, line[:max_width])
    stdscr.refresh()


def prompt(stdscr, label, default="", hidden_default=False):
    curses.echo()
    display_default = "saved" if hidden_default and default else default
    prompt_text = f"{label} [{display_default}]: "
    x = min(len(prompt_text), curses.COLS - 2)
    stdscr.addstr(curses.LINES - 2, 0, " " * (curses.COLS - 1))
    stdscr.addstr(curses.LINES - 2, 0, prompt_text[: curses.COLS - 1])
    value = stdscr.getstr(curses.LINES - 2, x)
    curses.noecho()
    decoded = value.decode("utf-8").strip()
    return decoded or default


def draw_menu(stdscr, config, message="", last_event=None):
    face = FACES["neutral"]
    if last_event:
        face = FACES["angry"] if last_event["action"] == "blocked" else FACES["alert"]

    lines = [
        "pixel_buddy agent",
        "",
        f"  {face}",
        "",
        f"status: {message or 'idle'}",
        f"server: {config.server or '-'}",
        f"interface: {config.interface or '-'}",
        f"protected ip: {config.protected_ip or '-'}",
        f"mode: {config.mode}",
        f"threshold/window: {config.threshold}/{config.window}s",
        f"ignored ports: {', '.join(str(port) for port in config.ignored_ports)}",
        "",
        "[s] start live monitor",
        "[c] configure",
        "[q] quit",
    ]

    if last_event:
        lines.extend(
            [
                "",
                f"last event: {last_event['event_type']}",
                f"source: {last_event['source_ip']}",
                f"port: {last_event.get('destination_port') or '-'}",
                f"packets: {last_event['packet_count']}",
                f"action: {last_event['action']}",
            ]
        )
        for line in wrap(f"summary: {last_event['summary']}", width=72):
            lines.append(line)

    draw_lines(stdscr, lines)


def configure(stdscr, config, config_path):
    updated = AgentConfig(
        server=prompt(stdscr, "server", config.server or "http://127.0.0.1:5000"),
        token=prompt(stdscr, "token", config.token, hidden_default=True),
        interface=prompt(stdscr, "interface", config.interface or "eth0"),
        protected_ip=prompt(stdscr, "protected ip", config.protected_ip),
        mode=prompt(stdscr, "mode", config.mode or "dry-run"),
        threshold=int(prompt(stdscr, "threshold", str(config.threshold))),
        window=int(prompt(stdscr, "window seconds", str(config.window))),
    )
    save_config(updated, config_path)
    return updated


def ensure_configured(stdscr, config, config_path):
    if config.is_complete():
        return config

    draw_menu(stdscr, config, "first setup required")
    return configure(stdscr, config, config_path)


def monitor_live(stdscr, config):
    analyzer = PacketAnalyzer(
        protected_ip=config.protected_ip,
        threshold=config.threshold,
        window_seconds=config.window,
        ignored_ports=config.ignored_ports,
    )
    last_event = None

    def tui_event_handler(active_config, event):
        nonlocal last_event
        last_event = handle_event(
            active_config,
            event,
            renderer=lambda _status, _event: None,
        )
        return last_event

    handler = build_packet_handler(
        config=config,
        analyzer=analyzer,
        event_handler=tui_event_handler,
    )

    stdscr.nodelay(True)
    try:
        while True:
            draw_menu(stdscr, config, "monitoring - press q to stop", last_event)
            if stdscr.getch() == ord("q"):
                break
            sniff(iface=config.interface, prn=handler, store=False, timeout=1)
    finally:
        stdscr.nodelay(False)


def tui_loop(stdscr, config_path):
    curses.curs_set(0)
    config = load_config(config_path)
    last_event = None
    message = ""

    while True:
        draw_menu(stdscr, config, message, last_event)
        key = stdscr.getch()

        if key == ord("q"):
            break
        if key == ord("c"):
            config = configure(stdscr, config, config_path)
            message = "config saved"
        elif key == ord("s"):
            try:
                config = ensure_configured(stdscr, config, config_path)
                monitor_live(stdscr, config)
                message = "monitor stopped"
            except Exception as exc:
                message = f"monitor error: {exc}"


def run_tui(config_path=None):
    path = Path(config_path) if config_path else default_config_path()
    curses.wrapper(tui_loop, path)
