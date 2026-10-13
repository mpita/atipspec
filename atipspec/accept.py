"""Local acceptance: the human approves in the conversation and the assistant
records that decision for a proposal, a result or the contract, naming the
approval code of the content that was presented. The gate detects any later
change.

What a record guarantees: the approved content is bound by hash, so an edit
after acceptance is visible; the code ties the record to the version shown by
`proposal`, `report` or `proposal contract`; and `channel` says how the command
reached a person: `terminal` (the code was typed at the CLI prompt in an
interactive terminal), `client-permission` (this project's rules make Claude
Code ask the human before this command, in a session opened at the project
root) or `assistant` (nothing asked the human). What it does not guarantee: who
approved, that the session loaded the rules, that a person typed at the
terminal, or that the client saw this command line rather than a script that
runs it. Agent markers can only lower the channel.
Trusted acceptance (signed approvals under an external policy) is the
authenticated form; the gate ignores these records when a policy is set.
"""
from __future__ import annotations

from .specs import load_spec

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from . import frontmatter, ui
from .delivery import parse_plan
from .errors import AtipSpecError
from .project import Project
from .trust import SUBJECT_VERSION, canonical, digest, subject, subject_content, text_bytes

PHASES = ("spec", "plan", "proposal", "result")
CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # Crockford base32: no I, L, O or U
# Environment variables coding agents set in the commands they run. They can
# only lower the channel: a marker never makes a command count as a person's.
# Claude Code also sets AI_AGENT, to claude-code_<version>_agent; Codex sets
# CODEX_SANDBOX only inside its macOS sandbox, CODEX_THREAD_ID outside it too.
AGENT_MARKERS = (("CLAUDECODE", "claude"), ("CODEX_SANDBOX", "codex"), ("CODEX_THREAD_ID", "codex"),
                 ("COPILOT_CLI", "github-copilot"), ("CURSOR_AGENT", "cursor"), ("GEMINI_CLI", "gemini"),
                 ("AI_AGENT", None))
# Claude Code's entry point in the Agent SDK (sdk-ts, sdk-py), which loads no
# project settings unless its program asks and hands permission prompts to that
# program, and in `claude -p` (sdk-cli), where no prompt reaches a person.
UNATTENDED_ENTRYPOINT = "sdk-"
REFUSALS = {"proposal": "Cannot accept the proposal: ", "spec": "Cannot accept the spec: ",
            "plan": "Cannot accept the plan: ", "result": "Cannot accept the result: "}
