"""A process adapter protocol for coding agents, separate from orchestration.

The configured executable receives one JSON request via stdin and emits one
JSON response. It owns model/tool integration. The core never infers a command
exit status from the model's narrative. Configuration is candidate content and
is included in the approved agreement.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from .errors import AtipSpecError
from .trust import read_regular


@dataclass
class CommandAdapter:
    command: list[str]
    name: str
    isolated_review: bool = False

    @classmethod
    def load(cls, project):
        path = project.dot / "adapter.json"
        if not path.exists():
            raise AtipSpecError("No execution adapter configured. Use the guided skills, or configure .atipspec/adapter.json with the documented process protocol")
        data = json.loads(read_regular(path))
        if not isinstance(data, dict) or data.get("schema") != 1:
            raise AtipSpecError("Adapter configuration needs schema: 1")
        command = data.get("command")
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
            raise AtipSpecError("Adapter command must be a nonempty argv array, not a shell string")
        isolated = data.get("isolated_review", False)
        if not isinstance(isolated, bool):
            raise AtipSpecError("isolated_review must be a boolean capability declaration")
        return cls(command, str(data.get("name") or "command"), isolated)

    def capabilities(self):
        return {"adapter": self.name, "protocol": 1, "process_per_call": True,
                "isolated_review": self.isolated_review, "checkpoints": True,
                "background_service": False, "human_approval": "explicit local command",
                "tokens": None, "cost": None}

    def invoke(self, project, request, timeout):
        if timeout <= 0:
            raise AtipSpecError("Execution budget exhausted")
        started = time.monotonic()
        # Files bound memory consumption even when an adapter writes excessive
        # diagnostics. A fresh process does not imply a fresh model conversation;
        # that is an adapter capability and must be declared honestly.
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            process = subprocess.Popen(self.command, cwd=project.root, stdin=subprocess.PIPE,
                                       stdout=out, stderr=err, start_new_session=os.name == "posix")
            try:
                process.communicate(json.dumps(request, ensure_ascii=False).encode(), timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
                raise
            if process.returncode:
                err.seek(0)
                detail = err.read(4000).decode("utf-8", "replace")
                raise AtipSpecError(f"Adapter exited {process.returncode}: {detail}")
            out.seek(0)
            raw = out.read(1_000_001)
        if len(raw) > 1_000_000:
            raise AtipSpecError("Adapter response exceeds 1 MB")
        try:
            response = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise AtipSpecError("Adapter must return one JSON response") from exc
        if (not isinstance(response, dict) or response.get("schema") != 1
                or response.get("status") not in ("done", "needs_decision", "blocked", "failed")
                or not isinstance(response.get("summary"), str) or not response["summary"].strip()):
            raise AtipSpecError("Invalid adapter response: schema, status and nonempty summary are required")
        response["duration_s"] = round(time.monotonic() - started, 3)
        return response
