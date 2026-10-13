"""External trust policy and detached SSH signatures.

Trust starts outside the candidate checkout: policy, signing keys and the
installed verifier must be controlled by the organization, not by the author.
A signature proves possession of an enrolled key, not biological humanity.
"""
from __future__ import annotations

from .specs import COMMIT, load_spec

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib

from .errors import AtipSpecError

NAMESPACE = "atipspec-v1"
ROLES = {"product", "engineering", "qa", "risk", "ci", "collector"}
PHASE_ROLES = {"spec": "product", "plan": "engineering", "acceptance": "qa",
               "exception": "risk", "decision": "engineering"}
# Gate minimums a policy may impose; config.yaml can add them, never lift them.
REQUIREMENTS = ("require_proof", "require_isolated_review")
# What an approval's subject hashes: 1 until 0.2.x, 2 from 0.3.0. Records say
# which they were written with; one without `subject_version` is 1.
SUBJECT_VERSION = 2


def canonical(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def date_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed
    except (ValueError, AttributeError, TypeError) as exc:
        raise AtipSpecError("invalid timestamp") from exc


def read_regular(path: Path) -> bytes:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AtipSpecError(f"Symlink is not allowed for an assurance artifact: {path}")
    return path.read_bytes()


def text_bytes(path: Path) -> bytes:
    """A file's bytes with CRLF read as LF, as Git for Windows checks text
    out with core.autocrlf: an approval, a signature or evidence made on one
    platform holds on every other. AtipSpec writes its records, signatures
    and logs with LF alone, so they read as written; a test report's copy
    keeps the CRLF a test tool on Windows wrote, which git commits as LF."""
    return read_regular(path).replace(b"\r\n", b"\n")


def unchanged(path: Path, sha256) -> bool:
    """Whether a file AtipSpec wrote still has the digest it recorded, read
    with CRLF as LF or, for a report copied before 0.3.0 with the line
    endings the test tool wrote, as it is."""
    raw = read_regular(path)
    return sha256 in (digest(raw), digest(raw.replace(b"\r\n", b"\n")))


def _check_attestation(data: dict) -> None:
    """Provider mode's [attestation] block: the evidence workflow it trusts lives
    in a separate repository of the same organization, pinned to one commit. In
    a pull request GitHub runs the workflows the pull request carries, so a
    workflow of the candidate repository can be rewritten by the change it
    attests."""
    attestation = data.get("attestation")
    if not isinstance(attestation, dict):
        raise AtipSpecError("Provider mode needs an [attestation] block with signer_workflow and signer_digest")
    organization, _, name = data["repository"].partition("/")
    if not organization or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise AtipSpecError("Provider mode needs repository = \"<organization>/<repository>\"")
    workflow = re.fullmatch(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml",
                            str(attestation.get("signer_workflow") or ""))
    if workflow is None:
        raise AtipSpecError("attestation.signer_workflow must name the trusted evidence workflow as "
                            "<organization>/<repository>/.github/workflows/<file>.yml")
    if workflow.group(1).casefold() != organization.casefold():
        raise AtipSpecError(f"attestation.signer_workflow must belong to {organization}, the organization of the "
                            "policy's repository")
    if workflow.group(2).casefold() == name.casefold():
        raise AtipSpecError(f"attestation.signer_workflow must live in a separate trusted repository, not in "
                            f"{data['repository']}: a pull request can rewrite the workflows of its own repository")
    if not isinstance(attestation.get("signer_digest"), str) or not COMMIT.fullmatch(attestation["signer_digest"]):
        raise AtipSpecError("attestation.signer_digest must pin the trusted workflow to a commit: its full 40 or "
                            "64 hex SHA, as git prints it")
    if "owner" in attestation and str(attestation["owner"]).casefold() != organization.casefold():
        raise AtipSpecError(f"attestation.owner, when set, must be {organization}, the organization of the "
                            "policy's repository")
    if not isinstance(attestation.get("allow_self_hosted_runners", False), bool):
        raise AtipSpecError("attestation.allow_self_hosted_runners must be true or false")


@dataclass
class TrustPolicy:
    path: Path
    data: dict
    sha256: str
    number: int | None = None    # the PR or MR the protected worker checks, in provider mode
    pull_head: str | None = None  # its head, when the approvals read are for an earlier commit of it

    @property
    def mode(self) -> str:
        """`ssh`: enrolled keys sign approvals and evidence. `provider`: approvals
        are read live from GitHub/GitLab and evidence carries an artifact attestation."""
        return str(self.data.get("mode") or "ssh")

    @classmethod
    def load(cls, path: Path, root: Path, expected: str | None = None):
        if path.is_symlink():
            raise AtipSpecError("Trust policy must not be a symlink")
        resolved = path.resolve()
        raw = read_regular(resolved)
        if resolved.is_relative_to(root.resolve()):
            raise AtipSpecError("Trust policy must be outside the candidate repository")
        if expected and digest(raw) != expected:
            raise AtipSpecError("Trust policy SHA-256 does not match the protected pin")
        try:
            data = tomllib.loads(raw.decode())
        except (ValueError, UnicodeError) as exc:
            raise AtipSpecError("Invalid trust policy TOML") from exc
        if data.get("schema") not in (1, 2) or not isinstance(data.get("version"), str) or not data["version"]:
            raise AtipSpecError("Trust policy needs schema = 1 or 2 and a version")
        if not isinstance(data.get("repository"), str) or not data["repository"]:
            raise AtipSpecError("Trust policy needs a repository identity")
        mode = data.get("mode", "ssh")
        if mode not in ("ssh", "provider") or (mode == "provider" and data.get("schema") != 2):
            raise AtipSpecError("Trust policy mode must be ssh, or provider with schema = 2")
        signers = data.get("signers") or []
        if mode == "provider":
            provider = data.get("provider")
            if not isinstance(provider, dict) or not isinstance(provider.get("roles"), dict) or not provider["roles"]:
                raise AtipSpecError("Provider mode needs a [provider] block with role-to-account lists")
            if provider.get("kind") != "github":
                raise AtipSpecError('Provider mode needs [provider] kind = "github": artifact attestations exist only '
                                    "on GitHub; use ssh mode with GitLab")
            _check_attestation(data)
            if any(isinstance(s, dict) and any(r in PHASE_ROLES.values() for r in s.get("roles", [])) for s in signers):
                raise AtipSpecError("Provider mode reads human approvals from the provider; enroll no human signers")
        elif not isinstance(signers, list) or not signers:
            raise AtipSpecError("Trust policy needs enrolled signers")
        if not isinstance(signers, list):
            raise AtipSpecError("signers must be a list")
        identities = set()
        for signer in signers:
            if not isinstance(signer, dict):
                raise AtipSpecError("Invalid signer")
            identity = signer.get("identity", "")
            roles = signer.get("roles", [])
            key = signer.get("public_key", "")
            if not re.fullmatch(r"[a-zA-Z0-9_.@-]+", identity) or identity in identities:
                raise AtipSpecError("Invalid or duplicate signer identity")
            if not isinstance(roles, list) or not roles or any(role not in ROLES for role in roles):
                raise AtipSpecError("Invalid signer roles")
            if not re.fullmatch(r"(?:ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp\d+) [A-Za-z0-9+/=]+(?: [^\r\n]+)?", key):
                raise AtipSpecError("Invalid signer public key")
            if ("ci" in roles or "collector" in roles) and any(role in roles for role in PHASE_ROLES.values()):
                raise AtipSpecError("Service signers cannot hold human approval roles")
            identities.add(identity)
        if not isinstance(data.get("contract_rules", []), list) or not all(isinstance(x, str) for x in data.get("contract_rules", [])):
            raise AtipSpecError("contract_rules must be a list of rules")
        for key in REQUIREMENTS:
            if key in data and not isinstance(data[key], bool):
                raise AtipSpecError(f"Trust policy {key} must be true or false")
        if "integration" in data and (not isinstance(data["integration"], str)
                                      or not data["integration"].startswith("refs/")):
            raise AtipSpecError("Trust policy integration must be a full Git ref name, such as refs/remotes/origin/main")
        return cls(resolved, data, digest(raw))

    def signer(self, identity: str, role: str) -> dict:
        for signer in self.data["signers"]:
            if signer["identity"] == identity and role in signer["roles"]:
                return signer
        raise AtipSpecError(f"{identity!r} is not enrolled for role {role}")

    def verify(self, path: Path, identity: str, role: str) -> None:
        signer = self.signer(identity, role)
        content = text_bytes(path)
        signature = text_bytes(Path(str(path) + ".sig"))
        with tempfile.TemporaryDirectory(prefix="atipspec-signature-") as temp:
            allowed = Path(temp) / "allowed"
            sig = Path(temp) / "signature"
            allowed.write_text(f'{identity} {signer["public_key"]}\n', encoding="utf-8", newline="\n")
            sig.write_bytes(signature)
            result = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", identity,
                                     "-n", NAMESPACE, "-s", str(sig)], input=content, capture_output=True)
        if result.returncode:
            raise AtipSpecError(f"Invalid or untrusted signature: {path.name}")


