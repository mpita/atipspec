"""Canonical working-branch specifications and compact delivery references.

Legacy deliveries keep their embedded requirements unless `atipspec migrate` converts them.
Guided deliveries bind a selection in specs/ and are compared with the living
spec at the base commit `new` recorded, which refuses to start over changes to
it not committed yet; one created before 0.3.0 keeps its creation-time baseline.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from . import frontmatter
from .delivery import REQ_HEADING, REQ_ID, Requirement, parse_spec
from .errors import AtipSpecError
from .project import SLUG, validate_slug

COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
LIVING = re.compile(r"\.atipspec/specs/[^/]+\.md")
RECEIPT = re.compile(r"(?:^|/)\.atipspec/archive/([^/]+)/reports/acceptance\.json$")
MISSING_BASE = "the recorded base commit is missing; restore history before checking"


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
    canonical = parse_spec(read_regular(source).decode("utf-8"), project.rel(source))
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
    from .trust import text_bytes
    return {"schema": 1, "capability": capability,
            "content": text_bytes(path).decode("utf-8") if path.exists() else "",
            "head": project.git.head()}


IMPORT_NOTES = "## Import review notes"


@dataclass
class Bound:
    """What `spec-bind` wrote."""
    target: Path                 # the living spec that holds the requirements
    form: str                    # the source's format: atipspec, or acceptance for an import
    notes: list[str]             # what the human checks before approving an import
    source: str | None = None    # where an imported original is kept


def bind_spec(project, slug, source: Path) -> Bound:
    """Install an authored spec and bind its requirements without accepting it.

    Existing requirements outside the imported selection are preserved. A
    document without requirement IDs, a list of acceptance criteria, is
    converted first: its original is kept in the delivery's sources/ and
    `## Import review notes` in spec.md lists what to check. The caller
    reviews the diff before approving; this command grants no authority.
    """
    from .trust import digest, read_regular
    from .deliver import merge_requirements
    directory = project.delivery_dir(slug)
    path = directory / "spec.md"
    meta, body = frontmatter.split(read_regular(path).decode("utf-8"))
    if meta.get("schema") != 2:
        raise AtipSpecError("This is a legacy delivery; migrate it with `atipspec migrate` before binding a canonical spec")
    raw = read_regular(source).decode("utf-8")
    incoming = parse_spec(raw, str(source))
    form, notes, kept = "atipspec", [], None
    if not incoming.requirements:
        from .migration import convert_spec
        capability = validate_slug(str(meta.get("capability") or ""), "capability")
        converted, notes, form = convert_spec(raw, capability)
        incoming = parse_spec(converted, f"{source} as converted")
        kept = f".atipspec/deliveries/{slug}/sources/{digest(raw.encode('utf-8'))}.md"
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
    if kept:
        existing = requirements_of(previous)
        clashes = [f"{req.id} ({existing[req.id].title!r} there, {req.title!r} here)" for req in incoming.requirements
                   if req.id in existing and existing[req.id].title.casefold() != req.title.casefold()]
        if clashes:
            raise AtipSpecError(f"A generated ID already names another requirement in {project.rel(target)}: "
                                f"{'; '.join(clashes)}; give the source explicit IDs before importing")
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
    if kept:
        original = project.root / kept
        if any(part.is_symlink() for part in (original, *original.parents)):
            raise AtipSpecError("Refusing a symlinked import source path")
        sources = meta.get("sources") or []
        if not isinstance(sources, list):
            raise AtipSpecError("sources in spec.md must be a list")
        meta["sources"] = list(dict.fromkeys([*sources, kept]))
        body = _with_notes(body, notes)
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_text(raw, encoding="utf-8", newline="\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(merged, encoding="utf-8", newline="\n")
    path.write_text(frontmatter.compose(meta, body), encoding="utf-8", newline="\n")
    return Bound(target, form, notes, kept)


def _with_notes(body: str, notes: list[str]) -> str:
    """spec.md's body with `## Import review notes` listing `notes`, in place
    of the section an earlier import wrote."""
    lines = body.rstrip("\n").splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == IMPORT_NOTES), None)
    if start is not None:
        end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
        lines[start:end] = []
        while lines and not lines[-1].strip():
            lines.pop()
    if notes:
        lines += ["", IMPORT_NOTES, ""] + [f"- {note}" for note in notes]
    return "\n".join(lines) + "\n"


def baseline_sections(project, slug) -> set[str]:
    """The decided sections `new` wrote into the delivery's spec.md: none for a
    delivery created before 0.3.0 or migrated from a legacy one."""
    from .trust import read_regular
    try:
        sections = json.loads(read_regular(project.delivery_dir(slug) / "baseline.json")).get("sections", [])
        return {str(name) for name in sections} if isinstance(sections, list) else set()
    except (OSError, ValueError, AttributeError, AtipSpecError):
        return set()


def requirements_of(text: str) -> dict[str, Requirement]:
    """A living spec's requirements by ID."""
    return {req.id: req for req in parse_spec(text).requirements}


