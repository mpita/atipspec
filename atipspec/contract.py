"""The architecture contract and its machine-checked rules.

`contract.md` is prose the model reads, plus one fenced ```rules block that
the CLI evaluates on every delivery (`check`) and on the whole repository
(`audit`). One rule per line, shell-style quoting, `#` starts a comment:

    forbid-path <glob>                       no file may match the glob
    forbid-pattern <glob> <regex>            no file matching the glob may contain the regex
    dependencies <manifest> <name-or-glob>...  the manifest may only declare these
    require-command <command>                every plan must verify with this command
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import shlex
import tomllib

RULE_KINDS = ("forbid-path", "forbid-pattern", "dependencies", "require-command")
BLOCK = re.compile(r"^```rules[^\n]*\n(.*?)^```", re.M | re.S)
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


@dataclass
class Rule:
    kind: str
    args: list[str]
    reason: str
    line: int

    @property
    def text(self) -> str:
        return f"{self.kind} {' '.join(shlex.quote(arg) for arg in self.args)}"


@dataclass
class Contract:
    rules: list[Rule] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def of(self, kind: str) -> list[Rule]:
        return [rule for rule in self.rules if rule.kind == kind]


@dataclass
class Violation:
    rule: Rule
    path: str
    detail: str

    def render(self) -> str:
        reason = f" ({self.rule.reason})" if self.rule.reason else ""
        return f"{self.path}: {self.detail}{reason}"


def parse_contract(text: str) -> Contract:
    contract = Contract()
    match = BLOCK.search(text)
    if match is None:
        return contract
    offset = text[:match.start(1)].count("\n") + 1
    for number, raw in enumerate(match.group(1).splitlines(), offset):
        line, _, comment = raw.partition("#")
        if not line.strip():
            continue
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            contract.problems.append(f"contract.md line {number}: {exc}")
            continue
        kind, args = parts[0], parts[1:]
        minimum = {"forbid-path": 1, "forbid-pattern": 2, "dependencies": 1, "require-command": 1}.get(kind)
        if minimum is None:
            contract.problems.append(f"contract.md line {number}: unknown rule {kind!r}")
            continue
        if len(args) < minimum:
            contract.problems.append(f"contract.md line {number}: {kind} needs at least {minimum} argument(s)")
            continue
        if kind == "forbid-pattern":
            try:
                re.compile(args[1])
            except re.error as exc:
                contract.problems.append(f"contract.md line {number}: invalid regex: {exc}")
                continue
        contract.rules.append(Rule(kind, args, comment.strip(), number))
    return contract


def glob_to_regex(pattern: str) -> re.Pattern:
    """`**` crosses directories, `*` and `?` do not. Anchored to the whole path."""
    out, index = [], 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif char == "*":
            out.append("[^/]*")
            index += 1
        elif char == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(char))
            index += 1
    return re.compile("^" + "".join(out) + "$")


def matches(pattern: str, path: str) -> bool:
    return glob_to_regex(pattern).match(path) is not None


def manifest_dependencies(path: Path) -> list[str]:
    """Dependency names declared by a manifest (lowercase). Supports pyproject.toml,
    requirements*.txt, package.json, Cargo.toml and go.mod."""
    name = path.name
    supported = name in ("pyproject.toml", "Cargo.toml", "package.json", "go.mod") or \
        (name.startswith("requirements") and name.endswith(".txt"))
    if not supported:
        raise ValueError(f"unsupported manifest {name}")
    text = path.read_text(encoding="utf-8", errors="replace")
    found: list[str] = []
    if name == "pyproject.toml" or name == "Cargo.toml":
        data = tomllib.loads(text)
        if name == "pyproject.toml":
            project = data.get("project", {})
            found += [_requirement_name(item) for item in project.get("dependencies", [])]
            for group in project.get("optional-dependencies", {}).values():
                found += [_requirement_name(item) for item in group]
            for group in data.get("dependency-groups", {}).values():
                found += [_requirement_name(item) for item in group if isinstance(item, str)]
            poetry = data.get("tool", {}).get("poetry", {})
            found += [key for key in poetry.get("dependencies", {}) if key.lower() != "python"]
            for group in poetry.get("group", {}).values():
                found += list(group.get("dependencies", {}))
        else:
            for key in ("dependencies", "dev-dependencies", "build-dependencies"):
                found += list(data.get(key, {}))
    elif name.startswith("requirements") and name.endswith(".txt"):
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                found.append(_requirement_name(line))
    elif name == "package.json":
        data = json.loads(text)
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            found += list(data.get(key, {}))
    elif name == "go.mod":
        block = False
        for line in text.splitlines():
            line = line.split("//", 1)[0].strip()
            if line.startswith("require ("):
                block = True
            elif line == ")":
                block = False
            elif line.startswith("require "):
                found.append(line.split()[1])
            elif block and line:
                found.append(line.split()[0])
    return [item.lower() for item in found if item]


def _requirement_name(item: str) -> str:
    match = REQUIREMENT_NAME.match(item)
    return match.group(1) if match else item


def evaluate(contract: Contract, root: Path, files: list[str], *, manifests_always: bool) -> list[Violation]:
    """Evaluate forbid-path, forbid-pattern and dependencies rules over `files`
    (paths relative to root). Dependencies rules run when the manifest is in
    `files`, or always for an audit."""
    violations: list[Violation] = []
    for rule in contract.of("forbid-path"):
        for path in files:
            if matches(rule.args[0], path):
                violations.append(Violation(rule, path, f"matches forbidden path {rule.args[0]}"))
    for rule in contract.of("forbid-pattern"):
        pattern = re.compile(rule.args[1])
        for path in files:
            if not matches(rule.args[0], path):
                continue
            try:
                text = (root / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    violations.append(Violation(rule, f"{path}:{number}", f"contains forbidden pattern {rule.args[1]!r}"))
                    break
    for rule in contract.of("dependencies"):
        manifest = rule.args[0]
        if not manifests_always and manifest not in files:
            continue
        path = root / manifest
        if not path.is_file():
            continue
        try:
            declared = manifest_dependencies(path)
        except (ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
            violations.append(Violation(rule, manifest, f"cannot read manifest: {exc}"))
            continue
        allowed = [item.lower() for item in rule.args[1:]]
        for dependency in declared:
            if not any(matches(pattern, dependency) for pattern in allowed):
                violations.append(Violation(rule, manifest, f"dependency {dependency!r} is not in the contract"))
    return violations


def missing_commands(contract: Contract, commands: list[str]) -> list[Rule]:
    """require-command rules whose command no task verifies with."""
    normalized = {" ".join(command.split()) for command in commands}
    return [rule for rule in contract.of("require-command") if " ".join(rule.args[0].split()) not in normalized]
