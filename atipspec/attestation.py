"""Provider-native provenance for CI evidence: GitHub artifact attestations
verified with the `gh` CLI, the way SSH signatures are verified with
`ssh-keygen`. The verifier binary is installed and pinned by the organization;
the candidate checkout never provides it.

`verify_attestation` fails closed: the tool must exist, exit 0, and report a
subject digest equal to the file's SHA-256 for the configured owner and
signer workflow.
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
    result = subprocess.run(arguments, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
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
    owner, workflow = config.get("owner"), config.get("signer_workflow")
    if not owner or not workflow:
        raise AtipSpecError("provider mode needs [attestation] owner and signer_workflow in the policy")
    expected = digest(read_regular(path))
    output = run_tool([tool_path(policy), "attestation", "verify", str(path), "--owner", str(owner),
                       "--signer-workflow", str(workflow), "--format", "json"])
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
