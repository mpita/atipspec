"""Run the Verify commands of a plan and write local evidence. Protected CI signs it separately.

Each evidence file records the commands, their exit codes, output tails and the
working-tree fingerprint they ran against. `atipspec check` accepts evidence
only while that fingerprint matches the current tree.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import platform
import uuid
from . import __version__
from pathlib import Path
import subprocess
import signal
import time

from .delivery import parse_plan
from .errors import AtipSpecError
from .project import Project
from .trust import digest

TAIL_LINES = 40
TAIL_CHARS = 4000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tail(text: str) -> str:
    lines = text.splitlines()[-TAIL_LINES:]
    return "\n".join(lines)[-TAIL_CHARS:]


def run_command(command: str, cwd: Path, timeout: int) -> dict:
    started = time.monotonic()
    process = subprocess.Popen(command, shell=True, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               errors="replace", start_new_session=os.name == "posix",
                               env={k: v for k, v in os.environ.items()
                                    if k not in ("GITHUB_TOKEN", "GH_TOKEN", "GITLAB_TOKEN")
                                    and not k.startswith("ATIPSPEC_")})
    try:
        output, _ = process.communicate(timeout=timeout)
        exit_code = process.returncode
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        output, _ = process.communicate()
        if isinstance(exc, KeyboardInterrupt):
            raise
        exit_code = None
        output += f"\n[atipspec] timed out after {timeout}s"
    return {"command": command, "exit_code": exit_code, "duration_s": round(time.monotonic() - started, 2),
            "output_tail": _tail(output), "_output": output}


def verify_delivery(project: Project, slug: str, tasks: list[str] | None = None, timeout: int = 1800,
                    *, budget_seconds: float | None = None) -> int:
    if timeout <= 0:
        raise AtipSpecError("timeout must be positive")
    directory = project.delivery_dir(slug)
    plan_path = directory / "plan.md"
    if not plan_path.is_file():
        raise AtipSpecError(f"{project.rel(plan_path)} not found; write the plan first.")
    plan = parse_plan(plan_path.read_text(encoding="utf-8"))
    if plan.problems:
        raise AtipSpecError("; ".join(plan.problems))
    if not plan.tasks:
        raise AtipSpecError("plan.md has no tasks (headings like `### T1: Title`).")
    if not project.git.available:
        raise AtipSpecError("git is required: evidence is bound to the working tree hash.")
    selected = plan.tasks
    if plan.final is not None and not tasks:
        selected = [plan.final]
    if tasks:
        known = {task.id: task for task in plan.tasks}
        missing = [ident for ident in tasks if ident not in known]
        if missing:
            raise AtipSpecError(f"Unknown task(s): {', '.join(missing)}")
        selected = [known[ident] for ident in tasks]
    evidence_dir = directory / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    failed = 0
    deadline = time.monotonic() + budget_seconds if budget_seconds is not None else None
    for task in selected:
        if not task.verify:
            print(f"{task.id}: no Verify commands, nothing to run")
            continue
        tree_before = project.fingerprint()
        started = _now()
        records = []
        execution = uuid.uuid4().hex
        logs = evidence_dir / "logs"
        if logs.is_symlink():
            raise AtipSpecError("Evidence logs directory must not be a symlink")
        logs.mkdir(exist_ok=True)
        for index, command in enumerate(task.verify, 1):
            print(f"[{task.id}] $ {command}")
            remaining = deadline - time.monotonic() if deadline is not None else timeout
            if remaining <= 0:
                raise AtipSpecError("Final verification exceeded the execution time budget; partial results cannot count as a pass")
            record = run_command(command, project.root, min(timeout, remaining))
            output = record.pop("_output").encode("utf-8")
            log = logs / f"{task.id}-{execution}-{index}.log"
            log.write_bytes(output)
            record["output_path"] = str(log.relative_to(evidence_dir))
            record["output_sha256"] = digest(output)
            records.append(record)
            for line in record["output_tail"].splitlines():
                print(f"    {line}")
            state = "ok" if record["exit_code"] == 0 else f"exit {record['exit_code']}"
            print(f"[{task.id}] {state} ({record['duration_s']}s)")
        result = "pass" if all(record["exit_code"] == 0 for record in records) else "fail"
        reports, tests = [], []
        if task.report:
            from .junit import read_report
            source = project.root / task.report
            try:
                relative = Path(task.report)
                if relative.is_absolute() or ".." in relative.parts:
                    raise AtipSpecError(f"test report must be a relative path inside the project: {task.report}")
                if any(part.is_symlink() for part in (source, *source.parents)) or (source.exists() and not source.is_file()):
                    raise AtipSpecError(f"test report must be a regular file inside the project: {task.report}")
                if not source.resolve().is_relative_to(project.root.resolve()):
                    raise AtipSpecError(f"test report must be inside the project: {task.report}")
                cases = read_report(source)
                raw = source.read_bytes()
            except AtipSpecError as exc:
                print(f"[{task.id}] {exc}")
                result = "fail"
                reports.append({"path": task.report, "error": str(exc)})
            else:
                copy = logs / f"{task.id}-{execution}-report.xml"
                copy.write_bytes(raw)
                reports.append({"path": task.report, "copy": str(copy.relative_to(evidence_dir)), "sha256": digest(raw),
                                "total": len(cases), "failed": sum(1 for case in cases if case["status"] == "failed")})
                tests = [{"id": case["id"], "name": case["name"], "classname": case["classname"], "status": case["status"]}
                         for case in cases]
                if any(case["status"] == "failed" for case in cases):
                    result = "fail"
                print(f"[{task.id}] report {task.report}: {len(cases)} test(s), "
                      f"{sum(1 for case in cases if case['status'] == 'failed')} failed")
        tree_after = project.fingerprint()
        stamp = started.replace(":", "").replace("-", "")
        path = evidence_dir / f"{task.id}-{stamp}-{uuid.uuid4().hex[:8]}.json"
        payload = {"schema": 1, "environment": {"python": platform.python_version(),
                   "platform": platform.platform(), "atipspec": __version__}, "delivery": slug, "task": task.id, "result": result, "tree": tree_before,
                   "tree_after": tree_after, "head": project.git.head(), "started": started,
                   "finished": _now(), "commands": records}
        if task.report:
            payload["reports"] = reports
            payload["tests"] = tests
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{task.id}: {result} -> {project.rel(path)}")
        if tree_after != tree_before:
            print(f"{task.id}: the commands modified the working tree, so this evidence is already stale; "
                  "inspect the changes and verify the finished candidate again")
        if result != "pass" or tree_after != tree_before:
            failed += 1
    return 1 if failed else 0
