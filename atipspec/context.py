"""Build the context a delivery needs: the contract, the living documents, the
living specs it touches, the decisions that affect them, and its own files.
Never the archive. Reports its size against the project's budget."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import frontmatter
from .delivery import parse_spec
from .project import Project


@dataclass
class Section:
    label: str
    text: str

    @property
    def lines(self) -> int:
        return self.text.count("\n") + (0 if self.text.endswith("\n") or not self.text else 1)


def _read(path: Path | None) -> str:
    return path.read_text(encoding="utf-8") if path is not None and path.is_file() else ""


def decisions_for(project: Project, names: list[str]) -> list[tuple[Path, dict]]:
    """Accepted decisions whose `affects` list names one of `names` (a
    capability, or `contract` / `contract:<section>`), or that affect everything."""
    wanted = set(names) | {"contract"}
    chosen = []
    for path in project.list_decisions():
        try:
            meta, _ = frontmatter.split(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if meta.get("status") != "accepted":
            continue
        affects = meta.get("affects") or []
        affects = [str(item) for item in affects] if isinstance(affects, list) else [str(affects)]
        if not affects or "*" in affects or any(item.split(":")[0] in wanted for item in affects):
            chosen.append((path, meta))
    return chosen


def build_context(project: Project, slug: str) -> tuple[list[Section], str]:
    directory = project.delivery_dir(slug)
    spec_text = _read(directory / "spec.md")
    spec = parse_spec(spec_text)
    sections: list[Section] = []

    def add(label: str, text: str) -> None:
        if text.strip():
            sections.append(Section(label, text.rstrip() + "\n"))

    add("contract (.atipspec/contract.md)", _read(project.contract))
    system = project.system
    if system is not None:
        add(f"system contract ({system / 'contract.md'})", _read(system / "contract.md"))
    add("overview (.atipspec/overview.md)", _read(project.overview))
    add("glossary (.atipspec/glossary.md)", _read(project.glossary))
    if system is not None:
        add(f"system glossary ({system / 'glossary.md'})", _read(system / "glossary.md"))
    for name in spec.impact:
        add(f"living spec {name} (.atipspec/specs/{name}.md)", _read(project.specs / f"{name}.md"))
    for path, meta in decisions_for(project, spec.impact):
        add(f"decision {meta.get('id') or path.stem}", _read(path))
    add(f"brief (.atipspec/deliveries/{slug}/brief.md)", _read(directory / "brief.md"))
    add(f"spec (.atipspec/deliveries/{slug}/spec.md)", spec_text)
    add(f"plan (.atipspec/deliveries/{slug}/plan.md)", _read(directory / "plan.md"))

    total = sum(section.lines for section in sections)
    budget = int(project.policy("context_budget"))
    summary = [f"Context for {slug}: {total} lines (budget {budget})"]
    summary += [f"  {section.lines:>5}  {section.label}" for section in sections]
    if total > budget:
        summary.append(f"  over budget by {total - budget} lines: run the curate phase, split living specs, "
                       "or narrow the impact list")
    return sections, "\n".join(summary)


def render_context(sections: list[Section]) -> str:
    parts = []
    for section in sections:
        parts.append(f"<!-- atipspec context: {section.label} -->\n{section.text}")
    return "\n".join(parts)
