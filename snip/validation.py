"""Checks a URL before it is shortened."""

from __future__ import annotations

from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048


def url_problem(url: str, own_host: str = "") -> str | None:
    """Return what is wrong with a URL, or None if it can be shortened."""
    if not url:
        return "Enter a URL."
    if len(url) > MAX_URL_LENGTH:
        return f"That URL is too long. The limit is {MAX_URL_LENGTH} characters."
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        return "A URL cannot contain spaces or control characters."

    try:
        parts = urlsplit(url)
    except ValueError:
        return "That does not look like a valid URL."

    # Only web links. This blocks javascript:, data: and file: links, which
    # could run code or read local files when someone clicks the short link.
    if parts.scheme not in ("http", "https"):
        return "Only http and https links can be shortened."
    if not parts.hostname or "." not in parts.hostname and parts.hostname != "localhost":
        return "That URL has no valid domain."

    # A short link that points at another short link here could loop forever.
    if own_host and parts.netloc.lower() == own_host.lower():
        return "That link already points to this site."
    return None
