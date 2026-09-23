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

from .contract import Contract, evaluate, matches, missing_commands, parse_contract
from .delivery import Plan, load_evidence, parse_deferred, parse_plan, parse_review, parse_spec, verification_task
from .project import Project
from .errors import AtipSpecError
from . import frontmatter
from .assurance import evidence_problems, check_assurance
from .trust import approvals_for, selected_policy

_UNSET = object()
STATUSES = ("draft", "ready", "planned", "in_progress", "implemented", "checked", "verified")


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

    def add(self, level: str, text: str, source: str | None = None) -> None:
        """Record an item; `source` names the part of the delivery it comes from
        (spec, plan, contract, violation, base, tasks, evidence, deferred, review, trust)."""
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
            return f"Review `atipspec report {self.slug}`; the user accepts the result with `atipspec accept {self.slug} result`"
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


def changed_files(project: Project, base: str | None) -> tuple[list[str], str | None]:
    """Files touched by the delivery: diff against its base (or HEAD when the base
    is unknown) plus untracked files, existing ones only."""
    git = project.git
    if base and git.rev_exists(base):
        label = base
    else:
        label = None
    names = set(git.changed(label)) | set(git.untracked(include_atipspec=True))
    return sorted(name for name in names if (project.root / name).exists()), label


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


def outside_scope(plan: Plan, files: list[str]) -> list[str]:
    """Touched files that match none of the plan's scope globs. Files under
    .atipspec/ are the delivery's own and never count."""
    if not plan.scope:
        return []
    return [name for name in files
            if not name.startswith(".atipspec/") and not any(matches(glob, name) for glob in plan.scope)]