def selected_policy(project, path: str | None = None, expected: str | None = None, number: int | None = None):
    value = path or os.environ.get("ATIPSPEC_TRUST_POLICY")
    if not value:
        return None
    policy = TrustPolicy.load(Path(value), project.root, expected or os.environ.get("ATIPSPEC_POLICY_SHA256"))
    raw = number if number is not None else os.environ.get("ATIPSPEC_PR_NUMBER")
    if raw not in (None, ""):
        try:
            policy.number = int(raw)
        except (TypeError, ValueError) as exc:
            raise AtipSpecError("ATIPSPEC_PR_NUMBER must be an integer") from exc
        if policy.number <= 0:
            raise AtipSpecError("PR/MR number must be positive")
    return policy


def sign_document(path: Path, data: dict, identity: str, key: Path, policy: TrustPolicy, role: str, root: Path):
    policy.signer(identity, role)
    if key.resolve().is_relative_to(root.resolve()):
        raise AtipSpecError("Signing key must be outside the candidate repository")
    data = {**data, "signer": identity, "policy_sha256": policy.sha256,
            "repository": policy.data["repository"]}
    # Sign in an isolated temporary directory; never follow a candidate sidecar.
    with tempfile.TemporaryDirectory(prefix="atipspec-sign-") as temp:
        source = Path(temp) / "document"
        source.write_bytes(canonical(data))
        result = subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key.resolve()), "-n", NAMESPACE,
                                 str(source)], capture_output=True, stdin=subprocess.DEVNULL)
        if result.returncode:
            raise AtipSpecError("SSH signing failed (use an enrolled key or an unlocked SSH agent)")
        if any(p.is_symlink() for p in (path, *path.parents, Path(str(path) + ".sig"))):
            raise AtipSpecError("Refusing symlink signature destination")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source.read_bytes())
        Path(str(path) + ".sig").write_bytes(Path(str(source) + ".sig").read_bytes())
    policy.verify(path, identity, role)


