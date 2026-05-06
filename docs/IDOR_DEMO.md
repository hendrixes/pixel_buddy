# IDOR Demonstration

The vulnerable pattern is a blocked IP lookup that trusts only the URL ID:

```python
blocked_ip = BlockedIP.query.get_or_404(blocked_ip_id)
```

This allows user B to access user A's blocked IP record by manually changing the
URL to `/blocked-ips/<id_from_user_a>`.

The fixed pattern includes ownership:

```python
blocked_ip = BlockedIP.query.filter_by(
    id=blocked_ip_id,
    user_id=current_user.id,
).first_or_404()
```

Presentation flow:

1. Create user A.
2. Create a blocked IP as user A.
3. Note the blocked IP ID.
4. Log out.
5. Create user B.
6. Try to access `/blocked-ips/<id_from_user_a>` as user B.
7. Show the vulnerable version allows access.
8. Apply the fixed query.
9. Repeat the request and show Flask returns 404.

Final code must keep the ownership-filtered query.
The vulnerable query is included only for presentation and should not be restored
in the application code.
