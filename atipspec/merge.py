"""The merge gate for a branch: every delivery the branch touches is accepted,
every delivery it archives still describes the code at its head, and every
file of code the branch changes is one the dossier of a delivery of the
branch shows as its change, or one `exempt_paths` on the target branch
exempts.

It runs no command from the candidate: it reads git and committed files (with
a trust policy, it checks an archived delivery in a temporary clone), so a
pull-request job can run it without credentials. Exit codes: 0 ready,
1 blocked.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import html
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from . import frontmatter
from .check import Report, check_delivery
from .deliver import delivered_spec, written_requirements
from .errors import AtipSpecError
from .gitrepo import Git
from .project import FINGERPRINT_EXCLUDES, SLUG, Project, globs
from .specs import COMMIT
from .trust import digest, read_regular

READY = ("accepted", "verified")
TREE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
SHOWN_FILES = 10
CONTRACT = ".atipspec/contract.md"
DECISION = re.compile(r"\.atipspec/decisions/DEC-[^/]*\.md")
# The policies of config.yaml a branch can relax; the summary shows it.
RELAXABLE = ("strict_scope", "strict_criteria", "criteria_syntax", "review_rounds", "max_tasks", "max_requirements",
             "max_age_hours", "require_proof", "require_isolated_review", "trust")


@dataclass
class MergeReport(Report):
    deliveries: list[dict] = field(default_factory=list)   # each one the branch touches: slug, state, ticket, link

    def render(self, next_action: bool = True) -> str:
        lines = [super().render(next_action)]
        if self.deliveries:
            lines.append("deliveries:")
        for row in self.deliveries:
            ticket = "no ticket"
            if row["ticket"]:
                url = row["ticket_url"]
                ticket = f"ticket {row['ticket']}" + (f" ({url})" if url and url != row["ticket"] else "")
            lines.append(f"  - {row['slug']} [{row['state']}] {ticket}")
        return "\n".join(lines)


def _ticket(project: Project, rev: str, path: str) -> str | None:
    """The ticket of the delivery whose spec.md is at `path` in `rev`."""
    try:
        meta, _ = frontmatter.split(project.git.run("show", f"{rev}:{path}"))
    except (ValueError, AtipSpecError):
        return None
    ticket = meta.get("ticket")
    return str(ticket) if ticket not in (None, "") else None


@dataclass
class Delivered:
    """What a receipt archived in the branch vouches for."""
    living_spec: dict[str, str]     # living spec path to the digest of the text `deliver` wrote
    commit: str | None = None       # with a policy: the commit it was delivered from, checked there
    base: str | None = None         # the delivery's base commit
    requirements: dict | None = None   # and living spec path to the text `deliver` writes of each listed requirement
    files: set[str] = field(default_factory=set)   # the files its dossier showed when it was delivered


def required_at(project: Project, rev: str) -> bool:
    """Whether the configuration committed at `rev` requires a trust policy, so
    a branch cannot turn the requirement off for its own merge. A configuration
    that cannot be read counts as requiring it."""
    path = ".atipspec/config.yaml"
    if not project.git.exists_at(rev, path):
        return False
    try:
        value = frontmatter.parse(project.git.run("show", f"{rev}:{path}")).get("trust")
    except (ValueError, AtipSpecError):
        return True
    return value not in (None, "optional")


def exempt_paths(project: Project, rev: str) -> tuple[list[str], str | None]:
    """The globs `exempt_paths` names in the configuration committed at `rev`,
    the target branch, so that a branch cannot exempt its own changes; with
    the reason when they cannot be read, which exempts nothing."""
    path = ".atipspec/config.yaml"
    if not project.git.exists_at(rev, path):
        return [], None
    try:
        value = frontmatter.parse(project.git.run("show", f"{rev}:{path}")).get("exempt_paths")
    except (ValueError, AtipSpecError) as exc:
        return [], f"{path} on {rev} cannot be read ({exc}), so exempt_paths exempts nothing"
    if value is None or globs(value):
        return value or [], None
    return [], f"exempt_paths in {path} on {rev} is not a list of globs, so it exempts nothing"


def dossier_files(project: Project, slug: str, base: str, policy=None) -> set[str]:
    """The files the dossier of the delivery `slug` shows at the head: each
    one that changed between its base and the head, or that the integration
    branch brought and the head holds otherwise (see `brought_paths`)."""
    from .integration import brought_paths
    since = set(_paths(project, base, "HEAD", "--", ".", ":(exclude).atipspec"))
    return since | brought_paths(project, slug, base, policy)[2]


def covered_code(project: Project, bases: dict[str, str], point: str, policy=None,
                 shown: dict[str, set[str]] | None = None) -> tuple[set[str], dict[str, str]]:
    """The files the deliveries of `bases` (slug to base commit) cover, as
    their dossiers show them (see `dossier_files`): one open at the head as
    its dossier shows them now, which the acceptance of its result binds;
    one archived in the branch as its dossier showed them when it was
    delivered (`shown`), but not those the target branch changed after the
    commit that archived it, whose change the branch, holding the delivered
    code, takes back. Never one the branch changed before a base, after the
    fork where the base meets the target branch. With the deliveries whose
    base is not in the history of HEAD, whose files it cannot tell."""
    shown = shown or {}
    covered, lost = set(), {}
    for slug, base in bases.items():
        if not COMMIT.fullmatch(base) or not project.git.is_ancestor(base, "HEAD"):
            lost[slug] = base
            continue
        try:
            fork = project.git.run("merge-base", base, point).strip()
            before = set(_paths(project, fork, base, "--", ".", ":(exclude).atipspec"))
            if slug in shown:
                taken = project.git.run("merge-base", archive_commit(project, slug) or "HEAD", point).strip()
                files = shown[slug] - set(_paths(project, taken, point, "--", ".", ":(exclude).atipspec"))
            else:
                files = dossier_files(project, slug, base, policy)
        except AtipSpecError:
            continue
        covered |= files - before
    return covered, lost


def check_outside(project: Project, base: str, point: str, report: Report, covered: set[str]) -> None:
    """The branch changes no code outside the `covered` files but files that
    `exempt_paths` on the target branch matches, and client files that hold
    only what AtipSpec installs."""
    from .contract import matches
    from .install import installed_unchanged
    code = [path for path in _paths(project, point, "HEAD", "--", ".", ":(exclude).atipspec")
            if path not in covered
            and not installed_unchanged(project.root, path, lambda path=path: project.git.blob_text(point, path))]
    if not code:
        return
    exempt, problem = exempt_paths(project, base)
    if problem:
        report.add("warning", problem)
    free = [path for path in code if any(matches(glob, path) for glob in exempt)]
    governed = [path for path in code if path not in free]
    if free:
        report.add("info", f"exempt_paths on {base} exempts the code this branch changes outside any delivery in "
                           f"{_shown(free)}")
    if governed:
        report.add("error", f"this branch changes code outside any delivery ({_shown(governed)}), and no acceptance "
                            "covers it. Make the change in a delivery (`atipspec new`), reverting it here first if "
                            "it was committed before one; or, if the user decides these files need no delivery, "
                            f"they add globs that match them to exempt_paths in .atipspec/config.yaml on {base}, the "
                            "target branch, first: merge-check reads exempt_paths there, never from this branch")


def check_exempt_change(project: Project, base: str, point: str, report: Report) -> None:
    """A branch that changes `exempt_paths` changes what merge-check lets
    through once it is merged: the job summary shows it to the human."""
    before, after = (exempt_paths(project, rev)[0] for rev in (point, "HEAD"))
    if before != after:
        report.add("warning", f"this branch changes exempt_paths in .atipspec/config.yaml ({before} → {after}): once "
                              f"merged into {base}, merge-check lets a branch change the files it matches without a "
                              "delivery; which files need none is the user's decision: review it as a change to the CI")


def _config_at(project: Project, rev: str) -> dict:
    """The configuration committed at `rev`; empty when it cannot be read."""
    text = project.git.blob_text(rev, ".atipspec/config.yaml")
    try:
        data = frontmatter.parse(text) if text is not None else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _relaxes(key: str, before, after) -> bool:
    """Whether the policy `key` set to `after` instead of `before` (None: not
    set, so its default) lets more through."""
    from .project import DEFAULT_POLICIES
    default = DEFAULT_POLICIES[key]
    before, after = (default if value is None else value for value in (before, after))
    if key == "trust":
        return before == "required" and after != "required"
    if key == "criteria_syntax":
        return before == "ears" and after != "ears"
    if isinstance(default, bool):
        return before is True and after is not True
    return type(before) is int and type(after) is int and after > before


def check_relaxed_policies(project: Project, base: str, point: str, report: Report) -> None:
    """A policy of config.yaml the branch relaxes against the target branch
    holds, once merged, for every delivery that starts after it, and no
    proposal lists it then: the job summary shows it to the human, in the
    form of the proposal's policy changes."""
    from .proposal import shown_policy
    target, fork, head = (_config_at(project, rev) for rev in (base, point, "HEAD"))
    relaxed = [f"{key} {shown_policy(target.get(key))} → {shown_policy(head.get(key))}" for key in RELAXABLE
               if fork.get(key) != head.get(key) and _relaxes(key, target.get(key), head.get(key))]
    if relaxed:
        report.add("warning", f"policy relaxations against {base}, in .atipspec/config.yaml: {', '.join(relaxed)}; "
                              "once merged, every delivery starts from them and no proposal lists them; which "
                              "policies the project keeps is the user's decision: review it as a change to the CI")


