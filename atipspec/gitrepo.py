"""Thin git wrapper.

The hash of the working tree binds evidence, reviews and approvals to the exact
content they judged, independently of how the commits are shaped. In a legacy
delivery a commit carrying `[slug:Tn]` also marks task Tn as done.
"""
from __future__ import annotations

import codecs
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .errors import AtipSpecError

_HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class Git:
    def __init__(self, root: Path):
        self.root = root
        self.available = self._inside_work_tree()

    def run(self, *args: str, env: dict | None = None) -> str:
        result = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=env, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise AtipSpecError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    def _inside_work_tree(self) -> bool:
        if shutil.which("git") is None:
            return False
        result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=self.root,
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                stdin=subprocess.DEVNULL)
        return result.returncode == 0 and result.stdout.strip() == "true"

    def head(self) -> str | None:
        if not self.available:
            return None
        result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"], cwd=self.root,
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                stdin=subprocess.DEVNULL)
        return result.stdout.strip() or None

    def rev_exists(self, rev: str) -> bool:
        if not self.available:
            return False
        result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
                                cwd=self.root, capture_output=True, stdin=subprocess.DEVNULL)
        return result.returncode == 0

    def is_ancestor(self, rev: str, of: str) -> bool:
        """Whether the commit `rev` is `of` or one of its ancestors."""
        if not self.available:
            return False
        result = subprocess.run(["git", "merge-base", "--is-ancestor", rev, of], cwd=self.root,
                                capture_output=True, stdin=subprocess.DEVNULL)
        return result.returncode == 0

    def fingerprint(self, exclude: list[str], rev: str | None = None, rewrite=None) -> str:
        """Content hash of the working tree: tracked and untracked files, ignored
        files left out, `exclude` paths removed. Equal trees give equal hashes
        whether or not the content is committed. With `rewrite` (a pathspec and
        a function of a file's text), each file the pathspec matches is hashed
        as the function returns it. Uses a temporary index."""
        index_path = self.run("rev-parse", "--git-path", "index").strip()
        index = Path(index_path) if os.path.isabs(index_path) else self.root / index_path
        descriptor, temp = tempfile.mkstemp(prefix="atipspec-index-")
        os.close(descriptor)
        try:
            if index.is_file():
                shutil.copyfile(index, temp)
                # Its time, as git compares it with each entry's, tells a file rewritten as the index was written.
                stat = index.stat()
                os.utime(temp, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            env = {**os.environ, "GIT_INDEX_FILE": temp}
            if rev:
                self.run("read-tree", rev, env=env)
            else:
                self.run("add", "-A", "--", ".", env=env)
            if exclude:
                # -f: the entries `rev` gave may differ from both the file and HEAD; only this index changes.
                self.run("rm", "--cached", "-r", "-q", "-f", "--ignore-unmatch", "--", *exclude, env=env)
            if rewrite is not None:
                self._rewrite(*rewrite, env)
            return self.run("write-tree", env=env).strip()
        finally:
            os.unlink(temp)

    def _rewrite(self, pathspec: str, change, env: dict) -> None:
        """Pass each file of the index `env` names that `pathspec` matches
        through `change`, a function of its text, in a few git calls whatever
        the number of files."""
        entries = [entry.split("\t", 1) for entry in self.run("ls-files", "-s", "-z", "--", pathspec, env=env)
                   .split("\0") if entry]
        if not entries:
            return
        output = self._bytes("cat-file", "--batch", data="".join(info.split(" ")[1] + "\n" for info, _ in entries)
                             .encode())
        changed = []
        for info, path in entries:
            header, _, output = output.partition(b"\n")
            if len(header.split()) != 3:
                continue   # an object git does not have, as a submodule's commit: nothing to read
            size = int(header.split()[2])
            text = output[:size].decode("utf-8", "surrogateescape")
            output = output[size + 1:]
            rewritten = change(text)
            if rewritten != text:
                changed.append((info.split(" ")[0], path, rewritten.encode("utf-8", "surrogateescape")))
        if not changed:
            return
        with tempfile.TemporaryDirectory(prefix="atipspec-rewrite-") as folder:
            files = []
            for index, (_, _, data) in enumerate(changed):
                files.append(os.path.join(folder, str(index)))
                Path(files[-1]).write_bytes(data)
            ids = self._bytes("hash-object", "-w", "--no-filters", "--stdin-paths",
                              data="".join(name + "\n" for name in files).encode()).decode().split()
        self._bytes("update-index", "-z", "--index-info", env=env, data="".join(
            f"{mode} {oid}\t{path}\0" for (mode, path, _), oid in zip(changed, ids)).encode("utf-8"))

    def _bytes(self, *args: str, data: bytes | None = None, env: dict | None = None) -> bytes:
        result = subprocess.run(["git", *args], cwd=self.root, capture_output=True, input=data, env=env,
                                stdin=None if data is not None else subprocess.DEVNULL)
        if result.returncode != 0:
            raise AtipSpecError(f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
        return result.stdout

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

    def _revs(self, base: str | None, target: str | None) -> list[str]:
        revs = [base] if base else ["HEAD"] if self.head() else []
        return revs + ([target] if target else [])

    def _raw(self, revs: list[str], spec: list[str]) -> dict[str, tuple[str, str, str]]:
        """Path to (old object id, new object id, status) for each path that differs."""
        raw = self._text("diff", "--raw", "-z", "--no-abbrev", "--no-renames", *revs, *spec).split("\0")
        found = {}
        for header, path in zip(raw[0::2], raw[1::2]):
            if header.startswith(":"):
                _, _, old, new, status = header[1:].split(" ")
                found[path] = (old, new, status[:1])
        return found

    def _numstat(self, revs: list[str], spec: list[str]) -> dict[str, tuple[str, str]]:
        found = {}
        for entry in self._text("diff", "--numstat", "-z", "--no-renames", "--no-textconv", *revs, *spec).split("\0"):
            added, _, rest = entry.partition("\t")
            deleted, _, path = rest.partition("\t")
            if path:
                found[path] = (added, deleted)
        return found

    def _reads_as_text(self, blob: str, path: str, status: str, new: bool, worktree: bool) -> bool:
        """Whether one side of a change is text in its first 8000 bytes, where
        git looks: no NUL byte, or UTF-8 with NUL bytes, which a script or a
        source file can hold and still run, though git shows it as binary."""
        try:
            if set(blob) != {"0"}:
                head = self._bytes("cat-file", "blob", blob)[:8000]
            elif new and worktree and status != "D":
                file = self.root / path
                if file.is_symlink():
                    return True
                with file.open("rb") as handle:
                    head = handle.read(8000)
            else:
                return True
        except (OSError, AtipSpecError):
            return False
        try:
            codecs.getincrementaldecoder("utf-8")().decode(head)
        except UnicodeDecodeError:
            return b"\0" not in head
        return True

    def _shown_binary_text(self, sides: dict, counts: dict, worktree: bool) -> list[str]:
        """Paths git shows as binary although both sides are text: an
        attribute or a diff driver says so, or a NUL byte in UTF-8 text."""
        return sorted(path for path, (added, _) in counts.items()
                      if added == "-" and path in sides
                      and all(self._reads_as_text(blob, path, sides[path][2], index == 1, worktree)
                              for index, blob in enumerate(sides[path][:2])))

    def _text(self, *args: str) -> str:
        """Output that carries file content or paths, which need not be UTF-8:
        a byte that does not decode is shown as �, never an error."""
        return self._bytes(*args).decode("utf-8", "replace")

    def _text_diff(self, *args: str) -> str:
        """`git diff --text` of text git takes for binary, NUL bytes shown as ␀."""
        return self._text(*args).replace("\0", "\u2400")

    def diff(self, base: str | None, target: str | None = None, exclude: tuple[str, ...] = (".atipspec",),
             omit: tuple[str, ...] = (), only: tuple[str, ...] = ()) -> str:
        """The diff from `base` (or HEAD) to the working tree, or to the tree-ish
        `target`, of the files `only` names, as written, or of all, with the
        `exclude` paths and the files `omit` names, as written, left out. It
        shows the stored content, whatever the local git configuration says: no
        textconv filter, and a text file an attribute marks as binary, or UTF-8
        text with a NUL byte, is shown as text; a byte that is not UTF-8 shows
        as �."""
        revs = self._revs(base, target)
        spec = ["--", *([f":(literal){path}" for path in only] or ["."]), *(f":(exclude){path}" for path in exclude),
                *(f":(exclude,literal){path}" for path in omit)]
        args = ["diff", "--no-color", "--no-ext-diff", "--no-textconv"] + (["--no-renames"] if target else [])
        marked = self._shown_binary_text(self._raw(revs, spec), self._numstat(revs, spec), worktree=target is None)
        text = self._text(*args, *revs, *spec, *(f":(exclude,literal){path}" for path in marked))
        if marked:
            text += self._text_diff(*args, "--text", *revs, "--", *(f":(literal){path}" for path in marked))
        return text

    def diff_files(self, base: str, target: str, only: tuple[str, ...] = ()) -> list[dict]:
        """Each path that differs between two tree-ishes, of those `only`
        names, as written, or of all: status (A, M, D, T), added and deleted
        lines (None for a binary file, judged by content as in `diff`) and the
        object id of the new content (None when deleted)."""
        spec = ["--", *([f":(literal){path}" for path in only] or ["."])]
        sides = self._raw([base, target], spec)
        files = {path: {"path": path, "status": status, "added": None, "deleted": None,
                        "blob": None if status == "D" else new}
                 for path, (_, new, status) in sides.items()}
        counts = self._numstat([base, target], spec)
        for path in self._shown_binary_text(sides, counts, worktree=False):
            # numstat honors the attribute even with --text: count the text diff's lines.
            lines = self._text_diff("diff", "--no-color", "--no-ext-diff", "--no-textconv", "--text", "--no-renames",
                                    base, target, "--", f":(literal){path}").split("\n")
            body = lines[next((index for index, line in enumerate(lines) if line.startswith("@@")), len(lines)):]
            counts[path] = (str(sum(1 for line in body if line.startswith("+"))),
                            str(sum(1 for line in body if line.startswith("-"))))
        for path, (added, deleted) in counts.items():
            if path in files and added != "-":
                files[path].update(added=int(added), deleted=int(deleted))
        return [files[path] for path in sorted(files)]

    def hunks(self, old: str, new: str, path: str) -> list[tuple[int, int, int, int, list[str], list[str]]]:
        """The hunks of the diff of `path` between two tree-ishes, with no
        context, as written: where each starts in `old` and how many lines it
        takes out, where it starts in `new` and how many it puts in (a start
        with no lines names the line before), and those lines."""
        text = self._text("diff", "--no-color", "--no-ext-diff", "--no-textconv", "--text", "--no-renames", "-U0",
                          "--inter-hunk-context=0", old, new, "--", f":(literal){path}")
        hunks = []
        for line in text.split("\n"):
            match = _HUNK.match(line)
            if match:
                hunks.append((*(int(value) if value else 1 for value in match.groups()), [], []))
            elif hunks and line[:1] in ("-", "+"):
                hunks[-1][4 if line[0] == "-" else 5].append(line[1:])
        return hunks

    def changed_between(self, old: str, new: str) -> list[str] | None:
        """Paths that differ between two tree-ishes; None when one of them is not
        in the object store (pruned, or never written here)."""
        for tree in (old, new):
            result = subprocess.run(["git", "cat-file", "-e", f"{tree}^{{tree}}"], cwd=self.root,
                                    capture_output=True, stdin=subprocess.DEVNULL)
            if result.returncode:
                return None
        output = self.run("diff-tree", "-r", "-z", "--name-only", "--no-renames", old, new)
        return [name for name in output.split("\0") if name]

    def blob_text(self, tree: str, path: str) -> str | None:
        """A file's text in a tree-ish, or None when it is not there."""
        result = subprocess.run(["git", "cat-file", "-p", f"{tree}:{path}"], cwd=self.root,
                                capture_output=True, stdin=subprocess.DEVNULL)
        return result.stdout.decode("utf-8", "replace") if result.returncode == 0 else None

    def ignored(self, path: str) -> bool:
        """Whether git ignores `path`: an untracked path an ignore rule matches."""
        result = subprocess.run(["git", "check-ignore", "-q", "--", path], cwd=self.root,
                                capture_output=True, stdin=subprocess.DEVNULL)
        return result.returncode == 0

    def tracks(self, path: str) -> bool:
        """Whether `path` is in the index."""
        return bool(self.run("ls-files", "--", f":(literal){path}").strip())

    def diff_stat(self, base: str | None) -> str:
        args = ["diff", "--no-color", "--no-ext-diff", "--no-textconv", "--stat=120"]
        if base:
            args.append(base)
        elif self.head():
            args.append("HEAD")
        return self._text(*args, "--", ".", ":(exclude).atipspec")

    def untracked(self, include_atipspec: bool = False) -> list[str]:
        output = self._text("ls-files", "-z", "--others", "--exclude-standard", "--", ".")
        return [name for name in output.split("\0")
                if name and (include_atipspec or not name.startswith(".atipspec/"))]

    def tracked(self) -> list[str]:
        return [name for name in self._text("ls-files", "-z", "--", ".").split("\0") if name]

    def changed(self, base: str | None) -> list[str]:
        """Paths that differ between the working tree and `base` (or HEAD),
        unquoted."""
        args = ["diff", "--name-only", "-z", "--no-renames"]
        if base:
            args.append(base)
        elif self.head():
            args.append("HEAD")
        return [name for name in self._text(*args, "--", ".").split("\0") if name]

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
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                stdin=subprocess.DEVNULL)
        return result.stdout.strip() or None

    def create_branch(self, name: str) -> None:
        self.run("switch", "-c", name)
