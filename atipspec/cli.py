"""Console entry point: atipspec = atipspec.cli:main."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .errors import AtipSpecError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atipspec", description="Spec-driven delivery with a deterministic gate.")
    parser.add_argument("--version", action="version", version=f"AtipSpec v{__version__}")
    commands = parser.add_subparsers(dest="command", metavar="<command>")

    init = commands.add_parser("init", help="initialize .atipspec/ here, or manage it when it already exists")
    init.add_argument("--client", action="append", help="client skill to install (repeatable); asks when omitted")
    init.add_argument("--name", help="project name; skips the prompt")
    init.add_argument("--language", help="output language; skips the prompt")

    install = commands.add_parser("install", help="install the framework and client skills in an initialized project")
    install.add_argument("--client", action="append", help="client id (repeatable); asks when omitted")
    install.add_argument("--update", action="store_true",
                         help="replace framework and skill files that differ from this version")

    new = commands.add_parser("new", help="create a delivery")
    new.add_argument("slug", help="lowercase identifier, e.g. password-reset")
    new.add_argument("--title", required=True, help="human title")
    new.add_argument("--capability", help="living spec that receives the requirements (defaults to the slug)")
    new.add_argument("--impact", action="append", help="other living specs or contract sections it touches (repeatable)")
    new.add_argument("--owner", help="who owns this delivery")
    new.add_argument("--ticket", help="external ticket id, e.g. PROJ-123")
    new.add_argument("--initiative", help="initiative this delivery belongs to")
    new.add_argument("--branch", action="store_true", help="create and switch to branch delivery/<slug>")
    new.add_argument("--worktree", action="store_true", help="create branch delivery/<slug> in a sibling worktree")
    new.add_argument("--branch-name", help="use the team's branch naming convention with --branch or --worktree")
    new.add_argument("--reuse-branch", action="store_true", help="use an existing named local branch instead of creating it")
    new.add_argument("--depends-on", action="append", help="delivery whose acceptance is required before integration (repeatable)")
    new.add_argument("--kind", choices=("feature", "fix"), default="feature",
                     help="fix: a defect repair with a regression criterion and a one-task plan, no interview")
    binding = commands.add_parser("spec-bind", help="bind an authored specification to a guided delivery without approving it")
    binding.add_argument("slug")
    binding.add_argument("--file", required=True, help="Markdown requirements and scenarios with stable IDs")
    proposal = commands.add_parser("proposal", help="present scope, scenarios, approach, tests and spec diff for approval")
    proposal.add_argument("slug")
    execution = commands.add_parser("run", help="execute an approved guided delivery using the configured process adapter")
    execution.add_argument("slug")
    execution.add_argument("--resume", action="store_true", help="retry after resolving a reported decision or failure")
    execution.add_argument("--retry-interrupted", action="store_true", help="explicitly retry after inspecting an interrupted agent mutation")
    execution.add_argument("--budget", type=int, default=900, help="total elapsed seconds for this approved version")
    execution.add_argument("--timeout", type=int, default=300, help="seconds per adapter call or verification command")
    execution.add_argument("--max-rounds", type=int, default=2, help="maximum automatic correction rounds")
    commands.add_parser("adapter", help="show actual capabilities of the configured execution adapter")
    team = commands.add_parser("team", help="show owners, changes, dependencies and requirements across configured Git refs")
    team.add_argument("--json", action="store_true")
    pin = commands.add_parser("contract-pin", help="pin a shared contract to an immutable commit from a local repository")
    pin.add_argument("slug")
    pin.add_argument("name")
    pin.add_argument("--repository", required=True, help="repository alias in teams.json")
    pin.add_argument("--ref", required=True, help="commit, tag or branch to resolve once")
    pin.add_argument("--path", required=True, help="contract file at that revision")

    decision = commands.add_parser("decision", help="create a decision record in .atipspec/decisions/")
    decision.add_argument("slug")
    decision.add_argument("--title", required=True)
    decision.add_argument("--affects", action="append", help="capability, `contract` or `contract:<section>` (repeatable)")

    initiative = commands.add_parser("initiative", help="create an initiative roadmap")
    initiative.add_argument("slug")
    initiative.add_argument("--title", required=True)

    status = commands.add_parser("status", help="derived state of the project, or one delivery in detail")
    status.add_argument("slug", nargs="?")

    check = commands.add_parser("check", help="run the gate for a delivery (exit 0 green, 1 errors, 2 incomplete)")
    check.add_argument("slug")

    verify = commands.add_parser("verify", help="run the plan's Verify commands and write evidence")
    verify.add_argument("slug")
    verify.add_argument("--task", action="append", help="task id, e.g. T1 (repeatable; default all)")
    verify.add_argument("--timeout", type=int, default=1800, help="seconds per command (default 1800)")

    context = commands.add_parser("context", help="print the context a delivery needs, within the budget")
    context.add_argument("slug")
    context.add_argument("--out", help="write the context to this file instead of stdout")
    context.add_argument("--summary", action="store_true", help="print only the size summary")
    context.add_argument("--role", choices=("guide", "analyst", "designer", "tester", "implementer", "reviewer"))
    context.add_argument("--task", help="limit implementation context to this task and its requirements")

    for phase, text in (("explore", "enter the explore phase: brief an idea that is not clear yet"),
                        ("spec", "enter the spec phase: requirements and acceptance criteria"),
                        ("fix", "enter the fix phase: a regression criterion and a one-task plan for a defect"),
                        ("plan", "enter the plan phase: tasks the gate can prove"),
                        ("build", "enter the build phase: implementation, task progress and final verification")):
        entry = commands.add_parser(phase, help=f"{text} (refuses while a required step is missing)")
        entry.add_argument("slug")
        entry.add_argument("--no-context", action="store_true", help="print the workflow without the context material")

    done = commands.add_parser("task-done", help="record implementation progress without requiring a commit")
    done.add_argument("slug")
    done.add_argument("task")
    done.add_argument("--note", required=True, help="what was implemented; this does not replace verification")

    accept = commands.add_parser("accept", help="record explicit human approval; the assistant may run this after confirmation")
    accept.add_argument("slug", help="delivery slug, or `contract`")
    accept.add_argument("phase", nargs="?", choices=("spec", "plan", "proposal", "result"),
                        help="proposal approves spec and plan together; result accepts the reviewed candidate")
    accept.add_argument("--by", help="who accepts; defaults to git's user.email")

    review = commands.add_parser("review", help="enter the review phase: write the packet for a fresh-context reviewer")
    review.add_argument("slug")
    review.add_argument("--out", help="packet path (default .atipspec/tmp/<slug>-review-packet.md)")
    commands.add_parser("contract", help="enter the contract phase: define or change the architecture contract")
    ship = commands.add_parser("ship", help="ship mode: name the next phase a delivery can enter")
    ship.add_argument("slug")

    deliver = commands.add_parser("deliver", help="merge a green delivery into its living spec and archive it")
    deliver.add_argument("slug")

    for command in (check, verify, deliver):
        command.add_argument("--policy", help="external, organization-controlled trust policy TOML")
        command.add_argument("--policy-sha256", help="protected expected policy digest")
        command.add_argument("--number", type=int, help="PR or MR number, for a policy in provider mode (or ATIPSPEC_PR_NUMBER)")
    check.add_argument("--json", action="store_true", help="machine-readable gate result")

    approval = commands.add_parser("approve", help="sign a human approval from an enrolled identity")
    approval.add_argument("slug")
    approval.add_argument("phase", help="spec, plan, acceptance, exception:F1 or decision:DEC-001")
    approval.add_argument("--identity", required=True)
    approval.add_argument("--key", required=True)
    approval.add_argument("--expires", help="future ISO timestamp; required for risk exceptions")

    sync = commands.add_parser("sync-approvals", help="collect existing human PR/MR approvals (read-only API)")
    sync.add_argument("slug")
    sync.add_argument("phase")
    sync.add_argument("--number", type=int, required=True, help="PR or MR number")
    sync.add_argument("--identity", required=True, help="enrolled collector service identity")
    sync.add_argument("--key", required=True)
    sync.add_argument("--expires")

    subject = commands.add_parser("approval-subject", help="show the exact content digest and provider approval marker")
    subject.add_argument("slug")
    subject.add_argument("phase")

    attest = commands.add_parser("attest", help="sign evidence collected by a protected CI producer")
    attest.add_argument("slug")
    attest.add_argument("--identity", required=True)
    attest.add_argument("--key", required=True)
    attest.add_argument("--run-url", required=True)

    report = commands.add_parser("report", help="export acceptance dossier and traceability matrix")
    report.add_argument("slug")
    report.add_argument("--format", choices=("json", "markdown", "html"), default="markdown")
    report.add_argument("--out")
    for command in (approval, sync, attest, report):
        command.add_argument("--policy")
        command.add_argument("--policy-sha256")
    report.add_argument("--number", type=int, help="PR or MR number, for a policy in provider mode")

    ids = commands.add_parser("ids", help="generate independent stable IDs for concurrent work")
    ids.add_argument("capability")
    ids.add_argument("--legacy", action="store_true", help="show local numeric counters for an existing sequential workflow")
    enterprise = commands.add_parser("enterprise-init", help="write trust policy, CI examples and adoption guide")
    enterprise.add_argument("--out", default=".atipspec/enterprise")

    pilot = commands.add_parser("pilot", help="prepare and measure a real-world comparison")
    pilot_commands = pilot.add_subparsers(dest="pilot_command", required=True)
    for name in ("init", "report"):
        pilot_commands.add_parser(name).add_argument("name")
    observation = pilot_commands.add_parser("record")
    observation.add_argument("name")
    observation.add_argument("--delivery", required=True)
    observation.add_argument("--cohort", choices=("baseline", "atipspec"), required=True)
    observation.add_argument("--source", required=True)
    observation.add_argument("--collector", required=True)
    from .pilot import METRICS
    for metric in METRICS:
        observation.add_argument("--" + metric.replace("_", "-"), type=float, required=True)

    commands.add_parser("audit", help="check the whole repository against the contract and the living documents")
    commands.add_parser("curate", help="enter the curate phase: regenerate the overview index and report document sizes")
    return parser


def run(args: argparse.Namespace) -> int:
    from .install import CLIENT_PATHS, init_project, install_clients
    from .project import Project

    if args.command == "init":
        for client in args.client or []:
            if client not in CLIENT_PATHS:
                raise AtipSpecError(f"Unsupported client: {client}. Known: {', '.join(CLIENT_PATHS)}")
        init_project(Path.cwd(), clients=args.client, name=args.name, language=args.language)
        return 0
    project = Project.find()
    from .trust import selected_policy
    policy = selected_policy(project, getattr(args, "policy", None), getattr(args, "policy_sha256", None),
                             getattr(args, "number", None) if args.command in ("check", "verify", "deliver", "report") else None)
    if args.command in ("approve", "attest", "sync-approvals") and policy is None:
        raise AtipSpecError("This operation requires --policy pointing outside the candidate repository")
    if args.command == "approval-subject":
        from .trust import subject
        from .providers import marker
        print(marker(args.slug, args.phase, subject(project, args.slug, args.phase), project.git.head()))
        return 0
    if args.command == "approve":
        from .trust import approve
        print(approve(project, args.slug, args.phase, args.identity, Path(args.key), policy, expires=args.expires))
        return 0
    if args.command == "sync-approvals":
        from .providers import sync_approvals
        for path in sync_approvals(project, args.slug, args.phase, policy, args.number, args.identity, Path(args.key), args.expires):
            print(path)
        return 0
    if args.command == "attest":
        from .assurance import attest
        for path in attest(project, args.slug, policy, args.identity, Path(args.key), args.run_url):
            print(path)
        return 0
    if args.command == "report":
        from .reporting import get_report, render_report
        content = render_report(get_report(project, args.slug, policy), args.format)
        if args.out:
            target = Path(args.out).resolve()
            safe = project.tmp.resolve()
            reports_dir = (project.deliveries / args.slug / "reports").resolve()
            if target.is_relative_to(project.root) and not any(target.is_relative_to(folder) for folder in (safe, reports_dir)):
                raise AtipSpecError("Write reports outside the repository or under .atipspec/tmp or this delivery's reports directory, so exports do not invalidate acceptance")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            print(target)
        else:
            print(content, end="")
        return 0
    if args.command == "ids":
        from .traceability import next_ids, concurrent_ids
        if args.legacy:
            req, ac = next_ids(project, args.capability)
            print(f"{args.capability}/REQ-{req:03d} {args.capability}/AC-{ac:03d}")
        else:
            req, ac = concurrent_ids(args.capability)
            print(f"{args.capability}/{req} {args.capability}/{ac}")
        return 0
    if args.command == "enterprise-init":
        from .enterprise import scaffold
        for path in scaffold(Path(args.out)):
            print(path)
        return 0
    if args.command == "pilot":
        from . import pilot
        import json
        if args.pilot_command == "init":
            print(pilot.initialize(project, args.name))
        elif args.pilot_command == "report":
            print(json.dumps(pilot.pilot_report(project, args.name), indent=2))
        else:
            print(pilot.record(project, args.name, args.delivery, args.cohort,
                               {key: getattr(args, key) for key in pilot.METRICS}, args.source, args.collector))
        return 0
    if args.command == "install":
        for client in args.client or []:
            if client not in CLIENT_PATHS:
                raise AtipSpecError(f"Unsupported client: {client}. Known: {', '.join(CLIENT_PATHS)}")
        install_clients(project.root, args.client, update=args.update)
        return 0
    if args.command == "new":
        from .creators import new_delivery
        directory = new_delivery(project, args.slug, args.title, capability=args.capability, impact=args.impact,
                                 owner=args.owner, ticket=args.ticket, initiative=args.initiative,
                                 branch=args.branch, worktree=args.worktree, kind=args.kind,
                                 branch_name=args.branch_name, reuse_branch=args.reuse_branch, depends_on=args.depends_on)
        print(f"AtipSpec: created {directory} ({'spec.md, plan.md, deferred.md, kind fix' if args.kind == 'fix' else 'guided references, plan and baseline'})")
        if args.worktree:
            print(f"Worktree on branch {args.branch_name or 'delivery/' + args.slug}: cd {directory.parents[2]}")
        print(f"Next: `atipspec {'fix' if args.kind == 'fix' else 'spec'} {args.slug}`")
        return 0
    if args.command == "spec-bind":
        from .specs import bind_spec
        print(bind_spec(project, args.slug, Path(args.file)))
        return 0
    if args.command == "proposal":
        from .proposal import render_proposal
        print(render_proposal(project, args.slug), end="")
        return 0
    if args.command == "adapter":
        from .adapter import CommandAdapter
        import json
        print(json.dumps(CommandAdapter.load(project).capabilities(), indent=2))
        return 0
    if args.command == "team":
        from .teams import board
        import json
        data = board(project)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(data["visibility"])
            for change in data["changes"]:
                print(f"{change['slug']} [{change['status']}] @{change['owner'] or 'unassigned'} "
                      f"{change['ref']} {change['capability']}: {', '.join(change['requirements'])}; "
                      f"dependencies: {', '.join(change['depends_on']) or 'none'}")
        return 0
    if args.command == "contract-pin":
        from .teams import pin_contract
        print(pin_contract(project, args.slug, args.name, args.repository, args.ref, args.path))
        return 0
    if args.command == "run":
        from .runner import run_delivery
        import json
        state = run_delivery(project, args.slug, resume=args.resume, retry_interrupted=args.retry_interrupted,
                             budget=args.budget, timeout=args.timeout, max_rounds=args.max_rounds)
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0 if state["status"] in ("ready_for_acceptance", "accepted") else 2
    if args.command == "decision":
        from .creators import new_decision
        path = new_decision(project, args.slug, args.title, args.affects)
        print(f"AtipSpec: created {project.rel(path)} (status: proposed)")
        print("Next: fill in context, decision, alternatives and consequences; set status: accepted when approved")
        return 0
    if args.command == "initiative":
        from .creators import new_initiative
        path = new_initiative(project, args.slug, args.title)
        print(f"AtipSpec: created {project.rel(path)}")
        print("Next: list its deliveries under ## Deliveries as `- <slug>: title`, and the interfaces between them")
        return 0
    if args.command == "status":
        from .status import show_status
        show_status(project, args.slug)
        return 0
    if args.command == "check":
        from .check import check_delivery
        report = check_delivery(project, args.slug, policy=policy)
        if args.json:
            import json
            from dataclasses import asdict
            print(json.dumps(asdict(report), indent=2))
        else:
            print(report.render())
        return report.exit_code
    if args.command == "verify":
        from .verify import verify_delivery
        if policy:
            from .assurance import require_preflight
            require_preflight(project, args.slug, policy)
        return verify_delivery(project, args.slug, args.task, args.timeout)
    if args.command == "context":
        from .context import build_context, render_context
        sections, summary = build_context(project, args.slug, role=args.role, task_id=args.task)
        if args.out:
            Path(args.out).write_text(render_context(sections), encoding="utf-8")
            print(summary)
            print(f"written to {args.out}")
        elif args.summary:
            print(summary)
        else:
            print(render_context(sections))
            print(summary)
        return 0
    if args.command == "accept":
        from .accept import accept_contract, accept_plan, accept_spec, accept_proposal, accept_result
        if args.slug == "contract" and args.phase is None:
            accept_contract(project)
            print("AtipSpec: contract.md accepted (status: accepted)")
            print("Next: continue with the requested delivery; `atipspec spec <slug>` can start now")
            return 0
        if args.phase is None:
            raise AtipSpecError("Say what you accept: `atipspec accept <slug> spec|plan`, or `atipspec accept contract`")
        action = {"spec": accept_spec, "plan": accept_plan, "proposal": accept_proposal, "result": accept_result}
        path = action[args.phase](project, args.slug, args.by)
        print(f"AtipSpec: {args.phase} of {args.slug} accepted for its current content ({project.rel(path)})")
        next_command = "plan" if args.phase == "spec" else "deliver" if args.phase == "result" else "build"
        print(f"Next: `atipspec {next_command} {args.slug}`")
        return 0
    if args.command == "task-done":
        from .progress import mark_done
        print(mark_done(project, args.slug, args.task, args.note))
        return 0
    if args.command in ("explore", "spec", "fix", "plan", "build"):
        from .phases import enter
        print(enter(project, args.command, args.slug, with_context=not args.no_context), end="")
        return 0
    if args.command == "review":
        from .phases import enter_review
        print(enter_review(project, args.slug, Path(args.out) if args.out else None), end="")
        return 0
    if args.command == "contract":
        from .phases import enter_project_phase
        print(enter_project_phase(project, "contract"), end="")
        return 0
    if args.command == "ship":
        from .phases import ship
        print(ship(project, args.slug), end="")
        return 0
    if args.command == "deliver":
        from .deliver import deliver
        living, target = deliver(project, args.slug, policy=policy)
        print(f"AtipSpec: merged into {project.rel(living)} and moved to {project.rel(target)}/")
        print("Result archived. Commit, merge and deployment follow the repository's explicit policy.")
        return 0
    if args.command == "audit":
        from .audit import audit_project
        report = audit_project(project)
        print(report.render(next_action=False))
        return 1 if report.errors else 0
    if args.command == "curate":
        from .curate import curate_project
        from .phases import enter_project_phase
        report = curate_project(project)
        print(report.render(next_action=False))
        print()
        print(enter_project_phase(project, "curate"), end="")
        return 0
    raise AtipSpecError(f"Unknown command {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return run(args)
    except (EOFError, KeyboardInterrupt):
        print("\nAtipSpec: operation cancelled.", file=sys.stderr)
        return 130
    except (AtipSpecError, OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"AtipSpec: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
