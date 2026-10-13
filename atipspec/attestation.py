"""Provider-native provenance for CI evidence: GitHub artifact attestations
verified with the `gh` CLI, the way SSH signatures are verified with
`ssh-keygen`. The verifier binary is installed and pinned by the organization;
the candidate checkout never provides it.

`verify_attestation` fails closed: the tool must exist, exit 0, and report a
subject digest equal to the file's SHA-256, attested for the policy's
repository and pull request by the trusted workflow at its pinned commit,
which lives outside the candidate repository. `records_to_attest` is what that
workflow attests: the records this run wrote, and nothing else.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from .errors import AtipSpecError
from .trust import digest, read_regular


def run_tool(arguments: list[str]) -> str:
    """Run the attestation tool and return its stdout; non-zero exit is an error."""
    result = subprocess.run(arguments, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            stdin=subprocess.DEVNULL, timeout=120)
    if result.returncode != 0:
        raise AtipSpecError("attestation verification failed: " + (result.stderr.strip().splitlines() or ["no output"])[-1])
    return result.stdout


def tool_path(policy) -> str:
    config = policy.data.get("attestation") or {}
    tool = str(config.get("tool") or "gh")
    if "/" in tool or "\\" in tool:
        path = Path(tool)
        if not path.is_absolute() or not path.is_file():
            raise AtipSpecError(f"attestation tool must be an absolute path to an installed binary: {tool}")
        return str(path)
    found = shutil.which(tool)
    if not found:
        raise AtipSpecError(f"attestation tool {tool!r} is not installed on this worker")
    return found


def verify_attestation(path: Path, policy) -> dict:
    """Verify the provenance of one file; returns the parsed verification result."""
    config = policy.data.get("attestation") or {}
    workflow, pinned = config.get("signer_workflow"), config.get("signer_digest")
    if not workflow or not pinned:
        raise AtipSpecError("provider mode needs [attestation] signer_workflow and signer_digest in the policy")
    if policy.number is None:
        raise AtipSpecError("provider mode needs the PR number to verify evidence attestations: --number or "
                            "ATIPSPEC_PR_NUMBER")
    expected = digest(read_regular(path))
    arguments = [tool_path(policy), "attestation", "verify", str(path), "--repo", str(policy.data["repository"]),
                 "--signer-workflow", str(workflow), "--signer-digest", str(pinned),
                 "--source-ref", f"refs/pull/{policy.number}/merge", "--format", "json"]
    if config.get("allow_self_hosted_runners") is not True:
        arguments.append("--deny-self-hosted-runners")
    output = run_tool(arguments)
    try:
        results = json.loads(output)
    except ValueError as exc:
        raise AtipSpecError("attestation tool returned no JSON") from exc
    if not isinstance(results, list) or not results:
        raise AtipSpecError("attestation tool returned no verification result")
    for result in results:
        if not isinstance(result, dict):
            continue
        statement = (result.get("verificationResult") or {}).get("statement") or {}
        subjects = statement.get("subject") if isinstance(statement, dict) else None
        for entry in subjects or []:
            if isinstance(entry, dict) and isinstance(entry.get("digest"), dict) \
                    and entry["digest"].get("sha256") == expected:
                return result
    raise AtipSpecError("attestation subject digest does not match the file")


def records_to_attest(project) -> list[Path]:
    """The evidence records the trusted workflow attests, after it cleared the
    committed evidence and took this run's: for each active delivery, exactly
    one record per task the plan verifies (the final verification when there
    is one), valid, passing, written on the checked-out head and tree. Raises
    when a record is missing, failed, stale or invalid, or when evidence/
    holds any other record, so nothing but this run's results is attested."""
    from .assurance import evidence_problems
    from .delivery import load_evidence, parse_plan
    head, tree = project.git.head(), project.fingerprint()
    if head is None or tree is None:
        raise AtipSpecError("git is required: attested evidence binds the head commit and the working tree")
    chosen = []
    for slug in project.list_deliveries():
        directory = project.delivery_dir(slug)
        folder = directory / "evidence"
        if any(path.is_symlink() for path in (folder / "logs", folder, *folder.parents)):
            raise AtipSpecError(f"{slug}: refusing a symlinked evidence folder")
        plan_path = directory / "plan.md"
        plan = parse_plan(read_regular(plan_path).decode("utf-8")) if plan_path.is_file() else None
        tasks = [task for task in (([plan.final] if plan.final else plan.tasks) if plan else []) if task.verify]
        files = sorted(folder.glob("*.json")) if folder.is_dir() else []
        if not tasks:
            if files:
                raise AtipSpecError(f"{slug}: evidence records exist, but its plan verifies no task")
            continue
        evidence, problems = load_evidence(folder)
        if problems:
            raise AtipSpecError(f"{slug}: " + "; ".join(problems))
        expected = {task.id for task in tasks}
        if len(files) != len(evidence) or set(evidence) - expected:
            raise AtipSpecError(f"{slug}: evidence/ holds records this run did not write for its plan; clear "
                                "evidence/ before verifying")
        for task in tasks:
            record = evidence.get(task.id)
            if record is None:
                raise AtipSpecError(f"{slug}: no evidence record for {task.id}")
            problems = evidence_problems(record, task, slug)
            if record.path.is_symlink():
                problems.append("its record is a symlink")
            if record.result != "pass":
                problems.append(f"its result is {record.result}")
            if record.tree != tree:
                problems.append("it was not written on the checked-out tree")
            if record.data.get("head") != head:
                problems.append("it was not written on the checked-out head commit")
            if problems:
                raise AtipSpecError(f"{slug}: cannot attest {task.id}: {'; '.join(problems)}")
            chosen.append(record.path)
    return chosen