def check_context(project: Project, point: str, report: Report) -> None:
    """The overview, the glossary and the decisions reach the agent as context
    in every phase, and no delivery's approval covers them: the job summary
    names those the branch adds, changes or removes, with the status of each
    decision."""
    git, named = project.git, []
    for path in _paths(project, point, "HEAD", "--", ".atipspec/overview.md", ".atipspec/glossary.md",
                       ".atipspec/decisions"):
        name = path.removeprefix(".atipspec/")
        if not path.startswith(".atipspec/decisions/"):
            named.append(name)
        elif DECISION.fullmatch(path) and not git.exists_at("HEAD", path):
            named.append(f"{name} (removed)")
        elif DECISION.fullmatch(path):
            try:
                status = frontmatter.split(git.blob_text("HEAD", path) or "")[0].get("status") or "no status"
            except ValueError:
                status = "unreadable"
            named.append(f"{name} ({'changed' if git.exists_at(point, path) else 'added'}, {status})")
    if named:
        report.add("warning", f"this branch changes what the agent reads as context in every phase: {_shown(named)}; "
                              "no delivery's approval covers these documents, and the implementation and the review "
                              "follow an accepted decision: review them with the code before the merge")
    settings = [path.removeprefix(".atipspec/") for path in
                _paths(project, point, "HEAD", "--", ".atipspec/adapter.json", ".atipspec/teams.json")]
    if settings:
        report.add("warning", f"this branch changes {', '.join(settings)}: adapter.json names the program `atipspec "
                              "run` executes and whether its reviews count as isolated, teams.json the owners and the "
                              "integration branch; no delivery's approval covers them: review them as a change to "
                              "the CI")


