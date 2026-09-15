"""Markdown frontmatter and a small YAML subset: scalars and flat lists.

AtipSpec artifacts carry a few machine-readable fields. Supporting only this
subset keeps the CLI dependency-free and the files easy to write by hand.
"""
from __future__ import annotations

import json
import re

_KEY = re.compile(r"^([A-Za-z_][\w-]*)\s*:(?:\s+(.*))?$")
_ITEM = re.compile(r"^\s+-\s*(.*)$")
_PLAIN = re.compile(r"[A-Za-z0-9_./+@-]+")
_INT = re.compile(r"-?\d+")


def split(text: str) -> tuple[dict, str]:
    """Return (metadata, body). Metadata is empty when there is no frontmatter."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return {}, text
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            return parse("".join(lines[1:index])), "".join(lines[index + 1:])
    raise ValueError("frontmatter is not terminated by '---'")


def parse(block: str) -> dict:
    """Parse `key: value` lines, `key:` + `  - item` lists and `[a, b]` lists."""
    data: dict = {}
    key: str | None = None
    for number, raw in enumerate(block.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = _ITEM.match(line)
        if item and key is not None and (data[key] is None or isinstance(data[key], list)):
            if data[key] is None:
                data[key] = []
            data[key].append(scalar(item.group(1)))
            continue
        match = _KEY.match(line)
        if match is None:
            raise ValueError(f"line {number}: expected 'key: value', got {raw!r}")
        key, value = match.group(1), (match.group(2) or "").strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [scalar(part) for part in inner.split(",")] if inner else []
        else:
            data[key] = scalar(value) if value else None
    return data


def scalar(value: str):
    value = value.strip()
    if not value:
        return None
    if value[0] in "\"'":
        quote = value[0]
        end = value.rfind(quote)
        if end == 0:
            raise ValueError(f"unterminated string: {value!r}")
        body = value[1:end]
        return json.loads(f'"{body}"') if quote == '"' else body.replace("''", "'")
    value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
    if value in ("null", "~", "Null", "NULL"):
        return None
    if value in ("true", "True", "TRUE"):
        return True
    if value in ("false", "False", "FALSE"):
        return False
    if _INT.fullmatch(value):
        return int(value)
    return value


def dump(meta: dict) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {_format(item)}" for item in value)
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {_format(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def compose(meta: dict, body: str) -> str:
    return dump(meta) + body


def _format(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    reserved = text in ("null", "~", "true", "false", "True", "False") or _INT.fullmatch(text)
    if _PLAIN.fullmatch(text) and not reserved:
        return text
    return json.dumps(text, ensure_ascii=False)