def requirement_blocks(text: str) -> dict[str, str]:
    """A living spec's text split at its requirement headings: each block,
    from its heading to the next one, by requirement ID, and under "" the
    text before the first, each without the blank lines around it. A repeated
    ID keeps every block of it; an empty part is left out."""
    parts: dict[str, list[list[str]]] = {"": [[]]}
    current = ""
    for line in text.splitlines():
        match = REQ_HEADING.match(line)
        if match:
            current = match.group(1).upper()
            parts.setdefault(current, []).append([])
        parts[current][-1].append(line)
    blocks = {}
    for key, chunks in parts.items():
        trimmed = []
        for lines in chunks:
            while lines and not lines[-1].strip():
                lines.pop()
            while lines and not lines[0].strip():
                lines.pop(0)
            if lines:
                trimmed.append("\n".join(lines))
        if trimmed:
            blocks[key] = "\n\n".join(trimmed)
    return blocks


def row(req) -> tuple | None:
    """What a requirement states, to compare two versions of it: its title,
    removal mark and non-blank lines; None when it is not there."""
    return None if req is None else (req.title, req.remove, [line.rstrip() for line in req.body if line.strip()])


def outside(text: str, listed=()) -> list[str]:
    """The non-blank lines of a living spec, as written, that no approval
    hashes and no requirement check reads: its frontmatter, those before the
    first requirement and under a heading that ends one, its headings left
    out, and the HTML comments and fenced code that `parse_spec` leaves out
    of a requirement not `listed`."""
    from .delivery import AC_HEADING, HEADING, _lines
    try:
        _, lines, _ = _lines(text)
        _, body = frontmatter.split(text)
    except ValueError:
        lines, body = None, ""
    raw = body.splitlines()
    if lines is None or len(raw) != len(lines):
        return [line.rstrip() for line in text.splitlines() if line.strip()]
    found = [line.rstrip() for line in text[:len(text) - len(body)].splitlines() if line.strip()]
    current = None   # the requirement a line is in
    for line, read in zip(raw, lines):
        if match := REQ_HEADING.match(read):
            current = match.group(1).upper()
        elif HEADING.match(read) and not AC_HEADING.match(read):
            current = None
        elif current is None and line.strip():
            found.append(line.rstrip())
            continue
        if line != read and current not in listed:
            found.append(line.rstrip())
    return found


def listed_elsewhere(project, slug, capability) -> set[str]:
    """Requirements of `capability` that another open guided delivery lists:
    its own check reads them."""
    from .trust import read_regular
    found: set[str] = set()
    for directory in sorted(project.deliveries.iterdir()) if project.deliveries.is_dir() else []:
        if directory.name == slug or directory.is_symlink():
            continue
        try:
            meta, _ = frontmatter.split(read_regular(directory / "spec.md").decode("utf-8"))
        except (OSError, ValueError, UnicodeError, AtipSpecError):
            continue
        if meta.get("schema") == 2 and meta.get("capability") == capability and isinstance(meta.get("requirements"), list):
            found.update(str(ident).upper() for ident in meta["requirements"])
    return found


def unlisted_changes(project, slug, spec, before: str, rel: str | None = None) -> dict[str, tuple[str, bool]]:
    """Requirements of the living spec `rel` (by default the delivery's
    capability) that differ from `before` but that the delivery does not list,
    so `check` does not read them: each `added`, `changed` or `removed`, deleted
    or marked `[remove]`, and whether HEAD commits it so. Those another open
    delivery lists are its own."""
    from .trust import read_regular
    own = project.rel(canonical_path(project, spec))
    rel = rel or own
    path = project.root / rel
    try:
        old = {ident: row(req) for ident, req in requirements_of(before).items()}
        new = {ident: row(req) for ident, req in requirements_of(
            read_regular(path).decode("utf-8") if path.is_file() else "").items()}
    except (OSError, UnicodeError, AtipSpecError):
        return {}
    listed = listed_elsewhere(project, slug, Path(rel).stem)
    if rel == own:
        listed |= {req.id for req in spec.requirements}
    found = {ident: "removed" if state[1] else "changed" if ident in old else "added"
             for ident, state in new.items() if ident not in listed and old.get(ident) != state}
    found.update({ident: "removed" for ident in old if ident not in listed and ident not in new})
    if not found:
        return {}
    head = {ident: row(req) for ident, req in requirements_of(project.git.blob_text("HEAD", "./" + rel) or "").items()}
    return {ident: (change, head.get(ident) == new.get(ident)) for ident, change in found.items()}


