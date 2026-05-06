# IDOR Demonstration

IDOR means the application trusts an object ID from the URL without checking who
owns that object. In `pixel_buddy`, the easiest classroom example is a blocked IP
record:

```text
/blocked-ips/<blocked_ip_id>
```

The sensitive code is centralized in `app/firewall/routes.py`, inside
`get_owned_blocked_ip()`.

## Vulnerable Version

This version looks up only by ID:

```python
def get_owned_blocked_ip(blocked_ip_id):
    return BlockedIP.query.filter_by(id=blocked_ip_id).first_or_404()
```

Problem: user B can change the URL to the ID of user A's record and see data that
does not belong to them.

## Fixed Version

The final project must keep the ownership filter:

```python
def get_owned_blocked_ip(blocked_ip_id):
    return BlockedIP.query.filter_by(
        id=blocked_ip_id,
        user_id=current_user.id,
    ).first_or_404()
```

Now the record must match both the URL ID and the logged-in user's ID. If user B
tries to open user A's record, Flask returns `404`.

## Presentation Flow

1. Start the app with the vulnerable version.
2. Register/login as user A.
3. Create a blocked IP in `/blocked-ips/new`.
4. Open the blocked IP detail page and note its ID in the URL.
5. Logout.
6. Register/login as user B.
7. Manually open `/blocked-ips/<id_from_user_a>`.
8. Show that user B can see user A's record.
9. Replace the vulnerable lookup with the fixed lookup.
10. Repeat the same request as user B.
11. Show that the same URL now returns `404`.

## Test Evidence

The fixed behavior is covered by:

```bash
uv run pytest tests/test_firewall_routes.py -k idor
```

Keep the vulnerable snippet only for the live demonstration. Do not leave it in
the submitted code.
