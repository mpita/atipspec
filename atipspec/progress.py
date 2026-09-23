"""Operational completion records, independent of a repository's commit policy.

These are agent declarations, never proof of quality or human approval. The
gate checks verification and review independently. Plan/spec drift invalidates
the declarations; execution checkpoints will build on this representation.
"""
from __future__ import annotations

from dataclasses import asdict
import json

from .delivery import parse_plan
from .errors import AtipSpecError
from .trust import canonical, digest, read_regular, subject, timestamp


def _task_digest(task):
    data = asdict(task)
    data.pop("line", None)
    return digest(canonical(data))


def _read(project, slug):
    path = project.delivery_dir(slug) / "progress.json"
    if not path.exists():
        return {"schema": 1, "delivery": slug, "tasks": {}}
    try:
        data = json.loads(read_regular(path))
        if (not isinstance(data, dict) or data.get("schema") != 1
                or data.get("delivery") != slug or not isinstance(data.get("tasks"), dict)):
            raise ValueError("invalid progress schema")
        return data
    except (ValueError, TypeError) as exc:
        raise AtipSpecError(f"Invalid task progress: {exc}") from exc


def completed_tasks(project, slug, plan):
    data = _read(project, slug)
    if not data["tasks"]:
        return set()
    current = subject(project, slug, "plan")
    return {task.id for task in plan.tasks
            if isinstance(record := data["tasks"].get(task.id), dict)
            and record.get("subject") == current and record.get("task_digest") == _task_digest(task)
            and record.get("note")}


def mark_done(project, slug, task_id, note):
    if not note.strip():
        raise AtipSpecError("Task completion needs a summary of the implementation")
    from .check import check_delivery
    report = check_delivery(project, slug)
    blocking = report.blocking(("spec", "plan", "contract", "base", "coordination"))
    if blocking:
        raise AtipSpecError("Cannot complete a task before approval: " + blocking[0].text)
    directory = project.delivery_dir(slug)
    plan = parse_plan((directory / "plan.md").read_text())
    task = next((task for task in plan.tasks if task.id == task_id), None)
    if task is None:
        raise AtipSpecError(f"Unknown task: {task_id}")
    data = _read(project, slug)
    data["tasks"][task_id] = {"note": note.strip(), "completed_at": timestamp(),
                              "subject": subject(project, slug, "plan"), "task_digest": _task_digest(task)}
    path = directory / "progress.json"
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AtipSpecError("Refusing a symlinked progress path")
    temporary = path.with_suffix(".json.tmp")
    if temporary.is_symlink():
        raise AtipSpecError("Refusing a symlinked progress temporary path")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)
    return path