def subject(project, slug: str, phase: str, *, version: int = SUBJECT_VERSION, policy=None) -> str:
    """Hash each approval's actual subject; acceptance includes excluded reports.
    A record is compared with the subject of the version it was written with."""
    return digest(canonical({"delivery": slug, "phase": phase,
                             "content": subject_content(project, slug, phase, version=version, policy=policy)}))


def subject_content(project, slug: str, phase: str, *, version: int = SUBJECT_VERSION, policy=None) -> dict:
    """The per-file digests an approval's subject hashes, keyed by file. From
    version 2, a guided delivery's living spec and teams.json are hashed in
    named parts (see `_named_parts`) and spec.md without its ticket; version 1
    hashes them whole. The acceptance of a result that puts back what the
    integration branch (the policy's under `policy`) changed names the merge
    base its dossier shows those files against, so taking that branch in
    again, even with the tree kept, voids it."""
    directory = project.delivery_dir(slug)
    kind, _, ident = phase.partition(":")
    if kind in ("spec", "plan") and not ident:
        paths = [directory / "spec.md"]
        if kind == "plan":
            paths.append(directory / "plan.md")
        paths.append(project.contract)
        spec = load_spec(project, slug)
        named = spec.meta.get("schema") == 2 and version >= 2
        if spec.meta.get("schema") == 2:
            from .specs import canonical_path
            paths.extend(([] if named else [canonical_path(project, spec)]) + [directory / "baseline.json"])
            paths.extend(path for path in (project.dot / "config.yaml", project.dot / "adapter.json") if path.exists())
            paths.extend(path for path in ((directory / "contracts.json",) if named else
                                           (project.dot / "teams.json", directory / "contracts.json")) if path.exists())
        content = {project.rel(p): digest(_config_bytes(p) if p == project.dot / "config.yaml" else text_bytes(p))
                   for p in paths}
        if spec.meta.get("schema") == 2:
            from . import frontmatter
            from .delivery import parse_plan, plan_commitments
            spec_path = directory / "spec.md"
            meta, body = frontmatter.split(text_bytes(spec_path).decode("utf-8"))
            meta.pop("status", None)
            if named:
                meta.pop("ticket", None)
                content.update(_named_parts(project, spec))
            content[project.rel(spec_path)] = digest(frontmatter.compose(meta, body).encode("utf-8"))
            if kind == "plan":
                plan_path = directory / "plan.md"
                plan_text = read_regular(plan_path).decode("utf-8")
                # Legacy per-task verification remains part of approval until
                # explicitly moved into a final verification section.
                if parse_plan(plan_text).final is not None:
                    content[project.rel(plan_path)] = digest(plan_commitments(plan_text).encode("utf-8"))
    elif kind == "decision" and re.fullmatch(r"DEC-\d{3,}", ident):
        paths = list(project.decisions.glob(f"{ident}-*.md"))
        if len(paths) != 1:
            raise AtipSpecError(f"Expected one decision for {ident}")
        content = {project.rel(paths[0]): digest(text_bytes(paths[0])),
                   "contract": digest(text_bytes(project.contract))}
    elif (kind == "exception" and re.fullmatch(r"F[1-9]\d*", ident)) or phase == "acceptance":
        tree = project.fingerprint()
        if tree is None:
            raise AtipSpecError("git is required: an acceptance binds the working tree")
        content = {"tree": tree,
                   "review": digest(text_bytes(directory / "review.md")),
                   "deferred": digest(text_bytes(directory / "deferred.md"))}
        if phase == "acceptance":
            content["evidence"] = {p.relative_to(directory / "evidence").as_posix(): digest(text_bytes(p)) for p in sorted((directory / "evidence").rglob("*")) if p.is_file()}
            from .integration import brought_paths
            found, _, rebased = brought_paths(project, slug, load_spec(project, slug).meta.get("base"), policy)
            if rebased:
                content["integrated"] = found.commit
    else:
        raise AtipSpecError(f"Unknown approval phase {phase}")
    return content


