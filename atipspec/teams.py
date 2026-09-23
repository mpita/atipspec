"""Repository-backed coordination without a second backlog or central service.

Only local objects and explicitly configured refs are visible. No fetch, remote
publication or teammate approval is implied by reading them.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re

from .delivery import parse_spec
from .errors import AtipSpecError
from .gitrepo import Git
from .project import validate_slug
from .specs import load_spec


def _json(path, default):
    from .trust import read_regular
    if not path.exists():
        return default
    try:
        data = json.loads(read_regular(path))
    except (OSError, ValueError) as exc:
        raise AtipSpecError(f"Invalid {path.name}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise AtipSpecError(f"{path.name} needs schema: 1")
    return data


def configuration(project):
    data = _json(project.dot / "teams.json", {"schema": 1, "refs": [], "owners": {}, "repositories": {}})
    refs, owners, repositories = data.get("refs", []), data.get("owners", {}), data.get("repositories", {})
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.startswith("refs/") for ref in refs):
        raise AtipSpecError("teams.json refs must be full Git ref names (refs/heads/... or refs/remotes/...)")
    if not isinstance(owners, dict) or any(not isinstance(value, list) or not value or
                                         any(not isinstance(owner, str) or not owner.strip() for owner in value)
                                         for value in owners.values()):
        raise AtipSpecError("teams.json owners maps capabilities to nonempty lists of human owners")
    for capability in owners:
        validate_slug(capability, "owned capability")
    if not isinstance(repositories, dict) or any(not isinstance(value, str) or not value for value in repositories.values()):
        raise AtipSpecError("teams.json repositories maps repository names to local checkout paths")
    return {**data, "refs": refs, "owners": owners, "repositories": repositories}


def resolve_ref(git, ref):
    if not isinstance(ref, str) or not ref or ref.startswith("-"):
        raise AtipSpecError("Invalid Git revision")
    return git.run("rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()


def _row(spec, slug, ref, revision):
    return {"slug": slug, "change_id": spec.meta.get("change_id") or slug,
            "title": spec.title, "owner": spec.meta.get("owner"), "ticket": spec.meta.get("ticket"),
            "capability": spec.capability, "ref": ref, "revision": revision,
            "requirements": {req.id: {"title": req.title, "remove": req.remove,
                                       "body": [line.strip() for line in req.body if line.strip()]}
                             for req in spec.requirements},
            "depends_on": spec.meta.get("depends_on") or [], "status": spec.status}


def ref_changes(project, ref):
    revision = resolve_ref(project.git, ref)
    names = project.git.run("ls-tree", "-r", "--name-only", revision, "--", ".atipspec/deliveries").splitlines()
    rows = []
    for name in names:
        if not re.fullmatch(r"\.atipspec/deliveries/[a-z0-9-]+/spec\.md", name):
            continue
        slug = name.split("/")[2]
        spec = parse_spec(project.git.run("show", f"{revision}:{name}"))
        if spec.problems:
            raise AtipSpecError(f"Malformed change in {ref}: {name}")
        if spec.meta.get("schema") == 2:
            capability = validate_slug(spec.capability or "", "capability")
            refs = spec.meta.get("requirements", [])
            if not isinstance(refs, list) or any(not isinstance(ident, str) for ident in refs):
                raise AtipSpecError(f"Invalid requirement references in {ref}:{name}")
            source = f".atipspec/specs/{capability}.md"
            if refs and not project.git.exists_at(revision, source):
                raise AtipSpecError(f"Missing canonical specification in {ref}: {source}")
            canonical = parse_spec(project.git.run("show", f"{revision}:{source}")) if refs else parse_spec("")
            known = {req.id: req for req in canonical.requirements}
            if refs and (canonical.problems or set(refs) - set(known)):
                raise AtipSpecError(f"Unresolved canonical requirements in {ref}:{name}")
            spec.requirements = [known[ident] for ident in refs]
        rows.append(_row(spec, slug, ref, revision))
    return rows


def board(project):
    config = configuration(project)
    rows = [_row(load_spec(project, slug), slug, "working-tree", project.git.head()) for slug in project.list_deliveries()]
    for ref in config["refs"]:
        rows.extend(ref_changes(project, ref))
    for row in rows:
        row["capability_owners"] = config["owners"].get(row["capability"], [])
    return {"schema": 1, "visibility": "working checkout and configured local Git refs; unpublished work and unfetched remote changes are not visible",
            "refs": config["refs"], "changes": rows}


def conflicts(project, slug):
    own = _row(load_spec(project, slug), slug, "working-tree", project.git.head())
    problems = []
    for other in board(project)["changes"]:
        if other["change_id"] == own["change_id"]:
            continue
        if other["capability"] != own["capability"]:
            continue
        for ident in own["requirements"].keys() & other["requirements"].keys():
            if own["requirements"][ident] != other["requirements"][ident]:
                problems.append(f"{own['capability']}/{ident}: incompatible declared behavior in {other['slug']} at {other['ref']} ({other['revision']}); reconcile the specs before execution or acceptance")
    return sorted(set(problems))


def dependencies(project, slug):
    spec = load_spec(project, slug)
    declared = spec.meta.get("depends_on") or []
    if not isinstance(declared, list) or any(not isinstance(item, str) for item in declared):
        raise AtipSpecError("depends_on must be a list of delivery slugs")
    problems = []
    for dependency in declared:
        validate_slug(dependency, "dependency")
        if dependency == slug:
            problems.append(f"{slug} cannot depend on itself")
            continue
        path = project.archive / dependency / "reports" / "acceptance.json"
        receipt = _json(path, {})
        if receipt.get("delivery") != dependency or receipt.get("accepted") is not True:
            problems.append(f"Waiting for accepted dependency {dependency}")
    return problems


def _repository(project, name):
    repositories = configuration(project)["repositories"]
    if name not in repositories:
        raise AtipSpecError(f"Unknown repository {name!r}; map it in teams.json repositories")
    path = Path(repositories[name])
    path = path if path.is_absolute() else project.root / path
    git = Git(path.resolve())
    if not git.available:
        raise AtipSpecError(f"Repository {name!r} is unavailable locally")
    return git


def _contract_path(path):
    if not isinstance(path, str) or not path or "\\" in path:
        raise AtipSpecError("Contract path must be a relative POSIX file path")
    relative = PurePosixPath(path)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != path:
        raise AtipSpecError("Contract path must be a normalized relative file path")
    return path


def read_contracts(project, slug):
    from .trust import digest
    data = _json(project.delivery_dir(slug) / "contracts.json", {"schema": 1, "contracts": []})
    entries = data.get("contracts")
    if not isinstance(entries, list):
        raise AtipSpecError("contracts.json needs a contracts list")
    results, names = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"]:
            raise AtipSpecError("Each contract needs a name")
        if entry["name"] in names:
            raise AtipSpecError("Duplicate pinned contract name")
        names.add(entry["name"])
        revision = entry.get("revision", "")
        if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", revision):
            raise AtipSpecError("Contracts must pin an immutable full commit ID, not a mutable branch/tag")
        git = _repository(project, entry.get("repository"))
        path = _contract_path(entry.get("path"))
        content = git.run("show", f"{revision}:{path}")
        if digest(content.encode("utf-8")) != entry.get("sha256"):
            raise AtipSpecError(f"Pinned contract digest mismatch: {entry['name']}")
        results.append({**entry, "content": content})
    return results


def pin_contract(project, slug, name, repository, ref, path):
    from .trust import digest
    validate_slug(name, "contract name")
    git = _repository(project, repository)
    revision = resolve_ref(git, ref)
    path = _contract_path(path)
    content = git.run("show", f"{revision}:{path}")
    target = project.delivery_dir(slug) / "contracts.json"
    entries = read_contracts(project, slug)
    entries = [{key: value for key, value in entry.items() if key != "content"} for entry in entries if entry["name"] != name]
    entries.append({"name": name, "repository": repository, "revision": revision, "path": path,
                    "sha256": digest(content.encode("utf-8"))})
    if any(part.is_symlink() for part in (target, *target.parents)):
        raise AtipSpecError("Refusing a symlinked contract pin file")
    target.write_text(json.dumps({"schema": 1, "contracts": entries}, ensure_ascii=False, indent=2) + "\n")
    return revision
