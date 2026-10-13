"""Run the Verify commands of a plan and write local evidence. Protected CI signs it separately.

Each evidence file records the commands, their exit codes, output tails and the
working-tree fingerprint they ran against. `atipspec check` accepts evidence
only while that fingerprint matches the current tree. A task's JUnit Report is
deleted before its commands run and counts only when they write it again.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import platform
import shutil
import uuid
from . import __version__
from pathlib import Path
import subprocess
import signal
import time

from .delivery import leaves_project, parse_plan
from .errors import AtipSpecError
from .project import Project
from .trust import digest, text_bytes

TAIL_LINES = 40
TAIL_CHARS = 4000
MTIME_TOLERANCE = 2   # seconds: file systems that store coarse modification times


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tail(text: str) -> str:
    lines = text.splitlines()[-TAIL_LINES:]
    return "\n".join(lines)[-TAIL_CHARS:]


# Credentials the candidate's commands never get: provider tokens, an approver's SSH agent (it signs with
# the enrolled key), CI job and OIDC tokens, and credential helpers; every ATIPSPEC_ variable too.
WITHHELD = ("GITHUB_TOKEN", "GH_TOKEN", "GITLAB_TOKEN", "SSH_AUTH_SOCK", "SSH_AGENT_PID", "SSH_ASKPASS",
            "GIT_ASKPASS", "CI_JOB_TOKEN", "CI_JOB_JWT", "CI_JOB_JWT_V2", "CI_REGISTRY_PASSWORD",
            "CI_DEPLOY_PASSWORD", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
            "ACTIONS_ID_TOKEN_REQUEST_URL")


# Files that configure how a test runner runs and reports: a change in them can change what the
# evidence says without changing the code under test, so the packet and the dossier name them.
HARNESS = ("conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml", "noxfile.py", "package.json",
           "jest.config.*", "vitest.config.*", "karma.conf.*", ".mocharc.*", "playwright.config.*", "phpunit.xml*")


def harness_files(paths) -> list[str]:
    from fnmatch import fnmatchcase
    return sorted(path for path in paths if any(fnmatchcase(path.rsplit("/", 1)[-1], name) for name in HARNESS))


def command_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items()
            if key.upper() not in WITHHELD and not key.upper().startswith("ATIPSPEC_")}


def run_command(command: str, cwd: Path, timeout: int) -> dict:
    started = time.monotonic()
    process = subprocess.Popen(command, shell=True, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace", start_new_session=os.name == "posix",
                               env=command_environment())
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


def report_path_problem(project: Project, report: str) -> str | None:
    """Why a plan's Report path cannot hold this run's results, or None: it
    must be a regular file inside the project, reached through no symlink, at
    a path git ignores, so it never changes the tree the evidence binds and no
    committed copy can stand in for a run."""
    source = project.root / report
    if leaves_project(report):
        return f"test report must be a relative path inside the project: {report}"
    if any(part.is_symlink() for part in (source, *source.parents)) or (source.exists() and not source.is_file()):
        return f"test report must be a regular file inside the project: {report}"
    if not source.resolve().is_relative_to(project.root.resolve()):
        return f"test report must be inside the project: {report}"
    if project.git.tracks(report):
        return (f"test report {report} is tracked by git, so a committed copy could stand in for a run: remove it "
                f"from the index with `git rm --cached {report}`, keeping the path git ignores")
    if not project.git.ignored(report):
        return (f"test report {report} must be a path git ignores, such as .atipspec/tmp/junit.xml: verify deletes "
                "it before the commands run")
    return None


def clear_evidence(project: Project) -> list[str]:
    """Delete the evidence/ folder of every active delivery, so only records a
    run writes next can be attested: the trusted evidence workflow runs it
    before verifying and before taking that run's records, the protected worker
    before downloading them. Returns the deliveries it cleared."""
    cleared = []
    for slug in project.list_deliveries():
        folder = project.delivery_dir(slug) / "evidence"
        if any(part.is_symlink() for part in (folder, *folder.parents)):
            raise AtipSpecError(f"Refusing a symlinked evidence folder: {project.rel(folder)}")
        if folder.is_dir():
            shutil.rmtree(folder)
        elif folder.exists():
            folder.unlink()
        else:
            continue
        cleared.append(slug)
    return cleared


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
        report_problem = report_path_problem(project, task.report) if task.report else None
        if task.report and report_problem is None:
            # Only a report these commands write counts: a file left by an
            # earlier run, or planted, must not pass for this run's results.
            (project.root / task.report).unlink(missing_ok=True)
        cleared = time.time()
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
            record["output_path"] = log.relative_to(evidence_dir).as_posix()
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
                # Checked again: the commands could have left a link in its place.
                problem = report_problem or report_path_problem(project, task.report)
                if problem:
                    raise AtipSpecError(problem)
                cases = read_report(source)
                if source.stat().st_mtime < cleared - MTIME_TOLERANCE:
                    raise AtipSpecError(f"test report {task.report} predates this verification; the Verify "
                                        "commands must write it")
                raw = source.read_bytes()
            except AtipSpecError as exc:
                print(f"[{task.id}] {exc}")
                result = "fail"
                reports.append({"path": task.report, "error": str(exc)})
            else:
                copy = logs / f"{task.id}-{execution}-report.xml"
                copy.write_bytes(raw)
                reports.append({"path": task.report, "copy": copy.relative_to(evidence_dir).as_posix(),
                                "sha256": digest(text_bytes(copy)), "total": len(cases),
                                "failed": sum(1 for case in cases if case["status"] == "failed"),
                                "fresh": True})
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
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"{task.id}: {result} -> {project.rel(path)}")
        if tree_after != tree_before:
            print(f"{task.id}: the commands modified the working tree, so this evidence is already stale; "
                  "inspect the changes and verify the finished candidate again")
        if result != "pass" or tree_after != tree_before:
            failed += 1
    return 1 if failed else 0
