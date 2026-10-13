"""Reviewable imports and opt-in migration, with exact-input checks and backups.

`atipspec spec-bind` imports an acceptance-criteria document through
`convert_spec`; `atipspec migrate` turns a legacy delivery into a guided one
through `prepare_migration`, shown as a diff before `--apply` writes it.
Importing a historical done/approved document never imports its approval or
execution status, and neither grants one: the human approves the result with
the delivery's proposal. The original remains available for reviewing
constraints and history that the small parser cannot interpret semantically.
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
from .traceability import token
from .trust import canonical, digest, read_regular

IMPORT_NAMESPACE = uuid.UUID("36689ef2-5f4c-4a92-a41b-c1ce915909e4")
FORMATS = {"atipspec": "AtipSpec", "acceptance": "acceptance criteria"}


def _ident(kind, capability, title):
    # Stable on repeated previews; IDs emitted into the imported spec should
    # subsequently be preserved explicitly, including when titles change.
    key = f"{capability}/{kind}/{title.strip().casefold()}"
    return f"{kind}-{capability.upper()}-{token(uuid.uuid5(IMPORT_NAMESPACE, key).bytes)}-001"


def _section(text, title):
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"^#{2,3}\s+" + title + r"\s*$", line, re.I)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#{1,3}\s", lines[i])), len(lines))
    return "\n".join(lines[start + 1:end]).strip()


def _steps(item):
    """`**Given** a, **When** b, **Then** c` as scenario steps, or None when
    the item has no WHEN and THEN."""
    words = list(re.finditer(r"\*\*(GIVEN|WHEN|THEN|AND|BUT)\*\*\s*", item, re.I))
    if not words or not {match.group(1).upper() for match in words} >= {"WHEN", "THEN"}:
        return None
    steps = []
    for index, match in enumerate(words):
        end = words[index + 1].start() if index + 1 < len(words) else len(item)
        value = item[match.end():end].strip().rstrip(",;—–-").strip()
        steps.append(f"- **{match.group(1).upper()}** {value}")
    return steps


def detect_format(text) -> str | None:
    """The source format `convert_spec` reads, or None."""
    _, body = frontmatter.split(text)
    if parse_spec(text).requirements:
        return "atipspec"
    normalized = re.sub(r"^\*\*Acceptance Criteria:\*\*\s*$", "## Acceptance Criteria", body, flags=re.M | re.I)
    if _section(normalized, r"(?:Acceptance Criteria|Criterios de aceptación|Critérios de aceitação)"):
        return "acceptance"
    return None


def convert_spec(text, capability):
    """The document as AtipSpec requirements and criteria, the notes for the
    human who approves the import, and the format it came in."""
    form = detect_format(text)
    parsed = parse_spec(text)
    if form == "atipspec":
        if parsed.problems:
            raise AtipSpecError("; ".join(parsed.problems))
        return text, ["Existing requirement and criterion IDs were preserved."], form
    meta, body = frontmatter.split(text)
    title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), str(meta.get("title") or capability))
    # Recognize the acceptance section, including one that opens with a bold
    # `**Acceptance Criteria:**` line. Other checkboxes are execution history, not ACs.
    normalized = re.sub(r"^\*\*Acceptance Criteria:\*\*\s*$", "## Acceptance Criteria", body, flags=re.M | re.I)
    acceptance = _section(normalized, r"(?:Acceptance Criteria|Criterios de aceptación|Critérios de aceitação)")
    if not acceptance:
        raise AtipSpecError("No supported requirements or acceptance section found; bind AtipSpec requirements with "
                            "their IDs, or import explicit numbered or bulleted criteria under an Acceptance Criteria "
                            "heading")
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
    parts = [f"# {title}", "", "## Purpose", "", intent or title, "", f"### {req}: {title}", ""]
    scenarios = []   # after the plain criteria: a criterion line under a scenario heading would be one of its steps
    for index, item in enumerate(items, 1):
        ac = _ident("AC", capability, title + f"/{index}")
        steps = _steps(item)
        if steps:
            scenarios += [f"#### {ac}: Acceptance {index}"] + steps + [""]
        else:
            parts += [f"- {ac}: {item}", ""]
    parts += scenarios
    converted = "\n".join(parts).rstrip() + "\n"
    result = parse_spec(converted)
    if result.problems or not result.requirements or any(not req.criteria for req in result.requirements):
        raise AtipSpecError("Converted specification is incomplete: " + "; ".join(result.problems or ["requirements need acceptance criteria"]))
    return converted, ["Only explicit acceptance criteria were converted; implementation checkboxes and prior done "
                       "status are historical, not new evidence. Review the preserved original for additional "
                       "constraints."], form


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


def prepare_migration(project, slug):
    directory = project.delivery_dir(slug)
    path = directory / "spec.md"
    original = read_regular(path).decode("utf-8")
    spec = parse_spec(original)
    if spec.meta.get("schema") == 2:
        raise AtipSpecError("This delivery already uses canonical specifications")
    if spec.kind == "fix":
        raise AtipSpecError("A legacy fix keeps its legacy flow until it is delivered; `migrate` converts features")
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
    retained = _without_empty_sections(retained, r"(?:Requirements|Requisitos)")
    changes = {project.rel(path): frontmatter.compose(meta, "\n".join(retained).rstrip() + "\n"),
               project.rel(target): canonical_text,
               project.rel(directory / "baseline.json"): json.dumps(baseline(project, spec.capability), indent=2, ensure_ascii=False) + "\n"}
    return _preview(project, slug, "migration", changes, warnings=[
        "Original files and approval records are backed up. Historical approvals/evidence are not reclassified or accepted for the migrated candidate.",
        "The existing verification plan is preserved; move shared checks into Final verification explicitly after reviewing their execution semantics."])


def _without_empty_sections(lines, title):
    """`lines` without each `## <title>` heading that only blank lines follow."""
    kept = []
    for index, line in enumerate(lines):
        if re.match(r"^##\s+" + title + r"\s*$", line, re.I):
            end = next((i for i in range(index + 1, len(lines)) if re.match(r"^#{1,2}\s", lines[i])), len(lines))
            if not any(item.strip() for item in lines[index + 1:end]):
                while kept and not kept[-1].strip():
                    kept.pop()
                continue
        kept.append(line)
    return kept


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
        (archive / "preview.json").write_text(json.dumps(preview, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8", newline="\n")
        written = []
        try:
            for name, content in preview["changes"].items():
                target = project.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                written.append(name)
                target.write_text(content, encoding="utf-8", newline="\n")
        except OSError:
            for name in reversed(written):
                original = backups[name]
                if original is None:
                    (project.root / name).unlink(missing_ok=True)
                else:
                    (project.root / name).write_bytes(original)
            raise
        (archive / "applied.json").write_text(json.dumps({"schema": 1, "digest": actual_digest, "accepted": False}) + "\n",
                                              encoding="utf-8", newline="\n")
        return archive
