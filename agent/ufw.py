import subprocess
from ipaddress import ip_address


def normalize_ip(value):
    return str(ip_address(value))


def block_ip(source_ip, mode):
    normalized_ip = normalize_ip(source_ip)

    if mode == "dry-run":
        return "reported"

    if mode != "ufw":
        raise ValueError(f"unsupported mode: {mode}")

    subprocess.run(
        ["ufw", "deny", "from", normalized_ip],
        check=True,
        capture_output=True,
        text=True,
    )
    return "blocked"
