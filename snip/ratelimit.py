"""Limits how many links one IP address can create per minute."""

from __future__ import annotations

import time

from snip.db import get_db

WINDOW_SECONDS = 60


def allow(ip: str, limit: int, now: float | None = None) -> bool:
    """Record this attempt and say whether it is within the limit.

    This is a sliding window: it counts the requests in the 60 seconds before
    now, so a burst cannot sneak through at the boundary between two minutes.
    """
    now = time.time() if now is None else now
    database = get_db()
    database.execute("DELETE FROM create_log WHERE created_at <= ?", (now - WINDOW_SECONDS,))
    recent = database.execute(
        "SELECT COUNT(*) AS n FROM create_log WHERE ip = ? AND created_at > ?",
        (ip, now - WINDOW_SECONDS),
    ).fetchone()["n"]

    if recent >= limit:
        database.commit()
        return False

    database.execute("INSERT INTO create_log (ip, created_at) VALUES (?, ?)", (ip, now))
    database.commit()
    return True
