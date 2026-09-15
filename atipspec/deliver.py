"""Deliver a verified delivery: merge its requirements into the living spec of
its capability and move the folder to .atipspec/archive/."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import shutil

from . import frontmatter
from .check import check_delivery
from .delivery import Requirement, parse_spec
from .errors import AtipSpecError
from .project import Project, template, validate_slug

SECTION = re.compile(r"^###\s+(.+?)\s*$")


def _normalize(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    header: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        match = SECTION.match(line)
        if match:
            sections.append((match.group(1), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            header.append(line)
    return "\n".join(header), [(title, "\n".join(body).strip("\n")) for title, body in sections]


def merge_requirements(text: str, requirements: list[Requirement]) -> str:
    from .delivery import REQ_HEADING
    header, sections = split_sections(text)
    indexed = []
    for title, body in sections:
        match = REQ_HEADING.match("### " + title)
        if not match:
            raise AtipSpecError("Living spec requirements must have stable IDs: use headings like ### REQ-001: Title")
        indexed.append((match.group(1).upper(), title, body))
    for requirement in requirements:
        position = next((i for i, row in enumerate(indexed) if row[0] == requirement.id), None)
        if requirement.remove:
            if position is None:
                raise AtipSpecError(f"Cannot remove unknown requirement {requirement.id}")
            indexed.pop(position)
            continue
        entry = (requirement.id, f"{requirement.id}: {requirement.title}", "\n".join(requirement.body).strip("\n"))
        if position is None:
            indexed.append(entry)
        else:
            indexed[position] = entry
    parts = [header.rstrip("\n")]
    parts += [f"### {title}\n\n{body}" if body else f"### {title}" for _, title, body in indexed]
    return "\n\n".join(parts).rstrip("\n") + "\n"


def deliver(project: Project, slug: str, policy=None) -> tuple[Path, Path]:
    from .trust import selected_policy
    policy = policy or selected_policy(project)
    if policy is None:
        raise AtipSpecError("Delivery requires an external trust policy; a local check is not human acceptance")
    report = check_delivery(project, slug, policy=policy)
    if not report.ok:
        raise AtipSpecError("Cannot deliver: the check is not green.\n" + report.render())
    directory = project.delivery_dir(slug)
    target = project.archive / slug
    if target.exists():
        raise AtipSpecError(f"{project.rel(target)} already exists.")
    spec_path = directory / "spec.md"
    spec = parse_spec(spec_path.read_text(encoding="utf-8"))
    capability = validate_slug(spec.capability, "capability") if spec.capability else slug
    living = project.specs / f"{capability}.md"
    if living.is_file():
        text = living.read_text(encoding="utf-8")
    else:
        text = template("capability.md").replace("{{capability}}", capability)
    project.specs.mkdir(parents=True, exist_ok=True)
    merged = merge_requirements(text, spec.requirements)
    from .reporting import report_data
    import json
    receipt = report_data(project, slug, policy, report=report)
    (directory / "reports").mkdir(exist_ok=True)
    (directory / "reports" / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    living.write_text(merged, encoding="utf-8")
    meta, body = frontmatter.split(spec_path.read_text(encoding="utf-8"))
    meta["status"] = "delivered"
    meta["delivered"] = date.today().isoformat()
    spec_path.write_text(frontmatter.compose(meta, body), encoding="utf-8")
    project.archive.mkdir(parents=True, exist_ok=True)
    shutil.move(str(directory), str(target))
    return living, target
