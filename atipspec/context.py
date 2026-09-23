"""Build the context a delivery needs: the contract, the living documents, the
living specs it touches, the decisions that affect them, and its own files.
Never the archive. Reports its size against the project's budget."""
from __future__ import annotations

from .specs import load_spec

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


def build_context(project: Project, slug: str, *, role=None, task_id=None) -> tuple[list[Section], str]:
    directory = project.delivery_dir(slug)
    spec_text = _read(directory / "spec.md")
    spec = load_spec(project, slug)
    task = None
    if task_id:
        from .delivery import parse_plan
        from .errors import AtipSpecError
        plan = parse_plan(_read(directory / "plan.md"))
        task = next((task for task in plan.tasks if task.id == task_id), None)
        if task is None:
            raise AtipSpecError(f"Unknown context task: {task_id}")
    sections: list[Section] = []

    def add(label: str, text: str) -> None:
        if text.strip():
            if role:
                from .trust import digest
                label += f" sha256:{digest(text.encode('utf-8'))}"
            sections.append(Section(label, text.rstrip() + "\n"))

    if role:
        from .roles import role_instruction
        add(f"role {role}", role_instruction(role, str(spec.meta.get("risk") or "normal")))

    add("contract (.atipspec/contract.md)", _read(project.contract))
    system = project.system
    if system is not None:
        add(f"system contract ({system / 'contract.md'})", _read(system / "contract.md"))
    if spec.meta.get("schema") == 2:
        from .teams import read_contracts
        for contract in read_contracts(project, slug):
            add(f"pinned contract {contract['name']} ({contract['repository']}@{contract['revision']}:{contract['path']})",
                contract["content"])
    if role not in ("implementer", "reviewer", "tester"):
        add("overview (.atipspec/overview.md)", _read(project.overview))
    add("glossary (.atipspec/glossary.md)", _read(project.glossary))
    if system is not None:
        add(f"system glossary ({system / 'glossary.md'})", _read(system / "glossary.md"))
    for name in spec.impact:
        text = _read(project.specs / f"{name}.md")
        if task and name == spec.capability:
            text = "\n\n".join(f"### {req.id}: {req.title}\n" + "\n".join(req.body)
                               for req in spec.requirements if req.id in task.covers)
        add(f"living spec {name} (.atipspec/specs/{name}.md)", text)
    for path, meta in decisions_for(project, spec.impact):
        add(f"decision {meta.get('id') or path.stem}", _read(path))
    add(f"brief (.atipspec/deliveries/{slug}/brief.md)", _read(directory / "brief.md"))
    add(f"spec (.atipspec/deliveries/{slug}/spec.md)", spec_text)
    plan_text = _read(directory / "plan.md")
    if task:
        from dataclasses import asdict
        import json
        from .delivery import plan_commitments
        plan_text = plan_commitments(plan_text) + "\nAssigned operational task:\n" + json.dumps(asdict(task), ensure_ascii=False)
    add(f"plan (.atipspec/deliveries/{slug}/plan.md)", plan_text)

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
