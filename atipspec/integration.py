"""What the integration branch brought into a delivery's branch: like the
diff of a pull request, the scope check, the review packet, the dossier, the
requirement checks and the proposal's diff leave it out of the delivery's
change. The integration branch is `integration` in teams.json, or the first
of origin/HEAD, origin/main and origin/master that resolves (see
`unshared_default`); under a trust policy only the policy's `integration`.

What it brought changed between the fork, where the delivery's base meets
that branch, and the merge base of HEAD with it: each path the working tree
has not changed since, and each requirement of a living spec as that merge
base holds it, however main took in other deliveries, and a hotfix main made
outside a delivery too. Changing it since, putting it back as the base had
it included, in the index or not, is the delivery's change, shown against
that merge base.
Nothing counts without a ref, with a base outside the history of HEAD, or
when that merge base holds the delivery itself. In local mode the ref could
be moved: this detects drift, it does not authenticate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .errors import AtipSpecError
from .specs import COMMIT, requirements_of, row

# Without `integration` in teams.json: `git clone` sets origin/HEAD, a CI checkout often lacks it.
DEFAULT_REFS = ("refs/remotes/origin/HEAD", "refs/remotes/origin/main", "refs/remotes/origin/master")
_points: dict = {}   # (root, slug, ref, base, head, ref commit) -> Point | None


@dataclass(frozen=True)
class Point:
    ref: str        # the integration ref
    commit: str     # the merge base of HEAD with it: what the branch took in
    fork: str       # the merge base of that commit with the delivery's base: what the ref had brought by then


def integration_ref(project, policy=None) -> str | None:
    """The ref whose history counts as integrated, when it names a commit."""
    if policy is not None:
        refs = [policy.data.get("integration")]
    else:
        from .teams import configuration
        try:
            declared = configuration(project).get("integration")
            refs = [declared] if declared else list(DEFAULT_REFS)
        except (AtipSpecError, OSError):
            refs = []
    return next((ref for ref in refs if isinstance(ref, str) and ref.startswith("refs/")
                 and project.git.rev_exists(ref)), None)


def unshared_default(project) -> str | None:
    """A warning when the integration branch is the one origin/HEAD names and
    that is neither origin/main nor origin/master: a CI checkout has no
    origin/HEAD, so it finds another branch, or none, and attributes otherwise there."""
    if integration_ref(project) != DEFAULT_REFS[0]:
        return None
    try:
        target = project.git.run("symbolic-ref", "-q", DEFAULT_REFS[0]).strip()
    except AtipSpecError:
        return None
    if not target or target in DEFAULT_REFS[1:]:
        return None
    return (f"the integration branch is {target.removeprefix('refs/remotes/')}, named by origin/HEAD, which a CI "
            "checkout lacks: there it is origin/main, origin/master or none, so check judges what that branch "
            f"brought otherwise; set \"integration\": \"{target}\" in .atipspec/teams.json, and integration = "
            f"\"{target}\" in the trust policy if one judges the merge")


def point(project, slug: str, base, policy=None) -> Point | None:
    """Where the delivery `slug`'s branch took in the integration branch since
    `base`, the delivery's base commit; None when nothing counts as brought."""
    git = project.git
    ref = integration_ref(project, policy)
    head = git.head()
    if ref is None or head is None or not isinstance(base, str) or not COMMIT.fullmatch(base):
        return None
    target = git.run("rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()
    key = (str(project.root), slug, ref, base, head, target)
    if key not in _points:
        _points[key] = _find(project, slug, ref, base, head, target)
    return _points[key]


def _find(project, slug: str, ref: str, base: str, head: str, target: str) -> Point | None:
    git = project.git
    if not git.is_ancestor(base, head):
        return None
    try:
        commit = git.run("merge-base", head, target).strip()
        fork = git.run("merge-base", commit, base).strip() if commit else ""
    except AtipSpecError:
        return None
    if not commit or not fork or fork == commit:
        return None
    if any(git.exists_at(commit, f".atipspec/{folder}/{slug}/spec.md") for folder in ("deliveries", "archive")):
        return None
    return Point(ref, commit, fork)


def brought_requirements(project, found: Point | None, rel: str) -> dict:
    """The requirements of the living spec `rel` the integration branch
    brought: each one the merge base holds otherwise than the fork did, by
    ID, as it holds it (None when removed)."""
    if found is None:
        return {}
    at, before = (requirements_of(project.git.blob_text(rev, "./" + rel) or "") for rev in (found.commit, found.fork))
    return {ident: at.get(ident) for ident in sorted(at.keys() | before.keys())
            if row(at.get(ident)) != row(before.get(ident))}


def brought_paths(project, slug: str, base, policy=None) -> tuple[Point | None, set[str], set[str]]:
    """Where the branch took in the integration branch (see `point`), the
    paths changed since `base` that it brought and the working tree has not
    changed since, and the paths it changed that the working tree changed
    since, untracked files included, putting them back as at `base` too:
    that is the delivery's change, which a diff from the merge base shows,
    as a pull request's does, and a diff from `base` mixes with what it
    brought or hides."""
    found = point(project, slug, base, policy)
    if found is None:
        return None, set(), set()
    git = project.git
    between = set(git.changed_between(found.fork, found.commit) or ())
    since = set(git.changed(found.commit)) | set(git.untracked(include_atipspec=True))
    return found, (set(git.changed(base)) - since) & between, since & between
