"""The gate. Everything a delivery must satisfy, computed from its files, the
contract and git.

Levels:
  error    something is wrong or failed; the gate is red
  todo     work that has not happened yet; the gate is not yet green
  warning  worth attention, does not block
  info     context
Exit codes: 0 green, 1 errors, 2 incomplete.
"""
from __future__ import annotations

from .specs import load_spec

from dataclasses import dataclass, field
import re

from .contract import Contract, evaluate, matches, missing_commands, parse_contract
from .delivery import REQ_ID, Plan, load_evidence, parse_deferred, parse_plan, parse_review, parse_spec, verification_task
from .project import Project
from .errors import AtipSpecError
from . import frontmatter
from .assurance import evidence_problems, check_assurance
from .pointers import observation, resolve
from .trust import approvals_for, selected_policy

_UNSET = object()
GIT_REQUIRED = ("git is required: the base commit, contract rules and evidence freshness come from git; run "
                "`git init` and commit, or check a clone")
STATUSES = ("draft", "ready", "planned", "in_progress", "implemented", "checked", "verified")
SESSIONS = ("isolated", "shared")


@dataclass
class Item:
    level: str
    text: str
    source: str = "general"


@dataclass
class Report:
    slug: str
    items: list[Item] = field(default_factory=list)
    status: str = "draft"
    title: str | None = None
    tasks_total: int = 0
    tasks_done: int = 0
    fingerprint: str | None = None
    source: str = "general"
    lead_time: dict | None = None
    proven: set[str] = field(default_factory=set)   # criteria risk low takes from their named test, without a verdict

    def add(self, level: str, text: str, source: str | None = None) -> None:
        """Record an item; `source` names the part of the delivery it comes from
        (policy, spec, plan, contract, violation, base, tasks, evidence, deferred, review, rounds, trust)."""
        self.items.append(Item(level, text, source or self.source))

    def of(self, level: str) -> list[str]:
        return [item.text for item in self.items if item.level == level]

    def blocking(self, sources: tuple[str, ...]) -> list[Item]:
        """Errors and todos that come from the given sources."""
        return [item for item in self.items if item.level in ("error", "todo") and item.source in sources]

    @property
    def errors(self) -> list[str]:
        return self.of("error")

    @property
    def todos(self) -> list[str]:
        return self.of("todo")

    @property
    def ok(self) -> bool:
        return not self.errors and not self.todos

    @property
    def exit_code(self) -> int:
        return 1 if self.errors else 2 if self.todos else 0

    @property
    def next_action(self) -> str:
        if self.errors:
            return "Fix: " + self.errors[0]
        if self.todos:
            return self.todos[0]
        if self.status == "checked":
            return (f"Present `atipspec report {self.slug}`; after explicit human approval in the conversation, "
                    f"record it with `atipspec accept {self.slug} result --code <code from the report>`")
        return f"Run `atipspec deliver {self.slug}`"

    def render(self, next_action: bool = True) -> str:
        head = f"{self.slug}  [{self.status}]"
        if self.tasks_total:
            head += f"  tasks {self.tasks_done}/{self.tasks_total}"
        lines = [head]
        for level in ("error", "todo", "warning", "info"):
            for text in self.of(level):
                lines.append(f"  {level:<8}{text}")
        if next_action:
            lines.append(f"Next: {self.next_action}")
        return "\n".join(lines)


def load_contract(project: Project) -> Contract:
    if not project.contract.is_file():
        return Contract()
    return parse_contract(project.contract.read_text(encoding="utf-8"))


def touched_files(project: Project, base: str | None) -> list[str]:
    """Every path the delivery touched, deleted ones included: for the scope,
    a removal outside the plan is as much drift as an addition."""
    git = project.git
    label = base if base and git.rev_exists(base) else None
    return sorted(set(git.changed(label)) | set(git.untracked(include_atipspec=True)))


def proof_problems(task, record) -> dict[str, str]:
    """For each criterion the task names in Proof, why the evidence does not
    prove it: the test did not run, or it did not pass."""
    from .junit import find
    problems = {}
    if not task.proof:
        return problems
    from .junit import recorded_cases
    cases = recorded_cases(record.data)
    for ident, proof in task.proof.items():
        case = find(proof, cases)
        if case is None:
            problems[ident] = f"the named test {proof} did not run in {task.id}'s evidence"
        elif case["status"] != "passed":
            problems[ident] = f"the named test {proof} {case['status']} in {task.id}'s evidence"
    return problems


def fresh_reports(record) -> bool:
    """Whether every test report in the evidence was written by its own run:
    `verify` marks it `fresh` since 0.3.0."""
    return all(isinstance(entry, dict) and entry.get("fresh") is True for entry in record.data.get("reports") or [])


def review_isolation_required(project: Project, spec, policy=None) -> str | None:
    """What requires the review to come from an isolated session, or None."""
    from .risk import level
    if level(spec) == "high":
        return "risk: high"
    if project.requirement("require_isolated_review", policy):
        return "require_isolated_review"
    return None


def review_cases(project: Project, plan: Plan, evidence: dict, current: str | None) -> list[dict]:
    """The test cases a review pointer may name: those of the current, passing evidence."""
    from .junit import recorded_cases
    cases = []
    for ident in dict.fromkeys(verification_task(plan, task).id for task in plan.tasks):
        record = evidence.get(ident)
        if (record is not None and record.result == "pass"
                and project.same_candidate(record.tree, current)):
            cases += recorded_cases(record.data)
    return cases


def outside_scope(plan: Plan, files: list[str], project: Project | None = None, base: str | None = None) -> list[str]:
    """Touched files that match none of the plan's scope globs. Files under
    .atipspec/ are the delivery's own and never count; with the project, neither
    do the client files AtipSpec installs while they hold only its content."""
    if not plan.scope:
        return []
    from .install import installed_unchanged
    return [name for name in files
            if not name.startswith(".atipspec/") and not any(matches(glob, name) for glob in plan.scope)
            and not (project is not None
                     and installed_unchanged(project.root, name, lambda: _content_at(project, base, name)))]


