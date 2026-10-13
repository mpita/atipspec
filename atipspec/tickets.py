"""The external ticket a delivery belongs to, as `new --ticket` records it.

AtipSpec links the ticket and never updates it: no tracker is written. A
ticket is a key such as PROJ-123 (Jira, Linear), an issue number such as #42,
or an https URL. `ticket_url` in teams.json, with `{ticket}` where the key or
number goes, turns the first two into a link. It is not part of what the
proposal's approval hashes, so it can be added or corrected in spec.md later.
Values written before 0.3.0 are shown as they are, without a link.
"""
from __future__ import annotations

import re
import urllib.parse

from .errors import AtipSpecError

KEY = re.compile(r"[A-Z][A-Z0-9_]*-\d+")
ISSUE = re.compile(r"#\d+")
MAX_LENGTH = 300


def _https(value: str) -> bool:
    if len(value) > MAX_LENGTH or any(char.isspace() for char in value):
        return False
    parts = urllib.parse.urlsplit(value)
    return parts.scheme == "https" and bool(parts.hostname) and not parts.username and not parts.password


def validate(value: str) -> str:
    """The ticket as `new --ticket` records it, or an error naming the forms."""
    value = value.strip()
    if KEY.fullmatch(value) or ISSUE.fullmatch(value) or _https(value):
        return value
    raise AtipSpecError(f"Invalid ticket {value!r}: use a key like PROJ-123, an issue number like #42, "
                        "or an https URL")


def link(project, value) -> str | None:
    """The ticket's URL: an https URL as it is, a key or issue number through
    teams.json `ticket_url`; None otherwise."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if _https(value):
        return value
    if not (KEY.fullmatch(value) or ISSUE.fullmatch(value)):
        return None
    from .teams import configuration
    try:
        template = configuration(project).get("ticket_url")
    except (AtipSpecError, OSError):
        return None
    if not template:
        return None
    return template.replace("{ticket}", urllib.parse.quote(value.lstrip("#"), safe=""))


def label(project, value) -> str | None:
    """The ticket with its link in parentheses, for plain text; None without one."""
    if not isinstance(value, str) or not value.strip():
        return None
    url = link(project, value)
    return value.strip() + (f" ({url})" if url and url != value.strip() else "")
