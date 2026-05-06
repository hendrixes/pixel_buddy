# pixel_buddy Firewall Agent Design

## Product Direction

`pixel_buddy` is an educational, gamified firewall SaaS. A user creates an
account, configures a buddy, and runs a Python terminal agent on a protected lab
machine. The agent monitors network traffic with Scapy, detects simple
high-volume patterns, optionally applies a UFW block, and reports events back to
the Flask web app.

The web app is the control panel. It owns authentication, user resources,
database state, the visual buddy, firewall events, blocked IPs, and leaderboard.
The terminal agent is the local sensor/firewall companion.

## Core Concept

The same buddy appears in two places:

- In the web UI, rendered as the current persisted state of the user's pet.
- In the terminal agent, rendered as ASCII text while the agent runs.

The Flask app remains the source of truth for the buddy state. The agent observes
traffic, blocks when configured to do so, and reports events. It does not own the
official pet state.

Example terminal display:

```text
pixel_buddy agent
user: felipinho
mode: ufw

  (ಠ_ಠ)

status: ALERT
event: possible_dos
source: 192.168.0.23
action: blocked via ufw
```

## Main Flow

1. User registers and logs into the Flask app.
2. User creates or configures a buddy.
3. User creates an agent token in the authenticated area.
4. User runs `agent.py` on a protected Ubuntu/Debian lab machine.
5. The agent authenticates with the Flask app using the token.
6. Scapy monitors packets arriving at the protected machine.
7. If traffic crosses a simple threshold, the agent classifies it as a firewall
   event such as `possible_dos`.
8. In `dry-run` mode, the agent only reports the event.
9. In `ufw` mode, the agent validates the source IP and applies a UFW block.
10. The agent reports the event and action to Flask.
11. Flask persists the event, updates the blocked IP list, updates the buddy
    mood/stats/XP, and refreshes leaderboard data.
12. The web UI and terminal both show the buddy reaction.

## Modes

`dry-run`

The agent detects suspicious traffic and reports it, but does not modify the
host firewall. This is the default local development mode.

`ufw`

The agent detects suspicious traffic, reports it, and applies a real UFW block
on the protected machine. This mode is intended for controlled lab demos.

## Detection Scope

Detection is intentionally simple and explainable:

- Many packets from the same source IP in a short time window.
- Many TCP SYN packets from the same source IP.
- Many packets targeting the same destination port.
- Repeated ICMP traffic.

The app should not claim to be a production IDS, IPS, or advanced firewall. It is
an educational firewall companion for lab demonstrations.

## Data Model

Existing concepts remain:

- `User`: authenticated account and resource owner.
- `Pet`: one buddy per user, with mood, stats, XP, and display state.

New concepts:

- `Agent`: a registered terminal agent with a token, display name, mode, and
  last-seen timestamp.
- `FirewallEvent`: a reported detection event from an agent.
- `BlockedIP`: an IP blocked by the system, either simulated or applied through
  UFW.

The `.pcap` upload idea is no longer the primary product direction. PCAP upload
can remain a future optional feature, but it is outside the MVP.

## CRUD Requirement

The MVP CRUD entity for the assignment is `BlockedIP`. Agent management can be
added with create/list/token-rotation behavior, but the full required CRUD should
be demonstrated through blocked IP records.

Required MVP CRUD:

- List blocked IPs.
- Create a manual blocked IP.
- View a blocked IP.
- Edit the reason/notes.
- Delete/unblock a blocked IP.

The pet setup remains part of the game experience, but the firewall CRUD is more
aligned with the SaaS product story.

## Security Demonstration

The required vulnerability demonstration should be IDOR / broken access control.

Vulnerable version:

```python
blocked_ip = BlockedIP.query.get_or_404(blocked_ip_id)
```

Problem:

A logged-in user could manually change the URL and view, edit, or delete another
user's blocked IP record if they know or guess the ID.

Corrected version:

```python
blocked_ip = BlockedIP.query.filter_by(
    id=blocked_ip_id,
    user_id=current_user.id,
).first_or_404()
```

Presentation script:

1. Create user A and let the agent or UI create a blocked IP.
2. Note the blocked IP ID.
3. Log out and log in as user B.
4. Attempt to access `/blocked-ips/<id_from_user_a>`.
5. Show that the vulnerable version allows access.
6. Apply the ownership-filtered query.
7. Repeat the access attempt and show that user B is denied.

## Assignment Coverage

- Flask backend: required backend framework.
- Flask-Login: authentication and protected area.
- Flask-SQLAlchemy: SQLite persistence.
- Blueprints: auth, pets/game, agents, firewall/blocklist, API.
- Cookies: Flask session plus optional retro theme preference.
- SQLite tables: users, pets, agents, firewall events, blocked IPs.
- CRUD: blocked IPs.
- GET/POST forms: auth, pet setup, blocked IP CRUD, agent creation.
- Vulnerability: IDOR demonstrated and corrected.
- Usability: authenticated dashboard, retro buddy screen, blocklist table,
  event feed, and leaderboard.

## Non-Goals

- Production-grade IDS/IPS.
- Real-time enterprise monitoring.
- Full firewall rule management.
- Capturing traffic from unrelated machines in a switched LAN.
- Requiring packet sniffing inside the Flask web container.

## Implementation Boundary

The MVP should keep the Flask app and the terminal agent separate:

- Flask app: account, state, dashboard, CRUD, API endpoints.
- Agent: Scapy monitoring, optional UFW action, terminal rendering, event
  reporting.

This keeps the SaaS story clear while preserving the local Pwnagotchi-like
terminal personality.