def _content_at(project: Project, base: str | None, name: str) -> str | None:
    """A file's text at the existing commit `base` (HEAD when None), or None
    when it is not there."""
    try:
        return project.git.run("show", f"{base or 'HEAD'}:{name}")
    except AtipSpecError:
        return None


SCOPE_PROBES = ("x", "x/y", "x/y/z")


def declares_scope(plan: Plan) -> bool:
    """Whether the plan names a scope narrower than the whole repository: globs
    that together match any path declare nothing."""
    globs = [glob for glob in plan.scope if glob.strip()]
    return bool(globs) and not all(any(matches(glob, probe) for glob in globs) for probe in SCOPE_PROBES)


def drift_text(project: Project, slug: str, phase: str) -> str:
    """What changed since a recorded acceptance: the files, when the record names them."""
    from .accept import changed_since
    changed = changed_since(project, slug, phase)
    return ", ".join(changed) if changed else "the approved content"


def _preview_proposal(report: Report, project: Project, slug: str, policy) -> None:
    """In a guided draft, what the proposal still lacks in the plan and the
    contract, and their warnings, such as its size: errors as pending work, so
    `check` names them before `proposal` does."""
    for item in check_delivery(project, slug, policy=policy, preapproval=True).items:
        level = "warning" if item.level == "warning" else "todo" if item.level in ("error", "todo") else None
        if level and item.source in ("plan", "contract") and item.text not in report.of(level):
            report.add(level, item.text, item.source)