def _baseline(project, slug) -> dict:
    from .trust import read_regular
    path = project.delivery_dir(slug) / "baseline.json"
    try:
        data = json.loads(read_regular(path))
        if data.get("schema") != 1 or not isinstance(data.get("content"), str):
            raise ValueError("invalid baseline schema")
        return data
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise AtipSpecError(f"Missing or invalid immutable delivery baseline: {exc}") from exc


def baseline_text(project, slug):
    return _baseline(project, slug)["content"]


def base_problem(project, spec, slug) -> str | None:
    """Why the delivery's `base` cannot stand for the commit it started from,
    which its checks compare with; None when it can: the full id of a commit in
    the history of HEAD (a name such as HEAD moves with new commits) and, in a
    guided delivery, the head `atipspec new` recorded in baseline.json; in one
    whose baseline.json records no sections (created before 0.3.0, or migrated
    from a legacy delivery, which keeps its earlier base), not later than it."""
    git = project.git
    base = spec.meta.get("base")
    if not isinstance(base, str) or not base:
        return MISSING_BASE
    if not COMMIT.fullmatch(base):
        return (f"base must be the full id of the commit the delivery started from, as `atipspec new` recorded it, "
                f"not {base!r}, which moves with new commits: restore it")
    if not git.is_ancestor(base, "HEAD"):
        return MISSING_BASE if not git.rev_exists(base) else (
            f"the base commit {base[:12]} is not in the history of HEAD, as after a rebase that rewrote it: restore "
            "the history the delivery was created on (`git reflog` lists the branch before the rebase) and take in "
            "the target branch with a merge")
    data = {}
    if spec.meta.get("schema") == 2:
        try:
            data = _baseline(project, slug)
        except AtipSpecError:
            data = {}
    head = data.get("head")
    if not isinstance(head, str) or head == base or not COMMIT.fullmatch(head):
        return None
    if "sections" in data:
        return (f"the base commit {base[:12]} is not the head `atipspec new` recorded in baseline.json, "
                f"{head[:12]}: restore `base: {head}`")
    if git.rev_exists(head) and not git.is_ancestor(base, head):
        return (f"the base commit {base[:12]} is later than the head `atipspec new` recorded in baseline.json, "
                f"{head[:12]}: restore `base: {head}`")
    return None


@dataclass
class Change:
    """Requirements that reached a living spec from elsewhere than the delivery being checked."""
    source: str     # the slug of a delivery archived since, or the integration ref
    fix: bool       # a guided fix, which corrects requirements that were there before it
    states: dict    # requirement ID -> its Requirement, None when removed


def states_of(written) -> dict:
    """The requirements a receipt's `living_requirements` records for one
    living spec, by ID: each as its text states it, None when removed."""
    states = {}
    for ident, block in written.items() if isinstance(written, dict) else ():
        ident = str(ident).upper()
        req = requirements_of(block).get(ident) if isinstance(block, str) else None
        if block is None or req is not None:
            states[ident] = req
    return states


def later_changes(project, rel: str, *since: str) -> list[Change]:
    """What the deliveries archived in the branch wrote to the living spec
    `rel`, oldest first: each one that none of the commits `since` holds, in
    a folder named as a slug, as merge-check finds them, with the
    requirements its spec lists as its receipt records the text `deliver`
    wrote of them, both read as the commit that archived it added them, so a
    later edit of the receipt vouches for nothing. One archived but not
    committed yet counts while HEAD holds it open, as `deliver` leaves it,
    and comes last. The first of `since` is where the branch's history is
    read from."""
    from .trust import read_regular
    git = project.git
    if not project.archive.is_dir():
        return []
    earlier = {name.rsplit("/", 1)[-1] for rev in since
               for name in git.run("ls-tree", "--name-only", rev, "--", ".atipspec/archive/").splitlines()}
    archived = [directory for directory in sorted(project.archive.iterdir())
                if directory.name not in earlier and SLUG.match(directory.name) and not directory.is_symlink()
                and directory.is_dir()]
    if not archived:
        return []
    added: dict[str, str] = {}   # slug -> the newest commit that added its receipt, in the order of the first
    commit = None
    for line in git.run("log", "--format=%H", "--name-only", "--no-renames", "--diff-filter=A", "--full-history",
                        "--topo-order", "--reverse", f"{since[0]}..HEAD", "--", ".atipspec/archive").splitlines():
        if COMMIT.fullmatch(line):
            commit = line
        elif commit and (match := RECEIPT.search(line)):
            added[match.group(1)] = commit
    order = {slug: index for index, slug in enumerate(added)}
    found = []
    for directory in archived:
        name = directory.name
        try:
            if (git.exists_at("HEAD", f".atipspec/deliveries/{name}/spec.md")
                    and not git.exists_at("HEAD", f".atipspec/archive/{name}/reports/acceptance.json")):
                rank = len(order)
                receipt, text = (read_regular(directory / part).decode("utf-8")
                                 for part in ("reports/acceptance.json", "spec.md"))
            elif name in added:
                rank = order[name]
                receipt, text = (git.blob_text(added[name], f"./.atipspec/archive/{name}/{part}")
                                 for part in ("reports/acceptance.json", "spec.md"))
            else:
                continue
            written = json.loads(receipt)["living_requirements"][rel]
            spec = parse_spec(text)
        except (OSError, ValueError, UnicodeError, KeyError, TypeError, AttributeError, AtipSpecError):
            continue
        refs = spec.meta.get("requirements")
        listed = {str(ident).upper() for ident in refs} if isinstance(refs, list) else set()
        listed |= {req.id for req in spec.requirements}
        states = {ident: req for ident, req in states_of(written).items() if ident in listed}
        found.append((rank, Change(name, spec.meta.get("schema") == 2 and spec.kind == "fix", states)))
    return [change for _, change in sorted(found, key=lambda item: item[0])]


