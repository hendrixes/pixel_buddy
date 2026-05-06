from pathlib import Path

from agent.config import AgentConfig, load_config, save_config


def test_load_config_returns_defaults_when_file_does_not_exist(tmp_path):
    config = load_config(Path(tmp_path) / "missing.json")

    assert config == AgentConfig()
    assert config.missing_fields() == ["server", "token", "interface", "protected_ip"]


def test_save_and_load_config_roundtrip(tmp_path):
    path = Path(tmp_path) / "agent.json"
    config = AgentConfig(
        server="http://127.0.0.1:5000",
        token="secret",
        interface="eth0",
        protected_ip="192.168.56.20",
        mode="dry-run",
        threshold=10,
        window=3,
    )

    save_config(config, path)
    loaded = load_config(path)

    assert loaded == config
    assert path.stat().st_mode & 0o777 == 0o600