def check_delivery(project: Project, slug: str, fingerprint=_UNSET, policy=None, *, preapproval=False) -> Report:
    directory = project.delivery_dir(slug)
    report = Report(slug)
    policy = policy or selected_policy(project)
    if policy is None and project.trust_required:
        report.add("error", "this project requires an external trust policy (`trust: required` in "
                            ".atipspec/config.yaml): set ATIPSPEC_TRUST_POLICY or pass --policy; local "
                            "acceptance is disabled", "policy")
    report.source = "spec"
    spec = load_spec(project, slug)
    report.title = spec.title
    from .status import lead_time
    clock = _clock(report, project, lead_time(project, slug, spec, policy))
    from .risk import describe, level
    guided = spec.meta.get("schema") == 2
    risk = level(spec)
    if risk is None:
        report.add("error", f"risk must be low, normal or high, found {spec.meta.get('risk')!r}")
        risk = "normal"
    elif guided or "risk" in spec.meta:
        report.add("info", describe(risk))
    if risk == "low":
        for req in spec.requirements:
            if req.remove:
                report.add("error", f"risk low does not apply to a change that removes {req.id}: set `risk: normal` "
                                    "or `high` in spec.md")
    fix = guided and spec.kind == "fix"
    if not guided and spec.meta.get("change_id"):
        # Only guided deliveries get a change_id: without the schema line the gate would read the legacy flow.
        report.add("error", "spec.md has a change_id and no `schema: 2`: a guided delivery stays guided; restore "
                            "the line `schema: 2` in its frontmatter")
    for problem in spec.problems:
        report.add("error", problem)
    if spec.status not in ("draft", "ready"):
        report.add("error", f"spec.md status must be draft or ready, found {spec.status!r}")
    if not spec.title:
        report.add("error", "spec.md needs a title line: # Title")
    # While the spec is a draft, missing content is pending work, not a defect.
    incomplete = "todo" if spec.status == "draft" else "error"
    reference = None
    if guided:
        from .specs import compared
        try:
            reference = compared(project, slug, spec, policy)
        except AtipSpecError as exc:
            report.add("error", str(exc))
    if fix:
        _check_fix_references(report, project, spec, incomplete, reference)
    elif guided:
        if not spec.meta.get("requirements"):
            report.add(incomplete, f"no requirements referenced yet: write them in .atipspec/specs/{spec.capability}.md "
                                   "and list their IDs under `requirements` in spec.md, or run "
                                   f"`atipspec spec-bind {slug} --file <authored.md>`")
    elif not spec.requirements:
        report.add(incomplete, "spec.md has no requirements; use headings like `### REQ-001: Behavior`")
    _check_ids(report, "requirement", [req.id for req in spec.requirements], "REQ")
    _check_ids(report, "criterion", [ac.id for ac in spec.criteria], "AC")
    for req in spec.requirements:
        if not req.criteria and not req.remove:
            report.add(incomplete, f"{req.id} has no acceptance criteria; " + (
                f"add a scenario under it in .atipspec/specs/{spec.capability}.md: `#### AC-...: Title` with "
                "WHEN and THEN steps" if guided else "add lines like `- AC-001: outcome`"))
    if spec.open_questions:
        count = len(spec.open_questions)
        if spec.status == "ready":
            report.add("error", f"{count} open question(s) remain; resolve them in spec.md or set status: draft")
        else:
            report.add("info", f"{count} open question(s) recorded")
    if spec.assumptions and spec.status == "draft":
        report.add("info", f"{len(spec.assumptions)} assumption(s) for the user to confirm at acceptance")
    if spec.meta.get("schema") == 2:
        _check_decisions(report, project, slug, spec, policy, preapproval)
    from .lint import lint_spec
    level = "error" if project.policy("strict_criteria") else "warning"
    for finding in lint_spec(spec, project.language, str(project.policy("criteria_syntax"))):
        report.add(level if finding.strict else "warning", finding.text)
    if reference is not None:
        _check_unlisted(report, project, slug, spec, risk, reference, policy)
    for name in spec.impact:
        if not (project.specs / f"{name}.md").is_file() and name != spec.capability:
            report.add("warning", f"impact names {name!r}, which is not a living spec in .atipspec/specs/")
    limit = min(int(project.policy("max_requirements")), 2) if spec.kind == "fix" else int(project.policy("max_requirements"))
    if (spec.status == "ready" or preapproval) and len(spec.requirements) > limit:
        report.add("warning", f"{len(spec.requirements)} requirements (policy {limit}): a delivery should fit in a "
                              "working day; split it into deliveries under an initiative")
    from .accept import describe_contract, contract_acceptance, is_current, read_record
    if guided and project.contract.is_file() and contract_acceptance(project).state != "accepted":
        report.add("warning", f"contract: {describe_contract(project)}", "contract")
    if policy is None and project.trust_required:
        approval = (f"each approver inspects `atipspec approval-subject {slug} spec` (and `plan`) and signs it with "
                    "`atipspec approve` under the organization's trust policy")
    elif guided:
        approval = (f"present `atipspec proposal {slug}` and, after explicit human approval in the conversation, "
                    f"record it with `atipspec accept {slug} proposal --code <code>`")
    else:
        approval = (f"present `atipspec proposal {slug}`, request human confirmation in the conversation, "
                    "then record it with the `atipspec accept` command and code that view prints")
    if not project.git.available:
        report.add("error", GIT_REQUIRED, "base")
    from .install import framework_problem
    if problem := framework_problem(project.root, project.git):
        report.add("error", problem, "base")
    if guided:
        if spec.status != "ready" and not preapproval:
            report.status = "draft"
            todo = Item("todo", approval[0].upper() + approval[1:], report.source)
            report.items.append(todo)
            _preview_proposal(report, project, slug, policy)
            if spec.open_questions or any(item is not todo and item.level in ("error", "todo")
                                          and item.source in ("spec", "plan", "contract") for item in report.items):
                todo.text = "Finish the scenarios, approach and tests; " + approval
            return report
        if policy is None and not preapproval and not is_current(project, slug, "proposal"):
            report.status = "draft"
            changed = read_record(project, slug, "proposal") is not None
            report.add("todo", (f"{drift_text(project, slug, 'proposal')} changed after the proposal's acceptance" if changed
                                else "the proposal is not accepted for its current content") + "; " + approval)
            _preview_proposal(report, project, slug, policy)
            return report
    else:
        if spec.status != "ready" and not preapproval:
            report.status = "draft"
            report.add("todo", "Finish the spec phase; " + approval)
            return report
        if policy is None and not preapproval and not is_current(project, slug, "spec"):
            report.status = "draft"
            changed = read_record(project, slug, "spec") is not None
            report.add("todo", (f"{drift_text(project, slug, 'spec')} changed after the acceptance" if changed
                                else "spec.md is not accepted for its current content") + "; " + approval)
            return report

    report.source = "plan"
    plan_path = directory / "plan.md"
    plan = parse_plan(plan_path.read_text(encoding="utf-8")) if plan_path.is_file() else None
    if plan is None or not plan.tasks:
        report.status = "ready"
        report.add("todo", "Write plan.md: tasks with Covers and Tests or Manual lines, and a `## Final verification` "
                           "section with Verify commands (framework/workflows/plan.md)" if guided else
                   "Write plan.md: tasks with Covers and Verify lines (framework/workflows/plan.md)")
        return report
    for problem in plan.problems:
        report.add("error", problem)
    if (project.policy("strict_scope") or risk == "high") and not declares_scope(plan):
        report.add("error", "plan.md declares no scope: list in `scope:` the paths this change may touch "
                            "(globs that together match every path declare nothing)"
                   + ("" if project.policy("strict_scope") else "; risk: high requires it"))
    _check_ids(report, "task", [task.id for task in plan.tasks], "T")
    active = {req.id for req in spec.requirements}
    covered: set[str] = set()
    for task in plan.tasks:
        if not task.covers:
            report.add("error", f"{task.id} has no Covers line")
        for ident in task.covers:
            if ident in active:
                covered.add(ident)
            else:
                report.add("error", f"{task.id} covers {ident}, which is not an active requirement")
        if not task.verify and not task.verify_none and plan.final is None:
            report.add("warning", f"{task.id} has no Verify commands; only the review can verify it")
    for ident in sorted(active - covered):
        report.add("error", f"{ident} is not covered by any task")
    methods = {ac.id: ac.method for ac in spec.criteria}
    parents = {ac.id: ac.requirement for ac in spec.criteria}
    mapped: set[str] = set()
    for task in plan.tasks:
        for ident in task.tests + task.manual:
            if parents.get(ident) not in task.covers:
                report.add("error", f"{task.id}: {ident} must belong to a requirement in Covers")
        if task.tests and not verification_task(plan, task).verify:
            report.add("error", f"{task.id}: Tests needs executable Verify commands")
        if set(task.tests) & set(task.manual):
            report.add("error", f"{task.id}: a criterion cannot be both Tests and Manual")
        for ident in task.tests:
            if methods.get(ident) == "manual":
                report.add("error", f"{task.id} lists {ident} under Tests, but the spec marks it [manual]")
        for ident in task.manual:
            if methods.get(ident) == "test":
                report.add("error", f"{task.id} lists {ident} under Manual, but the spec expects a test; mark it [manual] in the spec or move it to Tests")
        mapped.update(task.tests + task.manual)
    for ident in sorted(set(methods) - mapped):
        report.add("todo", f"{ident}: no task lists it under Tests or Manual")
    if plan.final:
        for ident in plan.final.proof:
            if ident not in methods or methods[ident] != "test":
                report.add("error", f"Final verification Proof names unknown or manual criterion {ident}")
    if fix and spec.requirements and not set(methods) & {ident for task in plan.tasks for ident in task.tests}:
        report.add("error", "a fix needs an automated regression criterion: list a criterion of the corrected "
                            "requirement under Tests, with a test that fails before the fix and passes after it")
    required = ("require_proof is on" if project.requirement("require_proof", policy)
                else "risk is high" if risk == "high" else None)
    reported: set[str] = set()
    for task in plan.tasks:
        verification = verification_task(plan, task)
        where = "Final verification" if verification.id == "FINAL" else verification.id
        first = verification.id not in reported
        reported.add(verification.id)
        if verification.report and first and project.git.available:
            from .verify import report_path_problem
            problem = report_path_problem(project, verification.report)
            if problem:
                report.add("error", f"{where}: {problem}")
        if required and task.tests:
            if not verification.report and first:
                report.add("error", f"{where}: {required}, so the Verify commands write a JUnit XML "
                                    "report named in `Report:`, at a path git ignores")
            for ident in task.tests:
                if ident not in verification.proof:
                    report.add("error", f"{ident}: {required}: name the test that proves it under "
                                        f"{where}'s `Proof:`")
    report.tasks_total = len(plan.tasks)
    limit = int(project.policy("max_tasks"))
    if len(plan.tasks) > limit:
        report.add("warning", f"{len(plan.tasks)} tasks (policy {limit}): a delivery should fit in a working day; "
                              "split it into deliveries under an initiative")

    report.source = "contract"
    if not project.contract.is_file():
        report.add("error", "contract.md is missing; restore the architecture contract")
    contract = load_contract(project)
    for problem in contract.problems:
        report.add("error", problem)
    commands = plan.final.verify if plan.final else [command for task in plan.tasks for command in task.verify]
    for rule in missing_commands(contract, commands):
        report.add("error", f"contract requires every plan to verify with `{rule.args[0]}` (contract.md line {rule.line})")
    if (policy is None and not preapproval and not guided and project.policy("approve_plan") and spec.kind != "fix"
            and not is_current(project, slug, "plan")):
        changed = read_record(project, slug, "plan") is not None
        report.add("todo", (f"{drift_text(project, slug, 'plan')} changed after the plan's acceptance" if changed
                            else "plan.md is not accepted for its current content")
                   + f"; present `atipspec proposal {slug}`, request human confirmation in the conversation, "
                     f"then record it with `atipspec accept {slug} plan --code <code>`", "plan")

    git = project.git
    if git.available:
        current = project.fingerprint() if fingerprint is _UNSET else fingerprint
        from .specs import base_problem
        problem = base_problem(project, spec, slug)
        label = None if problem else spec.meta["base"]
        from .integration import brought_paths
        found, brought, rebased = brought_paths(project, slug, label, policy)
        # Every path the delivery touched since its base (HEAD when the base is unusable), deleted ones included.
        since_base = set(git.changed(label))
        changed = since_base | set(git.untracked(include_atipspec=True)) | rebased
        files = sorted(name for name in changed if (project.root / name).exists())
        done = git.task_commits(slug, label)
        if spec.meta.get("schema") == 2:
            done = {}  # guided task completion is bound to the approved task, not a past commit label
        if problem and problem not in report.errors:
            report.add("error", problem, "base")
        for violation in evaluate(contract, project.root, files, manifests_always=False):
            report.add("error", f"contract: {violation.render()}", "violation")
        if brought:
            shown = sorted(name for name in brought if not name.startswith(".atipspec/"))
            rest = len(brought) - len(shown)
            names = ", ".join(shown[:10]) + (", ..." if len(shown) > 10 else "")
            if rest:
                names += (" and " if shown else "") + f"{rest} file(s) under .atipspec/"
            report.add("info", f"brought by {found.ref} since the base, so not this delivery's change: {names}")
        taken_back = sorted((rebased - since_base) | _undone(project, found, rebased, current))
        if taken_back:
            names = ", ".join(taken_back[:10]) + (", ..." if len(taken_back) > 10 else "")
            report.add("warning", f"undoes, in whole or in part, what {found.ref} changed there since the base, so "
                                  f"this delivery's change, shown against the merge base {found.commit[:12]}: "
                                  f"{names}; keep it only if a task needs it")
        stray = outside_scope(plan, sorted(changed - brought), project, label)
        if stray:
            report.add("error" if project.policy("strict_scope") or risk == "high" else "warning",
                       f"files outside the declared scope: {', '.join(stray)}; widen `scope` in plan.md "
                       "with the task that needs them, or revert them", "violation")
        if guided and label:
            _check_other_specs(report, project, slug, spec, risk, label, changed, policy)
        contract_path = ".atipspec/contract.md"
        existed = git.head() is not None and git.exists_at(label or "HEAD", contract_path)
        if contract_path in changed and existed and risk == "low":
            report.add("error", "risk low does not apply to a change of the architecture contract: set `risk: normal` "
                                "or `high` in spec.md", "contract")
        if contract_path in changed and existed:
            new = [name for name in sorted(changed)
                   if name.startswith(".atipspec/decisions/DEC-") and name.endswith(".md")
                   and not git.exists_at(label or "HEAD", name) and (project.root / name).is_file()]
            if policy:
                accepted = []
                for name in new:
                    try:
                        meta, _ = frontmatter.split((project.root / name).read_text(encoding="utf-8"))
                        affects = meta.get("affects", [])
                        affects = affects if isinstance(affects, list) else [affects]
                        if meta.get("status") == "accepted" and any(str(x).split(":")[0] == "contract" for x in affects):
                            if not approvals_for(project, slug, "decision:" + str(meta.get("id")), policy, spec.meta.get("owner")):
                                continue
                            accepted.append(name)
                    except (ValueError, OSError, AtipSpecError):
                        continue
                if not accepted:
                    report.add("error", "contract.md changed without a new decision that is accepted, affects contract, "
                                        "and has required approval", "violation")
            else:
                # A status written by hand is not an acceptance: the new decision
                # must be in the contract's recorded acceptance of this content.
                acceptance = contract_acceptance(project)
                included = acceptance.record["content"] if acceptance.state == "accepted" else {}
                if not any(name in included for name in new):
                    # Name what is missing: accepting the same content again adds no decision.
                    report.add("error", "contract.md changed without a new decision included in the contract's "
                                        "recorded acceptance: add one with `atipspec decision <slug> --title \"...\" "
                                        "--affects contract` that says why, then present `atipspec proposal contract` "
                                        "and, after the human approves it, record `atipspec accept contract --code "
                                        "<code>`", "violation")

    else:
        done = {}
        current = None
        if GIT_REQUIRED not in report.errors:
            report.add("error", GIT_REQUIRED, "base")
    report.fingerprint = current
    report.source = "evidence"
    evidence, problems = load_evidence(directory / "evidence")
    for problem in problems:
        report.add("error", problem)
    from .progress import completed_tasks
    completed = completed_tasks(project, slug, plan)
    proven: set[str] = set()   # criteria whose test named in Proof passed in the current evidence
    for task in plan.tasks:
        if task.id in done or task.id in completed:
            report.tasks_done += 1
        else:
            report.add("todo", f"{task.id} is not complete: implement it and record "
                               f"`atipspec task-done {slug} {task.id} --note <summary>`", "tasks")
        task = verification_task(plan, task)
        if not task.verify:
            continue
        record = evidence.get(task.id)
        defects = evidence_problems(record, task, slug) if record is not None else []
        if task.id != "FINAL":
            _judge_evidence(report, project, slug, task, record, defects, current)
        if record is not None and (current is None
                                   or project.same_candidate(record.tree, current)):
            unproven = proof_problems(task, record)
            for ident, problem in unproven.items():
                report.add("error", f"{ident}: {problem}")
            if current is not None and record.result == "pass" and not defects and fresh_reports(record):
                proven.update(ident for ident in task.proof
                              if ident not in unproven and ident in task.tests and methods.get(ident) == "test")
        if task.report and not required:
            for ident in task.tests:
                if ident not in task.proof:
                    report.add("info", f"{ident} has no named test in {task.id}'s Proof; the reviewer must verify it")
    if plan.final is not None and plan.final.verify and plan.tasks:
        # The final verification backs every task: judged once, after them, so a task left comes first.
        final = verification_task(plan, plan.tasks[0])
        record = evidence.get("FINAL")
        _judge_evidence(report, project, slug, final, record,
                        evidence_problems(record, final, slug) if record is not None else [], current)

    report.source = "deferred"
    deferred_path = directory / "deferred.md"
    deferred, problems = parse_deferred(deferred_path.read_text(encoding="utf-8")) if deferred_path.is_file() else ({}, [])
    for problem in problems:
        report.add("error", problem)
    for ident in deferred:
        if not ident.startswith("F"):
            report.add("error", f"{ident} cannot be deferred: acceptance criteria are met or the spec changes explicitly")

    report.source = "review"
    from .rounds import FILE as ROUNDS, missing, read as read_rounds, used_up
    rounds = None
    recorded = (directory / ROUNDS).exists()
    lost = missing(project, slug) if policy is None else None
    if lost:
        report.add("error", lost, "rounds")
    if recorded:
        try:
            rounds = read_rounds(project, slug)
        except (AtipSpecError, OSError) as exc:
            report.add("error", str(exc))
    refusal = used_up(project, slug, rounds, current) if rounds else None
    if refusal:
        report.add("error", "review rounds are used up: " + refusal, "rounds")
    review_path = directory / "review.md"
    if not review_path.is_file():
        if not (refusal or lost):   # `review` would refuse: the user decides first
            report.add("todo", f"No review.md: run `atipspec review {slug}` and give the packet to a reviewer in "
                               "an isolated session")
    else:
        review = parse_review(review_path.read_text(encoding="utf-8"))
        for problem in review.problems:
            report.add("error", problem)
        stale = False
        if review.tree is None:
            report.add("error", "review.md frontmatter needs `tree:` with the fingerprint from the packet")
        elif current is not None and not project.same_candidate(review.tree, current):
            stale = True
            report.add("todo", f"review.md is stale (the working tree changed since the review); run "
                               f"`atipspec review {slug}` and review again")
        elif current is not None and (rounds is not None or not recorded) and not (
                rounds and project.same_candidate(rounds["packet_tree"], current)):
            # Rounds are counted when `review` writes a packet: a review of a candidate it never counted is not taken.
            report.add("todo", f"review.md is not the review of the last packet `atipspec review` counted; run "
                               f"`atipspec review {slug}` and give the packet to a reviewer in an isolated session")
        if not review.reviewer:
            report.add("error", "review.md frontmatter needs `reviewer:` with the client or model that wrote the review")
        if review.session not in SESSIONS:
            report.add("error", f"review.md session must be isolated or shared, found {review.session!r}")
        elif review.session == "shared":
            declared = "says session: shared" if "session" in review.meta else "declares no session, so it counts as shared"
            text = (f"review.md {declared}: verdicts from a session that saw the author's conversation are not "
                    "independent; give the packet to a reviewer in an isolated session (a subagent or a new session)")
            reason = review_isolation_required(project, spec, policy)
            report.add("error" if reason else "warning", text + (f"; {reason} requires it" if reason else ""))
        cases = review_cases(project, plan, evidence, current)
        # A stale review is done again; until the evidence is current, a test it names cannot be found.
        pointers = None if stale else "todo" if report.blocking(("evidence",)) else "error"
        known = {ac.id for ac in spec.criteria}
        named: dict[str, str] = {}   # criterion -> the test its Proof names
        for task in plan.tasks:
            for ident, test in verification_task(plan, task).proof.items():
                named.setdefault(ident, test)
        for ac in spec.criteria:
            verdict = review.verdicts.get(ac.id)
            if verdict is None and risk == "low" and ac.id in proven:
                report.proven.add(ac.id)
                report.add("info", f"{ac.id}: its test named in Proof passed in the current evidence, so risk low "
                                   "needs no reviewer verdict")
            elif verdict is None:
                report.add("error", f"{ac.id} has no verdict in review.md")
            elif not verdict[1].strip():
                report.add("error", f"{ac.id} needs a proof pointer or precise failure reason")
            elif verdict[0] == "FAIL":
                note = f": {verdict[1]}" if verdict[1] else ""
                report.add("error", f"{ac.id} FAIL{note}")
            elif pointers and resolve(project, verdict[1], cases, directory) is None and not (
                    ac.method == "manual" and observation(verdict[1])):
                report.add(pointers, f"{ac.id} PASS points to nothing the gate can find ({verdict[1]!r}): name a test "
                                     "that passed in the evidence report, a `path:line` of a file outside .atipspec/ "
                                     "(the evidence logs under `evidence/logs/` included) or a `path::test`"
                                     + ("; or describe what was done and observed" if ac.method == "manual" else ""))
            elif verdict[0] == "PASS" and named.get(ac.id) and named[ac.id] not in verdict[1]:
                # A pointer that resolves names something real; the Proof says which test proves the criterion.
                report.add("warning", f"{ac.id} PASS points to {verdict[1]!r}, not to {named[ac.id]}, the test its "
                                      "Proof names: point to that test, or say why another proof holds")
        for ident in review.verdicts:
            if ident not in known:
                report.add("warning", f"review.md gives a verdict for unknown {ident}")
        finding_ids = {finding.id for finding in review.findings}
        for finding in review.findings:
            label = f"{finding.id} [{finding.severity}] {finding.text}"
            if finding.id in deferred:
                approved = []
                if policy:
                    try:
                        approved = approvals_for(project, slug, "exception:" + finding.id, policy, spec.meta.get("owner"))
                    except (OSError, AtipSpecError):
                        pass
                if finding.severity in ("blocker", "major") and not approved:
                    report.add("error", f"{label}: deferral needs a trusted risk approval with expiry")
                else:
                    report.add("info", f"{label} (deferred: {deferred[finding.id]})")
            elif finding.severity in ("blocker", "major"):
                # Only a minor finding is deferred without a policy: a deferral of these needs a risk exception.
                report.add("error", f"{label}; fix it, or under a trust policy obtain a risk exception with expiry")
            else:
                report.add("info", label)
        for ident in deferred:
            if ident.startswith("F") and ident not in finding_ids:
                report.add("warning", f"deferred {ident} is not in the current review")

    from .traceability import merge_conflicts
    for problem in merge_conflicts(project, spec, slug):
        report.add("error", problem, "spec")
    if spec.meta.get("schema") == 2:
        from .teams import configuration, conflicts, dependencies, read_contracts
        try:
            config = configuration(project)
            for problem in conflicts(project, slug):
                report.add("error", problem, "coordination")
            owners = config["owners"].get(spec.capability, [])
            if owners and not spec.meta.get("owner"):
                report.add("error", f"Assign a human owner for {spec.capability}; capability owners: {', '.join(owners)}", "coordination")
            for problem in dependencies(project, slug):
                report.add("todo", problem, "integration")
            pins = read_contracts(project, slug)
            if project.system and not any(pin["name"] == "system-contract" for pin in pins):
                from .teams import system_pin_command
                report.add("error", "config.yaml sets `system`, and the system contract is not pinned for this "
                                    f"delivery: run `{system_pin_command(slug)}`", "coordination")
        except (AtipSpecError, OSError, ValueError, TypeError) as exc:
            report.add("error", str(exc), "coordination")
    report.source = "trust"
    if policy:
        from .status import created_at
        accepted = check_assurance(project, slug, policy, report, spec, plan, evidence)
        signed = [approval["approved_at"] for approval in accepted if created_at(approval.get("approved_at"))]
        if signed:
            # Under a policy the result is accepted when its acceptance is signed.
            for item in clock:
                report.items.remove(item)
            _clock(report, project, lead_time(project, slug, spec, policy, max(signed, key=created_at)))
    else:
        report.add("info", "Local mode: acceptance records detect drift; identity and evidence provenance are not externally authenticated")
    if report.tasks_done == 0:
        report.status = "planned"
    elif report.tasks_done < report.tasks_total:
        report.status = "in_progress"
    else:
        report.status = ("verified" if policy else "checked") if report.ok else "implemented"
    if policy is None and report.ok and is_current(project, slug, "result"):
        report.status = "accepted"
    return report


