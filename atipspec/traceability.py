"""Capability-scoped stable requirement and criterion identities."""
from __future__ import annotations

from .delivery import parse_spec
from .project import validate_slug


def next_ids(project, capability):
    validate_slug(capability, "capability")
    paths = [project.specs / f"{capability}.md"]
    for folder in (project.deliveries, project.archive):
        for path in folder.glob("*/spec.md"):
            if parse_spec(path.read_text()).capability == capability:
                paths.append(path)
    requirements, criteria = [0], [0]
    for path in paths:
        if not path.is_file():
            continue
        spec = parse_spec(path.read_text())
        requirements += [int(req.id[4:]) for req in spec.requirements]
        criteria += [int(ac.id[3:]) for ac in spec.criteria]
    return max(requirements) + 1, max(criteria) + 1


def merge_conflicts(project, spec, slug=None):
    """Three-way check of the living requirements a delivery intends to replace."""
    capability = spec.capability or slug
    base = spec.meta.get("base")
    if not capability or not base or not project.git.rev_exists(base):
        return []
    path = f".atipspec/specs/{validate_slug(capability)}.md"
    current_path = project.root / path
    current = parse_spec(current_path.read_text()) if current_path.is_file() else parse_spec("")
    old = parse_spec(project.git.run("show", f"{base}:{path}")) if project.git.exists_at(base, path) else parse_spec("")
    def rows(parsed):
        return {req.id: (req.title, req.body) for req in parsed.requirements}
    before, now = rows(old), rows(current)
    conflicts = []
    for req in spec.requirements:
        if req.remove and req.id not in now:
            conflicts.append(f"Cannot remove unknown requirement {capability}/{req.id}")
        if before.get(req.id) != now.get(req.id):
            conflicts.append(f"{capability}/{req.id} changed since the delivery base; reconcile the specification and base explicitly")
    old_ac = {ac.id: ac.requirement for ac in current.criteria}
    for req in spec.requirements:
        for ac in req.criteria:
            if ac.id in old_ac and old_ac[ac.id] != req.id:
                conflicts.append(f"{capability}/{ac.id} already belongs to {old_ac[ac.id]}")
    return conflicts
