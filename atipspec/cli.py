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
    new.add_argument("--kind", choices=("feature", "fix"), default="feature",
                     help="fix: a defect repair with a regression criterion and a one-task plan, no interview")

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

    for phase, text in (("explore", "enter the explore phase: brief an idea that is not clear yet"),
                        ("spec", "enter the spec phase: requirements and acceptance criteria"),
                        ("fix", "enter the fix phase: a regression criterion and a one-task plan for a defect"),
                        ("plan", "enter the plan phase: tasks the gate can prove"),
                        ("build", "enter the build phase: code, evidence and one commit per task")):
        entry = commands.add_parser(phase, help=f"{text} (refuses while a required step is missing)")
        entry.add_argument("slug")
        entry.add_argument("--no-context", action="store_true", help="print the workflow without the context material")

    accept = commands.add_parser("accept", help="a person accepts the spec or the plan of a delivery, or the contract")
    accept.add_argument("slug", help="delivery slug, or `contract`")
    accept.add_argument("phase", nargs="?", choices=("spec", "plan"), help="spec or plan (omit for the contract)")
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

    ids = commands.add_parser("ids", help="show next available IDs for a capability")
    ids.add_argument("capability")
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
        from .traceability import next_ids
        req, ac = next_ids(project, args.capability)
        print(f"{args.capability}/REQ-{req:03d} {args.capability}/AC-{ac:03d}")
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
                                 branch=args.branch, worktree=args.worktree, kind=args.kind)
        print(f"AtipSpec: created {directory} (spec.md, plan.md, deferred.md{', kind fix' if args.kind == 'fix' else ''})")
        if args.worktree:
            print(f"Worktree on branch delivery/{args.slug}: cd {directory.parents[2]}")
        print(f"Next: `atipspec {'fix' if args.kind == 'fix' else 'spec'} {args.slug}`")
        return 0
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
        sections, summary = build_context(project, args.slug)
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
        from .accept import accept_contract, accept_plan, accept_spec
        if args.slug == "contract" and args.phase is None:
            accept_contract(project)
            print("AtipSpec: contract.md accepted (status: accepted)")
            print("Next: commit it; `atipspec spec <slug>` can start now")
            return 0
        if args.phase is None:
            raise AtipSpecError("Say what you accept: `atipspec accept <slug> spec|plan`, or `atipspec accept contract`")
        path = accept_spec(project, args.slug, args.by) if args.phase == "spec" else accept_plan(project, args.slug, args.by)
        print(f"AtipSpec: {args.phase} of {args.slug} accepted for its current content ({project.rel(path)})")
        print("Next: " + (f"`atipspec plan {args.slug}`" if args.phase == "spec" else f"`atipspec build {args.slug}`"))
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
        print("Next: commit, then ask the user to merge the branch")
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