def _judge_evidence(report: Report, project: Project, slug: str, task, record, defects: list[str], current) -> None:
    """Whether a verification's last evidence holds for the current candidate."""
    for problem in defects:
        report.add("error", f"{task.id}: {problem}")
    if record is None:
        selection = "" if task.id == "FINAL" else f" --task {task.id}"
        report.add("todo", f"{task.id}: no evidence; run `atipspec verify {slug}{selection}`")
    elif record.result != "pass":
        report.add("error", f"{task.id}: last verification failed ({record.path.name}); fix and verify again")
    elif current is not None and not project.same_candidate(record.tree, current):
        report.add("todo", f"{task.id}: evidence is stale (the working tree changed); verify again")
    elif task.report and not fresh_reports(record):
        report.add("todo", f"{task.id}: the evidence's test report predates the report freshness check "
                           f"(AtipSpec 0.2.x); run `atipspec verify {slug}` again")


def _clock(report: Report, project: Project, lead: dict) -> list[Item]:
    """Record the lead time: past `max_age_hours` a warning, below it an info.
    Returns the items it added."""
    from .status import age_warning, format_age
    report.lead_time = lead
    added = len(report.items)
    warning = age_warning(project, lead["hours"])
    if warning:
        report.add("warning", warning, "policy")
    elif lead["hours"] is not None:
        report.add("info", f"lead time {format_age(lead['hours'])}: " + (
            "from creation to result acceptance" if lead["complete"] else "since creation, until the result is accepted"),
            "policy")
    return report.items[added:]


