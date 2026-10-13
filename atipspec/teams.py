"""Repository-backed coordination without a second backlog or central service.

Only local objects and explicitly configured refs are visible. Reading them
fetches nothing and implies no teammate approval; `atipspec team --fetch`, and
nothing else, fetches the remotes those refs name.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.parse

from .delivery import parse_spec
from .errors import AtipSpecError
from .gitrepo import Git
from .project import validate_slug
from .specs import load_spec

# With these and without a terminal, neither git nor ssh can ask for a password or a passphrase;
# an empty GIT_ASKPASS also turns off git's core.askPass and SSH_ASKPASS.
NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS_REQUIRE": "never"}


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
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.startswith("refs/")
                                         or "*" in ref[:-1] for ref in refs):
        raise AtipSpecError("teams.json refs must be full Git ref names (refs/heads/... or refs/remotes/...), "
                            "with `*` only at the end, as in refs/remotes/origin/delivery/*")
    integration = data.get("integration")
    if integration is not None and (not isinstance(integration, str) or not integration.startswith("refs/")
                                    or "*" in integration):
        raise AtipSpecError("teams.json integration must be a full Git ref name, such as refs/remotes/origin/main")
    ticket_url = data.get("ticket_url")
    if ticket_url is not None and not _ticket_template(ticket_url):
        raise AtipSpecError("teams.json ticket_url must be an https URL with {ticket} where the ticket goes, "
                            "such as https://example.atlassian.net/browse/{ticket}")
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


def _ticket_template(value) -> bool:
    if not isinstance(value, str) or "{ticket}" not in value or any(char.isspace() for char in value):
        return False
    parts = urllib.parse.urlsplit(value.replace("{ticket}", "x"))
    return parts.scheme == "https" and bool(parts.hostname) and not parts.username and not parts.password


def expand_refs(git, patterns) -> list[str]:
    """The refs `patterns` name: a full ref name as it is, a pattern ending in
    `*` as every ref it matches in its last segment (`refs/heads/team-*`)."""
    refs = []
    for pattern in patterns:
        if pattern.endswith("*"):
            refs += [line for line in git.run("for-each-ref", "--format=%(refname)", pattern).splitlines()
                     if line and not line.endswith("/HEAD")]
        else:
            refs.append(pattern)
    return list(dict.fromkeys(refs))


def fetch_remotes(project, patterns) -> list[str]:
    """Fetch each remote that a `refs/remotes/<remote>/...` pattern names, once,
    without prompting for credentials. Returns a warning per remote that
    failed; the board then shows its last fetched state."""
    git = project.git
    known = set(git.run("remote").split())
    names = list(dict.fromkeys(pattern.split("/")[2] for pattern in patterns
                               if pattern.startswith("refs/remotes/") and pattern.count("/") >= 3))
    warnings = []
    for name in names:
        if name not in known:
            warnings.append(f"no remote named {name}; the refs under refs/remotes/{name}/ were not fetched")
            continue
        try:
            failed = subprocess.run(["git", "fetch", "--prune", "--no-tags", "--quiet", name], cwd=project.root,
                                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                                    stdin=subprocess.DEVNULL, timeout=300,
                                    start_new_session=True, env={**os.environ, **NO_PROMPT}).returncode != 0
        except subprocess.TimeoutExpired:
            failed = True
        if failed:
            warnings.append(f"fetching {name} failed; showing its last fetched state")
    return warnings


def last_fetch(project) -> str | None:
    """When this repository last fetched, from FETCH_HEAD; None if never."""
    try:
        path = Path(project.git.run("rev-parse", "--git-path", "FETCH_HEAD").strip())
        stamp = (path if path.is_absolute() else project.root / path).stat().st_mtime
    except (AtipSpecError, OSError):
        return None
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


_changes: dict = {}   # (root, revision) -> rows: what a commit holds never changes


def ref_changes(project, ref):
    revision = resolve_ref(project.git, ref)
    key = (str(project.root), revision)
    if key not in _changes:
        _changes[key] = _revision_changes(project, ref, revision)
    return [{**row, "ref": ref} for row in _changes[key]]


def _revision_changes(project, ref, revision):
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


def board(project, fetch: bool = False):
    from .tickets import link
    config = configuration(project)
    warnings = fetch_remotes(project, config["refs"]) if fetch else []
    refs = expand_refs(project.git, config["refs"])
    rows = [_row(load_spec(project, slug), slug, "working-tree", project.git.head()) for slug in project.list_deliveries()]
    for ref in refs:
        rows.extend(ref_changes(project, ref))
    for row in rows:
        row["capability_owners"] = config["owners"].get(row["capability"], [])
        row["ticket_url"] = link(project, row["ticket"])
    fetched = last_fetch(project)
    visibility = ("working checkout and configured local Git refs; unpublished work and unfetched remote changes "
                  "are not visible; " + (f"last fetch {fetched}" if fetched else "never fetched")
                  + " (`atipspec team --fetch` fetches the remotes the refs name)")
    return {"schema": 1, "visibility": visibility, "refs": refs, "patterns": config["refs"],
            "last_fetch": fetched, "warnings": warnings, "changes": rows}


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
    if name == "system" and name not in repositories and project.system is not None:
        repositories = {**repositories, "system": str(project.system)}
    if name not in repositories:
        raise AtipSpecError(f"Unknown repository {name!r}; map it in teams.json repositories")
    path = project.local_path(repositories[name]).resolve()
    git = Git(path) if path.is_dir() else None
    if git is None or not git.available:
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
    target.write_text(json.dumps({"schema": 1, "contracts": entries}, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    return revision


SYSTEM_CONTRACTS = (("system-contract", "contract.md"), ("system-glossary", "glossary.md"))


def pin_system(project, slug) -> list[tuple[str, str, str]]:
    """Pin the system repository's contract.md, and its glossary.md when its
    HEAD has one, for a guided delivery: `system:` in config.yaml is a shortcut
    for `contract-pin`. Returns (name, path, revision) for each pin."""
    git = _repository(project, "system")
    pins = []
    for name, path in SYSTEM_CONTRACTS:
        if name == "system-contract" or git.exists_at("HEAD", path):
            pins.append((name, path, pin_contract(project, slug, name, "system", "HEAD", path)))
    return pins


def system_pin_command(slug) -> str:
    return f"atipspec contract-pin {slug} system-contract --repository system --ref HEAD --path contract.md"
