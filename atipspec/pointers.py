"""Review pointers: what a PASS verdict points to, resolved against the
candidate, so `PASS. ok` cannot pass for proof.

A pointer resolves when one of its tokens (separated by spaces; a span in
backticks is one token) is:
  - a test that ran and passed in the current evidence's JUnit reports;
  - `path:line` or `path:line-line`, a line of a file of the candidate: outside
    .atipspec/ and .git and not ignored by git, or an evidence log of the
    delivery (`evidence/logs/...` from the delivery folder), ignored or not;
  - `path::test`, such a file that holds that name as a word.
Resolving shows that the pointer names something real, not that it proves the
criterion: the dossier shows what each pointer resolved to for the human to
judge, a `path::test` as a name found in a file, and Proof entries bind a
criterion to its test.
"""
from __future__ import annotations

from pathlib import Path
import re

from .junit import find_all

LINE = re.compile(r"^(?P<path>[^:]+):(?P<start>[1-9]\d*)(?:-(?P<end>[1-9]\d*))?$")
TEST = re.compile(r"^(?P<path>[^:]+)::(?P<name>\S+)$")
# Punctuation around a pointer in a sentence, not part of it; a closing
# bracket stays when the token opens it, as in `test_total[eur]`.
CLOSING = {")": "(", "]": "[", "}": "{", ">": "<"}


def _trim(word: str) -> str:
    word = word.lstrip("([{<'\"")
    while word and (word[-1] in ".,;:!?'\"" or (word[-1] in CLOSING
                                                and word.count(CLOSING[word[-1]]) < word.count(word[-1]))):
        word = word[:-1]
    return word


def tokens(text: str) -> list[str]:
    found = [span.strip() for span in re.findall(r"`([^`]+)`", text)]
    found += [_trim(word) for word in re.sub(r"`[^`]*`", " ", text).split()]
    return [token for token in found if token]


def _same(path: Path, other: Path) -> bool:
    try:
        return path.samefile(other)
    except OSError:
        return False


def _file(project, relative: str, folder: Path | None) -> Path | None:
    """A regular file of the candidate the pointer names, reached through no
    symlink: relative to the project root, outside .atipspec/ and .git and not
    ignored by git, or an evidence log, relative to the delivery folder, which
    git may ignore. Folders are compared as the file system finds them, so
    `.ATIPSPEC/` is .atipspec/ where names ignore case."""
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return None
    logs = folder / "evidence" / "logs" if folder is not None else None
    depth = len(logs.relative_to(project.root).parts) if logs is not None else 0
    for base in (project.root, folder):
        if base is None:
            continue
        try:
            inside = (base / path).relative_to(project.root).parts
        except ValueError:
            continue
        steps = [project.root.joinpath(*inside[:count]) for count in range(1, len(inside) + 1)]
        try:
            if any(step.is_symlink() for step in steps) or not steps[-1].is_file():
                continue
        except OSError:
            continue
        if _same(steps[0], project.root / ".git"):
            continue
        if _same(steps[0], project.dot):
            if logs is not None and len(steps) > depth and _same(steps[depth - 1], logs):
                return steps[-1]
            continue
        if not (project.git.available and project.git.ignored("/".join(inside))):
            return steps[-1]
    return None


def _lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def resolve(project, text: str, cases: list[dict], folder: Path | None = None) -> str | None:
    """What the pointer in `text` resolves to, or None. `cases` are the test
    cases of the current, passing evidence; `folder` is the delivery folder."""
    for token in tokens(text):
        found = find_all(token, cases)
        if found and all(case["status"] == "passed" for case in found):
            return f"test {token} passed"
        line = LINE.match(token)
        if line:
            path = _file(project, line.group("path"), folder)
            start, end = int(line.group("start")), int(line.group("end") or line.group("start"))
            try:
                if path is not None and start <= end <= _lines(path):
                    return f"file {token}"
            except OSError:
                pass
            continue
        test = TEST.match(token)
        if test:
            path = _file(project, test.group("path"), folder)
            names = [re.sub(r"\[.*\]$", "", part) for part in test.group("name").split("::")]
            if path is not None and all(names):
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if all(re.search(rf"(?<!\w){re.escape(name)}(?!\w)", content) for name in names):
                    return f"name {test.group('name')} found in {test.group('path')}"
    return None


def observation(text: str) -> bool:
    """A manual criterion's PASS may describe what was done and observed
    instead: at least three words."""
    return len(re.findall(r"[^\W_]+", text)) >= 3
