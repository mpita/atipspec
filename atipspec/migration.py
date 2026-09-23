"""Reviewable imports and opt-in migration, with exact-input checks and backups.

Importing a historical done/approved document never imports its approval or
execution status. The original remains available for reviewing constraints and
history that the small parser cannot interpret semantically.
"""
from __future__ import annotations

from dataclasses import replace
import difflib
import json
from pathlib import Path
import re
import uuid

from . import frontmatter
from .deliver import merge_requirements
from .delivery import parse_spec, REQ_HEADING
from .errors import AtipSpecError
from .specs import baseline, canonical_path
from .trust import canonical, digest, read_regular

IMPORT_NAMESPACE = uuid.UUID("36689ef2-5f4c-4a92-a41b-c1ce915909e4")


def _ident(kind, capability, title):
    # Stable on repeated previews; IDs emitted into the imported spec should
    # subsequently be preserved explicitly, including when titles change.
    key = f"{capability}/{kind}/{title.strip().casefold()}"
    component = uuid.uuid5(IMPORT_NAMESPACE, key).hex.upper()
    return f"{kind}-{capability.upper()}-{component}-001"


def _section(text, title):
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"^#{2,3}\s+" + title + r"\s*$", line, re.I)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#{1,3}\s", lines[i])), len(lines))
    return "\n".join(lines[start + 1:end]).strip()


def convert_spec(text, capability):
    parsed = parse_spec(text)
    warnings = []
    if parsed.requirements:
        if parsed.problems:
            raise AtipSpecError("; ".join(parsed.problems))
        return text, ["Existing requirement and criterion IDs were preserved."]
    if re.search(r"^##\s+REMOVED\s+Requirements", text, re.M | re.I):
        raise AtipSpecError("Removed requirements need explicit existing IDs and removal criteria; do not infer deletion from an import")
    if re.search(r"^###\s+(?:Requirement|Requisito):", text, re.M | re.I):
        output, current, seen_req, seen_ac = [], None, set(), set()
        _, body = frontmatter.split(text)
        for line in body.splitlines():
            requirement = re.match(r"^###\s+(?:Requirement|Requisito):\s*(.+)$", line, re.I)
            scenario = re.match(r"^####\s+(?:Scenario|Escenario|Cenário):\s*(.+)$", line, re.I)
            if requirement:
                current = requirement.group(1).strip()
                ident = _ident("REQ", capability, current)
                if ident in seen_req:
                    raise AtipSpecError("Duplicate external requirement titles need explicit distinct IDs before import")
                seen_req.add(ident)
                line = f"### {ident}: {current}"
            elif scenario:
                if current is None:
                    raise AtipSpecError("External scenario is outside a requirement")
                title = scenario.group(1).strip()
                ident = _ident("AC", capability, current + "/" + title)
                if ident in seen_ac:
                    raise AtipSpecError("Duplicate external scenario titles need explicit distinct IDs before import")
                seen_ac.add(ident)
                line = f"#### {ident}: {title}"
            output.append(line)
        converted = "\n".join(output).rstrip() + "\n"
        warnings.append("Generated stable IDs from capability and titles. Preserve these explicit IDs on future edits; renaming an ID-less source cannot be inferred as a rename.")
    else:
        meta, body = frontmatter.split(text)
        title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), str(meta.get("title") or capability))
        # Recognize the acceptance section, including the inline heading used by
        # quick bugfix documents. Other checkboxes are execution history, not ACs.
        normalized = re.sub(r"^\*\*Acceptance Criteria:\*\*\s*$", "## Acceptance Criteria", body, flags=re.M | re.I)
        acceptance = _section(normalized, r"(?:Acceptance Criteria|Criterios de aceptación|Critérios de aceitação)")
        if not acceptance:
            raise AtipSpecError("No supported requirements or acceptance section found; import ATIPSpec, OpenSpec scenarios or explicit numbered/bulleted acceptance criteria")
        items = []
        for line in acceptance.splitlines():
            match = re.match(r"^(?:\d+[.)]|[-*])\s+(.*)$", line)
            if match:
                items.append(match.group(1))
            elif line.strip() and items:
                items[-1] += " " + line.strip()
        if not items:
            raise AtipSpecError("Acceptance section has no explicit criteria")
        req = _ident("REQ", capability, title)
        intent = _section(body, "Intent") or _section(body, "Story")
        constraints = _section(body, r"Boundaries & Constraints")
        parts = [f"# {title}", "", "## Purpose", "", intent or title, "", f"### {req}: {title}", ""]
        if constraints:
            parts += ["Source constraints:", "", constraints, ""]
        for index, item in enumerate(items, 1):
            ac = _ident("AC", capability, title + f"/{index}")
            words = list(re.finditer(r"\*\*(GIVEN|WHEN|THEN|AND|BUT)\*\*\s*", item, re.I))
            if words and {match.group(1).upper() for match in words} >= {"WHEN", "THEN"}:
                parts += [f"#### {ac}: Acceptance {index}"]
                for word_index, match in enumerate(words):
                    end = words[word_index + 1].start() if word_index + 1 < len(words) else len(item)
                    value = item[match.end():end].strip().rstrip("—–-").strip()
                    parts.append(f"- **{match.group(1).upper()}** {value}")
            else:
                parts += [f"- {ac}: {item}"]
            parts.append("")
        matrix = _section(body, r"I/O & Edge-Case Matrix")
        if matrix:
            # Keep potentially contradictory expectations visible. Resolving
            # them is a semantic/human decision, not an import heuristic.
            parts += ["## Source expectation matrix", "", matrix, ""]
            warnings.append("The source also has an expectation matrix. Reconcile it with the acceptance criteria before approving; both were preserved.")
        converted = "\n".join(parts).rstrip() + "\n"
        warnings.append("Only explicit acceptance criteria were converted; implementation checkboxes and prior done status are historical, not new evidence. Review the preserved original for additional constraints.")
    result = parse_spec(converted)
    if result.problems or not result.requirements or any(not req.criteria for req in result.requirements):
        raise AtipSpecError("Converted specification is incomplete: " + "; ".join(result.problems or ["requirements need acceptance criteria"]))
    return converted, warnings


