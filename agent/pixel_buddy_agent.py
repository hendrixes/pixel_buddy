import argparse
from ipaddress import ip_address

from agent.config import AgentConfig, load_config, merge_config
from agent.runtime import build_packet_handler, run_live_monitor
from agent.tui import run_tui


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


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--server")
    parser.add_argument("--token")
    parser.add_argument("--interface")
    parser.add_argument("--protected-ip", type=ip_address_arg)
    parser.add_argument("--mode", choices=["dry-run", "ufw"])
    parser.add_argument("--threshold", type=positive_int)
    parser.add_argument("--window", type=positive_int)
    return parser.parse_args(argv)


def build_config(args):
    config = load_config(args.config)
    return merge_config(
        config,
        {
            "server": args.server,
            "token": args.token,
            "interface": args.interface,
            "protected_ip": args.protected_ip,
            "mode": args.mode,
            "threshold": args.threshold,
            "window": args.window,
        },
    )


def has_cli_overrides(args):
    return any(
        (
            args.server,
            args.token,
            args.interface,
            args.protected_ip,
        )
    )


def require_complete_config(config):
    missing = config.missing_fields()
    if missing:
        raise SystemExit(f"missing agent config fields: {', '.join(missing)}")


def main():
    args = parse_args()
    if not has_cli_overrides(args):
        run_tui(args.config)
        return

    config = build_config(args)
    require_complete_config(config)
    run_live_monitor(config)


if __name__ == "__main__":
    main()
