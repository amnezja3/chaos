"""Public labels are separate from account IDs used by routing and safety."""
def labels(rows, identities, key='sender', output='sender_display_name'):
    rows = list(rows)
    names = identities.public_names(row.get(key) for row in rows)
    return [dict(row, **{output: names.get(row.get(key), row.get(key) or '')}) for row in rows]