DECIDED = {"out_of_scope": "Out of scope", "quality": "Quality attributes"}


def _check_decisions(report: Report, project: Project, slug: str, spec, policy, preapproval: bool) -> None:
    """A guided delivery's spec.md states its intent and decides what it
    leaves out and which limits it must hold, `- None` included. Until the
    proposal is approved, a missing decision is pending work; afterwards a
    warning to settle when the proposal next changes, since editing spec.md
    voids its approval. Approved means a local record of this content,
    whatever the status line says; under a trust policy, whose signatures are
    the approval, the status the people set by hand, except on the way to a
    local record (`proposal`, `accept proposal`), where only such a record
    counts. A section a delivery was not created with, as in 0.2.0, is a
    warning when missing."""
    from .accept import is_current
    from .delivery import EMPTY_ITEM, LIST_ITEM, PLACEHOLDER
    from .specs import baseline_sections
    approved = spec.status == "ready" if policy and not preapproval else is_current(project, slug, "proposal")
    pending = "warning" if approved else "todo"
    later = ", the next time the proposal changes: editing spec.md only for this voids its approval" if approved else ""
    if spec.kind == "fix":
        stated = defect_statement(spec.sections.get("defect"))
        missing = [label for label in ("Observed", "Expected") if not stated.get(label.lower())]
        if missing:
            report.add(pending, f"spec.md ## Defect does not state {' and '.join(f'`{label}:`' for label in missing)}: "
                                "what happens today, with the steps and values, and what the corrected requirement "
                                f"says should happen{later}")
        return
    created = baseline_sections(project, slug)

    def decided(lines: list[str]) -> list[str]:
        values = [(match.group(1) if (match := LIST_ITEM.match(line)) else line) for line in lines]
        return [value for value in values if not PLACEHOLDER.match(value)]

    def items(lines: list[str]) -> list[str]:
        return [value for value in decided(lines) if not EMPTY_ITEM.match(value)]

    if not items(spec.sections.get("intent", [])):
        report.add(pending, "spec.md ## Intent is empty: state the actor, the trigger, the observable result "
                            f"and how the user will know it worked{later}")
    for meaning, heading in DECIDED.items():
        if meaning not in spec.sections:
            report.add(pending if meaning in created else "warning",
                       f"spec.md has no ## {heading} section: add it with its items, or `- None`{later}")
        elif not decided(spec.sections[meaning]):
            report.add(pending, f"spec.md ## {heading} is undecided: list the items, or write `- None`{later}")
    active = {req.id for req in spec.requirements}
    for item in items(spec.sections.get("quality", [])):
        named = [ident.upper() for ident in REQ_ID.findall(item)]
        unknown = [ident for ident in named if ident not in active]
        if not named or unknown:
            what = f"names {', '.join(unknown)}, not a requirement" if unknown else "names no requirement"
            report.add("error" if approved else "todo",
                       f"quality attribute `{item}` {what} of this change: write the limit in specs/ "
                       "as a requirement whose criterion states the number and how it is measured, list it under "
                       "`requirements`, and name it here as `- REQ-...: limit`")