def check_delivery(project: Project, slug: str, fingerprint=_UNSET, policy=None, *, preapproval=False) -> Report:
    directory = project.delivery_dir(slug)
    report = Report(slug)
    policy = policy or selected_policy(project)
    report.source = "spec"
    spec = load_spec(project, slug)
    report.title = spec.title
    if spec.meta.get("risk", "normal") not in ("low", "normal", "high"):
        report.add("error", "risk must be low, normal or high")
    for problem in spec.problems:
        report.add("error", problem)
    if spec.status not in ("draft", "ready"):
        report.add("error", f"spec.md status must be draft or ready, found {spec.status!r}")
    if not spec.title:
        report.add("error", "spec.md needs a title line: # Title")
    # While the spec is a draft, missing content is pending work, not a defect.
    incomplete = "todo" if spec.status == "draft" else "error"
    if not spec.requirements:
        report.add(incomplete, "spec.md has no requirements; use headings like `### REQ-001: Behavior`")
    _check_ids(report, "requirement", [req.id for req in spec.requirements], "REQ")
    _check_ids(report, "criterion", [ac.id for ac in spec.criteria], "AC")
    for req in spec.requirements:
        if not req.criteria and not req.remove:
            report.add(incomplete, f"{req.id} has no acceptance criteria; add lines like `- AC-001: outcome`")
    if spec.open_questions:
        count = len(spec.open_questions)
        if spec.status == "ready":
            report.add("error", f"{count} open question(s) remain; resolve them in spec.md or set status: draft")
        else:
            report.add("info", f"{count} open question(s) recorded")
    if spec.assumptions and spec.status == "draft":
        report.add("info", f"{len(spec.assumptions)} assumption(s) for the user to confirm at acceptance")
    from .lint import lint_criterion
    level = "error" if project.policy("strict_criteria") else "warning"
    for ac in spec.criteria:
        for problem in lint_criterion(ac.id, ac.text, project.language,
                                      "free" if ac.form != "statement" else str(project.policy("criteria_syntax"))):
            report.add(level, problem)
    for name in spec.impact:
        if not (project.specs / f"{name}.md").is_file() and name != spec.capability:
            report.add("warning", f"impact names {name!r}, which is not a living spec in .atipspec/specs/")
    limit = min(int(project.policy("max_requirements")), 2) if spec.kind == "fix" else int(project.policy("max_requirements"))
    if spec.status == "ready" and len(spec.requirements) > limit:
        report.add("warning", f"{len(spec.requirements)} requirements (policy {limit}): a delivery should fit in a "
                              "working day; split it into deliveries under an initiative")
    if spec.status != "ready" and not preapproval:
        report.status = "draft"
        report.add("todo", f"Finish the spec phase; the user accepts it with `atipspec accept {slug} spec`")
        return report
    from .accept import is_current, read_record
    if policy is None and not preapproval and not is_current(project, slug, "spec"):
        report.status = "draft"
        changed = read_record(project, slug, "spec") is not None
        report.add("todo", ("spec.md or the contract changed after the acceptance" if changed
                            else "spec.md is not accepted for its current content")
                   + f"; the user runs `atipspec accept {slug} spec`")
        return report

    report.source = "plan"
    plan_path = directory / "plan.md"
    plan = parse_plan(plan_path.read_text(encoding="utf-8")) if plan_path.is_file() else None
    if plan is None or not plan.tasks:
        report.status = "ready"
        report.add("todo", "Write plan.md: tasks with Covers and Verify lines (framework/workflows/plan.md)")
        return report
    for problem in plan.problems:
        report.add("error", problem)
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
    if policy is None and not preapproval and project.policy("approve_plan") and spec.kind != "fix" and not is_current(project, slug, "plan"):
        changed = read_record(project, slug, "plan") is not None
        report.add("todo", ("plan.md, spec.md or the contract changed after the plan's acceptance" if changed
                            else "plan.md is not accepted for its current content")
                   + f"; the user runs `atipspec accept {slug} plan`", "plan")

    git = project.git
    if git.available:
        current = project.fingerprint() if fingerprint is _UNSET else fingerprint
        base = spec.meta.get("base") if isinstance(spec.meta.get("base"), str) else None
        files, label = changed_files(project, base)
        done = git.task_commits(slug, label)
        if spec.meta.get("schema") == 2:
            done = {}  # guided task completion is bound to the approved task, not a past commit label
        if not base or label is None:
            report.add("error", "the recorded base commit is missing; restore history before checking", "base")
        for violation in evaluate(contract, project.root, files, manifests_always=False):
            report.add("error", f"contract: {violation.render()}", "violation")
        stray = outside_scope(plan, touched_files(project, base))
        if stray:
            report.add("error" if project.policy("strict_scope") else "warning",
                       f"files outside the declared scope: {', '.join(stray)}; widen `scope` in plan.md "
                       "with the task that needs them, or revert them", "violation")
        contract_path = ".atipspec/contract.md"
        existed = git.head() is not None and git.exists_at(label or "HEAD", contract_path)
        changed = set(git.changed(label)) | set(git.untracked(include_atipspec=True))
        if contract_path in changed and existed:
            accepted = []
            for name in sorted(changed):
                if not name.startswith(".atipspec/decisions/DEC-") or not name.endswith(".md"):
                    continue
                if git.exists_at(label or "HEAD", name) or not (project.root / name).is_file():
                    continue
                try:
                    meta, _ = frontmatter.split((project.root / name).read_text())
                    affects = meta.get("affects", [])
                    affects = affects if isinstance(affects, list) else [affects]
                    if meta.get("status") == "accepted" and any(str(x).split(":")[0] == "contract" for x in affects):
                        if policy and not approvals_for(project, slug, "decision:" + str(meta.get("id")), policy, spec.meta.get("owner")):
                            continue
                        accepted.append(name)
                except (ValueError, OSError, AtipSpecError):
                    continue
            if not accepted:
                report.add("error", "contract.md changed without a new decision that is accepted, affects contract, "
                                    "and has required approval", "violation")

    else:
        done = {}
        current = None
        report.add("warning", "git is unavailable or this is not a repository: task completion, "
                              "contract rules and evidence freshness cannot be determined", "base")
    report.fingerprint = current
    report.source = "evidence"
    evidence, problems = load_evidence(directory / "evidence")
    for problem in problems:
        report.add("error", problem)
    from .progress import completed_tasks
    completed = completed_tasks(project, slug, plan)
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
        if record is not None:
            for problem in evidence_problems(record, task, slug):
                report.add("error", f"{task.id}: {problem}")
        if record is None:
            selection = "" if task.id == "FINAL" else f" --task {task.id}"
            report.add("todo", f"{task.id}: no evidence; run `atipspec verify {slug}{selection}`")
        elif record.result != "pass":
            report.add("error", f"{task.id}: last verification failed ({record.path.name}); fix and verify again")
        elif current is not None and record.tree != current:
            report.add("todo", f"{task.id}: evidence is stale (the working tree changed); verify again")
        if record is not None and (current is None or record.tree == current):
            for ident, problem in proof_problems(task, record).items():
                report.add("error", f"{ident}: {problem}")
        if task.report:
            for ident in task.tests:
                if ident not in task.proof:
                    report.add("info", f"{ident} has no named test in {task.id}'s Proof; the reviewer must verify it")

    report.source = "deferred"
    deferred_path = directory / "deferred.md"
    deferred, problems = parse_deferred(deferred_path.read_text(encoding="utf-8")) if deferred_path.is_file() else ({}, [])
    for problem in problems:
        report.add("error", problem)
    for ident in deferred:
        if not ident.startswith("F"):
            report.add("error", f"{ident} cannot be deferred: acceptance criteria are met or the spec changes explicitly")

    report.source = "review"
    review_path = directory / "review.md"
    if not review_path.is_file():
        report.add("todo", f"No review.md: run `atipspec review {slug}` and launch the reviewer in a fresh context")
    else:
        review = parse_review(review_path.read_text(encoding="utf-8"))
        for problem in review.problems:
            report.add("error", problem)
        if review.tree is None:
            report.add("error", "review.md frontmatter needs `tree:` with the fingerprint from the packet")
        elif current is not None and review.tree != current:
            report.add("todo", f"review.md is stale (the working tree changed since the review); run "
                               f"`atipspec review {slug}` and review again")
        known = {ac.id for ac in spec.criteria}
        for ac in spec.criteria:
            verdict = review.verdicts.get(ac.id)
            if verdict is None:
                report.add("error", f"{ac.id} has no verdict in review.md")
            elif not verdict[1].strip():
                report.add("error", f"{ac.id} needs a proof pointer or precise failure reason")
            elif verdict[0] == "FAIL":
                note = f": {verdict[1]}" if verdict[1] else ""
                report.add("error", f"{ac.id} FAIL{note}")
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
            elif finding.severity == "blocker":
                report.add("error", f"{label}; fix it or defer it in deferred.md with a reason")
            elif finding.severity == "major":
                report.add("error", f"{label}; fix it or obtain a trusted risk exception")
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
            read_contracts(project, slug)
            if project.system:
                report.add("error", "Guided changes require immutable contract pins; replace the mutable system path with contract-pin", "coordination")
        except (AtipSpecError, OSError, ValueError, TypeError) as exc:
            report.add("error", str(exc), "coordination")
    report.source = "trust"
    if policy:
        check_assurance(project, slug, policy, report, spec, plan, evidence)
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


def _check_ids(report: Report, what: str, ids: list[str], prefix: str) -> None:
    seen: set[str] = set()
    for ident in ids:
        if ident in seen:
            report.add("error", f"duplicate {what} id {ident}")
        seen.add(ident)