def _config_bytes(path: Path) -> bytes:
    """config.yaml as an approval hashes it: without `exempt_paths`, which
    only merge-check reads, on the target branch, so changing it there voids
    no delivery's approval."""
    raw = text_bytes(path)
    try:
        lines = raw.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return raw
    kept, key = [], None
    for line in lines:
        if found := re.match(r"[A-Za-z_][\w-]*(?=\s*:)", line):
            key = found.group()
        if key != "exempt_paths":
            kept.append(line)
    return "".join(kept).encode("utf-8")


def _named_parts(project, spec) -> dict:
    """Version 2 of a guided delivery's subject: teams.json only as far as the
    delivery depends on it (its capability's owners and the integration ref
    it declares), and one part per requirement it lists of its capability's
    living spec. A requirement it does not list is not part of the approval:
    `check` and merge-check block one that changes, so taking in another
    delivery does not void this approval. The `integration` hashed is
    teams.json's under a policy too, though the policy's names the ref there:
    editing it voids a signed approval as it restarts the review round
    count."""
    from .specs import canonical_path, requirement_blocks
    from .teams import configuration
    teams = project.dot / "teams.json"
    try:
        config = configuration(project)
        parts = {".atipspec/teams.json#delivery": digest(canonical(
            {"owners": config["owners"].get(spec.capability) or [], "integration": config.get("integration")}))}
    except AtipSpecError:
        parts = {".atipspec/teams.json#delivery": digest(text_bytes(teams))}
    path = canonical_path(project, spec)
    rel = project.rel(path)
    current = requirement_blocks(read_regular(path).decode("utf-8") if path.exists() else "")
    refs = spec.meta.get("requirements")
    listed = {str(ident).upper() for ident in refs} if isinstance(refs, list) else set()
    for ident in sorted(listed):
        parts[f"{rel}#{ident}"] = digest(current[ident].encode("utf-8")) if ident in current else None
    return parts


def is_owner(identity, owner) -> bool:
    """Whether an approving identity is the declared owner. Case does not
    count, as in provider accounts: an owner written `Engineering` is the
    enrolled identity `engineering`."""
    return owner is not None and str(identity or "").casefold() == str(owner).casefold()


def is_identity(name) -> bool:
    """Whether a name is written as identities and provider accounts are:
    ASCII letters, digits, `_`, `.`, `@` and `-`. An owner that only reads as
    one, with a Cyrillic letter or an invisible character in it, is none."""
    return re.fullmatch(r"[A-Za-z0-9_.@-]+", str(name)) is not None


def owner_problem(owner) -> str | None:
    """Why spec.md's owner cannot be excluded from approving their own work."""
    if not owner:
        return "Trusted delivery requires an owner in spec.md"
    if not is_identity(owner):
        return (f"The owner in spec.md, {ascii(str(owner))}, is not an identity name: write the owner's identity or "
                "account in ASCII letters, digits, `_`, `.`, `@` and `-`")
    return None


def approval_path(project, slug, phase, identity):
    if not is_identity(identity):
        raise AtipSpecError("Invalid approval identity")
    return project.delivery_dir(slug) / "approvals" / f"{phase.replace(':', '-')}-{identity}.json"


