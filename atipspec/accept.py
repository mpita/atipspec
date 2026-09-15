"""Local acceptance: a person records that they accept the spec, the plan or
the contract, and the gate detects any later change.

This is drift detection, not authentication: the record binds the accepted
content by hash, so an edit after acceptance is visible, but nothing proves who
ran the command. Trusted acceptance (signed approvals under an external policy)
is the authenticated form; the gate ignores these records when a policy is set.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from . import frontmatter
from .delivery import parse_plan, parse_spec
from .errors import AtipSpecError
from .project import Project
from .trust import subject

PHASES = ("spec", "plan")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def record_path(project: Project, slug: str, phase: str) -> Path:
    return project.delivery_dir(slug, must_exist=False) / "approvals" / f"local-{phase}.json"


def read_record(project: Project, slug: str, phase: str) -> dict | None:
    path = record_path(project, slug, phase)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("kind") != "local-acceptance" or data.get("phase") != phase:
        return None
    return data


def is_current(project: Project, slug: str, phase: str) -> bool:
    """Whether the accepted content is the content on disk right now."""
    data = read_record(project, slug, phase)
    if data is None:
        return False
    try:
        return data.get("subject") == subject(project, slug, phase)
    except (OSError, AtipSpecError):
        return False


def who(project: Project, by: str | None) -> str:
    if by:
        return by
    if project.git.available:
        # The identity git itself would sign a commit with: config or environment.
        try:
            ident = project.git.run("var", "GIT_AUTHOR_IDENT").strip()
            start, end = ident.find("<"), ident.find(">")
            if 0 <= start < end:
                return ident[start + 1:end] or "unknown"
        except AtipSpecError:
            pass
    return "unknown"


def _set_status(path: Path, status: str) -> None:
    meta, body = frontmatter.split(path.read_text(encoding="utf-8"))
    meta["status"] = status
    path.write_text(frontmatter.compose(meta, body), encoding="utf-8")


def _write(project: Project, slug: str, phase: str, by: str | None) -> Path:
    path = record_path(project, slug, phase)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AtipSpecError("Refusing a symlinked acceptance path")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"schema": 1, "kind": "local-acceptance", "delivery": slug, "phase": phase,
            "subject": subject(project, slug, phase), "accepted_at": _now(), "by": who(project, by),
            "head": project.git.head()}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def accept_spec(project: Project, slug: str, by: str | None = None) -> Path:
    """Set the spec ready when it is complete, and record its content."""
    path = project.delivery_dir(slug) / "spec.md"
    spec = parse_spec(path.read_text(encoding="utf-8"))
    problems = list(spec.problems)
    if not spec.requirements:
        problems.append("the spec has no requirements")
    problems += [f"{req.id} has no acceptance criteria" for req in spec.requirements if not req.criteria and not req.remove]
    if spec.open_questions:
        problems.append(f"{len(spec.open_questions)} open question(s) remain")
    if spec.status not in ("draft", "ready"):
        problems.append(f"spec status is {spec.status!r}")
    from .check import check_delivery
    problems += [item.text for item in check_delivery(project, slug).blocking(("spec",)) if item.level == "error"]
    if problems:
        raise AtipSpecError("Cannot accept the spec yet: " + "; ".join(dict.fromkeys(problems)))
    if spec.status == "draft":
        _set_status(path, "ready")
    return _write(project, slug, "spec", by)


def accept_plan(project: Project, slug: str, by: str | None = None) -> Path:
    """Record the plan's content; the spec must be accepted first."""
    if not is_current(project, slug, "spec"):
        raise AtipSpecError("Accept the spec first: `atipspec accept %s spec`" % slug)
    path = project.delivery_dir(slug) / "plan.md"
    plan = parse_plan(path.read_text(encoding="utf-8")) if path.is_file() else None
    if plan is None or not plan.tasks:
        raise AtipSpecError("Cannot accept the plan: plan.md has no tasks")
    from .check import check_delivery
    report = check_delivery(project, slug)
    blocking = [item.text for item in report.blocking(("plan", "contract")) if item.level == "error"]
    if plan.problems or blocking:
        raise AtipSpecError("Cannot accept the plan yet: " + "; ".join(plan.problems + blocking))
    return _write(project, slug, "plan", by)


def accept_contract(project: Project) -> Path:
    """The person accepts the architecture contract: its status becomes accepted."""
    if not project.contract.is_file():
        raise AtipSpecError("There is no .atipspec/contract.md to accept; run the contract phase first")
    from .check import load_contract
    contract = load_contract(project)
    if contract.problems:
        raise AtipSpecError("Cannot accept the contract: " + "; ".join(contract.problems))
    _set_status(project.contract, "accepted")
    return project.contract


def describe(project: Project, slug: str) -> list[str]:
    """One line per phase accepted for its current content, for status."""
    lines = []
    for phase in PHASES:
        data = read_record(project, slug, phase)
        if data is None:
            continue
        state = "current" if is_current(project, slug, phase) else "outdated: the content changed"
        lines.append(f"{phase} accepted by {data.get('by')} at {data.get('accepted_at')} ({state})")
    return lines
