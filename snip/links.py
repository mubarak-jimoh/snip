"""Creating links, following them and reading their statistics."""

from __future__ import annotations

import sqlite3
import time
from urllib.parse import urlsplit

from snip.codes import alias_problem, random_code
from snip.db import get_db
from snip.validation import url_problem

MAX_EXPIRY_DAYS = 365
SECONDS_PER_DAY = 86_400


class LinkError(Exception):
    """A problem the user can fix. The message is safe to show them."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def create_link(
    url: str,
    alias: str = "",
    expires_in_days: int | None = None,
    own_host: str = "",
    now: float | None = None,
) -> sqlite3.Row:
    now = time.time() if now is None else now
    url = url.strip()
    alias = alias.strip()

    problem = url_problem(url, own_host)
    if problem:
        raise LinkError(problem)

    expires_at = None
    if expires_in_days is not None:
        if not 1 <= expires_in_days <= MAX_EXPIRY_DAYS:
            raise LinkError(f"Expiry must be between 1 and {MAX_EXPIRY_DAYS} days.")
        expires_at = now + expires_in_days * SECONDS_PER_DAY

    database = get_db()

    if alias:
        problem = alias_problem(alias)
        if problem:
            raise LinkError(problem)
        try:
            database.execute(
                "INSERT INTO links (code, url, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (alias, url, now, expires_at),
            )
        except sqlite3.IntegrityError as error:
            raise LinkError("That alias is already taken.", status=409) from error
    else:
        # Two links could be given the same random code. The UNIQUE rule on
        # the column makes the database reject the second one, so we just
        # try again with a new code.
        for _attempt in range(5):
            try:
                database.execute(
                    "INSERT INTO links (code, url, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (random_code(), url, now, expires_at),
                )
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise LinkError("Could not create a link. Try again.", status=503)

    database.commit()
    return database.execute("SELECT * FROM links WHERE id = last_insert_rowid()").fetchone()


def get_link(code: str) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()


def is_expired(link: sqlite3.Row, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return link["expires_at"] is not None and now >= link["expires_at"]


def record_click(link: sqlite3.Row, referrer: str = "", now: float | None = None) -> None:
    """Store when the click happened and which site it came from.

    Only the referring site's domain is kept, never the full address and
    never the visitor's IP, so the statistics cannot identify a person.
    """
    now = time.time() if now is None else now
    host = ""
    if referrer:
        try:
            host = (urlsplit(referrer).hostname or "")[:100]
        except ValueError:
            host = ""
    database = get_db()
    database.execute(
        "INSERT INTO clicks (link_id, clicked_at, referrer) VALUES (?, ?, ?)",
        (link["id"], now, host),
    )
    database.commit()


def get_stats(link: sqlite3.Row, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    database = get_db()

    totals = database.execute(
        "SELECT COUNT(*) AS clicks, MAX(clicked_at) AS last_clicked FROM clicks WHERE link_id = ?",
        (link["id"],),
    ).fetchone()

    referrers = database.execute(
        "SELECT CASE WHEN referrer = '' THEN 'Direct' ELSE referrer END AS source, "
        "COUNT(*) AS clicks FROM clicks WHERE link_id = ? "
        "GROUP BY source ORDER BY clicks DESC, source LIMIT 5",
        (link["id"],),
    ).fetchall()

    # Clicks per day for the last seven days, oldest first, including days with none
    today = int(now // SECONDS_PER_DAY)
    rows = database.execute(
        "SELECT CAST(clicked_at / ? AS INTEGER) AS day, COUNT(*) AS clicks FROM clicks "
        "WHERE link_id = ? AND clicked_at >= ? GROUP BY day",
        (SECONDS_PER_DAY, link["id"], (today - 6) * SECONDS_PER_DAY),
    ).fetchall()
    by_day = {row["day"]: row["clicks"] for row in rows}
    daily = [
        {
            "date": time.strftime("%Y-%m-%d", time.gmtime(day * SECONDS_PER_DAY)),
            "clicks": by_day.get(day, 0),
        }
        for day in range(today - 6, today + 1)
    ]

    return {
        "code": link["code"],
        "url": link["url"],
        "created_at": link["created_at"],
        "expires_at": link["expires_at"],
        "expired": is_expired(link, now),
        "clicks": totals["clicks"],
        "last_clicked": totals["last_clicked"],
        "referrers": [{"source": r["source"], "clicks": r["clicks"]} for r in referrers],
        "daily": daily,
    }
