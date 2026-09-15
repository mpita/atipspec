"""Evidence validation, attestation and release requirements."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .delivery import load_evidence, parse_plan, parse_spec
from .errors import AtipSpecError
from .trust import approvals_for, date_time, read_regular, sign_document, digest


def evidence_problems(record, task, slug):
    data = record.data
    problems = []
    if data.get("schema") != 1 or data.get("delivery") != slug or data.get("task") != task.id:
        problems.append("invalid evidence schema or delivery/task identity")
    if [c.get("command") for c in record.commands] != task.verify or not record.commands:
        problems.append("evidence commands do not match the plan")
    for command in record.commands:
        try:
            relative = Path(command.get("output_path", ""))
            if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 2 or relative.parts[0] != "logs":
                raise AtipSpecError("invalid log path")
            if digest(read_regular(record.path.parent / relative)) != command.get("output_sha256"):
                raise AtipSpecError("output hash mismatch")
        except (OSError, AtipSpecError, TypeError):
            problems.append("command output log is missing or its hash does not match")
    for entry in data.get("reports") or []:
        try:
            if "error" in entry:
                raise AtipSpecError(entry["error"])
            relative = Path(str(entry.get("copy", "")))
            if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 2 or relative.parts[0] != "logs":
                raise AtipSpecError("invalid report copy path")
            raw = read_regular(record.path.parent / relative)
            if digest(raw) != entry.get("sha256"):
                raise AtipSpecError("report hash mismatch")
            from .junit import read_report
            cases = read_report(record.path.parent / relative)
            recorded = [(case.get("id"), case.get("status")) for case in data.get("tests") or []]
            if recorded != [(case["id"], case["status"]) for case in cases]:
                raise AtipSpecError("recorded tests do not match the report")
        except (OSError, AtipSpecError, TypeError, ValueError) as exc:
            problems.append(f"test report is missing or altered: {exc}")
    if task.report and not (data.get("reports") or []):
        problems.append("the plan names a Report but the evidence has none; verify again")
    codes = [c.get("exit_code") for c in record.commands]
    if any(code is not None and (not isinstance(code, int) or isinstance(code, bool)) for code in codes):
        problems.append("invalid command exit code")
    computed = "pass" if codes and all(type(code) is int and code == 0 for code in codes) else "fail"
    if record.result != computed:
        problems.append("evidence result contradicts command exit codes")
    if not record.tree or data.get("tree_after") != record.tree:
        problems.append("verification modified the tree or has no before/after hash")
    environment = data.get("environment")
    if not isinstance(environment, dict) or not all(environment.get(k) for k in ("python", "platform", "atipspec")):
        problems.append("evidence has no execution environment")
    try:
        start, end = date_time(data.get("started")), date_time(data.get("finished"))
        if start > end or end > datetime.now(timezone.utc):
            problems.append("invalid evidence time interval")
    except AtipSpecError:
        problems.append("invalid evidence timestamps")
    return problems


def attest(project, slug, policy, identity, key: Path, run_url: str):
    """A protected collector vouches for records from its trusted CI producer.

    This command does not establish that an arbitrary downloaded artifact came
    from CI. The collector must enforce run identity and artifact provenance.
    """
    import urllib.parse
    if urllib.parse.urlsplit(run_url).scheme != "https":
        raise AtipSpecError("CI run URL must use HTTPS")
    directory = project.delivery_dir(slug)
    plan = parse_plan((directory / "plan.md").read_text())
    evidence, problems = load_evidence(directory / "evidence")
    if problems:
        raise AtipSpecError("; ".join(problems))
    tree = project.fingerprint()
    pending = []
    for task in plan.tasks:
        if not task.verify:
            continue
        record = evidence.get(task.id)
        if record is None:
            raise AtipSpecError(f"Missing evidence for {task.id}")
        problems = evidence_problems(record, task, slug)
        if problems or record.result != "pass" or record.tree != tree:
            raise AtipSpecError(f"Cannot attest {task.id}: stale, failed or invalid evidence: {'; '.join(problems)}")
        pending.append(record)
    if not pending:
        raise AtipSpecError("No executable evidence to attest")
    for record in pending:
        sign_document(record.path, {**record.data, "ci_run_url": run_url}, identity, key, policy, "ci", project.root)
    return [record.path for record in pending]


def require_preflight(project, slug, policy):
    spec = parse_spec((project.delivery_dir(slug) / "spec.md").read_text())
    if spec.status != "ready" or spec.problems or spec.open_questions:
        raise AtipSpecError("Finish the specification before verification")
    for phase in ("spec", "plan"):
        if not approvals_for(project, slug, phase, policy, spec.meta.get("owner")):
            raise AtipSpecError(f"Missing trusted {phase} approval before verification")


def check_assurance(project, slug, policy, report, spec, plan, evidence):
    from . import frontmatter
    from .contract import evaluate, parse_contract, missing_commands
    from .audit import repository_files
    from .trust import subject
    for req in spec.requirements:
        if req.remove and not req.criteria:
            report.add("error", f"{req.id}: removal needs explicit acceptance criteria for the removed behavior")
    if not spec.meta.get("owner"):
        report.add("error", "Trusted delivery requires an owner in spec.md")
    meta, _ = frontmatter.split(project.contract.read_text()) if project.contract.is_file() else ({}, "")
    if meta.get("status") != "accepted":
        report.add("error", "Architecture contract must be accepted")
    if not project.git.available:
        report.add("error", "Trusted delivery requires git")
        return
    if project.fingerprint() != project.fingerprint_at("HEAD"):
        report.add("error", "Commit the candidate source and specifications before trusted acceptance")
    contract = parse_contract("```rules\n" + "\n".join(policy.data.get("contract_rules", [])) + "\n```\n")
    for problem in contract.problems:
        report.add("error", f"corporate policy: {problem}")
    for violation in evaluate(contract, project.root, repository_files(project), manifests_always=True):
        report.add("error", f"corporate policy: {violation.render()}")
    for rule in missing_commands(contract, [command for task in plan.tasks for command in task.verify]):
        report.add("error", f"corporate policy requires command: {rule.args[0]}")
    approvals = {}
    for phase in ("spec", "plan", "acceptance"):
        try:
            approvals[phase] = approvals_for(project, slug, phase, policy, spec.meta.get("owner"))
        except (AtipSpecError, OSError) as exc:
            approvals[phase] = []
            if policy.mode == "provider":
                report.add("error", f"{phase} approval could not be read from the provider: {exc}")
        if not approvals[phase]:
            report.add("todo", f"Obtain trusted {phase} approval for the current content")
    criteria = {ac.id: ac.requirement for ac in spec.criteria}
    covered = set()
    for task in plan.tasks:
        for ac in task.tests + task.manual:
            if criteria.get(ac) not in task.covers:
                report.add("error", f"{task.id}: {ac} must belong to a requirement in Covers")
            covered.add(ac)
        if task.tests and not task.verify:
            report.add("error", f"{task.id}: Tests needs executable Verify commands")
        if set(task.tests) & set(task.manual):
            report.add("error", f"{task.id}: a criterion cannot be both Tests and Manual")
        if not task.tests and not task.manual:
            report.add("error", f"{task.id}: declare Tests or Manual acceptance criteria")
        if not task.verify:
            continue
        record = evidence.get(task.id)
        if record is None:
            continue
        try:
            if policy.mode == "provider":
                from .attestation import verify_attestation
                verify_attestation(record.path, policy)
            else:
                if (record.data.get("policy_sha256") != policy.sha256
                    or record.data.get("repository") != policy.data["repository"]
                    or not str(record.data.get("ci_run_url", "")).startswith("https://")):
                    raise AtipSpecError("evidence is not attested for this policy and repository")
                policy.verify(record.path, record.data.get("signer", ""), "ci")
            for phase in ("spec", "plan"):
                if approvals[phase] and not any(date_time(a["approved_at"]) <= date_time(record.data["started"]) for a in approvals[phase]):
                    report.add("error", f"{task.id}: verification predates {phase} approval; verify again")
        except (OSError, AtipSpecError, KeyError) as exc:
            report.add("error", f"{task.id}: missing or invalid trusted CI attestation ({exc})")
    for ac in sorted(set(criteria) - covered):
        report.add("error", f"{ac}: no test or manual validation mapping")
