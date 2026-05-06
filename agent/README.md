# pixel_buddy agent

The agent runs on a protected Ubuntu/Debian lab machine. It watches packets with
Scapy, renders the buddy in the terminal, and reports firewall events to the
Flask app.

Default TUI mode:

```bash
sudo uv run python -m agent.pixel_buddy_agent
```

On first run, use the configure option to set:

- Flask server URL
- agent token from `/agents`
- network interface
- local protected IP
- firewall mode: `dry-run` or `ufw`
- packet threshold/window

The config is saved at `~/.config/pixel_buddy/agent.json` with `0600`
permissions.

TUI actions:

- `s`: start live Scapy monitoring
- `c`: edit local config
- `q`: quit

Advanced non-interactive live mode:

```bash
sudo uv run python -m agent.pixel_buddy_agent \
  --server http://FLASK_HOST:5000 \
  --token TOKEN_FROM_WEB_UI \
  --interface eth0 \
  --protected-ip PROTECTED_VM_IP \
  --mode dry-run \
  --threshold 20 \
  --window 5
```

Use `dry-run` for normal development. Use `ufw` only inside a controlled lab VM.
