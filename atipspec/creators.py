"""Create deliveries, decisions and initiatives from the templates."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import re

from . import frontmatter
from .delivery import HEADING2, parse_roadmap
from .errors import AtipSpecError
from .project import Project, template, validate_slug


def _from_template(name: str, meta_updates: dict, replacements: dict[str, str]) -> str:
    meta, body = frontmatter.split(template(name))
    meta.update(meta_updates)
    for key, value in replacements.items():
        body = body.replace("{{" + key + "}}", value)
    return frontmatter.compose(meta, body)


KINDS = ("feature", "fix")


def required_verify(project: Project) -> str:
    """The contract's required commands as Verify list items, or a placeholder."""
    from .check import load_contract
    commands = [rule.args[0] for rule in load_contract(project).of("require-command")]
    if not commands:
        return "- `<!-- the test command that reproduces the defect, red then green -->`"
    return "\n".join(f"- `{command}`" for command in commands)


def new_delivery(project: Project, slug: str, title: str, *, capability: str | None = None,
                 impact: list[str] | None = None, owner: str | None = None, ticket: str | None = None,
                 initiative: str | None = None, branch: bool = False, worktree: bool = False,
                 kind: str = "feature") -> Path:
    validate_slug(slug)
    if kind not in KINDS:
        raise AtipSpecError(f"Unknown kind {kind!r}: use feature or fix")
    if capability:
        validate_slug(capability, "capability")
    for name in impact or []:
        validate_slug(name, "impact entry")
    if initiative and not (project.initiatives / initiative / "roadmap.md").is_file():
        raise AtipSpecError(f"Initiative not found: {initiative}. Create it with `atipspec initiative {initiative} --title ...`")
    if (project.deliveries / slug).exists() or (project.archive / slug).exists():
        raise AtipSpecError(f"A delivery named {slug} already exists.")
    root = project.root
    if branch or worktree:
        if not project.git.available:
            raise AtipSpecError("--branch and --worktree need a git repository.")
        name = f"delivery/{slug}"
        if worktree:
            root = project.root.parent / f"{project.root.name}-{slug}"
            if root.exists():
                raise AtipSpecError(f"{root} already exists.")
            project.git.add_worktree(root, name)
        else:
            project.git.create_branch(name)
    base = project.git.head() if project.git.available else None
    directory = root / ".atipspec" / "deliveries" / slug
    replacements = {"title": title, "slug": slug, "verify": required_verify(project)}
    prefix = "fix-" if kind == "fix" else ""
    meta = {"title": title, "status": "draft", "capability": capability or slug, "impact": list(impact or []),
            "owner": owner, "ticket": ticket, "initiative": initiative, "base": base,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    if kind == "fix":
        meta = {"title": title, "status": "draft", "kind": "fix", **{k: v for k, v in meta.items() if k not in ("title", "status")}}
    files = {
        "spec.md": _from_template(f"{prefix}spec.md", meta, replacements),
        "plan.md": _from_template(f"{prefix}plan.md", {"title": title}, replacements),
        "deferred.md": _from_template("deferred.md", {"title": title}, replacements),
    }
    from .traceability import next_ids
    req_no, ac_no = next_ids(project, capability or slug)
    for filename in ("spec.md", "plan.md"):
        files[filename] = re.sub(r"REQ-(\d{3,})", lambda m: f"REQ-{req_no + int(m.group(1)) - 1:03d}", files[filename])
        files[filename] = re.sub(r"AC-(\d{3,})", lambda m: f"AC-{ac_no + int(m.group(1)) - 1:03d}", files[filename])
    directory.mkdir(parents=True)
    for name, content in files.items():
        (directory / name).write_text(content, encoding="utf-8")
    if initiative:
        register_in_roadmap(root / ".atipspec" / "initiatives" / initiative / "roadmap.md", slug, title)
    return directory


def register_in_roadmap(path: Path, slug: str, title: str) -> bool:
    """Add `- slug: title` under the roadmap's Deliveries section unless listed."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if slug in {item for item, _ in parse_roadmap(text).deliveries}:
        return False
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines)
                  if (match := HEADING2.match(line)) and match.group(1).lower().startswith("deliver")), None)
    if start is None:
        lines += ["", "## Deliveries", "", f"- {slug}: {title}"]
    else:
        end = next((index for index in range(start + 1, len(lines)) if HEADING2.match(lines[index])), len(lines))
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        lines.insert(end, f"- {slug}: {title}")
        if end == start + 1:
            lines.insert(end, "")
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return True


def next_decision_id(project: Project) -> str:
    numbers = [int(match.group(1)) for path in project.list_decisions()
               if (match := re.match(r"DEC-(\d+)", path.name))]
    return f"DEC-{max(numbers, default=0) + 1:03d}"


def new_decision(project: Project, slug: str, title: str, affects: list[str] | None = None) -> Path:
    validate_slug(slug)
    project.decisions.mkdir(parents=True, exist_ok=True)
    ident = next_decision_id(project)
    path = project.decisions / f"{ident}-{slug}.md"
    content = _from_template("decision.md", {
        "id": ident, "title": title, "status": "proposed", "affects": list(affects or []),
        "supersedes": None, "date": date.today().isoformat()}, {"title": title, "id": ident})
    path.write_text(content, encoding="utf-8")
    return path


def new_initiative(project: Project, slug: str, title: str) -> Path:
    validate_slug(slug)
    directory = project.initiatives / slug
    if directory.exists():
        raise AtipSpecError(f"An initiative named {slug} already exists.")
    directory.mkdir(parents=True)
    path = directory / "roadmap.md"
    path.write_text(_from_template("roadmap.md", {"title": title, "status": "active",
                                                  "created": date.today().isoformat()},
                                   {"title": title, "slug": slug}), encoding="utf-8")
    return path