LABELED = re.compile(r"^(?:[-*]\s+)?(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:(.*)$")


def defect_statement(lines: list[str] | None) -> dict[str, str]:
    """What a fix's `## Defect` section states after each label it knows
    (`Observed:`, `Expected:`, `Reproduction:`), by meaning; a label's text
    continues on the lines up to the next label."""
    from .delivery import PLACEHOLDER
    from .locale import DEFECT_LABELS
    found: dict[str, list[str]] = {}
    current = None
    for line in lines or []:
        match = LABELED.match(line)
        meaning = next((key for key, names in DEFECT_LABELS.items()
                        if match and match.group(1).strip().lower() in names), None)
        if meaning:
            current = meaning
            found[current] = [match.group(2).strip()]
        elif current:
            found[current].append(line.strip())
    statement = {key: " ".join(part for part in parts if part) for key, parts in found.items()}
    return {key: text for key, text in statement.items() if not PLACEHOLDER.match(text)}


def _check_fix_references(report: Report, project: Project, spec, incomplete: str, reference: str | None) -> None:
    """A guided fix corrects requirements its capability had already accepted,
    those of `reference`: its living spec as committed at the delivery's base,
    with what the integration branch brought and the deliveries archived in
    the branch wrote since. Only a project whose living specs held none may
    get its first one from a fix."""
    if not spec.meta.get("requirements"):
        report.add(incomplete, f"spec.md lists no requirement: a fix names under `requirements` the accepted "
                               f"requirement of specs/{spec.capability}.md it corrects")
        return
    if reference is None:
        return
    accepted = {req.id for req in parse_spec(reference).requirements}
    from .specs import specified
    first = not accepted and not specified(project, spec.meta["base"])
    for req in spec.requirements:
        if req.remove:
            report.add("error", f"a fix cannot remove {req.id}: removing a behavior is a feature delivery")
        elif req.id in accepted:
            continue
        elif first:
            report.add("info", f"{req.id} specifies {spec.capability} for the first time: no living spec held a "
                               "requirement at the delivery's base commit")
        elif accepted:
            report.add("error", f"{req.id} is not an accepted requirement of {spec.capability}: a fix corrects one "
                                f"that specs/{spec.capability}.md held at the delivery's base commit or that a "
                                "delivery wrote there since; a behavior no requirement covers is a feature delivery")
        else:
            report.add("error", f"{req.id} is not an accepted requirement of {spec.capability}: "
                                f"specs/{spec.capability}.md held none at the delivery's base commit, while other "
                                "living specs did; set `capability:` in spec.md to the capability whose requirement "
                                "this fix corrects, or deliver the behavior as a feature")