def contract_summary(project: Project, point: str, report: Report) -> None:
    """When the branch changes the contract or a decision that affects it, the
    job summary shows the contract's acceptance and the channel `accept
    contract` declared, unless `check_contract` already blocks on it."""
    from .accept import contract_acceptance, describe_contract
    changed = contract_changes(project, point)
    if not changed:
        return
    names = ", ".join(path.removeprefix(".atipspec/") for path in changed)
    if contract_acceptance(project).state == "accepted":
        report.add("info", f"contract: this branch changes {names}; the contract is {describe_contract(project)} (the "
                           "channel is how `accept contract` ran, not who approved)")
    elif not any(text.startswith("contract: ") for text in report.errors):
        report.add("warning", f"contract: this branch changes {names}, and the contract is "
                              f"{describe_contract(project)}")


def _shown(paths: list[str]) -> str:
    return ", ".join(paths[:SHOWN_FILES]) + (", ..." if len(paths) > SHOWN_FILES else "")


def touched_deliveries(project: Project, point: str) -> list[str]:
    """Slugs of the active and archived deliveries the branch changes."""
    slugs = set()
    for path in _paths(project, point, "HEAD", "--", ".atipspec/deliveries", ".atipspec/archive"):
        parts = path.split("/")
        if len(parts) >= 4 and SLUG.match(parts[2]):
            slugs.add(parts[2])
    return sorted(slugs)


def _paths(project: Project, *args: str) -> list[str]:
    """The paths `git diff` names for `args`, as written: with -z git does not
    quote a path that holds characters outside ASCII."""
    output = project.git.run("diff", "-z", "--name-only", "--no-renames", *args)
    return [path for path in output.split("\0") if path]


def _blob(project: Project, rev: str | None, path: str) -> str | None:
    if not rev or not project.git.exists_at(rev, path):
        return None
    return project.git.run("rev-parse", f"{rev}:{path}").strip()


def archive_commits(project: Project, slug: str) -> list[str]:
    """The commits that added the delivery's receipt, newest first: more than
    one when it was removed, as by reverting its archive commit, and added
    again, or when a merge took it from another branch, which history
    simplification would leave out."""
    return project.git.run("log", "--format=%H", "--diff-filter=A", "--full-history", "HEAD", "--",
                           f".atipspec/archive/{slug}/reports/acceptance.json").split()


def archive_commit(project: Project, slug: str) -> str:
    """The commit that added the delivery's receipt, archiving it."""
    return next(iter(archive_commits(project, slug)), "")


def _archived(project: Project, slug: str, added: list[str]) -> bool:
    """Whether the newest of `added`, the commits that added the delivery's
    receipt, added it as an archive does: the first one; one after a revert
    of the archive commit reopened the delivery, so the commit before holds it
    open; or one that restores a receipt such an archive added."""
    archived, blob = set(), None
    for index, rev in enumerate(reversed(added)):
        blob = _blob(project, rev, f".atipspec/archive/{slug}/reports/acceptance.json")
        if index == 0 or blob in archived or project.git.exists_at(f"{rev}^", f".atipspec/deliveries/{slug}/spec.md"):
            archived.add(blob)
    return not added or blob in archived


