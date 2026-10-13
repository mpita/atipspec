"""Reviewable, content-addressed proposal views; presentation grants no approval.

Each view shows the approval code of the content it presents, and only when
`atipspec accept` would record it: the assistant passes that code with --code,
so a record names the version the human saw.
"""
from __future__ import annotations

import difflib

from .accept import (acceptance_subject, approval_problems, approvals_reset_by_contract, contract_acceptance,
                     contract_code, contract_decisions, contract_subject, decision_problems, describe_contract,
                     is_current, short_code)
from .check import check_delivery
from .delivery import parse_plan, parse_spec
from .errors import AtipSpecError
from .specs import load_spec, base_problem, baseline_text, canonical_path, compared, other_changes

PERMISSION_NOTE = ("A client configured by AtipSpec asks the human to allow that command; "
                   "that prompt confirms this same approval.")


def presented_phase(project, slug, spec) -> str | None:
    """What `proposal` presents for approval: the proposal in guided deliveries;
    in legacy ones the spec until it is accepted (fixes approve only the spec),
    or spec and plan together when both are ready, then the plan when
    `approve_plan` asks for it. None when no approval is pending."""
    if spec.meta.get("schema") == 2:
        return "proposal"
    if is_current(project, slug, "spec"):
        if spec.kind == "fix" or not project.policy("approve_plan") or is_current(project, slug, "plan"):
            return None
        return "plan"
    if spec.kind == "fix" or approval_problems(project, slug, "proposal"):
        return "spec"
    return "proposal"


PRESENT = {"proposal": "Present scope, approach and tests together.",
           "spec": "Present the requirements, their criteria and the assumptions.",
           "plan": "Present the approach, the tasks and how each criterion is verified."}


def approval_lines(project, slug, phase) -> list[str]:
    digest = acceptance_subject(project, slug, phase)
    code = short_code(digest)
    lines = [f"Approval code: {code} (sha256 `{digest}`)", "",
             f"{PRESENT[phase]} Offer: Approve and continue / Request changes / Cancel.",
             f"After explicit human approval in this conversation, record it with "
             f"`atipspec accept {slug} {phase} --code {code}`. {PERMISSION_NOTE}",
             "Approval authorizes the next phases within this agreement. Result acceptance, merge and deployment remain separate."]
    if is_current(project, slug, phase):
        lines.append("This content is already accepted; record it again only for a new explicit approval.")
    return lines


def criteria_line(project) -> str:
    """How `check` treats the criteria lint in this project, for the human to see before approving."""
    free = "; criteria_syntax: free, so their form is not checked" if project.policy("criteria_syntax") == "free" else ""
    if project.policy("strict_criteria"):
        what = "vague criteria block" if free else "vague or unstructured criteria block"
        return f"Criteria check: strict; {what} approval{free}"
    return f"Criteria check: warnings only (strict_criteria: false in config.yaml){free}"


def risk_lines(project, spec, reference: str | None) -> list[str]:
    """The kind and the risk level with what it asks of the gate, and for a
    fix the requirements it corrects, as `reference` (what check compares
    with) has them: for the human to see before approving."""
    from .risk import EFFECTS, level
    from .specs import specified
    risk = level(spec)
    effects = "; ".join(EFFECTS[risk]) if risk else f"{spec.meta.get('risk')!r} is not a level: set low, normal or high"
    lines = [f"Kind: {spec.kind} · Risk: {risk or 'invalid'} — {effects}"]
    if spec.kind == "fix" and spec.meta.get("schema") == 2 and spec.requirements:
        try:
            accepted = None if reference is None else {req.id for req in parse_spec(reference).requirements}
            first = accepted is not None and not accepted and not specified(project, spec.meta["base"])
        except AtipSpecError:
            accepted = None

        def state(ident):
            if accepted is None:
                return "the accepted requirements cannot be read"
            if ident in accepted:
                return "accepted requirement"
            return "new: no living spec held a requirement" if first else "not accepted: a fix cannot add it"
        lines.append("Corrects: " + ", ".join(f"{req.id} ({state(req.id)})" for req in spec.requirements))
    return lines


def shown_policy(value) -> str:
    """A policy value as the proposal and `merge-check` show it."""
    return "unset" if value is None else str(value).lower() if isinstance(value, bool) else str(value)


