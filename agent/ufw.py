import subprocess
import shutil
from ipaddress import ip_address
from pathlib import Path


class FirewallCommandError(RuntimeError):
    pass


def normalize_ip(value):
    return str(ip_address(value))


def ufw_command():
    discovered = shutil.which("ufw")
    if discovered:
        return discovered

    for path in ("/usr/sbin/ufw", "/sbin/ufw"):
        if Path(path).exists():
            return path

    raise FirewallCommandError("ufw command not found")


def block_ip(source_ip, mode):
    normalized_ip = normalize_ip(source_ip)

    if mode == "dry-run":
        return "reported"

    if mode != "ufw":
        raise ValueError(f"unsupported mode: {mode}")

    command = [ufw_command(), "deny", "from", normalized_ip]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        raise FirewallCommandError(
            f"ufw failed with exit code {result.returncode}: {output}"
        )

    return "blocked"