def _undone(project: Project, found, paths, tree: str) -> set[str]:
    """Of `paths`, which the fingerprint tree `tree` changed since the merge
    base `found` holds, those whose change undoes, in whole or in part, what
    the integration branch changed there: it takes out or rewrites a line
    that branch added, or puts back one it took out, where it was or, when
    the merge base holds that line nowhere, anywhere. Both diffs place their
    lines in the merge base, so a line the file holds elsewhere does not
    hide that."""
    def lines(text) -> set[str]:
        return {line.rstrip() for line in text if line.strip()}

    def span(start: int, count: int) -> tuple[int, int]:
        """The boundaries between lines a hunk touches, counted in halves."""
        return (2 * start - 1, 2 * (start + count) - 1) if count else (2 * start + 1, 2 * start + 1)

    def touch(one: tuple[int, int], other: tuple[int, int]) -> bool:
        return one[0] <= other[1] and other[0] <= one[1]

    if not paths:
        return set()
    merged = project.fingerprint_at(found.commit)
    undone = set()
    for path in paths:
        theirs = project.git.hunks(found.fork, found.commit, path)
        ours = project.git.hunks(merged, tree, path)
        added = {start + index for _, _, start, _, _, put in theirs for index, line in enumerate(put) if line.strip()}
        taken = {at + index for at, size, *_ in ours for index in range(size)}
        gone = (lines(line for *_, out, _ in theirs for line in out)
                - lines((project.git.blob_text(found.commit, "./" + path) or "").split("\n")))
        if added & taken or gone & lines(line for *_, back in ours for line in back) or any(
                touch(span(start, count), span(at, size)) and lines(out) & lines(back)
                for _, _, start, count, out, _ in theirs for at, size, _, _, _, back in ours):
            undone.add(path)
    return undone


