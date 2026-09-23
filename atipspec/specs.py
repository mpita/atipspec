"""Canonical working-branch specifications and compact delivery references.

Legacy deliveries retain their embedded requirements until explicitly migrated.
Guided deliveries bind a selection in specs/ and keep a creation-time baseline,
so uncommitted local work can be reviewed against what preceded the change.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import frontmatter
from .delivery import REQ_ID, parse_spec
from .errors import AtipSpecError
from .project import validate_slug


def canonical_path(project, spec):
    return project.specs / f"{validate_slug(spec.capability or '', 'capability')}.md"


def load_spec(project, slug):
    from .trust import read_regular
    path = project.delivery_dir(slug) / "spec.md"
    spec = parse_spec(read_regular(path).decode("utf-8"))
    if spec.meta.get("schema") != 2:
        return spec
    if spec.requirements:
        spec.problems.append("Guided deliveries reference canonical requirements; move their definition into specs/")
        return spec
    refs = spec.meta.get("requirements", [])
    if not isinstance(refs, list) or any(not isinstance(ident, str) or not REQ_ID.fullmatch(ident) for ident in refs):
        spec.problems.append("requirements must be a list of stable REQ IDs from the canonical capability")
        return spec
    refs = [ident.upper() for ident in refs]
    if len(refs) != len(set(refs)):
        spec.problems.append("requirements contains duplicate references")
    source = canonical_path(project, spec)
    if not refs:
        return spec
    if not source.is_file():
        spec.problems.append(f"Referenced specification is missing: {project.rel(source)}")
        return spec
    canonical = parse_spec(read_regular(source).decode("utf-8"))
    spec.problems.extend(canonical.problems)
    spec.open_questions.extend(canonical.open_questions)
    spec.assumptions.extend(canonical.assumptions)
    known = {req.id: req for req in canonical.requirements}
    if len(known) != len(canonical.requirements):
        spec.problems.append("Canonical specification contains duplicate requirement IDs")
    criteria = [ac.id for ac in canonical.criteria]
    if len(criteria) != len(set(criteria)):
        spec.problems.append("Canonical specification contains duplicate criterion IDs")
    for ident in refs:
        if ident not in known:
            spec.problems.append(f"Unknown canonical requirement {spec.capability}/{ident}")
        else:
            spec.requirements.append(known[ident])
    return spec


def baseline(project, capability):
    path = project.specs / f"{validate_slug(capability)}.md"
    from .trust import read_regular
    return {"schema": 1, "capability": capability,
            "content": read_regular(path).decode("utf-8") if path.exists() else "",
            "head": project.git.head()}


def bind_spec(project, slug, source: Path):
    """Install an authored spec and bind its requirements without accepting it.

    Existing requirements outside the imported selection are preserved. The
    caller reviews the diff before approving; this command grants no authority.
    """
    from .trust import read_regular
    from .deliver import merge_requirements
    directory = project.delivery_dir(slug)
    path = directory / "spec.md"
    meta, body = frontmatter.split(read_regular(path).decode("utf-8"))
    if meta.get("schema") != 2:
        raise AtipSpecError("This is a legacy delivery; migrate it explicitly before binding a canonical spec")
    incoming = parse_spec(read_regular(source).decode("utf-8"))
    if incoming.problems or incoming.open_questions or not incoming.requirements:
        raise AtipSpecError("Cannot bind the specification: " + "; ".join(incoming.problems or ["requirements must be complete and questions resolved"]))
    if any(not req.criteria for req in incoming.requirements):
        raise AtipSpecError("Every imported requirement, including removal, needs acceptance criteria")
    ids = [req.id for req in incoming.requirements]
    ac_ids = [ac.id for ac in incoming.criteria]
    if len(ids) != len(set(ids)) or len(ac_ids) != len(set(ac_ids)):
        raise AtipSpecError("Imported requirements and criteria need unique IDs")
    spec = parse_spec(read_regular(path).decode("utf-8"))
    target = canonical_path(project, spec)
    if any(part.is_symlink() for part in (target, *target.parents)):
        raise AtipSpecError("Refusing a symlinked canonical spec path")
    previous = read_regular(target).decode("utf-8") if target.exists() else f"# {spec.capability}\n\n## Requirements\n"
    merged = merge_requirements(previous, incoming.requirements)
    merged_spec = parse_spec(merged)
    merged_criteria = [ac.id for ac in merged_spec.criteria]
    if len(merged_criteria) != len(set(merged_criteria)):
        raise AtipSpecError("An imported criterion ID already belongs to another canonical requirement; preserve identities explicitly")
    # For removals, keep the explicit proposed tombstone and its criteria until
    # acceptance. deliver removes it from the accepted capability.
    if any(req.remove for req in incoming.requirements):
        raise AtipSpecError("Bind supports additions and replacements; reference an explicit removal in the canonical spec directly")
    meta["requirements"] = ids
    meta["status"] = "draft"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(merged, encoding="utf-8")
    path.write_text(frontmatter.compose(meta, body), encoding="utf-8")
    return target


def baseline_text(project, slug):
    from .trust import read_regular
    path = project.delivery_dir(slug) / "baseline.json"
    try:
        data = json.loads(read_regular(path))
        if data.get("schema") != 1 or not isinstance(data.get("content"), str):
            raise ValueError("invalid baseline schema")
        return data["content"]
    except (OSError, ValueError, TypeError) as exc:
        raise AtipSpecError(f"Missing or invalid immutable delivery baseline: {exc}") from exc
