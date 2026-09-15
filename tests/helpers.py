"""Temporary git projects for tests, isolated from the user's git configuration."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from atipspec.cli import main

GIT = shutil.which("git")

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
---

# Review: Password reset

## Criteria

- AC-001: {v1}. proof
- AC-002: {v2}. proof
- AC-003: {v3}. proof

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
        config = self.root / ".gitconfig-empty"
        config.write_text("")
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t"}
        self.enterContext(patch.dict(os.environ, self.env))
        self.enterContext(contextlib.chdir(self.root))
        self.enterContext(patch("builtins.input", side_effect=AssertionError("unexpected prompt")))
        self.enterContext(patch("atipspec.ui.interactive", return_value=False))
        self.git("init", "-q", "-b", "main", ".")
        (self.root / ".gitignore").write_text(".gitconfig-empty\n")
        (self.root / "README.md").write_text("# demo\n")
        self.commit("init")
        self.run_cli("init", "--client", "claude", "--name", "Demo", "--language", "es")

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=self.root, text=True, env=self.env)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
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

    def accept(self, slug: str = "password-reset", phase: str = "spec") -> tuple[int, str, str]:
        return self.run_cli("accept", slug, phase, "--by", "tester")

    def write_review(self, tree: str, v1="PASS", v2="PASS", v3="PASS", findings="", slug="password-reset") -> None:
        (self.delivery(slug) / "review.md").write_text(REVIEW.format(tree=tree, v1=v1, v2=v2, v3=v3, findings=findings))

    def new_delivery(self, slug: str = "password-reset", *extra: str) -> None:
        code, out, err = self.run_cli("new", slug, "--title", "Password reset", "--capability", "auth", *extra)
        self.assertEqual(code, 0, err)

    def write_contract(self, rules: str) -> None:
        (self.root / ".atipspec" / "contract.md").write_text(
            "---\ntitle: contract\nstatus: accepted\n---\n\n# Contract\n\n## Rules\n\n```rules\n" + rules + "\n```\n")