def _proposed_canonical(previous, requirements):
    known = {req.id for req in parse_spec(previous).requirements}
    for req in requirements:
        if req.remove and (req.id not in known or not req.criteria):
            raise AtipSpecError(f"Removal {req.id} needs an existing requirement and explicit criteria")
    merged = merge_requirements(previous, [replace(req, remove=False) for req in requirements])
    for req in requirements:
        if req.remove:
            merged = re.sub(r"^### " + re.escape(req.id) + r":", f"### {req.id} [remove]:", merged, flags=re.M)
    ids = [ac.id for ac in parse_spec(merged).criteria]
    if len(ids) != len(set(ids)):
        raise AtipSpecError("Criterion IDs collide with an existing canonical requirement")
    return merged


def _preview(project, slug, operation, changes, *, source=None, warnings=None):
    before = {}
    for name in changes:
        path = project.root / name
        if not path.resolve().is_relative_to(project.root.resolve()) or any(part.is_symlink() for part in (path, *path.parents)):
            raise AtipSpecError("Migration paths must stay inside the repository without symlinks")
        before[name] = digest(read_regular(path)) if path.exists() else None
    data = {"schema": 1, "operation": operation, "delivery": slug, "before": before,
            "changes": changes, "source": source, "warnings": warnings or []}
    data["digest"] = digest(canonical(data))
    return data


def prepare_import(project, slug, source):
    directory = project.delivery_dir(slug)
    spec_path = directory / "spec.md"
    meta, body = frontmatter.split(read_regular(spec_path).decode("utf-8"))
    if meta.get("schema") != 2:
        raise AtipSpecError("Migrate the legacy delivery before importing canonical requirements")
    raw = read_regular(source).decode("utf-8")
    capability = parse_spec(spec_path.read_text()).capability
    converted, warnings = convert_spec(raw, capability)
    incoming = parse_spec(converted)
    target = canonical_path(project, parse_spec(spec_path.read_text()))
    previous = read_regular(target).decode("utf-8") if target.exists() else ""
    if previous:
        canonical_text = _proposed_canonical(previous, incoming.requirements)
    else:
        canonical_text = converted
    meta["requirements"] = [req.id for req in incoming.requirements]
    meta["status"] = "draft"
    source_id = digest(raw.encode("utf-8"))
    # A retained source is part of the approved input, not merely an ignored log.
    reference = f".atipspec/deliveries/{slug}/sources/{source_id}.md"
    existing = meta.get("sources") or []
    if not isinstance(existing, list):
        raise AtipSpecError("sources must be a list")
    meta["sources"] = list(dict.fromkeys(existing + [reference]))
    if warnings:
        body += "\n## Import review notes\n\n" + "\n".join(f"- {warning}" for warning in warnings) + "\n"
    return _preview(project, slug, "import", {project.rel(spec_path): frontmatter.compose(meta, body),
                    project.rel(target): canonical_text, reference: raw},
                    source={"path": str(source.resolve()), "sha256": source_id}, warnings=warnings)


