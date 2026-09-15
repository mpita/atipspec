"""Parse the artifacts of a delivery: spec.md, plan.md, review.md, deferred.md,
the evidence files written by `atipspec verify`, and initiative roadmaps.

The grammar is deliberately small and line based so that a model or a person
can write the files by hand and the CLI can still read them without ambiguity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re

from . import frontmatter
from .locale import NO_COMMANDS, empty_pattern, section_pattern

REQ_HEADING = re.compile(r"^#{2,4}\s+(REQ-\d{3,})(?:\s*\[(remove)\])?\s*:\s*(\S.*?)\s*$", re.I)
AC_LINE = re.compile(r"^\s*[-*]\s+(AC-\d{3,})(?:\s*\[\s*(test|manual)\s*\])?\s*:\s*(\S.*?)\s*$", re.I)
AC_LIKE = re.compile(r"^\s*[-*]\s+AC-\d{3,}\b", re.I)
AC_PLACEHOLDER = re.compile(r"^\s*[-*]\s+AC-\d{3,}\s*:\s*$", re.I)   # the template's empty criterion
TASK_HEADING = re.compile(r"^#{2,4}\s+(T\d+)\s*:\s*(\S.*?)\s*$")
FIELD = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?(Covers|Verify|Tests|Manual|Report|Proof)(?:\*\*)?\s*:\s*(.*?)\s*$", re.I)
PROOF_ITEM = re.compile(r"^\s*[-*]\s+(AC-\d{3,})\s*:\s*(\S.*?)\s*$", re.I)
LIST_ITEM = re.compile(r"^\s*[-*]\s+(\S.*?)\s*$")
HEADING2 = re.compile(r"^##\s+(.+?)\s*$")
HEADING = re.compile(r"^#{1,6}\s")
VERDICT = re.compile(r"^\s*[-*]\s+(AC-\d{3,})\s*:\s*(PASS|FAIL)\b[\s.:—–-]*(.*?)\s*$", re.I)
FINDING = re.compile(r"^\s*[-*]\s+(F\d+)\s*\[(blocker|major|minor)\]\s*:\s*(\S.*?)\s*$", re.I)
DEFERRED = re.compile(r"^\s*[-*]\s+(F\d+|AC-\d{3,}|REQ-\d{3,})\s*:\s*(\S.*?)\s*$", re.I)
REQ_ID = re.compile(r"REQ-\d{3,}", re.I)
OPEN_QUESTIONS = section_pattern("open_questions")
ASSUMPTIONS = section_pattern("assumptions")
EMPTY_ITEM = empty_pattern()
COMMENT = re.compile(r"<!--.*?-->", re.S)


@dataclass
class Criterion:
    id: str
    text: str
    requirement: str
    line: int
    method: str = "test"     # test, or manual: a person observes it


@dataclass
class Requirement:
    id: str
    title: str
    remove: bool
    line: int
    body: list[str] = field(default_factory=list)
    criteria: list[Criterion] = field(default_factory=list)


@dataclass
class Spec:
    meta: dict
    title: str | None
    requirements: list[Requirement]
    open_questions: list[str]
    problems: list[str]
    assumptions: list[str] = field(default_factory=list)

    @property
    def criteria(self) -> list[Criterion]:
        return [criterion for requirement in self.requirements for criterion in requirement.criteria]

    @property
    def status(self):
        return self.meta.get("status")

    def _list(self, key: str) -> list[str]:
        value = self.meta.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return [str(value)] if value else []

    @property
    def capability(self) -> str | None:
        value = self.meta.get("capability")
        return str(value) if value else None

    @property
    def kind(self) -> str:
        """feature, or fix: a defect repair with a regression criterion and one task."""
        return "fix" if self.meta.get("kind") == "fix" else "feature"

    @property
    def impact(self) -> list[str]:
        """Living specs and contract sections this delivery reads or affects."""
        names = ([self.capability] if self.capability else []) + self._list("impact")
        return list(dict.fromkeys(names))


@dataclass
class Task:
    id: str
    title: str
    line: int
    covers: list[str] = field(default_factory=list)
    verify: list[str] = field(default_factory=list)
    verify_none: bool = False
    tests: list[str] = field(default_factory=list)
    manual: list[str] = field(default_factory=list)
    report: str | None = None                        # JUnit XML the Verify commands write
    proof: dict[str, str] = field(default_factory=dict)   # AC id -> test id in that report


@dataclass
class Plan:
    meta: dict
    tasks: list[Task]
    problems: list[str]

    @property
    def scope(self) -> list[str]:
        """Globs of the files the tasks may touch; empty means undeclared."""
        value = self.meta.get("scope")
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return [str(value)] if value else []


@dataclass
class Finding:
    id: str
    severity: str
    text: str


@dataclass
class Review:
    meta: dict
    verdicts: dict[str, tuple[str, str]]
    findings: list[Finding]
    problems: list[str]

    @property
    def tree(self):
        return self.meta.get("tree")


@dataclass
class Evidence:
    path: Path
    task: str
    tree: str | None
    result: str
    finished: str
    commands: list[dict]
    data: dict = field(default_factory=dict)


def _lines(text: str) -> tuple[dict, list[str], str | None]:
    """Split frontmatter, blank out HTML comments and fenced code, keep line numbers."""
    meta, body = frontmatter.split(text)
    body = COMMENT.sub(lambda match: "\n" * match.group(0).count("\n"), body)
    lines = []
    in_code = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            lines.append("")
            continue
        lines.append("" if in_code else line)
    return meta, lines, None


def parse_spec(text: str) -> Spec:
    try:
        meta, lines, _ = _lines(text)
    except ValueError as exc:
        return Spec({}, None, [], [], [f"spec.md frontmatter: {exc}"])
    spec = Spec(meta, None, [], [], [])
    section = ""
    current: Requirement | None = None
    for number, line in enumerate(lines, 1):
        if spec.title is None and line.startswith("# "):
            spec.title = line[2:].strip() or None
            continue
        requirement = REQ_HEADING.match(line)
        if requirement:
            current = Requirement(requirement.group(1).upper(), requirement.group(3),
                                  bool(requirement.group(2)), number)
            spec.requirements.append(current)
            continue
        heading = HEADING2.match(line)
        if heading:
            section = heading.group(1)
            current = None
            continue
        if HEADING.match(line):
            current = None
            continue
        criterion = AC_LINE.match(line)
        if criterion:
            if current is None:
                spec.problems.append(f"spec.md line {number}: {criterion.group(1).upper()} is outside a requirement")
            else:
                current.criteria.append(Criterion(criterion.group(1).upper(), criterion.group(3), current.id, number,
                                                  (criterion.group(2) or "test").lower()))
                current.body.append(line)
            continue
        if AC_LIKE.match(line) and not AC_PLACEHOLDER.match(line):
            spec.problems.append(f"spec.md line {number}: malformed criterion line; use `- AC-001: text` or `- AC-001 [manual]: text`")
            if current is not None:
                current.body.append(line)
            continue
        if OPEN_QUESTIONS.match(section) or ASSUMPTIONS.match(section):
            item = LIST_ITEM.match(line)
            if item and not EMPTY_ITEM.match(item.group(1)):
                (spec.open_questions if OPEN_QUESTIONS.match(section) else spec.assumptions).append(item.group(1))
        if current is not None:
            current.body.append(line)
    if spec.title is None and isinstance(meta.get("title"), str):
        spec.title = meta["title"]
    return spec


def _clean_command(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        value = value[1:-1].strip()
    return value


def parse_plan(text: str) -> Plan:
    try:
        meta, lines, _ = _lines(text)
    except ValueError as exc:
        return Plan({}, [], [f"plan.md frontmatter: {exc}"])
    plan = Plan(meta, [], [])
    current: Task | None = None
    listing: str | None = None      # "verify" or "proof" while reading that field's list items
    for number, line in enumerate(lines, 1):
        task = TASK_HEADING.match(line)
        if task:
            current = Task(task.group(1), task.group(2), number)
            plan.tasks.append(current)
            listing = None
            continue
        if HEADING.match(line):
            current = None
            listing = None
            continue
        if current is None:
            continue
        fld = FIELD.match(line)
        if fld:
            name, value = fld.group(1).lower(), fld.group(2)
            listing = None
            if name == "covers":
                current.covers = [ident.upper() for ident in REQ_ID.findall(value)]
                if value and not current.covers:
                    plan.problems.append(f"plan.md line {number}: Covers must list REQ ids")
            elif name in ("tests", "manual"):
                setattr(current, name, re.findall(r"AC-\d{3,}", value.upper()))
            elif name == "report":
                current.report = _clean_command(value) or None
                if not current.report:
                    plan.problems.append(f"plan.md line {number}: Report needs the path of a JUnit XML file")
                elif Path(current.report).is_absolute() or ".." in Path(current.report).parts:
                    plan.problems.append(f"plan.md line {number}: Report must be a relative path inside the project")
                    current.report = None
            elif name == "proof":
                listing = "proof"
                item = PROOF_ITEM.match("- " + value) if value else None
                if item:
                    current.proof[item.group(1).upper()] = _clean_command(item.group(2))
                elif value:
                    plan.problems.append(f"plan.md line {number}: Proof entries look like `- AC-001: test id`")
            else:
                listing = "verify"
                if value.lower() in NO_COMMANDS:
                    current.verify_none = True
                    listing = None
                elif value:
                    current.verify.append(_clean_command(value))
            continue
        if listing == "verify":
            item = LIST_ITEM.match(line)
            if not line.strip():
                listing = None
            elif item:
                command = _clean_command(item.group(1))
                if command.lower() in NO_COMMANDS:
                    current.verify_none = True
                elif command:
                    current.verify.append(command)
            else:
                listing = None
        elif listing == "proof":
            item = PROOF_ITEM.match(line)
            if not line.strip():
                listing = None
            elif item:
                current.proof[item.group(1).upper()] = _clean_command(item.group(2))
            elif LIST_ITEM.match(line):
                plan.problems.append(f"plan.md line {number}: Proof entries look like `- AC-001: test id`")
            else:
                listing = None
    return plan


def parse_review(text: str) -> Review:
    try:
        meta, lines, _ = _lines(text)
    except ValueError as exc:
        return Review({}, {}, [], [f"review.md frontmatter: {exc}"])
    review = Review(meta, {}, [], [])
    for number, line in enumerate(lines, 1):
        verdict = VERDICT.match(line)
        if verdict:
            ident = verdict.group(1).upper()
            if ident in review.verdicts:
                review.problems.append(f"review.md line {number}: {ident} has two verdicts")
            review.verdicts[ident] = (verdict.group(2).upper(), verdict.group(3))
            continue
        finding = FINDING.match(line)
        if finding:
            ident = finding.group(1).upper()
            if any(item.id == ident for item in review.findings):
                review.problems.append(f"review.md line {number}: duplicate finding {ident}")
            review.findings.append(Finding(ident, finding.group(2).lower(), finding.group(3)))
        elif re.match(r"^\s*[-*]\s+(?:AC-\d+|F\d+)\b", line, re.I):
            review.problems.append(f"review.md line {number}: malformed verdict or finding")
    return review


def parse_deferred(text: str) -> tuple[dict[str, str], list[str]]:
    try:
        _, lines, _ = _lines(text)
    except ValueError as exc:
        return {}, [f"deferred.md frontmatter: {exc}"]
    entries: dict[str, str] = {}
    problems: list[str] = []
    for number, line in enumerate(lines, 1):
        match = DEFERRED.match(line)
        if match:
            ident = match.group(1).upper()
            if ident in entries:
                problems.append(f"deferred.md line {number}: {ident} is listed twice")
            entries[ident] = match.group(2)
    return entries, problems


def load_evidence(directory: Path) -> tuple[dict[str, Evidence], list[str]]:
    """Latest evidence per task, by finish time, plus unreadable files."""
    latest: dict[str, Evidence] = {}
    problems: list[str] = []
    if not directory.is_dir():
        return latest, problems
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            evidence = Evidence(path, str(data["task"]), data.get("tree"), str(data["result"]),
                                str(data.get("finished", "")), list(data.get("commands", [])), data)
            if not re.fullmatch(r"T[1-9][0-9]*", evidence.task):
                raise ValueError("invalid task id")
            if not all(isinstance(command, dict) for command in evidence.commands):
                raise ValueError("commands must be objects")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            problems.append(f"evidence {path.name} is unreadable: {exc}")
            continue
        current = latest.get(evidence.task)
        if current is None or evidence.finished >= current.finished:
            latest[evidence.task] = evidence
    return latest, problems


ROADMAP_ITEM = re.compile(r"^\s*[-*]\s+([a-z0-9][a-z0-9-]*)\s*:\s*(\S.*?)\s*$")


@dataclass
class Roadmap:
    meta: dict
    title: str | None
    deliveries: list[tuple[str, str]]
    problems: list[str]


def parse_roadmap(text: str) -> Roadmap:
    """An initiative's roadmap: `- <delivery-slug>: title` lines under Deliveries."""
    try:
        meta, lines, _ = _lines(text)
    except ValueError as exc:
        return Roadmap({}, None, [], [f"roadmap.md frontmatter: {exc}"])
    roadmap = Roadmap(meta, None, [], [])
    section = ""
    for line in lines:
        if roadmap.title is None and line.startswith("# "):
            roadmap.title = line[2:].strip() or None
            continue
        heading = HEADING2.match(line)
        if heading:
            section = heading.group(1).lower()
            continue
        if section.startswith("deliver"):
            item = ROADMAP_ITEM.match(line)
            if item:
                roadmap.deliveries.append((item.group(1), item.group(2)))
    if roadmap.title is None and isinstance(meta.get("title"), str):
        roadmap.title = meta["title"]
    return roadmap