def changed_code(project: Project, slug: str, accepted: str, head: str) -> list[str]:
    """The code files that differ from the accepted tree: compared with that tree
    where its object exists (the clone that delivered), else with the commit that
    archived the delivery when that commit holds the accepted code."""
    git = project.git
    try:
        return [path for path in git.run("diff-tree", "-r", "-z", "--name-only", accepted, head).split("\0") if path]
    except AtipSpecError:
        pass
    commit = archive_commit(project, slug)
    if commit and project.code_fingerprint(commit) == accepted:
        return _paths(project, commit, "HEAD", "--", ".", ":(exclude).atipspec")
    return []


def verify_delivered(project: Project, slug: str, policy, head: str) -> Delivered:
    """A delivery archived in this branch, checked under the trust policy as
    `deliver` found it: the commit before the one that archived it, checked out
    in a temporary clone with the repository's refs, with the files the archive
    keeps outside commits (evidence, review, deferral terms, approvals,
    progress) restored from the archive; not its reports, which hold the
    receipt `deliver` wrote after its check. Its check must be verified and that
    commit must hold the code at the head; what it vouches for includes the
    files its dossier shows there. Raises with the reason it is not."""
    git = project.git
    if any(name in os.environ for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")):
        raise AtipSpecError("GIT_DIR, GIT_WORK_TREE or GIT_INDEX_FILE is set, as inside a git hook: run merge-check "
                            "outside it, so the delivery can be checked in a temporary clone")
    archived = archive_commit(project, slug)
    if not archived or not git.rev_exists(f"{archived}^"):
        raise AtipSpecError("no commit before the one that archived it holds the delivery")
    commit = git.run("rev-parse", f"{archived}^").strip()
    if project.code_fingerprint(commit) != head:
        raise AtipSpecError(f"the code at the head is not the code delivered from {commit[:12]}, the commit before "
                            "the one that archived it")
    with tempfile.TemporaryDirectory(prefix="atipspec-merge-") as temp:
        root = Path(temp).resolve() / "checkout"
        git.run("clone", "-q", "--mirror", "--shared", str(project.root), str(root / ".git"))
        Git(root).run("config", "core.bare", "false")
        Git(root).run("checkout", "-q", "--detach", commit)
        directory = root / ".atipspec" / "deliveries" / slug
        if any(path.is_symlink() for path in (directory, *directory.parents) if path.is_relative_to(root)):
            raise AtipSpecError(f"{commit[:12]}, the commit before the one that archived it, links the delivery's "
                                "folder elsewhere")
        if not (root / ".atipspec" / "config.yaml").is_file() or not (directory / "spec.md").is_file():
            raise AtipSpecError(f"{commit[:12]}, the commit before the one that archived it, has no active delivery "
                                f"{slug}")
        for name in (name for name in FINGERPRINT_EXCLUDES if name != "reports"):
            source, target = project.archive / slug / name, directory / name
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()
            if source.is_symlink():
                continue
            if source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            elif source.is_file():
                shutil.copyfile(source, target)
        clone = replace(Project.find(root), cloned_from=project.root)
        report = check_delivery(clone, slug, policy=replace(policy, pull_head=git.head()))
        if not report.ok or report.status != "verified":
            blocking = "; ".join((report.errors + report.todos)[:3])
            raise AtipSpecError(f"its check at {commit[:12]}, the commit it was delivered from, is "
                                f"{report.status}" + (f": {blocking}" if blocking else ""))
        living, text = delivered_spec(clone, slug)
        meta, _ = frontmatter.split((directory / "spec.md").read_text(encoding="utf-8"))
        base = meta.get("base") if isinstance(meta.get("base"), str) else None
        files = set()
        if base and COMMIT.fullmatch(base) and clone.git.is_ancestor(base, "HEAD"):
            files = dossier_files(clone, slug, base, policy)
        return Delivered({clone.rel(living): digest(text.encode("utf-8"))}, commit, base,
                         {clone.rel(living): written_requirements(clone, slug, text)}, files)


def check_receipt(project: Project, slug: str, head: str, trusted: bool, report: Report,
                  policy=None) -> Delivered | None:
    """A delivery archived in this branch: its receipt records an accepted result
    whose code tree is the head's, and a policy verifies a trusted one where it
    was delivered from. Returns what the receipt vouches for: its own word where
    the receipt blocks or no policy judges it, None when it is unreadable."""
    try:
        data = json.loads(read_regular(project.archive / slug / "reports" / "acceptance.json"))
    except (OSError, ValueError, AtipSpecError) as exc:
        report.add("error", f"{slug}: the acceptance receipt is missing or unreadable ({exc})")
        return None
    if not isinstance(data, dict) or data.get("delivery") != slug or data.get("accepted") is not True:
        report.add("error", f"{slug}: the receipt does not record an accepted result")
        return None
    written = data.get("living_spec")
    changes = data.get("changes") if isinstance(data.get("changes"), dict) else {}
    integrated = changes.get("integrated") if isinstance(changes.get("integrated"), dict) else {}
    shown = [entry.get("path") for entry in changes["files"] if isinstance(entry, dict)] \
        if isinstance(changes.get("files"), list) else []
    shown += integrated.get("files") if isinstance(integrated.get("files"), list) else []
    declared = Delivered({path: sha for path, sha in written.items() if isinstance(sha, str)}
                         if isinstance(written, dict) else {},
                         base=changes.get("base") if isinstance(changes.get("base"), str) else None,
                         files={path for path in shown if isinstance(path, str)})
    accepted = data.get("code_tree")
    git = project.git
    receipt = f".atipspec/archive/{slug}/reports/acceptance.json"
    added = archive_commits(project, slug)
    commit = added[0] if added else "HEAD"
    if trusted and data.get("acceptance_mode") != "trusted":
        report.add("error", f"{slug}: accepted locally, but with `trust: required` or a trust policy the merge "
                            "needs a trusted acceptance: reopen the delivery (revert the commit that archived it) and "
                            "deliver it under the policy")
    elif not isinstance(accepted, str) or not TREE.fullmatch(accepted):
        report.add("error", f"{slug}: the receipt has no code_tree (delivered before AtipSpec 0.3.0), so the head "
                            "cannot be compared with the accepted code; reopen the delivery (revert the commit that "
                            "archived it) and deliver it again")
    elif accepted != head:
        files = changed_code(project, slug, accepted, head)
        shown = f" ({_shown(files)})" if files else ""
        report.add("error", f"{slug}: the code changed after `atipspec deliver`{shown}, as it does when the branch "
                            "takes the target branch in (merge or rebase) after delivering. Reopen the delivery: "
                            "revert the commit that archived it, then verify, review, accept the result and deliver "
                            "it again; reverting just those files fixes it only when this branch made the change, "
                            "not when it came from the target branch. To avoid it, take the target branch in before "
                            "`atipspec deliver`")
    elif policy is None and _blob(project, commit, receipt) != _blob(project, "HEAD", receipt):
        # Locally the receipt is the record the head is compared with: rewriting its code_tree after a
        # change of the code must show. A policy checks the delivery again where it was delivered from.
        report.add("error", f"{slug}: the receipt changed after {commit[:12]}, the commit that archived the "
                            "delivery; an archive records a past acceptance and does not change: restore the receipt "
                            "and revert the code changed since, or reopen the delivery (revert the commit that "
                            "archived it), then verify, review, accept and deliver it again")
    elif policy is None and not _archived(project, slug, added):
        report.add("error", f"{slug}: the receipt was removed and added again in {commit[:12]}, whose parent has no "
                            f"open delivery {slug}, and no earlier archive added that receipt; a delivery is archived "
                            "again after reverting the commit that archived it, which reopens it: revert the commits "
                            "that removed the receipt and added it again, or reopen the delivery that way, then "
                            "verify, review, accept and deliver it again")
    elif policy is None and accepted not in {project.code_fingerprint(rev) for rev in (commit, f"{commit}^")
                                             if git.rev_exists(rev)}:
        report.add("error", f"{slug}: neither {commit[:12]}, the commit that archived the delivery, nor the commit "
                            "before it holds the code its receipt records; commit the delivered code before or with "
                            "the archive, or reopen the delivery (revert the commit that archived it) and deliver "
                            "it again")
    elif policy is not None:
        try:
            delivered = verify_delivered(project, slug, policy, head)
        except (AtipSpecError, OSError, ValueError) as exc:
            report.add("error", f"{slug}: the trust policy does not authenticate this receipt: {exc}")
        else:
            report.add("info", f"{slug}: delivered; its trusted check passes at {delivered.commit[:12]}, the commit "
                               "it was delivered from, which holds the code at the head")
            return delivered
    else:
        report.add("info", f"{slug}: delivered; the head matches the accepted code{_channels(data.get('approvals'))}")
    return declared


def _channels(approvals) -> str:
    """How each local approval was recorded, for the job summary: the channel
    is what the command declared, not who approved."""
    shown = [f"{row.get('phase')} via {row.get('channel') or 'an unrecorded channel'}"
             for row in approvals if isinstance(row, dict) and row.get("source") == "local"] \
        if isinstance(approvals, list) else []
    return f" (channels as `accept` declared them, not who approved: {', '.join(shown)})" if shown else ""


def _contract_level_at(project: Project, rev: str, path: str) -> bool:
    """Whether the decision at `path` in `rev` is part of the contract's acceptance."""
    from .accept import contract_level
    try:
        meta, _ = frontmatter.split(project.git.run("show", f"{rev}:{path}"))
    except (ValueError, AtipSpecError):
        return False
    return contract_level(meta) and meta.get("status") not in ("rejected", "superseded")


def contract_changes(project: Project, point: str) -> list[str]:
    """The contract and the decisions that affect it, at the merge base or at
    the head, that the branch changes."""
    return [path for path in _paths(project, point, "HEAD", "--", CONTRACT, ".atipspec/decisions")
            if path == CONTRACT or (DECISION.fullmatch(path) and (_contract_level_at(project, point, path)
                                                                  or _contract_level_at(project, "HEAD", path)))]


def check_contract(project: Project, point: str, report: Report, policy=None,
                   judged: list[tuple[str | None, str]] = ()) -> None:
    """A branch that changes the accepted contract, or a decision that affects it,
    carries the contract's acceptance of the new content. Under a trust policy
    they change only in a delivery whose verified check judged the change: its
    base has the content of the merge base, and the commit it was checked at
    (`judged`: base and commit pairs) the content of the head. A contract not
    accepted at the merge base needs only the latter: the delivery's approved
    plan names the contract it accepts."""
    from .accept import contract_acceptance, describe_contract
    git = project.git
    try:
        meta, _ = frontmatter.split(git.run("show", f"{point}:{CONTRACT}"))
    except (ValueError, AtipSpecError):
        meta = {}
    accepted = meta.get("status") == "accepted"
    changed = contract_changes(project, point)
    if policy is not None:
        for path in changed:
            before, after = _blob(project, point, path), _blob(project, "HEAD", path)
            if any(_blob(project, rev, path) == after and (not accepted or _blob(project, base, path) == before)
                   for base, rev in judged):
                continue
            name = path.removeprefix(".atipspec/")
            if accepted:
                report.add("error", f"contract: this branch changes {name} outside a delivery the trust policy "
                                    "verifies; under a policy the contract and the decisions that affect it change in "
                                    "a delivery, and contract.md with a new decision that affects it, accepted and "
                                    "approved by engineering")
            else:
                report.add("error", f"contract: this branch changes {name}, and no delivery the trust policy verifies "
                                    "was checked with that content; under a policy a draft contract is first accepted, "
                                    "with the decisions that affect it, in a branch with such a delivery")
        return
    if not accepted or not changed:
        return
    if contract_acceptance(project).state != "accepted":
        report.add("error", f"contract: this branch changes the contract or a decision that affects it, and the "
                            f"contract is {describe_contract(project)}")


def check_living_specs(project: Project, point: str, recorded: dict[str, set[str]],
                       opened: dict[str, list[tuple[str, bool, list[str]]]], report: Report,
                       verified: dict[str, dict] | None = None) -> None:
    """Living specs change in a branch only through `atipspec deliver` (the receipt
    records what it wrote) or as an open guided delivery's approved proposal,
    and requirement by requirement: the head holds each one as the merge base
    had it, as the last delivery of this branch that lists it wrote it, or as
    an open delivery of `opened` (capability -> slug, whether it is a fix, the
    requirements it lists) lists it. Under a trust policy, `verified` (slug ->
    living spec path -> requirement ID -> text) holds what it found each
    delivery it authenticated writes, not its receipt's word, and no other
    delivery counts. A guided fix corrects a requirement that was there before
    it."""
    git = project.git
    for path in _paths(project, point, "HEAD", "--", ".atipspec/specs"):
        deliveries = opened.get(path.rsplit("/", 1)[-1].removesuffix(".md"), [])
        try:
            text = git.run("show", f"HEAD:{path}")
        except AtipSpecError:
            text = None
        if not deliveries and (text is None or digest(text.encode("utf-8")) not in recorded.get(path, set())):
            report.add("error", f"{path}: changed in this branch outside `atipspec deliver`; a living spec changes "
                                "through a delivery the human accepts: revert the edit, or make it in a delivery")
            continue
        _check_requirements(project, point, path, text or "", deliveries, report, verified)


def _check_requirements(project: Project, point: str, path: str, text: str,
                        opened: list[tuple[str, bool, list[str]]], report: Report,
                        verified: dict[str, dict] | None) -> None:
    """The requirements of the living spec `path` at the head, `text`, against
    the merge base with the requirements the deliveries archived in the branch
    wrote applied, oldest first (under a trust policy only those of
    `verified`, as it has them), and what the fixes among them and among
    `opened` correct."""
    from .specs import later_changes, requirements_of, row, specified, states_of
    state = requirements_of(project.git.blob_text(point, path) or "")
    head = requirements_of(text)
    empty = None

    def corrects(slug: str, listed: list[str], archived: bool) -> None:
        nonlocal empty
        missing = [ident for ident in listed if ident not in state]
        if missing and not state and empty is None:
            empty = not specified(project, point)
        for ident in [] if not state and empty else missing:
            report.add("error", f"{slug}: a fix corrects a requirement accepted before it, and {ident} "
                                + ("was" if archived else "is") + f" not in {path} at the merge base nor written by "
                                + ("an earlier" if archived else "a") + " delivery of this branch; a behavior no "
                                "requirement covers is a feature delivery: "
                                + ("reopen it (revert the commit that archived it) and deliver" if archived
                                   else "deliver") + " that behavior as a feature")

    for change in later_changes(project, path, point):
        if verified is not None and change.source not in verified:
            continue
        states = change.states if verified is None else states_of(verified[change.source].get(path))
        if change.fix:
            corrects(change.source, list(states), True)
        for ident, req in states.items():
            if req is None:
                state.pop(ident, None)
            else:
                state[ident] = req
    for slug, fix, listed in opened:
        if fix:
            corrects(slug, listed, False)
    excused = {ident for _, _, listed in opened for ident in listed}
    for ident in sorted(state.keys() | head.keys()):
        if ident in excused or row(state.get(ident)) == row(head.get(ident)):
            continue
        what = "removed" if head.get(ident) is None else "added" if state.get(ident) is None else "changed"
        report.add("error", f"{path}: {ident} is {what} in this branch outside the deliveries that list it; a living "
                            "spec changes through a delivery the human accepts: revert the edit, or make it in a "
                            "delivery")


def merge_check(project: Project, base: str, policy=None) -> MergeReport:
    from .tickets import link
    report = MergeReport(f"merge-check --base {base}")
    git = project.git
    if not git.available or git.head() is None:
        report.add("error", "git with at least one commit is required: merge-check judges the branch head")
    elif prefix := git.run("rev-parse", "--show-prefix").strip():
        report.add("error", f"the project is in {prefix} of its git repository, and merge-check reads "
                            ".atipspec/ at the repository root: run it where .atipspec/ is at the top of the "
                            "repository")
    elif base.startswith("-") or not git.rev_exists(base):
        report.add("error", f"base revision {base!r} not found: fetch the target branch with full history "
                            "(fetch-depth: 0)")
    else:
        try:
            point = git.run("merge-base", base, "HEAD").strip()
        except AtipSpecError:
            report.add("error", f"{base} and HEAD share no history")
    if report.errors:
        report.status = "blocked"
        return report
    report.add("info", f"merge base {point[:12]}, head {git.head()[:12]}")
    if git.fingerprint([]) != git.fingerprint([], "HEAD"):
        report.add("error", "the working tree differs from HEAD: merge-check judges the committed head; commit the "
                            "changes or run it on a clean checkout of the branch head")
    from .install import framework_problem
    if problem := framework_problem(project.root, git):
        report.add("error", problem)
    trusted = policy is not None or project.trust_required or required_at(project, point) or required_at(project, base)
    if policy is None and trusted:
        report.add("error", "this project requires an external trust policy (`trust: required` in "
                            ".atipspec/config.yaml, here or on the target branch): run merge-check with --policy "
                            "on the protected worker")
    head = project.code_fingerprint("HEAD")
    slugs = touched_deliveries(project, point)
    recorded: dict[str, set[str]] = {}
    opened: dict[str, list[tuple[str, bool, list[str]]]] = {}
    judged: list[tuple[str | None, str]] = []
    verified: dict[str, dict] = {}
    bases: dict[str, str] = {}   # slug to base commit, of the deliveries archived in the branch or open at its head
    shown: dict[str, set[str]] = {}   # slug to the files the dossier of one archived in the branch showed
    for slug in slugs:
        archived, active = f".atipspec/archive/{slug}/spec.md", f".atipspec/deliveries/{slug}/spec.md"
        found = next(((rev, path) for rev in ("HEAD", point) for path in (active, archived) if git.exists_at(rev, path)),
                     None)
        ticket = _ticket(project, *found) if found else None
        row = {"slug": slug, "ticket": ticket, "ticket_url": link(project, ticket),
               "state": "open" if git.exists_at("HEAD", active) else "delivered" if git.exists_at("HEAD", archived)
               else "removed"}
        report.deliveries.append(row)
        if git.exists_at("HEAD", archived):
            if git.exists_at(point, archived):
                report.add("error", f"{slug}: archived before this branch and changed in it; an archive records "
                                    "a past acceptance and does not change")
            else:
                delivered = check_receipt(project, slug, head, trusted, report, policy)
                for path, sha in (delivered.living_spec.items() if delivered else ()):
                    recorded.setdefault(path, set()).add(sha)
                if delivered and delivered.base:
                    bases[slug] = delivered.base
                    shown[slug] = delivered.files
                if delivered and delivered.commit:
                    judged.append((delivered.base, delivered.commit))
                    verified[slug] = delivered.requirements or {}
        if git.exists_at("HEAD", active):
            try:
                meta, _ = frontmatter.split((project.delivery_dir(slug) / "spec.md").read_text(encoding="utf-8"))
                if isinstance(meta.get("base"), str):
                    bases[slug] = meta["base"]   # one that is not ready blocks the merge
                if meta.get("schema") == 2 and meta.get("capability"):
                    listed = meta.get("requirements") if isinstance(meta.get("requirements"), list) else []
                    opened.setdefault(str(meta["capability"]), []).append(
                        (slug, meta.get("kind") == "fix", [str(ident).upper() for ident in listed]))
                result = check_delivery(project, slug, policy=policy)
            except (AtipSpecError, OSError, ValueError) as exc:
                report.add("error", f"{slug}: {exc}")
                continue
            row["state"] = result.status
            if result.ok and result.status in READY:
                from .accept import PHASES, is_current, read_record
                records = [{"phase": phase, "channel": read_record(project, slug, phase).get("channel"),
                            "source": "local"} for phase in PHASES
                           if policy is None and is_current(project, slug, phase)]
                report.add("info", f"{slug}: {result.status}, not delivered yet{_channels(records)}")
                if policy is not None and isinstance(meta.get("base"), str):
                    judged.append((meta["base"], "HEAD"))
            else:
                report.add("error", f"{slug} [{result.status}]: {result.next_action}")
        elif not git.exists_at("HEAD", archived):
            if git.exists_at(point, archived):
                report.add("error", f"{slug}: this branch removes an archived delivery")
            else:
                report.add("info", f"{slug}: removed without delivery")
    check_contract(project, point, report, policy, judged)
    if policy is None:
        contract_summary(project, point, report)
    check_living_specs(project, point, recorded, opened, report, None if policy is None else verified)
    if not slugs:
        report.add("info", "this branch touches no delivery")
    covered, lost = covered_code(project, bases, point, policy, shown)
    for slug, start in lost.items():
        if not git.exists_at("HEAD", f".atipspec/deliveries/{slug}/spec.md"):   # check names an open one's
            report.add("error", f"{slug}: its base commit {start[:12]} is not in the history of HEAD, as in a "
                                "shallow clone or after a squash or a rebase of the branch, so merge-check cannot "
                                "tell which files the delivery changed: fetch the full history (fetch-depth: 0), or "
                                "restore the history the delivery was created on (`git reflog` lists the branch "
                                "before it was rewritten) and squash it only when it merges")
    if lost:
        report.add("warning", "merge-check did not look for code this branch changes outside its deliveries, as it "
                              f"cannot tell the files of {', '.join(sorted(lost))}: once the base commits are in the "
                              "history of HEAD, it does, and code outside any delivery blocks too")
    else:
        check_outside(project, base, point, report, covered)
    check_exempt_change(project, base, point, report)
    check_relaxed_policies(project, base, point, report)
    check_context(project, point, report)
    report.status = "blocked" if report.errors else "ready"
    return report


def _markdown_text(text: str) -> str:
    """Text outside code spans with its angle brackets escaped, so a placeholder
    such as <code> stays visible."""
    parts = text.split("`")
    return "`".join(part if index % 2 else html.escape(part, quote=False) for index, part in enumerate(parts))


def _ticket_cell(row: dict) -> str:
    if not row["ticket"]:
        return "—"
    text = html.escape(row["ticket"], quote=False).replace("|", "\\|")
    url = row["ticket_url"]
    return f"[{text}](<{url.replace('<', '%3C').replace('>', '%3E').replace('|', '%7C')}>)" if url else text


def render_markdown(report: Report) -> str:
    """The result as Markdown, for a CI job summary."""
    lines = [f"## AtipSpec {report.slug}: {report.status}", ""]
    rows = getattr(report, "deliveries", [])
    if rows:
        lines += ["| Delivery | Ticket | State |", "| --- | --- | --- |"]
        lines += [f"| {row['slug']} | {_ticket_cell(row)} | {row['state']} |" for row in rows] + [""]
    for level in ("error", "todo", "warning", "info"):
        lines += [f"- **{level}** {_markdown_text(text)}" for text in report.of(level)]
    return "\n".join(lines) + "\n"