def prepare_migration(project, slug):
    directory = project.delivery_dir(slug)
    path = directory / "spec.md"
    original = read_regular(path).decode("utf-8")
    spec = parse_spec(original)
    if spec.meta.get("schema") == 2:
        raise AtipSpecError("This delivery already uses canonical specifications")
    if spec.problems or not spec.requirements:
        raise AtipSpecError("Complete the legacy spec before migrating: " + "; ".join(spec.problems or ["no requirements"]))
    target = canonical_path(project, spec)
    previous = read_regular(target).decode("utf-8") if target.exists() else f"# {spec.capability}\n\n## Requirements\n"
    canonical_text = _proposed_canonical(previous, spec.requirements)
    meta, body = frontmatter.split(original)
    meta.update(schema=2, status="draft", change_id=uuid.uuid5(IMPORT_NAMESPACE, str(project.root) + "/" + slug).hex,
                requirements=[req.id for req in spec.requirements], risk="normal")
    retained, skipping = [], False
    for line in body.splitlines():
        if REQ_HEADING.match(line):
            skipping = True
            continue
        if re.match(r"^##\s", line):
            skipping = False
        if not skipping:
            retained.append(line)
    changes = {project.rel(path): frontmatter.compose(meta, "\n".join(retained).rstrip() + "\n"),
               project.rel(target): canonical_text,
               project.rel(directory / "baseline.json"): json.dumps(baseline(project, spec.capability), indent=2, ensure_ascii=False) + "\n"}
    return _preview(project, slug, "migration", changes, warnings=[
        "Original files and approval records are backed up. Historical approvals/evidence are not reclassified or accepted for the migrated candidate.",
        "The existing verification plan is preserved; move shared checks into Final verification explicitly after reviewing their execution semantics."])


def render_preview(project, preview):
    lines = [f"{preview['operation']} preview for {preview['delivery']}", f"Digest: {preview['digest']}", ""]
    lines += [f"- {warning}" for warning in preview["warnings"]]
    for name, after in preview["changes"].items():
        path = project.root / name
        before = read_regular(path).decode("utf-8") if path.exists() else ""
        lines += ["", "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                   fromfile=name + " (before)", tofile=name + " (after)")).rstrip()]
    return "\n".join(lines).rstrip() + "\n"


def apply_preview(project, preview, expected_digest):
    check = dict(preview)
    actual_digest = check.pop("digest")
    if actual_digest != expected_digest or digest(canonical(check)) != actual_digest:
        raise AtipSpecError("The preview changed; inspect its new diff before applying that digest")
    from .runner import _lock
    with _lock(project):
        for name, expected in preview["before"].items():
            path = project.root / name
            actual = digest(read_regular(path)) if path.exists() else None
            if actual != expected:
                raise AtipSpecError(f"{name} changed since preview; regenerate the diff")
        source = preview.get("source")
        if source and digest(read_regular(Path(source["path"]))) != source["sha256"]:
            raise AtipSpecError("Import source changed since preview")
        archive = project.dot / "migrations" / actual_digest
        if archive.exists():
            raise AtipSpecError("This preview was already applied or backed up; inspect its manifest before retrying")
        backups = {name: read_regular(project.root / name) if (project.root / name).exists() else None for name in preview["changes"]}
        approvals = project.delivery_dir(preview["delivery"]) / "approvals"
        for path in approvals.glob("*"):
            if path.is_file():
                backups[project.rel(path)] = read_regular(path)
        archive.mkdir(parents=True)
        for name, content in backups.items():
            if content is not None:
                target = archive / "originals" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        (archive / "preview.json").write_text(json.dumps(preview, indent=2, ensure_ascii=False) + "\n")
        written = []
        try:
            for name, content in preview["changes"].items():
                target = project.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                written.append(name)
                target.write_text(content, encoding="utf-8")
        except OSError:
            for name in reversed(written):
                original = backups[name]
                if original is None:
                    (project.root / name).unlink(missing_ok=True)
                else:
                    (project.root / name).write_bytes(original)
            raise
        (archive / "applied.json").write_text(json.dumps({"schema": 1, "digest": actual_digest, "accepted": False}) + "\n")
        return archive
