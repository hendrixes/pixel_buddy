# pixel_buddy agent

The agent runs on a protected Ubuntu/Debian lab machine. It watches packets with
Scapy, renders the buddy in the terminal, and reports firewall events to the
Flask app.

Development mode:

```bash
uv run python -m agent.pixel_buddy_agent \
  --server http://127.0.0.1:5000 \
  --token TOKEN_FROM_WEB_UI \
  --interface eth0 \
  --protected-ip PROTECTED_VM_IP \
  --mode dry-run \
  --threshold 20 \
  --window 5
```

Demo mode with UFW:

```bash
sudo uv run python -m agent.pixel_buddy_agent \
  --server http://FLASK_HOST:5000 \
  --token TOKEN_FROM_WEB_UI \
  --interface eth0 \
  --protected-ip PROTECTED_VM_IP \
  --mode ufw \
  --threshold 20 \
  --window 5
```

Use `dry-run` for normal development. Use `ufw` only inside a controlled lab VM.