def approve(project, slug: str, phase: str, identity: str, key: Path, policy: TrustPolicy, *,
            expires: str | None = None, owner: str | None = None):
    """Sign an approval. The spec approval also signs `owner`: the product
    approver confirms who owns the delivery, the identity the later phases
    exclude, since spec.md is written by the author."""
    role = PHASE_ROLES.get(phase.split(":")[0])
    if role is None:
        raise AtipSpecError("Unknown approval phase")
    spec = load_spec(project, slug)
    declared = spec.meta.get("owner")
    if declared and not is_identity(declared):
        raise AtipSpecError(owner_problem(declared))
    if phase == "spec":
        if not owner:
            raise AtipSpecError("A spec approval confirms the delivery owner: pass `--owner <identity>` with the "
                                "owner spec.md declares, after checking who owns the work")
        if declared is None or owner != str(declared):
            raise AtipSpecError(f"--owner {owner} is not the owner spec.md declares ({declared or 'none'}): correct "
                                "the owner in spec.md, or confirm the declared one")
    elif owner is not None:
        raise AtipSpecError("--owner is only for the spec approval, where the product approver confirms the owner")
    if is_owner(identity, declared):
        raise AtipSpecError("The declared delivery owner cannot approve their own work")
    if role == "risk" and (not expires or date_time(expires) <= datetime.now(timezone.utc)):
        raise AtipSpecError("A risk exception needs a future --expires timestamp")
    path = approval_path(project, slug, phase, identity)
    data = {"schema": 1, "kind": "approval", "delivery": slug, "phase": phase,
            "subject": subject(project, slug, phase, policy=policy), "subject_version": SUBJECT_VERSION,
            "identity": identity, "role": role,
            "approved_at": timestamp(), "expires": expires, "source": "ssh", "head": project.git.head(),
            **({"owner": owner} if phase == "spec" else {})}
    sign_document(path, data, identity, key, policy, role, project.root)
    return path


def approvals_for(project, slug: str, phase: str, policy: TrustPolicy, owner: str | None = None) -> list[dict]:
    """The approvals the policy's mode accepts for a phase: signed records in
    ssh mode, the provider's current reviews in provider mode."""
    if policy.mode != "provider":
        return valid_approvals(project, slug, phase, policy, owner)
    if phase.startswith("exception:"):
        return []   # a risk exception needs an expiry the provider cannot carry: fix the finding, or use ssh mode
    if policy.number is None:
        raise AtipSpecError("provider mode needs the PR or MR number: --number or ATIPSPEC_PR_NUMBER")
    from .providers import fetch_approvals
    return [record for record in fetch_approvals(project, slug, phase, policy, policy.number)
            if not is_owner(record.get("identity"), owner)]


def valid_approvals(project, slug: str, phase: str, policy: TrustPolicy, owner: str | None = None) -> list[dict]:
    expected = {}   # subject version -> the current content's subject in it
    role = PHASE_ROLES[phase.split(":")[0]]
    valid = []
    for path in sorted((project.delivery_dir(slug) / "approvals").glob("*.json")):
        try:
            data = json.loads(read_regular(path))
            if not isinstance(data, dict) or data.get("phase") != phase:
                continue
            version = data.get("subject_version", 1)
            if version not in (1, SUBJECT_VERSION):
                continue
            if version not in expected:
                expected[version] = subject(project, slug, phase, version=version, policy=policy)
            if (data.get("schema") != 1 or data.get("kind") != "approval" or data.get("delivery") != slug
                or data.get("subject") != expected[version] or data.get("policy_sha256") != policy.sha256
                or data.get("repository") != policy.data["repository"] or data.get("role") != role):
                continue
            identity = data.get("identity")
            if not identity or is_owner(identity, owner):
                continue
            if date_time(data["approved_at"]) > datetime.now(timezone.utc):
                continue
            if data.get("expires") and date_time(data["expires"]) <= datetime.now(timezone.utc):
                continue
            if role == "risk" and not data.get("expires"):
                continue
            if data.get("source") == "ssh":
                if data.get("signer") != identity:
                    continue
                if phase == "spec" and (owner is None or data.get("owner") != str(owner)):
                    continue   # the owner the later phases exclude is the one product signed
                policy.verify(path, identity, role)
            elif data.get("source") in ("github", "gitlab"):
                # Re-fetch: a locally cached API response cannot override revocation.
                policy.verify(path, data["signer"], "collector")
                from .providers import refresh_approval
                if not refresh_approval(project, data, policy):
                    continue
            else:
                continue
            valid.append(data)
        except (ValueError, KeyError, TypeError, OSError, AtipSpecError):
            continue
    return valid
