"""Short codes: the part after the slash in a short link."""

from __future__ import annotations

import re
import secrets

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
CODE_LENGTH = 6

# Paths the app uses itself, which a custom alias must not take over.
RESERVED = {"api", "stats", "static", "health", "admin", "login", "about"}

ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,30}$")


def random_code(length: int = CODE_LENGTH) -> str:
    """A random base62 code.

    Six characters give 62^6, about 56 billion, possible codes. They are
    random, not counted up from 1, so nobody can walk through every link by
    trying the next number. `secrets` is used instead of `random` because its
    output cannot be predicted.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def alias_problem(alias: str) -> str | None:
    """Return what is wrong with a custom alias, or None if it is fine."""
    if not ALIAS_PATTERN.match(alias):
        return "An alias must be 3 to 30 characters: letters, numbers, - or _."
    if alias.lower() in RESERVED:
        return "That alias is reserved. Choose another."
    return None