def policy_line(project, spec) -> str | None:
    """The policies config.yaml changes since the delivery's base commit, for
    the human to see that approving the proposal accepts them too, but
    `exempt_paths`, which no approval hashes; None when there are none or the
    base cannot be read."""
    from . import frontmatter
    from .project import DEFAULT_POLICIES
    base = spec.meta.get("base")
    text = project.git.blob_text(base, ".atipspec/config.yaml") if isinstance(base, str) and project.git.available \
        else None
    try:
        before = frontmatter.parse(text) if text is not None else None
    except ValueError:
        before = None
    if not isinstance(before, dict):
        return None
    changed = [f"{key} {shown_policy(before.get(key))} → {shown_policy(project.config.get(key))}"
               for key in DEFAULT_POLICIES if key != "exempt_paths" and before.get(key) != project.config.get(key)]
    return ("Policy changes since the base commit, in .atipspec/config.yaml: " + ", ".join(changed)) if changed else None


def evidence_line(project, spec) -> str:
    """What the gate will ask of the evidence and the review, for the human to see before approving."""
    from .check import review_isolation_required
    from .risk import level
    from .trust import selected_policy
    policy = selected_policy(project)
    proof = ("each criterion under Tests names its test in Proof (require_proof)"
             if project.requirement("require_proof", policy)
             else "each criterion under Tests names its test in Proof (risk: high)" if level(spec) == "high"
             else "a criterion under Tests without a Proof entry is verified by the reviewer")
    reason = review_isolation_required(project, spec, policy)
    review = (f"the review must come from an isolated session ({reason})" if reason
              else "a review from a shared session is a warning")
    return f"Evidence check: {proof}; {review}"


def contract_pins_line(project, slug) -> str | None:
    """The contracts of other repositories the delivery pinned, or None."""
    from .teams import read_contracts
    try:
        pins = read_contracts(project, slug)
    except (AtipSpecError, OSError, ValueError):
        return None
    return ("Pinned contracts: " + ", ".join(f"{pin['name']} ({pin['repository']}@{pin['revision'][:12]}:{pin['path']})"
                                             for pin in pins)) if pins else None


def decisions_line(project, spec) -> str | None:
    """The accepted capability decisions `context` and the review packet load
    for this delivery. The assistant marks them accepted after the human
    approves them in the conversation, with no code or record, so the human
    sees here what the implementation and the review will follow."""
    from .accept import contract_level
    from .context import decisions_for
    shown = [f"{meta.get('id') or path.stem} ({meta.get('title') or path.stem})"
             for path, meta in decisions_for(project, spec.impact) if not contract_level(meta)]
    return ("Capability decisions the implementation and the review follow, marked accepted in the conversation "
            "without a record: " + ", ".join(shown)) if shown else None


