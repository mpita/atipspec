"""Temporary git projects for tests, isolated from the user's git configuration."""
from __future__ import annotations

import atexit
import contextlib
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from atipspec.accept import AGENT_MARKERS, approval_code, contract_code
from atipspec.cli import main
from atipspec.errors import AtipSpecError
from atipspec.project import Project

GIT = shutil.which("git")
# Scripts and command shims the tests run, outside every test repository.
SUPPORT = Path(tempfile.mkdtemp(prefix="atipspec-test-support-")).resolve()
atexit.register(shutil.rmtree, SUPPORT, True)
if os.name == "nt":
    # cmd.exe runs the Verify commands there, and has no true, false or python3.
    for name, body in (("true", "@exit /b 0"), ("false", "@exit /b 1"), ("python3", f'@"{sys.executable}" %*')):
        (SUPPORT / f"{name}.cmd").write_text(body + "\n", encoding="utf-8")


def remove_tree(path: Path) -> None:
    """shutil.rmtree that also removes read-only files: git leaves its objects
    read-only, and Windows refuses to delete those."""
    def writable(function, name, _):
        os.chmod(name, stat.S_IWRITE)
        function(name)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=writable)
    else:
        shutil.rmtree(path, onerror=writable)


def python_command(code: str) -> str:
    """A Verify command that runs `code` with python3 the same way under sh and
    cmd.exe, whose quoting differs: the script lives outside the repository,
    so it adds nothing to the tree."""
    path = SUPPORT / f"script-{hashlib.sha256(code.encode('utf-8')).hexdigest()[:16]}.py"
    path.write_text(code, encoding="utf-8")
    return f'python3 "{path}"'


def junit_command(xml: str, age: int = 0) -> str:
    """A Verify command that writes `xml` to .atipspec/tmp/junit.xml, dated `age` seconds ago."""
    return python_command("import os, time\nos.makedirs('.atipspec/tmp', exist_ok=True)\n"
                          f"path = '.atipspec/tmp/junit.xml'\nopen(path, 'w', encoding='utf-8').write({xml!r})\n"
                          + (f"stamp = time.time() - {age}\nos.utime(path, (stamp, stamp))\n" if age else ""))
INTENT = "A user who forgot the password requests a link by email and sets a new password with it."

SPEC = """---
title: "Password reset"
status: {status}
capability: auth
impact: {impact}
base: {base}
created: 2026-09-12
---

# Password reset

## Intent

Let a user recover access to their account.

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Acceptance criteria:
- AC-001: When a registered email requests a reset, the system sends a link to that email.
- AC-002: When an unknown email requests a reset, the system responds like a valid one.

### REQ-002: The link expires

Acceptance criteria:
- AC-003: If a link is older than 30 minutes, then the system returns "link expired".

## Out of scope

- Password policy changes.

## Open questions

- {question}
"""

PLAN = """---
title: "Password reset"
scope: ["*", "src/**"]
---

# Plan: Password reset

## Approach

One module.

## Tasks

### T1: Request link

Covers: REQ-001
Tests: AC-001, AC-002
Verify:
- `{command1}`

### T2: Expiry

Covers: REQ-002
Tests: AC-003
Verify:
- `{command2}`
"""

REVIEW = """---
tree: {tree}
reviewer: test
session: isolated
---

# Review: Password reset

## Criteria

- AC-001: {v1}. README.md:1
- AC-002: {v2}. README.md:1
- AC-003: {v3}. README.md:1

## Findings

{findings}
"""


