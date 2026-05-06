import json
import os
from dataclasses import asdict, dataclass
from ipaddress import ip_address
from pathlib import Path


VALID_MODES = {"dry-run", "ufw"}


@dataclass
class AgentConfig:
    server: str = ""
    token: str = ""
    interface: str = ""
    protected_ip: str = ""
    mode: str = "dry-run"
    threshold: int = 50
    window: int = 5

    def missing_fields(self):
        fields = []
        for field_name in ("server", "token", "interface", "protected_ip"):
            if not getattr(self, field_name):
                fields.append(field_name)
        return fields

    def is_complete(self):
        return not self.missing_fields()


def default_config_path():
    override = os.environ.get("PIXEL_BUDDY_AGENT_CONFIG")
    if override:
        return Path(override)

    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "pixel_buddy" / "agent.json"

    return Path.home() / ".config" / "pixel_buddy" / "agent.json"


def normalize_config(data):
    config = AgentConfig(
        server=str(data.get("server", "")).strip(),
        token=str(data.get("token", "")).strip(),
        interface=str(data.get("interface", "")).strip(),
        protected_ip=str(data.get("protected_ip", "")).strip(),
        mode=str(data.get("mode", "dry-run")).strip() or "dry-run",
        threshold=int(data.get("threshold", 50)),
        window=int(data.get("window", 5)),
    )

    if config.mode not in VALID_MODES:
        raise ValueError("mode must be dry-run or ufw")
    if config.protected_ip:
        config.protected_ip = str(ip_address(config.protected_ip))
    if config.threshold <= 0:
        raise ValueError("threshold must be positive")
    if config.window <= 0:
        raise ValueError("window must be positive")

    return config


def load_config(path=None):
    config_path = Path(path) if path else default_config_path()
    if not config_path.exists():
        return AgentConfig()

    with config_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("agent config must be a JSON object")

    return normalize_config(data)


def save_config(config, path=None):
    validated_config = normalize_config(asdict(config))
    config_path = Path(path) if path else default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(asdict(validated_config), file, indent=2)
        file.write("\n")

    config_path.chmod(0o600)


def merge_config(base, overrides):
    data = asdict(base)
    for key, value in overrides.items():
        if value is not None and value != "":
            data[key] = value
    return normalize_config(data)