def applied(text: str, changes: list[Change]) -> str:
    """`text` with the requirements `changes` brought, oldest first."""
    from .deliver import merge_requirements
    states: dict = {}
    for change in changes:
        states.update(change.states)
    if not states:
        return text
    before = requirements_of(text)
    updates = []
    for ident, req in states.items():
        if req is not None:
            updates.append(req)
        elif ident in before:
            updates.append(Requirement(ident, before[ident].title, True, 0))
    try:
        return merge_requirements(text, updates)
    except AtipSpecError:
        return text


def _current(project, rel: str) -> dict[str, Requirement]:
    from .trust import read_regular
    path = project.root / rel
    try:
        return requirements_of(read_regular(path).decode("utf-8")) if path.is_file() else {}
    except (OSError, UnicodeError, AtipSpecError):
        return {}


def reached(project, slug, rel: str, text: str, base: str, policy=None) -> str:
    """`text`, the living spec `rel` as the delivery `slug` started from it at
    the commit `base`, with what reached it since from elsewhere: the
    requirements the integration branch brought (see integration.py), then
    those the deliveries archived in the branch wrote."""
    from .integration import brought_requirements, point
    found = point(project, slug, base, policy)
    changes = later_changes(project, rel, base, *([found.commit] if found else []))
    if found is not None:
        changes.insert(0, Change(found.ref, False, brought_requirements(project, found, rel)))
    return applied(text, changes)


def compared(project, slug, spec, policy=None) -> str:
    """What `check` and the proposal compare the capability's living spec
    with: the requirements accepted before the delivery, as its base commit
    has them, with what reached the capability from elsewhere since (see
    `reached`). A delivery created before 0.3.0, or migrated from a legacy
    one, keeps its baseline.json at risk normal or high, unless that holds
    another capability."""
    from .risk import level
    problem = base_problem(project, spec, slug)
    rel = project.rel(canonical_path(project, spec))
    data = None
    if spec.kind != "fix" and level(spec) != "low" and not baseline_sections(project, slug):
        data = _baseline(project, slug)
    if data is not None and data.get("capability") == spec.capability:
        text = data["content"]
    elif problem:
        raise AtipSpecError(problem)
    else:
        text = project.git.blob_text(spec.meta["base"], "./" + rel) or ""
    return text if problem else reached(project, slug, rel, text, spec.meta["base"], policy)


def other_changes(project, slug, spec, base: str, changed=None, policy=None) -> list[tuple[str, str]]:
    """The living specs of other capabilities whose requirements differ from
    the commit `base`, the delivery's, apart from what reached them from
    elsewhere since then: each path with the text it is compared with. Only
    the `changed` paths can differ, all changed since `base` by default."""
    git = project.git
    own = project.rel(canonical_path(project, spec))
    names = changed if changed is not None else (set(git.changed(base)) | set(git.untracked(include_atipspec=True)))
    found = []
    for name in sorted(names):
        if name == own or not LIVING.fullmatch(name):
            continue
        current = _current(project, name)
        before = reached(project, slug, name, git.blob_text(base, "./" + name) or "", base, policy)
        if ({ident: row(req) for ident, req in requirements_of(before).items()}
                != {ident: row(req) for ident, req in current.items()}):
            found.append((name, before))
    return found


def specified(project, rev: str) -> bool:
    """Whether any living spec at the commit `rev` holds a requirement."""
    git = project.git
    return any(LIVING.fullmatch(name) and requirements_of(git.blob_text(rev, "./" + name) or "")
               for name in git.run("ls-tree", "--name-only", rev, "--", ".atipspec/specs/").splitlines())