class ProjectCase(unittest.TestCase):
    """A temporary git repository with AtipSpec initialized for the claude client."""

    def setUp(self):
        if GIT is None:
            self.skipTest("git is not installed")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        config = self.root / ".gitconfig-tests"
        # Git for Windows' default on every platform: text is committed with LF, whatever line endings the
        # platform writes, and checked out with CRLF.
        config.write_text("[core]\n\tautocrlf = true\n\tsafecrlf = false\n", encoding="utf-8", newline="\n")
        # Without agent markers, so the approval channel does not depend on who runs the tests.
        markers = {name for name, _ in AGENT_MARKERS} | {"CLAUDE_CODE_ENTRYPOINT"}
        self.env = {**{key: value for key, value in os.environ.items() if key not in markers},
                    "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t"}
        if os.name == "nt":
            self.env["PATH"] = f"{SUPPORT}{os.pathsep}{self.env.get('PATH', '')}"
        self.enterContext(patch.dict(os.environ, self.env, clear=True))
        self.enterContext(contextlib.chdir(self.root))
        self.enterContext(patch("builtins.input", side_effect=AssertionError("unexpected prompt")))
        self.enterContext(patch("atipspec.ui.interactive", return_value=False))
        self.git("init", "-q", "-b", "main", ".")
        (self.root / ".gitignore").write_text(".gitconfig-tests\n")
        (self.root / "README.md").write_text("# demo\n")
        self.commit("init")
        self.run_cli("init", "--client", "claude", "--name", "Demo", "--language", "es")

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=self.root, text=True, encoding="utf-8", env=self.env)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        """Run the CLI in process, as the installed `atipspec` command would."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                patch.object(sys, "argv", ["atipspec", *args]), \
                patch.object(sys, "orig_argv", [sys.executable, "atipspec", *args]):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def delivery(self, slug: str = "password-reset") -> Path:
        return self.root / ".atipspec" / "deliveries" / slug

    def write_spec(self, status: str = "ready", question: str = "None", slug: str = "password-reset",
                   impact: str = "[]", accept: bool = True) -> None:
        """Write the spec; a ready spec is also accepted, as the person would."""
        base = self.git("rev-parse", "HEAD").strip()
        (self.delivery(slug) / "spec.md").write_text(SPEC.format(status=status, base=base, question=question,
                                                                  impact=impact))
        if status == "ready" and accept:
            self.accept(slug, "spec")

    def write_plan(self, command1: str = "true", command2: str = "true", slug: str = "password-reset",
                   accept: bool = True) -> None:
        (self.delivery(slug) / "plan.md").write_text(PLAN.format(command1=command1, command2=command2))
        if accept:
            self.accept(slug, "plan")

    def code(self, slug: str = "password-reset", phase: str = "spec") -> str:
        """The approval code `proposal` or `report` would show for this content."""
        try:
            return approval_code(Project.find(self.root), slug, phase)
        except (AtipSpecError, OSError):
            return "0000-0000"

    def accept(self, slug: str = "password-reset", phase: str = "spec", by: str = "tester") -> tuple[int, str, str]:
        """Record an approval as the assistant does after the human approved the presented content."""
        return self.run_cli("accept", slug, phase, "--by", by, "--code", self.code(slug, phase))

    def accept_contract(self, by: str = "tester") -> tuple[int, str, str]:
        return self.run_cli("accept", "contract", "--by", by, "--code", contract_code(Project.find(self.root)))

    def write_review(self, tree: str, v1="PASS", v2="PASS", v3="PASS", findings="", slug="password-reset") -> None:
        """Write the review of the packet for `tree`, whose round `atipspec review` counts first."""
        from atipspec.rounds import open_round
        open_round(Project.find(self.root), slug, tree)
        (self.delivery(slug) / "review.md").write_text(REVIEW.format(tree=tree, v1=v1, v2=v2, v3=v3, findings=findings))

    def new_delivery(self, slug: str = "password-reset", *extra: str) -> None:
        """Create the delivery with its intent stated, as the spec phase leaves it."""
        code, out, err = self.run_cli("new", slug, "--title", "Password reset", "--capability", "auth", *extra)
        self.assertEqual(code, 0, err)
        path = Project.find().delivery_dir(slug) / "spec.md"
        path.write_text(re.sub(r"(## Intent\n\n)<!--.*?-->", r"\1" + INTENT, path.read_text(), count=1, flags=re.S))

    def fill_decisions(self) -> None:
        """Write the context and the decision of each decision `atipspec decision` created, as the contract
        phase does before presenting it."""
        for path in (self.root / ".atipspec" / "decisions").glob("DEC-*.md"):
            text = path.read_text(encoding="utf-8")
            for section in ("Context", "Decision"):
                text = re.sub(rf"(## {section}\n\n)<!--.*?-->", rf"\1The {section.lower()} is written.", text,
                              count=1, flags=re.S)
            path.write_text(text, encoding="utf-8")

    def write_contract(self, rules: str, accept: bool = True) -> None:
        """Write the contract; by default the human approves it and its acceptance is recorded."""
        (self.root / ".atipspec" / "contract.md").write_text(
            "---\ntitle: contract\nstatus: draft\n---\n\n# Contract\n\n## Rules\n\n```rules\n" + rules + "\n```\n")
        if accept:
            code, out, err = self.accept_contract()
            self.assertEqual(code, 0, out + err)


class GuidedSteps:
    """A delivery approved by its proposal, completed and verified, for ProjectCase tests."""

    def prepare(self):
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        self.write_plan(accept=False)
        self.project = Project.find(self.root)

    def shared_plan(self, command="true"):
        path = self.delivery() / "plan.md"
        path.write_text("""---
scope: ["*", "src/**"]
---
# Plan
## Tasks
### T1: Request link
Covers: REQ-001
Tests: AC-001, AC-002
### T2: Expiry
Covers: REQ-002
Tests: AC-003
## Final verification
Verify:
- `""" + command + "`\n")

    def approve(self):
        code, out, err = self.accept("password-reset", "proposal", by="human")
        self.assertEqual(code, 0, out + err)

    def complete(self):
        for task in ("T1", "T2"):
            code, out, err = self.run_cli("task-done", "password-reset", task, "--note", "Implemented the approved behavior")
            self.assertEqual(code, 0, out + err)
