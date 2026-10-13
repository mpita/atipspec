"""Capability-scoped stable requirement and criterion identities."""
from __future__ import annotations

import secrets

from .delivery import AC_ID, REQ_ID, parse_spec
from .errors import AtipSpecError
from .project import validate_slug

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # Crockford base32: no I, L, O or U
TOKEN_LENGTH = 5   # 32**5, about 33.5 million prefixes per capability
ATTEMPTS = 20


def token(seed: bytes | None = None, length: int = TOKEN_LENGTH) -> str:
    """A short Crockford base32 token: random, or the first bits of `seed`."""
    bits = 5 * length
    if seed is None:
        value = secrets.randbits(bits)
    else:
        value = int.from_bytes(seed, "big") >> max(0, 8 * len(seed) - bits)
    return "".join(ALPHABET[(value >> shift) & 31] for shift in range(bits - 5, -1, -5))


def concurrent_ids(capability, taken=frozenset()):
    """Allocate identities without a shared counter or renumbering after merge:
    a requirement and its first criterion share a short random token that no
    ID in `taken` uses. Two branches that drew the same token before either
    was published get duplicate IDs, which `check` reports."""
    namespace = validate_slug(capability, "capability").upper()
    for _ in range(ATTEMPTS):
        component = token()
        prefixes = (f"REQ-{namespace}-{component}-", f"AC-{namespace}-{component}-")
        if not any(ident.upper().startswith(prefixes) for ident in taken):
            return f"REQ-{namespace}-{component}-001", f"AC-{namespace}-{component}-001"
    raise AtipSpecError(f"No unused ID prefix for {capability} after {ATTEMPTS} attempts; run `atipspec ids` again")


def known_ids(project, capability) -> set[str]:
    """The requirement and criterion IDs this checkout can see: the living spec
    of `capability`, every delivery and archived delivery, and the living spec
    at each ref teams.json lists."""
    from .teams import configuration, expand_refs
    validate_slug(capability, "capability")
    texts = []
    paths = [project.specs / f"{capability}.md"]
    for folder in (project.deliveries, project.archive):
        paths += sorted(folder.glob("*/spec.md")) if folder.is_dir() else []
    for path in paths:
        if path.is_file() and not path.is_symlink():
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
    if project.git.available:
        try:
            refs = expand_refs(project.git, configuration(project)["refs"])
        except AtipSpecError:
            refs = []
        for ref in refs:
            texts.append(project.git.blob_text(ref, f".atipspec/specs/{capability}.md") or "")
    found = set()
    for text in texts:
        found.update(ident.upper() for ident in REQ_ID.findall(text) + AC_ID.findall(text))
    return found


def next_ids(project, capability):
    validate_slug(capability, "capability")
    paths = [project.specs / f"{capability}.md"]
    for folder in (project.deliveries, project.archive):
        for path in folder.glob("*/spec.md"):
            if parse_spec(path.read_text(encoding="utf-8")).capability == capability:
                paths.append(path)
    requirements, criteria = [0], [0]
    for path in paths:
        if not path.is_file():
            continue
        spec = parse_spec(path.read_text(encoding="utf-8"))
        requirements += [int(req.id[4:]) for req in spec.requirements if req.id[4:].isdigit()]
        criteria += [int(ac.id[3:]) for ac in spec.criteria if ac.id[3:].isdigit()]
    return max(requirements) + 1, max(criteria) + 1


def merge_conflicts(project, spec, slug=None):
    """Three-way check of the living requirements a delivery intends to replace."""
    capability = spec.capability or slug
    base = spec.meta.get("base")
    if spec.meta.get("schema") == 2:
        # The working-branch canonical file IS the proposed content. Comparing
        # it with the base as an external change would flag every own edit.
        # Other published branches are checked by team coordination separately.
        from .specs import baseline_text
        baseline_text(project, slug)
        return []
    if not capability or not base or not project.git.rev_exists(base):
        return []
    path = f".atipspec/specs/{validate_slug(capability)}.md"
    current_path = project.root / path
    current = parse_spec(current_path.read_text(encoding="utf-8")) if current_path.is_file() else parse_spec("")
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