def render_proposal(project, slug):
    from .tickets import label
    from .trust import selected_policy
    directory = project.delivery_dir(slug)
    spec = load_spec(project, slug)
    plan_path = directory / "plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    plan = parse_plan(plan_text)
    phase = presented_phase(project, slug, spec)
    report = check_delivery(project, slug, preapproval=True) if phase else None
    problems = approval_problems(project, slug, phase, report) if phase else []
    policy, reference = selected_policy(project), None
    if spec.meta.get("schema") == 2:
        try:
            reference = compared(project, slug, spec, policy)
        except AtipSpecError:
            pass
    lines = [f"# Proposal: {spec.title or slug}", "",
             f"Change: {slug} · Owner: {spec.meta.get('owner') or 'not assigned'} · "
             f"Ticket: {label(project, spec.meta.get('ticket')) or 'none'}", "",
             f"{len(spec.requirements)} requirements · {len(spec.criteria)} criteria · {len(plan.tasks)} tasks",
             *risk_lines(project, spec, reference)]
    pins = contract_pins_line(project, slug) if spec.meta.get("schema") == 2 else None
    if pins:
        lines.append(pins)
    decided = decisions_line(project, spec)
    if decided:
        lines.append(decided)
    lines.append("")
    if phase is None:
        lines += ["No approval pending: the accepted content is current and this delivery needs no other "
                  f"approval before its result. `atipspec check {slug}` names the next step."]
    elif project.trust_required or problems:
        unready = problems
        if phase == "proposal" or project.trust_required:
            unready = [item.text for item in report.blocking(("spec", "plan", "contract", "base", "coordination"))]
            unready += [f"Open question: {question}" for question in spec.open_questions]
        if unready:
            lines += ["Not ready for approval:", ""] + [f"- {text}" for text in dict.fromkeys(unready)]
        if project.trust_required:
            if unready:
                lines.append("")
            lines += ["Trusted approval: this project sets `trust: required`, so `atipspec accept` records nothing. "
                      f"Each approver inspects `atipspec approval-subject {slug} spec` (and `plan`) and signs with "
                      "`atipspec approve` under the organization's policy."]
    else:
        lines += approval_lines(project, slug, phase)
    if report is not None:
        lines += ["", criteria_line(project), evidence_line(project, spec)]
        changed = policy_line(project, spec) if spec.meta.get("schema") == 2 else None
        if changed:
            lines.append(changed)
        warnings = [item.text for item in report.items
                    if item.level == "warning" and item.source in ("spec", "plan", "contract")]
        if warnings:
            lines += ["", "Warnings; resolve them, or name each one when presenting:", ""]
            lines += [f"- {text}" for text in dict.fromkeys(warnings)]
    lines += ["", "## Change intent", "", (directory / "spec.md").read_text(encoding="utf-8").strip(), "", "## Behaviors", ""]
    for req in spec.requirements:
        lines += [f"### {req.id}: {req.title}", "", "\n".join(req.body).strip(), ""]
    lines += ["## Approach and verification", "", plan_text.strip(), ""]
    if spec.meta.get("schema") == 2 and spec.requirements:
        before = baseline_text(project, slug) if reference is None else reference
        after = canonical_path(project, spec).read_text(encoding="utf-8")
        delta = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                             fromfile="accepted baseline", tofile="working proposal"))
        lines += ["## Specification changes", "", "```diff", delta.rstrip() or "(no behavior change; restores existing requirements)", "```", ""]
        for name, before in ([] if base_problem(project, spec, slug) else
                             other_changes(project, slug, spec, spec.meta["base"], policy=policy)):
            path = project.root / name
            after = path.read_text(encoding="utf-8") if path.is_file() else ""
            delta = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                 fromfile=f"{name} (accepted)", tofile=f"{name} (working)"))
            lines += [f"Another capability's living spec, {name}, changes too:", "", "```diff", delta.rstrip(), "```", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_contract_proposal(project):
    """The contract, its rules, the audit result and the decisions its approval
    includes, with the code `atipspec accept contract` needs."""
    from .audit import audit_project
    from .check import load_contract
    if not project.contract.is_file():
        raise AtipSpecError("There is no .atipspec/contract.md to present; run the contract phase first")
    contract = load_contract(project)
    decisions = contract_decisions(project)
    audit = audit_project(project)
    summary = f"{len(audit.errors)} error(s), {len(audit.of('warning'))} warning(s)" if audit.errors or audit.of("warning") else "clean"
    lines = [f"# Contract proposal: {project.name}", "",
             f"Contract: {project.rel(project.contract)} · {len(contract.rules)} machine-checked rules · audit: {summary}",
             f"Current state: {describe_contract(project)}", ""]
    problems = contract.problems + decision_problems(project)
    if problems:
        lines += ["Not ready for approval:", ""] + [f"- {problem}" for problem in problems]
    else:
        digest = contract_subject(project)
        code = contract_code(project)
        lines += [f"Approval code: {code} (sha256 `{digest}`)", "",
                  "Present the contract, its rules, the audit result and the decisions below together. "
                  "Offer: Approve and continue / Request changes / Cancel.",
                  f"After explicit human approval in this conversation, record it with "
                  f"`atipspec accept contract --code {code}`. {PERMISSION_NOTE}",
                  "The CLI then sets the contract and every decision listed below to accepted; "
                  "never edit their status by hand."]
        if contract_acceptance(project).state == "accepted":
            lines.append("This content is already accepted; record it again only for a new explicit approval.")
        reset = approvals_reset_by_contract(project)
        if reset:
            lines.append("Recording it changes status lines that these current approvals hash, so they become outdated "
                         f"and must be presented again: {', '.join(f'{slug} {phase}' for slug, phase in reset)}. "
                         "Tell the human before asking for approval.")
    lines += ["", "## Decisions included in this approval", ""]
    lines += [f"- {meta.get('id') or path.stem} ({meta.get('status')}): {meta.get('title') or ''} — {project.rel(path)}"
              for path, meta in decisions] or ["- None"]
    findings = [item for item in audit.items if item.level in ("error", "warning")]
    if findings:
        lines += ["", "## Audit findings", ""] + [f"- {item.level}: {item.text}" for item in findings]
    lines += ["", "## Contract", "", project.contract.read_text(encoding="utf-8").strip(), ""]
    for path, meta in decisions:
        lines += [f"## {meta.get('id') or path.stem}", "", path.read_text(encoding="utf-8").strip(), ""]
    return "\n".join(lines).rstrip() + "\n"
