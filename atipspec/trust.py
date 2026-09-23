"""External trust policy and detached SSH signatures.

Trust starts outside the candidate checkout: policy, signing keys and the
installed verifier must be controlled by the organization, not by the author.
A signature proves possession of an enrolled key, not biological humanity.
"""
from __future__ import annotations

from .specs import load_spec

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


@dataclass
class TrustPolicy:
    path: Path
    data: dict
    sha256: str
    number: int | None = None    # the PR or MR the protected worker checks, in provider mode

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
            attestation = data.get("attestation")
            if not isinstance(provider, dict) or not isinstance(provider.get("roles"), dict) or not provider["roles"]:
                raise AtipSpecError("Provider mode needs a [provider] block with role-to-account lists")
            if not isinstance(attestation, dict) or not attestation.get("owner") or not attestation.get("signer_workflow"):
                raise AtipSpecError("Provider mode needs an [attestation] block with owner and signer_workflow")
            workflow, owner = str(attestation["signer_workflow"]), str(attestation["owner"])
            if not workflow.startswith(data["repository"] + "/.github/workflows/") or data["repository"].split("/")[0] != owner:
                raise AtipSpecError("attestation.signer_workflow must be a workflow of the policy's repository, "
                                    "<owner>/<repo>/.github/workflows/<file>.yml, and owner must match")
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
        return cls(resolved, data, digest(raw))

    def signer(self, identity: str, role: str) -> dict:
        for signer in self.data["signers"]:
            if signer["identity"] == identity and role in signer["roles"]:
                return signer
        raise AtipSpecError(f"{identity!r} is not enrolled for role {role}")

    def verify(self, path: Path, identity: str, role: str) -> None:
        signer = self.signer(identity, role)
        content = read_regular(path)
        signature = read_regular(Path(str(path) + ".sig"))
        with tempfile.TemporaryDirectory(prefix="atipspec-signature-") as temp:
            allowed = Path(temp) / "allowed"
            sig = Path(temp) / "signature"
            allowed.write_text(f'{identity} {signer["public_key"]}\n')
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


def subject(project, slug: str, phase: str) -> str:
    """Hash each approval's actual subject; acceptance includes excluded reports."""
    directory = project.delivery_dir(slug)
    kind, _, ident = phase.partition(":")
    if kind in ("spec", "plan") and not ident:
        paths = [directory / "spec.md"]
        if kind == "plan":
            paths.append(directory / "plan.md")
        paths.append(project.contract)
        spec = load_spec(project, slug)
        if spec.meta.get("schema") == 2:
            from .specs import canonical_path
            paths.extend([canonical_path(project, spec), directory / "baseline.json"])
            paths.extend(path for path in (project.dot / "config.yaml", project.dot / "adapter.json") if path.exists())
            paths.extend(path for path in (project.dot / "teams.json", directory / "contracts.json") if path.exists())
        content = {project.rel(p): digest(read_regular(p)) for p in paths}
        if spec.meta.get("schema") == 2:
            from . import frontmatter
            from .delivery import parse_plan, plan_commitments
            spec_path = directory / "spec.md"
            meta, body = frontmatter.split(read_regular(spec_path).decode("utf-8"))
            meta.pop("status", None)
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
        content = {project.rel(paths[0]): digest(read_regular(paths[0])),
                   "contract": digest(read_regular(project.contract))}
    elif (kind == "exception" and re.fullmatch(r"F[1-9]\d*", ident)) or phase == "acceptance":
        content = {"tree": project.fingerprint(),
                   "review": digest(read_regular(directory / "review.md")),
                   "deferred": digest(read_regular(directory / "deferred.md"))}
        if phase == "acceptance":
            content["evidence"] = {str(p.relative_to(directory / "evidence")): digest(read_regular(p)) for p in sorted((directory / "evidence").rglob("*")) if p.is_file()}
    else:
        raise AtipSpecError(f"Unknown approval phase {phase}")
    return digest(canonical({"delivery": slug, "phase": phase, "content": content}))


def approval_path(project, slug, phase, identity):
    if not re.fullmatch(r"[A-Za-z0-9_.@-]+", identity):
        raise AtipSpecError("Invalid approval identity")
    return project.delivery_dir(slug) / "approvals" / f"{phase.replace(':', '-')}-{identity}.json"


def approve(project, slug: str, phase: str, identity: str, key: Path, policy: TrustPolicy, *, expires: str | None = None):
    from .delivery import parse_spec
    role = PHASE_ROLES.get(phase.split(":")[0])
    if role is None:
        raise AtipSpecError("Unknown approval phase")
    spec = load_spec(project, slug)
    if identity == spec.meta.get("owner"):
        raise AtipSpecError("The declared delivery owner cannot approve their own work")
    if role == "risk" and (not expires or date_time(expires) <= datetime.now(timezone.utc)):
        raise AtipSpecError("A risk exception needs a future --expires timestamp")
    path = approval_path(project, slug, phase, identity)
    data = {"schema": 1, "kind": "approval", "delivery": slug, "phase": phase,
            "subject": subject(project, slug, phase), "identity": identity, "role": role,
            "approved_at": timestamp(), "expires": expires, "source": "ssh", "head": project.git.head()}
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
            if record.get("identity") != owner]


def valid_approvals(project, slug: str, phase: str, policy: TrustPolicy, owner: str | None = None) -> list[dict]:
    expected = subject(project, slug, phase)
    role = PHASE_ROLES[phase.split(":")[0]]
    valid = []
    for path in sorted((project.delivery_dir(slug) / "approvals").glob("*.json")):
        try:
            data = json.loads(read_regular(path))
            if not isinstance(data, dict) or data.get("phase") != phase:
                continue
            if (data.get("schema") != 1 or data.get("kind") != "approval" or data.get("delivery") != slug
                or data.get("subject") != expected or data.get("policy_sha256") != policy.sha256
                or data.get("repository") != policy.data["repository"] or data.get("role") != role):
                continue
            identity = data.get("identity")
            if not identity or identity == owner:
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