def _remedy(action: str, committed: bool) -> str:
    """The action that undoes an unlisted change; one committed in the branch
    may come from another change, which then needs a delivery of its own."""
    return (f"{action} if this delivery made that change; if another change committed it, that change needs a "
            "delivery of its own") if committed else action


def _check_unlisted(report: Report, project: Project, slug: str, spec, risk: str, reference: str,
                    policy=None) -> None:
    """Requirements of the capability that the delivery adds, changes or
    removes in specs/ without listing them, compared with `reference`: an
    error at every risk, since the approval does not hash them and
    merge-check blocks them. A fix changes only what it lists, and neither a
    fix nor risk low removes a requirement. A change of the text no approval
    hashes (see `outside`) is a warning: only the acceptance of the result
    covers it. Where the integration branch changed that text, it is
    compared with the merge base instead; elsewhere, holding it as the merge
    base does is not this delivery's change either."""
    from .integration import point
    from .specs import canonical_path, listed_elsewhere, outside, unlisted_changes
    from .trust import read_regular
    path = project.rel(canonical_path(project, spec))
    fix = spec.kind == "fix"
    strict = fix or risk == "low"
    for ident, (change, committed) in unlisted_changes(project, slug, spec, reference).items():
        if change == "removed" and fix:
            text = (f"a fix cannot remove {ident}, deleted or marked `[remove]` in {path}: restore it; removing a "
                    "behavior is a feature delivery")
        elif change == "removed" and strict:
            text = (f"risk low does not apply to a change that removes {ident}, deleted or marked `[remove]` in "
                    f"{path}: restore it, or set `risk: normal` or `high` in spec.md, keep it as "
                    f"`### {ident} [remove]: <title>` and list it under `requirements`")
        elif change == "removed":
            text = (f"{ident} is deleted or marked `[remove]` in {path} but is not listed in `requirements`: "
                    f"restore it, or keep it as `### {ident} [remove]: <title>` and list it, so check reads the "
                    "removal")
        elif change == "added" and fix:
            text = (f"{ident} is new in {path}, and a fix adds no requirement: {_remedy('remove it', committed)}; "
                    "a behavior no requirement covers is a feature delivery")
        elif strict:
            text = (f"{ident} differs in {path} from the requirements accepted before this delivery but is not "
                    "listed in `requirements`: " + ("a fix changes only the requirements it lists" if fix else
                                                     "risk low reads only the listed requirements")
                    + "; list it if this change writes it, or " + _remedy("restore it", committed))
        else:
            text = (f"{ident} differs in {path} from the requirements accepted before this delivery but is not "
                    "listed in `requirements`: list it if this change writes it, so check reads it, or " + _remedy(
                        "remove it" if change == "added" else "restore it", committed))
        report.add("error", text)
    try:
        current = read_regular(project.root / path).decode("utf-8") if (project.root / path).is_file() else ""
    except (OSError, UnicodeError, AtipSpecError):
        return
    listed = listed_elsewhere(project, slug, spec.capability) | {req.id for req in spec.requirements}
    now = outside(current, listed)
    found = point(project, slug, spec.meta.get("base"), policy)
    merged, forked = ([outside(project.git.blob_text(rev, "./" + path) or "", listed)
                       for rev in (found.commit, found.fork)] if found else (None, None))
    if merged != forked:
        differs = f"the merge base with {found.ref}, which changed it" if now != merged else ""
    else:
        differs = "" if now in (outside(reference, listed), merged) else "the living spec accepted before this delivery"
    if differs:
        report.add("warning", f"the text of {path} that no approval hashes, outside its requirements (before the "
                              "first one or under a heading that ends one, and the frontmatter) or in an HTML comment "
                              f"or fenced code of a requirement not listed, differs from {differs}: no approval of the "
                              "proposal covers it, only the acceptance of the result, which binds the whole tree: "
                              "point it out to the human, or restore it")


def _check_other_specs(report: Report, project: Project, slug: str, spec, risk: str, base: str,
                       changed: set[str], policy=None) -> None:
    """Requirements the delivery adds, changes or removes in the living specs
    of other capabilities, among the `changed` paths: it does not deliver
    them, so they are an error, as merge-check blocks them."""
    from .specs import canonical_path, other_changes, unlisted_changes
    path = project.rel(canonical_path(project, spec))
    fix = spec.kind == "fix"
    strict = fix or risk == "low"
    for name, before in other_changes(project, slug, spec, base, changed, policy):
        for ident, (change, committed) in unlisted_changes(project, slug, spec, before, name).items():
            undo = "remove it" if change == "added" else "restore it"
            if strict:
                text = (f"{ident} is {change} in {name}, the living spec of another capability: "
                        + ("a fix" if fix else "risk low") + f" changes only the requirements of {path} it lists; "
                        + _remedy(undo, committed))
            else:
                text = (f"{ident} is {change} in {name}, the living spec of another capability, which this delivery "
                        f"does not deliver: {undo}, or make that change in a delivery of that capability")
            report.add("error", text, "spec")


def _check_ids(report: Report, what: str, ids: list[str], prefix: str) -> None:
    seen: set[str] = set()
    for ident in ids:
        if ident in seen:
            report.add("error", f"duplicate {what} id {ident}")
        seen.add(ident)
