"""Risk levels and what each one changes in the gate and the review.

`risk` lives in spec.md, whose frontmatter the proposal's approval hashes: the
human approves the level with the proposal, and changing it voids that
approval. A delivery without one, legacy deliveries included, is normal.
"""
from __future__ import annotations

LEVELS = ("low", "normal", "high")

EFFECTS = {
    "low": ("a criterion under Tests whose test named in Proof passed in the current evidence needs no reviewer "
            "verdict",
            "removing a requirement or changing the architecture contract is an error"),
    "normal": ("every criterion needs a reviewer verdict",),
    "high": ("plan.md declares a scope and a file outside it is an error",
             "every criterion under Tests names its test in Proof, with a Report",
             "the review comes from an isolated session (`session: isolated`)"),
}


def level(spec) -> str | None:
    """The delivery's risk level: `normal` when spec.md sets none, None when
    the value is not a level."""
    value = spec.meta.get("risk")
    if value is None or value == "":
        return "normal"
    return value if isinstance(value, str) and value in LEVELS else None


def describe(value: str) -> str:
    """`risk <level>: <what the gate asks>`, as check and the review packet show it."""
    return f"risk {value}: " + "; ".join(EFFECTS[value])
