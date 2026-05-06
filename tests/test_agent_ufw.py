import subprocess

import pytest

from agent.ufw import FirewallCommandError, block_ip


def test_block_ip_dry_run_validates_ip_and_reports():
    assert block_ip("192.168.56.10", "dry-run") == "reported"


def test_block_ip_rejects_invalid_ip_in_dry_run():
    with pytest.raises(ValueError):
        block_ip("not-an-ip", "dry-run")


def test_block_ip_ufw_mode_runs_deny_command(monkeypatch):
    calls = []
    monkeypatch.setattr("agent.ufw.ufw_command", lambda: "ufw")

    def fake_run(command, check, capture_output, text):
        calls.append(
            {
                "command": command,
                "check": check,
                "capture_output": capture_output,
                "text": text,
            }
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert block_ip("192.168.56.10", "ufw") == "blocked"
    assert calls == [
        {
            "command": ["ufw", "deny", "from", "192.168.56.10"],
            "check": False,
            "capture_output": True,
            "text": True,
        }
    ]


def test_block_ip_ufw_mode_reports_stderr(monkeypatch):
    monkeypatch.setattr("agent.ufw.ufw_command", lambda: "ufw")

    def fake_run(command, check, capture_output, text):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="ERROR: problem running ufw",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FirewallCommandError, match="ERROR: problem running ufw"):
        block_ip("192.168.56.10", "ufw")
