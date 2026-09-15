"""Thin git wrapper.

Git is AtipSpec's state machine: a commit carrying `[slug:Tn]` marks task Tn as
done, and the hash of the working tree binds evidence and reviews to the exact
code they judged, independently of how the commits are shaped.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .errors import AtipSpecError


class Git:
    def __init__(self, root: Path):
        self.root = root
        self.available = self._inside_work_tree()

    def run(self, *args: str, env: dict | None = None) -> str:
        result = subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                                text=True, env=env, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise AtipSpecError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    def _inside_work_tree(self) -> bool:
        if shutil.which("git") is None:
            return False
        result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=self.root,
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return result.returncode == 0 and result.stdout.strip() == "true"

    def head(self) -> str | None:
        if not self.available:
            return None
        result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"], cwd=self.root,
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return result.stdout.strip() or None

    def rev_exists(self, rev: str) -> bool:
        if not self.available:
            return False
        result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
                                cwd=self.root, capture_output=True, stdin=subprocess.DEVNULL)
        return result.returncode == 0

    def fingerprint(self, exclude: list[str], rev: str | None = None) -> str:
        """Content hash of the working tree: tracked and untracked files, ignored
        files left out, `exclude` paths removed. Equal trees give equal hashes
        whether or not the content is committed. Uses a temporary index."""
        index_path = self.run("rev-parse", "--git-path", "index").strip()
        index = Path(index_path) if os.path.isabs(index_path) else self.root / index_path
        descriptor, temp = tempfile.mkstemp(prefix="atipspec-index-")
        os.close(descriptor)
        try:
            if index.is_file():
                shutil.copyfile(index, temp)
            env = {**os.environ, "GIT_INDEX_FILE": temp}
            if rev:
                self.run("read-tree", rev, env=env)
            else:
                self.run("add", "-A", "--", ".", env=env)
            if exclude:
                self.run("rm", "--cached", "-r", "-q", "--ignore-unmatch", "--", *exclude, env=env)
            return self.run("write-tree", env=env).strip()
        finally:
            os.unlink(temp)

    def task_commits(self, slug: str, base: str | None = None) -> dict[str, str]:
        """Map task id to the short hash of the first commit in HEAD's history
        whose message carries `[slug:Tn]` (several ids may share one marker)."""
        if self.head() is None:
            return {}
        pattern = re.compile(r"\[" + re.escape(slug) + r":([T0-9,\s]+)\]")
        done: dict[str, str] = {}
        for entry in self.run("log", "--format=%h%x1f%B%x1e", *([f"{base}..HEAD"] if base else [])).split("\x1e"):
            if "\x1f" not in entry:
                continue
            short, message = entry.split("\x1f", 1)
            for match in pattern.finditer(message):
                for task in re.findall(r"T\d+", match.group(1)):
                    done.setdefault(task, short.strip())
        return done

    def diff(self, base: str | None) -> str:
        args = ["diff", "--no-color", "--no-ext-diff"]
        if base:
            args.append(base)
        elif self.head():
            args.append("HEAD")
        return self.run(*args, "--", ".", ":(exclude).atipspec")

    def diff_stat(self, base: str | None) -> str:
        args = ["diff", "--no-color", "--no-ext-diff", "--stat=120"]
        if base:
            args.append(base)
        elif self.head():
            args.append("HEAD")
        return self.run(*args, "--", ".", ":(exclude).atipspec")

    def untracked(self, include_atipspec: bool = False) -> list[str]:
        output = self.run("ls-files", "--others", "--exclude-standard", "--", ".")
        return [line for line in output.splitlines()
                if line and (include_atipspec or not line.startswith(".atipspec/"))]

    def tracked(self) -> list[str]:
        return [line for line in self.run("ls-files", "--", ".").splitlines() if line]

    def changed(self, base: str | None) -> list[str]:
        """Paths that differ between the working tree and `base` (or HEAD)."""
        args = ["diff", "--name-only", "--no-renames"]
        if base:
            args.append(base)
        elif self.head():
            args.append("HEAD")
        return [line for line in self.run(*args, "--", ".").splitlines() if line]

    def exists_at(self, rev: str, path: str) -> bool:
        """Whether `path` exists in the tree of `rev`."""
        if not self.available:
            return False
        result = subprocess.run(["git", "cat-file", "-e", f"{rev}:{path}"], cwd=self.root,
                                capture_output=True, stdin=subprocess.DEVNULL)
        return result.returncode == 0

    def add_worktree(self, path: Path, branch: str) -> None:
        self.run("worktree", "add", "-b", branch, str(path))

    def current_branch(self) -> str | None:
        if not self.available:
            return None
        result = subprocess.run(["git", "branch", "--show-current"], cwd=self.root,
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return result.stdout.strip() or None

    def create_branch(self, name: str) -> None:
        self.run("switch", "-c", name)
