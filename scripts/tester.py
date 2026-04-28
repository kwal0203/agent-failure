#!/usr/bin/env python3
"""Check outbox_events for provisioning errors."""

from sqlalchemy import create_engine, text

engine = create_engine(
    "postgresql+psycopg://postgres:localdev@172.17.0.1:5432/agent_failure"
)
with engine.connect() as conn:
    rows = conn.execute(
        text(
            "SELECT id, status, last_error, payload "
            "FROM outbox_events "
            "WHERE last_error IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 3"
        )
    ).fetchall()
    for r in rows:
        print(f"id={r[0]}")
        print(f"  status={r[1]}")
        print(f"  last_error={r[2]}")
        print(f"  payload={r[3]}")
        print()
