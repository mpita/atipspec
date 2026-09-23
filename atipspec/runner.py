"""Deterministic, resumable delivery execution after explicit proposal approval.

The adapter performs bounded creative work. This module owns state transitions,
verification, retry budgets and result readiness; it never approves, commits or
publishes. Interrupted agent mutations are surfaced rather than replayed blindly.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import json
import os
import subprocess
import time

from .accept import is_current
from .adapter import CommandAdapter
from .check import check_delivery
from .context import build_context, render_context
from .delivery import parse_plan, parse_review
from .errors import AtipSpecError
from .progress import mark_done
from .roles import active_roles, role_instruction
from .specs import load_spec
from .trust import read_regular, subject, timestamp


STATES = ("draft", "awaiting_approval", "approved", "running", "ready_for_acceptance",
          "accepted", "needs_decision", "blocked", "failed")


def read_state(project, slug):
    path = project.delivery_dir(slug) / "run.json"
    if not path.exists():
        return {"schema": 1, "delivery": slug, "status": "draft", "elapsed_s": 0, "rounds": 0}
    try:
        data = json.loads(read_regular(path))
        if (not isinstance(data, dict) or data.get("schema") != 1 or data.get("delivery") != slug
                or data.get("status") not in STATES or not isinstance(data.get("elapsed_s"), (int, float))
                or data["elapsed_s"] < 0 or not isinstance(data.get("rounds"), int) or data["rounds"] < 0):
            raise ValueError("invalid checkpoint schema")
        return data
    except (ValueError, TypeError) as exc:
        raise AtipSpecError(f"Invalid runner checkpoint: {exc}") from exc


def _write(project, slug, state):
    path = project.delivery_dir(slug) / "run.json"
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AtipSpecError("Refusing a symlinked checkpoint")
    temporary = path.with_suffix(".json.tmp")
    if temporary.is_symlink():
        raise AtipSpecError("Refusing a symlinked checkpoint temporary path")
    temporary.write_text(json.dumps({**state, "updated_at": timestamp()}, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


@contextmanager
def _lock(project):
    """One writer for this checkout. The OS releases the lock on process exit."""
    if os.name != "posix":
        raise AtipSpecError("The process runner currently supports POSIX locks; use guided mode on this platform")
    import fcntl
    project.tmp.mkdir(parents=True, exist_ok=True)
    path = project.tmp / "runner.lock"
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AtipSpecError("Refusing a symlinked runner lock")
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AtipSpecError("Another runner owns this checkout; use an independent worktree for parallel work") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_delivery(project, slug, *, resume=False, retry_interrupted=False, budget=900, timeout=300, max_rounds=2):
    if budget <= 0 or timeout <= 0 or max_rounds < 0:
        raise AtipSpecError("Budget and timeout must be positive; max-rounds cannot be negative")
    from .trust import selected_policy
    if selected_policy(project):
        raise AtipSpecError("This runner uses local proposal approval; use the organization's protected workflow with an external trust policy")
    spec = load_spec(project, slug)
    if spec.meta.get("schema") != 2:
        raise AtipSpecError("The resumable runner needs a guided delivery; legacy deliveries retain their phase workflow")
    with _lock(project):
        state = read_state(project, slug)
        if not is_current(project, slug, "proposal"):
            state.update(status="awaiting_approval", reason="Present and approve the current proposal before execution")
            _write(project, slug, state)
            return state
        adapter = CommandAdapter.load(project)
        agreement = subject(project, slug, "plan")
        if state.get("agreement") != agreement:
            # A newly approved version starts a new execution budget. Old
            # completion records remain on disk but are not valid for it.
            state = {"schema": 1, "delivery": slug, "status": "approved", "elapsed_s": 0,
                     "rounds": 0, "agreement": agreement}
        elif state["status"] in ("running", "needs_decision") and state.get("phase"):
            if not retry_interrupted:
                state.update(status="needs_decision", reason=f"Interrupted during {state['phase']}; inspect the candidate before explicitly retrying with --retry-interrupted")
                _write(project, slug, state)
                return state
        elif state["status"] in ("needs_decision", "blocked", "failed") and not (resume or retry_interrupted):
            return state
        risk = str(spec.meta.get("risk") or "normal")
        state.update(capabilities=adapter.capabilities(), roles=active_roles(risk))
        started = time.monotonic()
        previous_elapsed = state["elapsed_s"]

        def save(status, reason, **extra):
            state.update(status=status, reason=reason, elapsed_s=round(previous_elapsed + time.monotonic() - started, 3), **extra)
            _write(project, slug, state)
            return state

        def remaining():
            return budget - previous_elapsed - (time.monotonic() - started)

        def invoke(role, task=None, findings=None):
            save("running", f"Executing {role}", phase=role, task=task.id if task else None)
            if remaining() <= 0:
                raise AtipSpecError("Execution time budget exhausted")
            sections, _ = build_context(project, slug, role=role, task_id=task.id if task else None)
            request = {"schema": 1, "delivery": slug, "role": role, "risk": risk,
                       "instruction": role_instruction(role, risk), "agreement": agreement,
                       "context": render_context(sections), "task": asdict(task) if task else None,
                       "findings": findings or [], "permissions": {"commit": False, "push": False,
                       "merge": False, "deploy": False, "human_approval": False}}
            if role == "reviewer":
                from .review import build_packet
                request["review_packet"] = build_packet(project, slug)
                request["context"] = "See the versioned references in review_packet."
                request["response_contract"] = "Return schema:1, status:done, summary and review_markdown. Do not modify files."
            else:
                request["response_contract"] = "Return schema:1, status:done|needs_decision|blocked|failed, and a nonempty summary."
            before = project.fingerprint()
            head = project.git.head()
            response = adapter.invoke(project, request, min(timeout, remaining()))
            if project.git.head() != head:
                raise AtipSpecError("Adapter changed Git HEAD despite the no-commit policy; inspect the repository")
            if subject(project, slug, "plan") != agreement:
                return save("needs_decision", "The approved agreement changed during execution; inspect and approve its diff", phase=None)
            if role == "reviewer" and project.fingerprint() != before:
                raise AtipSpecError("Reviewer modified the candidate; verification and review must be repeated")
            if response["status"] != "done":
                return save(response["status"], response["summary"], phase=None)
            if role == "reviewer":
                text = response.get("review_markdown")
                if not isinstance(text, str):
                    raise AtipSpecError("Reviewer response is missing review_markdown")
                review = parse_review(text)
                if review.problems or review.tree != before:
                    raise AtipSpecError("Reviewer returned malformed or stale review content")
                target = project.delivery_dir(slug) / "review.md"
                if target.is_symlink():
                    raise AtipSpecError("Refusing a symlinked review")
                target.write_text(text, encoding="utf-8")
            elif task:
                mark_done(project, slug, task.id, response["summary"])
            save("running", response["summary"], phase=None)
            return None

        try:
            plan = parse_plan((project.delivery_dir(slug) / "plan.md").read_text())
            report = check_delivery(project, slug)
            invalid = report.blocking(("spec", "plan", "contract", "base", "coordination"))
            if invalid:
                return save("needs_decision", invalid[0].text, phase=None)
            if report.status == "accepted":
                return save("accepted", "The human has accepted the current result", phase=None)
            from .progress import completed_tasks
            while True:
                plan = parse_plan((project.delivery_dir(slug) / "plan.md").read_text())
                completed = completed_tasks(project, slug, plan)
                task = next((task for task in plan.tasks if task.id not in completed), None)
                if task is None:
                    break
                stop = invoke("implementer", task)
                if stop:
                    return stop
            while True:
                if remaining() <= 0:
                    return save("blocked", "Execution time budget exhausted", phase=None)
                report = check_delivery(project, slug)
                if report.blocking(("coordination",)):
                    return save("needs_decision", report.blocking(("coordination",))[0].text, phase=None)
                if report.blocking(("evidence",)):
                    from .verify import verify_delivery
                    save("running", "Verifying the finished candidate", phase="verification")
                    verify_delivery(project, slug, timeout=min(timeout, max(1, int(remaining()))), budget_seconds=remaining())
                    save("running", "Verification finished", phase=None)
                    report = check_delivery(project, slug)
                defects = report.blocking(("violation", "evidence", "deferred"))
                if not defects and report.blocking(("review",)):
                    stop = invoke("reviewer")
                    if stop:
                        return stop
                    report = check_delivery(project, slug)
                if report.ok:
                    return save("ready_for_acceptance", f"Present `atipspec report {slug}` and the result to the human", phase=None)
                if report.blocking(("integration",)) and not report.blocking(("violation", "evidence", "review", "tasks", "deferred")):
                    return save("blocked", report.blocking(("integration",))[0].text, phase=None)
                if state["rounds"] >= max_rounds:
                    return save("blocked", "Correction budget exhausted: " + report.next_action, phase=None)
                before = project.fingerprint()
                state["rounds"] += 1
                findings = [asdict(item) for item in report.items if item.level in ("error", "todo")]
                stop = invoke("implementer", findings=findings)
                if stop:
                    return stop
                if project.fingerprint() == before:
                    return save("blocked", "Correction made no candidate progress; inspect the remaining findings", phase=None)
        except KeyboardInterrupt:
            save("needs_decision", "Execution interrupted; inspect the last phase before retrying")
            raise
        except subprocess.TimeoutExpired:
            return save("needs_decision", "Adapter timed out; inspect partial work before retrying with --retry-interrupted")
        except (AtipSpecError, OSError, ValueError) as exc:
            return save("failed", str(exc), phase=None)