RESULT_LABELS = {"tree": "the working tree", "review": "review.md", "deferred": "deferred.md",
                 "integrated": "the merge base with the integration branch"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --- approval code -----------------------------------------------------------

def short_code(subject_hex: str) -> str:
    """The first 40 bits of a sha256 hex digest as XXXX-XXXX in Crockford base32."""
    value = int(subject_hex[:10], 16)
    text = "".join(CODE_ALPHABET[(value >> shift) & 31] for shift in range(35, -1, -5))
    return f"{text[:4]}-{text[4:]}"


def normalize_code(text: str) -> str:
    """A typed code compared without case, spaces or hyphen; O, I and L read as
    0, 1 and 1, as Crockford base32 defines."""
    return "".join(text.split()).replace("-", "").upper().translate(str.maketrans("OIL", "011"))


def _subject_phase(phase: str) -> str:
    return {"proposal": "plan", "result": "acceptance"}.get(phase, phase)


def acceptance_subject(project, slug, phase, version: int = SUBJECT_VERSION):
    return subject(project, slug, _subject_phase(phase), version=version)


def approval_code(project: Project, slug: str, phase: str) -> str:
    """The code `proposal` or `report` shows for the content `accept` would record."""
    return short_code(acceptance_subject(project, slug, phase))


# --- channel -----------------------------------------------------------------

def agent_markers() -> list[tuple[str, str | None]]:
    """Every agent marker set in the environment and the client it names."""
    found = []
    for name, client in AGENT_MARKERS:
        value = os.environ.get(name, "").strip().lower()
        if value and value not in ("0", "false", "no", "off"):
            found.append((name, "claude" if name == "AI_AGENT" and value.startswith(("claude-code", "claude_code"))
                          else client))
    return found


def direct_invocation() -> bool:
    """Whether this process is the command line the client's ask rule matches,
    `atipspec accept ...`, as the interpreter received it: the installed command
    or `python -m atipspec`, not `python -m atipspec.cli`, `python -m
    atipspec.__main__`, `python -c` or a program that imports the CLI or
    rewrites sys.argv."""
    args, line = sys.argv[1:], sys.orig_argv
    if not args or args[0] != "accept" or len(line) < len(args) + 2 or line[-len(args):] != args:
        return False
    program, before = line[-len(args) - 1], line[-len(args) - 2]
    if program == "-matipspec" or (program == "atipspec" and before == "-m"):
        return True
    return Path(program).name.lower() in ("atipspec", "atipspec.exe")


def detect_channel(project: Project) -> tuple[str, str | None]:
    """(channel, client) for this command. `terminal` needs a terminal and no
    agent marker. `client-permission` needs Claude Code as the only agent,
    outside the Agent SDK and `claude -p`, the command line its ask rule matches,
    its rules intact on disk and no hook in the project's settings that can
    answer its prompt. Each is what the process declares: the CLI cannot see
    whether the session loaded these rules, nor who typed at a terminal, which
    an agent can create. Claude Code exports its markers to every
    process it starts, so another agent's marker means that agent ran the
    command, outside Claude Code's rules."""
    markers = agent_markers()
    if not markers:
        return ("terminal", None) if ui.interactive() else ("assistant", None)
    others = [client for _, client in markers if client != "claude"]
    if others:
        return "assistant", others[0]
    from .install import permission_overrides, permission_rules_state
    if (direct_invocation() and not os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").startswith(UNATTENDED_ENTRYPOINT)
            and permission_rules_state(project.root, "claude") == "installed"
            and not permission_overrides(project.root, "claude")):
        return "client-permission", "claude"
    return "assistant", "claude"


def client_label(client: str | None) -> str | None:
    from .install import CLIENTS
    return CLIENTS[client].label if client in CLIENTS else client


def channel_text(record: dict) -> str:
    """' via <channel> (<client>)', or ', channel not recorded' for 0.2.x records."""
    channel = record.get("channel")
    if not channel:
        return ", channel not recorded"
    label = client_label(record.get("client"))
    return f" via {channel}" + (f" ({label})" if label else "")


def _confirm_code(expected: str, given: str | None, channel: str) -> None:
    """The code must name the content being recorded. In a terminal the person
    types it at the prompt; otherwise --code carries it. A mismatch never
    reveals the current code."""
    if channel == "terminal":
        typed = input("Approval code shown with the content you approve: ")
        if given is not None and normalize_code(typed) != normalize_code(given):
            raise AtipSpecError("The typed approval code differs from --code; nothing was recorded")
        given = typed
    if not given or not given.strip():
        raise AtipSpecError("Pass the approval code shown with the presented content: `--code XXXX-XXXX` "
                            "(from `atipspec proposal <slug>`, `atipspec report <slug>` or `atipspec proposal contract`)")
    if normalize_code(given) != normalize_code(expected):
        raise AtipSpecError("The approval code does not match the current content: it changed after it was presented, "
                            "or the code was mistyped. Present the content again and record the code it shows; "
                            "nothing was recorded")


# --- delivery records ----------------------------------------------------------

def record_path(project: Project, slug: str, phase: str) -> Path:
    return project.delivery_dir(slug, must_exist=False) / "approvals" / f"local-{phase}.json"


def read_record(project: Project, slug: str, phase: str) -> dict | None:
    path = record_path(project, slug, phase)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("kind") != "local-acceptance" or data.get("phase") != phase:
        return None
    return data


def record_version(data: dict) -> int | None:
    """The subject version a record was written with: 1 when it does not say,
    as in 0.2.x; None for one this CLI does not know."""
    version = data.get("subject_version", 1)
    return version if version in (1, SUBJECT_VERSION) else None


def is_current(project: Project, slug: str, phase: str) -> bool:
    """Whether the accepted content is the content on disk right now, hashed
    as the record was."""
    data = read_record(project, slug, phase)
    if data is None or record_version(data) is None:
        return False
    try:
        return data.get("subject") == acceptance_subject(project, slug, phase, record_version(data))
    except (OSError, AtipSpecError):
        return False


def _flat(content: dict, prefix: str = "") -> dict[str, str]:
    flat = {}
    for key, value in content.items():
        if isinstance(value, dict):
            flat.update(_flat(value, f"{prefix}{key}/"))
        else:
            flat[prefix + key] = value
    return flat


def changed_since(project: Project, slug: str, phase: str) -> list[str] | None:
    """The files whose content differs from the accepted one, or None when the
    record predates per-file digests (0.2.x) or the content cannot be read."""
    data = read_record(project, slug, phase)
    if data is None or not isinstance(data.get("files"), dict) or record_version(data) is None:
        return None
    try:
        current = _flat(subject_content(project, slug, _subject_phase(phase), version=record_version(data)))
    except (OSError, AtipSpecError):
        return None
    recorded = _flat(data["files"])
    return [part_label(name) for name in sorted(set(current) | set(recorded))
            if current.get(name) != recorded.get(name)]


def part_label(name: str) -> str:
    """How a drift message names a part of an approval's subject."""
    path, _, part = name.partition("#")
    if part == "delivery":
        return f"{path} (owners of the capability or integration)"
    return f"{path} {part}" if part else RESULT_LABELS.get(name, name)


def who(project: Project, by: str | None) -> str:
    if by:
        return by
    if project.git.available:
        # The identity git itself would sign a commit with: config or environment.
        try:
            ident = project.git.run("var", "GIT_AUTHOR_IDENT").strip()
            start, end = ident.find("<"), ident.find(">")
            if 0 <= start < end:
                return ident[start + 1:end] or "unknown"
        except AtipSpecError:
            pass
    return "unknown"


def _set_status(path: Path, status: str) -> None:
    meta, body = frontmatter.split(path.read_text(encoding="utf-8"))
    meta["status"] = status
    path.write_text(frontmatter.compose(meta, body), encoding="utf-8", newline="\n")


def _writable(path: Path) -> Path:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AtipSpecError("Refusing a symlinked acceptance path")
    return path


def _write_json(path: Path, data: dict) -> Path:
    _writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path


def _write(project: Project, slug: str, phase: str, by: str | None, code: str, channel: str,
           client: str | None) -> Path:
    data = {"schema": 2, "kind": "local-acceptance", "delivery": slug, "phase": phase,
            "subject": acceptance_subject(project, slug, phase), "subject_version": SUBJECT_VERSION, "code": code,
            "files": subject_content(project, slug, _subject_phase(phase)), "accepted_at": _now(),
            "by": who(project, by), "head": project.git.head(), "channel": channel, "client": client}
    return _write_json(record_path(project, slug, phase), data)


def guided_refusal(slug: str) -> str:
    return (f"{slug} is a guided delivery: spec, approach and tests are approved together. Present "
            f"`atipspec proposal {slug}` and, after the human approves it, record "
            f"`atipspec accept {slug} proposal --code <code>`")


def trusted_refusal() -> str:
    return ("this project requires trusted approval (`trust: required` in .atipspec/config.yaml), so local "
            "acceptance is disabled: approvers sign with `atipspec approve` under the organization's policy")


def approval_problems(project: Project, slug: str, phase: str, report=None) -> list[str]:
    """Why `atipspec accept <slug> <phase>` would refuse now; empty when it
    would record. `proposal` shows a code only when this is empty, and passes
    the pre-approval check it already ran as `report`."""
    from .check import check_delivery
    if project.trust_required:
        return [trusted_refusal()]
    spec = load_spec(project, slug)
    if phase in ("spec", "plan") and spec.meta.get("schema") == 2:
        return [guided_refusal(slug)]
    if phase == "proposal":
        report = report if report is not None else check_delivery(project, slug, preapproval=True)
        problems = [item.text for item in report.blocking(("spec", "plan", "contract", "base", "coordination"))]
        if spec.open_questions:
            problems.append("resolve the open questions before approving the proposal")
        return list(dict.fromkeys(problems))
    if phase == "result":
        from .trust import selected_policy
        if selected_policy(project) is not None:
            return ["this project selects a trust policy; use its authenticated acceptance procedure"]
        report = check_delivery(project, slug)
        return [] if report.ok else [report.render()]
    if phase == "spec":
        problems = list(spec.problems)
        if not spec.requirements:
            problems.append("the spec has no requirements")
        problems += [f"{req.id} has no acceptance criteria" for req in spec.requirements if not req.criteria and not req.remove]
        if spec.open_questions:
            problems.append(f"{len(spec.open_questions)} open question(s) remain")
        if spec.status not in ("draft", "ready"):
            problems.append(f"spec status is {spec.status!r}")
        problems += [item.text for item in check_delivery(project, slug).blocking(("spec",)) if item.level == "error"]
        return list(dict.fromkeys(problems))
    if phase == "plan":
        if not is_current(project, slug, "spec"):
            return [f"accept the spec first: present `atipspec proposal {slug}` and record "
                    f"`atipspec accept {slug} spec --code <code>`"]
        path = project.delivery_dir(slug) / "plan.md"
        plan = parse_plan(path.read_text(encoding="utf-8")) if path.is_file() else None
        if plan is None or not plan.tasks:
            return ["plan.md has no tasks"]
        report = check_delivery(project, slug)
        return plan.problems + [item.text for item in report.blocking(("plan", "contract")) if item.level == "error"]
    raise AtipSpecError(f"Unknown acceptance phase {phase}")


def _accept(project: Project, slug: str, phase: str, by: str | None, code: str | None) -> Path:
    problems = approval_problems(project, slug, phase)
    if problems:
        raise AtipSpecError(REFUSALS[phase] + "; ".join(problems))
    expected = approval_code(project, slug, phase)
    channel, client = detect_channel(project)
    _confirm_code(expected, code, channel)
    spec_path = project.delivery_dir(slug) / "spec.md"
    spec = load_spec(project, slug)
    legacy_pair = phase == "proposal" and spec.meta.get("schema") != 2
    for name in (("spec", "plan", phase) if legacy_pair else (phase,)):
        _writable(record_path(project, slug, name))
    if phase in ("spec", "proposal") and spec.status == "draft":
        _set_status(spec_path, "ready")
    if legacy_pair:
        # Legacy deliveries keep reading their spec and plan records.
        _write(project, slug, "spec", by, expected, channel, client)
        _write(project, slug, "plan", by, expected, channel, client)
    elif phase == "proposal":
        from .rounds import start
        start(project, slug)
    return _write(project, slug, phase, by, expected, channel, client)


def accept_proposal(project: Project, slug: str, by: str | None = None, code: str | None = None) -> Path:
    """Approve spec, approach and tests together, after validating all of them.

    No acceptance is written when the proposed plan is incomplete or the code
    does not name the current proposal. Guided deliveries record only the
    proposal; legacy ones also record their spec and plan.
    """
    return _accept(project, slug, "proposal", by, code)


def accept_result(project: Project, slug: str, by: str | None = None, code: str | None = None) -> Path:
    """Record the human's acceptance of the reviewed result shown by `report`."""
    return _accept(project, slug, "result", by, code)


def accept_spec(project: Project, slug: str, by: str | None = None, code: str | None = None) -> Path:
    """Legacy deliveries, fixes created before 0.3.0 included: set the spec ready when it is complete, and
    record its content."""
    return _accept(project, slug, "spec", by, code)


def accept_plan(project: Project, slug: str, by: str | None = None, code: str | None = None) -> Path:
    """Legacy deliveries: record the plan's content; the spec must be accepted first."""
    return _accept(project, slug, "plan", by, code)


def phases_for(spec) -> tuple[str, ...]:
    """The approvals a delivery uses: guided deliveries approve the proposal
    and the result; legacy deliveries may also record spec and plan."""
    return ("proposal", "result") if spec.meta.get("schema") == 2 else PHASES


def describe(project: Project, slug: str) -> list[str]:
    """One line per recorded approval, current or outdated, for status."""
    lines = []
    for phase in phases_for(load_spec(project, slug)):
        data = read_record(project, slug, phase)
        if data is None:
            continue
        if is_current(project, slug, phase):
            state = "current"
        else:
            changed = changed_since(project, slug, phase)
            state = f"outdated: {', '.join(changed)} changed" if changed else "outdated: the content changed"
        lines.append(f"{phase} accepted by {data.get('by')} at {data.get('accepted_at')}{channel_text(data)} ({state})")
    return lines


# --- contract ------------------------------------------------------------------

def _decision_id(path: Path) -> str:
    match = re.match(r"DEC-\d+", path.name)
    return match.group(0) if match else path.stem


def digest_without_status(path: Path) -> str:
    """Digest of a document with its status left out: the CLI writes the status."""
    raw = text_bytes(path)
    try:
        meta, body = frontmatter.split(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        return digest(raw)
    meta.pop("status", None)
    return digest(frontmatter.compose(meta, body).encode("utf-8"))


def contract_level(meta: dict) -> bool:
    """Whether a decision's `affects` names the contract, a section of it, or
    everything: `*` or nothing, as `context` reads it."""
    affects = meta.get("affects") or []
    affects = [str(item) for item in affects] if isinstance(affects, list) else [str(affects)]
    return not affects or any(item.split(":")[0] in ("contract", "*") for item in affects)


def contract_decisions(project: Project) -> list[tuple[Path, dict]]:
    """The decisions a contract approval includes: those that affect the
    contract and are neither rejected nor superseded, whatever their status says."""
    chosen = []
    for path in project.list_decisions():
        try:
            meta, _ = frontmatter.split(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if contract_level(meta) and meta.get("status") not in ("rejected", "superseded"):
            chosen.append((path, meta))
    return chosen


def decision_problems(project: Project) -> list[str]:
    """Why the decisions a contract approval includes are not ready: a Context
    or Decision section left as the template wrote it decides nothing."""
    from .locale import section_pattern
    problems = []
    for path, _ in contract_decisions(project):
        try:
            _, body = frontmatter.split(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        sections, current = {}, None
        for line in re.sub(r"<!--.*?-->", "", body, flags=re.S).splitlines():
            heading = re.match(r"^##\s+(.+?)\s*$", line)
            if heading:
                current = next((meaning for meaning in ("context", "decision")
                                if section_pattern(meaning).match(heading.group(1))), None)
                if current:
                    sections.setdefault(current, "")
            elif current:
                sections[current] += line.strip()
        empty = [name.capitalize() for name, text in sections.items() if not text]
        if empty:
            problems.append(f"{_decision_id(path)} ({project.rel(path)}) has no {' or '.join(empty)} yet: write "
                            "what it decides before presenting it")
    return problems


def contract_content(project: Project) -> dict[str, str]:
    content = {project.rel(project.contract): digest_without_status(project.contract)}
    for path, _ in contract_decisions(project):
        content[project.rel(path)] = digest_without_status(path)
    return content


def contract_subject(project: Project, content: dict | None = None) -> str:
    return digest(canonical({"kind": "contract", "content": content or contract_content(project)}))


def contract_code(project: Project) -> str:
    """The code `proposal contract` shows for the contract and its decisions."""
    return short_code(contract_subject(project))


def contract_record_path(project: Project) -> Path:
    return project.approvals / "contract.json"


def read_contract_record(project: Project) -> dict | None:
    path = contract_record_path(project)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("kind") != "contract-acceptance" or not isinstance(data.get("content"), dict):
        return None
    return data


@dataclass
class ContractAcceptance:
    state: str                        # missing, draft, unrecorded, outdated or accepted
    record: dict | None = None
    changes: list[str] = field(default_factory=list)


def _change_label(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    return _decision_id(Path(base)) if base.startswith("DEC-") else base


def contract_acceptance(project: Project) -> ContractAcceptance:
    """Whether the contract on disk, with the decisions that affect it, is the
    content a recorded acceptance names. A status written by hand is not one."""
    if not project.contract.is_file():
        return ContractAcceptance("missing")
    try:
        meta, _ = frontmatter.split(project.contract.read_text(encoding="utf-8"))
    except ValueError:
        meta = {}
    record = read_contract_record(project)
    if meta.get("status") != "accepted":
        return ContractAcceptance("draft", record)
    if record is None:
        return ContractAcceptance("unrecorded")
    try:
        current = contract_content(project)
    except OSError:
        return ContractAcceptance("outdated", record, ["contract.md unreadable"])
    if record.get("subject") == contract_subject(project, current):
        return ContractAcceptance("accepted", record)
    recorded = record["content"]
    changes = []
    for name in sorted(set(current) | set(recorded)):
        if current.get(name) != recorded.get(name):
            what = "new" if name not in recorded else "withdrawn" if name not in current else "changed"
            changes.append(f"{_change_label(name)} {what}")
    return ContractAcceptance("outdated", record, changes)


def describe_contract(project: Project) -> str:
    """The contract's acceptance in one phrase, for status, check and phase refusals."""
    acceptance = contract_acceptance(project)
    if acceptance.state == "missing":
        return "missing (run the contract phase)"
    if acceptance.state == "draft":
        return "not accepted yet: present `atipspec proposal contract` for approval"
    if acceptance.state == "unrecorded":
        return ("accepted without a record (set by hand or before 0.3.0): present `atipspec proposal contract` "
                "for approval")
    if acceptance.state == "outdated":
        return (f"outdated since its acceptance ({', '.join(acceptance.changes) or 'content changed'}): "
                "present `atipspec proposal contract` for approval again")
    record = acceptance.record
    decisions = record.get("decisions") or []
    return (f"accepted by {record.get('by')} at {record.get('accepted_at')}{channel_text(record)}, "
            f"code {record.get('code')}" + (f", decisions {', '.join(decisions)}" if decisions else ""))


def approvals_reset_by_contract(project: Project) -> list[tuple[str, str]]:
    """(slug, phase) of the current delivery approvals that recording the
    contract's acceptance leaves outdated: the status lines it writes are part
    of what they hash (contract.md in spec, plan and proposal; the tree in result)."""
    try:
        meta, _ = frontmatter.split(project.contract.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    contract_changes = meta.get("status") != "accepted"
    if not contract_changes and all(meta.get("status") == "accepted" for _, meta in contract_decisions(project)):
        return []
    found = []
    for slug in project.list_deliveries():
        try:
            phases = phases_for(load_spec(project, slug))
        except (OSError, ValueError, AtipSpecError):
            continue
        found += [(slug, phase) for phase in phases
                  if (contract_changes or phase == "result") and is_current(project, slug, phase)]
    return found


def accept_contract(project: Project, by: str | None = None, code: str | None = None) -> Path:
    """Record the human's approval of the contract and the decisions that affect
    it. The CLI, not the model, sets their status to accepted."""
    if not project.contract.is_file():
        raise AtipSpecError("There is no .atipspec/contract.md to accept; run the contract phase first")
    from .check import load_contract
    problems = load_contract(project).problems + decision_problems(project)
    if problems:
        raise AtipSpecError("Cannot accept the contract: " + "; ".join(problems))
    expected = contract_code(project)
    channel, client = detect_channel(project)
    _confirm_code(expected, code, channel)
    _writable(contract_record_path(project))
    decisions = contract_decisions(project)
    for path, meta in [(project.contract, None), *decisions]:
        current = meta if meta is not None else frontmatter.split(path.read_text(encoding="utf-8"))[0]
        if current.get("status") != "accepted":
            _set_status(path, "accepted")
    content = contract_content(project)
    data = {"schema": 1, "kind": "contract-acceptance", "subject": contract_subject(project, content),
            "code": expected, "content": content, "decisions": [_decision_id(path) for path, _ in decisions],
            "accepted_at": _now(), "by": who(project, by), "head": project.git.head(),
            "channel": channel, "client": client}
    return _write_json(contract_record_path(project), data)
