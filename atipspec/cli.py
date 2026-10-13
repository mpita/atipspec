"""Console entry point: atipspec = atipspec.cli:main."""
from __future__ import annotations

import argparse
import io
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
    new.add_argument("--ticket", help="external ticket: a key like PROJ-123, an issue number like #42, or an https URL")
    new.add_argument("--initiative", help="initiative this delivery belongs to")
    new.add_argument("--branch", action="store_true", help="create and switch to branch delivery/<slug>")
    new.add_argument("--worktree", action="store_true", help="create branch delivery/<slug> in a sibling worktree")
    new.add_argument("--branch-name", help="use the team's branch naming convention with --branch or --worktree")
    new.add_argument("--reuse-branch", action="store_true", help="use an existing named local branch instead of creating it")
    new.add_argument("--depends-on", action="append", help="delivery whose acceptance is required before integration (repeatable)")
    new.add_argument("--kind", choices=("feature", "fix"), default="feature",
                     help="fix: a defect repair that corrects an accepted requirement, with a regression "
                          "criterion and a one-task plan, no interview")
    binding = commands.add_parser("spec-bind", help="bind an authored specification to a guided delivery without "
                                                    "approving it; imports a list of acceptance criteria")
    binding.add_argument("slug")
    binding.add_argument("--file", required=True, help="Markdown requirements and scenarios with stable IDs, or an "
                                                       "acceptance-criteria document to import")
    migrate = commands.add_parser("migrate", help="show how a legacy delivery becomes a guided one; --apply writes it, "
                                                  "with backups, and the delivery returns to draft")
    migrate.add_argument("slug")
    migrate.add_argument("--apply", action="store_true", help="write the change shown, backing up the originals")
    proposal = commands.add_parser("proposal", help="present scope, scenarios, approach, tests and spec diff for approval, "
                                                   "with the approval code `accept` needs")
    proposal.add_argument("slug", help="delivery slug, or `contract` for the contract and the decisions it includes")
    execution = commands.add_parser("run", help="execute an approved guided delivery using the configured process adapter "
                                                "(POSIX: Linux, macOS, WSL)")
    execution.add_argument("slug")
    execution.add_argument("--resume", action="store_true", help="retry after resolving a reported decision or failure")
    execution.add_argument("--retry-interrupted", action="store_true", help="explicitly retry after inspecting an interrupted agent mutation")
    execution.add_argument("--budget", type=int, default=900, help="total elapsed seconds for this approved version")
    execution.add_argument("--timeout", type=int, default=300, help="seconds per adapter call or verification command")
    execution.add_argument("--max-rounds", type=int, default=None,
                           help="maximum automatic correction rounds (default and upper limit: review_rounds in "
                                "config.yaml less one, as each correction is reviewed again)")
    commands.add_parser("adapter", help="show actual capabilities of the configured execution adapter")
    team = commands.add_parser("team", help="show owners, changes, tickets, dependencies and requirements across "
                                            "configured Git refs")
    team.add_argument("--json", action="store_true", help="machine-readable output, with each ticket's link")
    team.add_argument("--fetch", action="store_true", help="fetch the remotes the configured refs name first; the only "
                                                           "command that uses the network")
    pin = commands.add_parser("contract-pin", help="pin a shared contract to an immutable commit from a local repository")
    pin.add_argument("slug", help="guided delivery that depends on the contract")
    pin.add_argument("name", help="name of the pin in contracts.json, e.g. system-contract")
    pin.add_argument("--repository", required=True, help="repository alias in teams.json, or `system` for the "
                                                          "checkout config.yaml names")
    pin.add_argument("--ref", required=True, help="commit, tag or branch to resolve once")
    pin.add_argument("--path", required=True, help="contract file at that revision")

    decision = commands.add_parser("decision", help="create a decision record in .atipspec/decisions/")
    decision.add_argument("slug")
    decision.add_argument("--title", required=True)
    decision.add_argument("--affects", action="append", help="capability, `contract`, `contract:<section>` or `*` (repeatable); "
                          "without it the decision affects everything and is accepted with the contract")

    initiative = commands.add_parser("initiative", help="create an initiative roadmap")
    initiative.add_argument("slug")
    initiative.add_argument("--title", required=True)

    status = commands.add_parser("status", help="derived state of the project, or one delivery in detail")
    status.add_argument("slug", nargs="?")
    status.add_argument("--format", choices=("text", "json", "markdown"), default="text",
                        help="json for scripts, markdown for a pull request or a job summary")

    check = commands.add_parser("check", help="run the gate for a delivery (exit 0 green, 1 errors, 2 incomplete)")
    check.add_argument("slug")

    verify = commands.add_parser("verify", help="run the plan's Verify commands and write evidence; a Report is deleted "
                                               "first and must be written again by the commands")
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
                        ("fix", "enter the fix phase: correct an accepted requirement with a regression criterion and a one-task plan"),
                        ("plan", "enter the plan phase: tasks the gate can prove"),
                        ("build", "enter the build phase: implementation, task progress and final verification")):
        entry = commands.add_parser(phase, help=f"{text} (refuses while a required step is missing)")
        entry.add_argument("slug")
        entry.add_argument("--no-context", action="store_true", help="print the workflow without the context material")

    done = commands.add_parser("task-done", help="record implementation progress without requiring a commit")
    done.add_argument("slug")
    done.add_argument("task")
    done.add_argument("--note", required=True, help="what was implemented; this does not replace verification")

    accept = commands.add_parser("accept", help="record a human approval of the content identified by its approval code; "
                                               "clients with AtipSpec permission rules ask the human first")
    accept.add_argument("slug", help="delivery slug, or `contract`")
    accept.add_argument("phase", nargs="?", choices=("spec", "plan", "proposal", "result"),
                        help="proposal approves spec and plan together; result accepts the reviewed candidate; "
                             "spec and plan are for legacy deliveries")
    accept.add_argument("--code", help="approval code shown by `proposal`, `report` or `proposal contract`, e.g. K7M2-QX4P; "
                                       "in a terminal the CLI also asks to type it")
    accept.add_argument("--by", help="who accepts, as the user named themselves; defaults to git's user.email")

    review = commands.add_parser("review", help="enter the review phase: write the packet for a reviewer in an isolated "
                                               "session; each changed candidate counts a review, passed or not, and "
                                               "once review_rounds reviews are counted it refuses another")
    review.add_argument("slug")
    review.add_argument("--out", help="packet path (default .atipspec/tmp/<slug>-review-packet.md)")
    commands.add_parser("contract", help="enter the contract phase: define or change the architecture contract")
    ship = commands.add_parser("ship", help="ship mode: name the next phase a delivery can enter")
    ship.add_argument("slug")

    deliver = commands.add_parser("deliver", help="archive an accepted delivery: merge its requirements into the living "
                                                 "spec, write the receipt and move it to archive/")
    deliver.add_argument("slug")

    merge = commands.add_parser("merge-check", help="gate a branch before merge: every delivery it touches is accepted, "
                                                   "every delivery it archives matches the head's code, and code no "
                                                   "delivery covers is exempt (exit 0 ready, 1 blocked)")
    merge.add_argument("--base", required=True, help="target branch or commit, e.g. origin/main; compared from its merge "
                                                     "base with HEAD; its config.yaml names exempt_paths")
    merge.add_argument("--format", choices=("text", "markdown"), default="text", help="markdown for a CI job summary")

    for command in (check, verify, deliver, merge):
        command.add_argument("--policy", help="external, organization-controlled trust policy TOML")
        command.add_argument("--policy-sha256", help="protected expected policy digest")
        command.add_argument("--number", type=int, help="pull request number, for a policy in provider mode (or ATIPSPEC_PR_NUMBER)")
    check.add_argument("--json", action="store_true", help="machine-readable gate result")

    approval = commands.add_parser("approve", help="sign a human approval from an enrolled identity")
    approval.add_argument("slug")
    approval.add_argument("phase", help="spec, plan, acceptance, exception:F1 or decision:DEC-001")
    approval.add_argument("--identity", required=True)
    approval.add_argument("--key", required=True)
    approval.add_argument("--expires", help="future ISO timestamp; required for risk exceptions")
    approval.add_argument("--owner", help="spec only, and required there: the delivery owner you confirm, as spec.md "
                                          "declares it; the owner cannot approve later phases")

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

    report = commands.add_parser("report", help="export acceptance dossier: traceability matrix, review, changed files "
                                               "and the diff from the base commit")
    report.add_argument("slug")
    report.add_argument("--format", choices=("json", "markdown", "html"), default="markdown")
    report.add_argument("--out")
    for command in (approval, sync, attest, report):
        command.add_argument("--policy")
        command.add_argument("--policy-sha256")
    report.add_argument("--number", type=int, help="pull request number, for a policy in provider mode")

    ids = commands.add_parser("ids", help="generate an unused ID prefix for a delivery's requirements and criteria")
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
        if metric == "lead_hours":
            observation.add_argument("--lead-hours", type=float,
                                     help="wall-clock hours from creation to result acceptance; for the atipspec "
                                          "cohort, read from the archived receipt when omitted")
        else:
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
                             getattr(args, "number", None) if args.command in ("check", "verify", "deliver", "report", "merge-check") else None)
    if args.command in ("approve", "attest", "sync-approvals") and policy is None:
        raise AtipSpecError("This operation requires --policy pointing outside the candidate repository")
    if args.command == "approval-subject":
        from .trust import subject
        from .providers import marker
        print(marker(args.slug, args.phase, subject(project, args.slug, args.phase, policy=policy),
                     project.git.head()))
        return 0
    if args.command == "approve":
        from .trust import approve
        print(approve(project, args.slug, args.phase, args.identity, Path(args.key), policy, expires=args.expires,
                      owner=args.owner))
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
            target.write_text(content, encoding="utf-8", newline="\n")
            print(target)
        else:
            print(content, end="")
        return 0
    if args.command == "ids":
        from .traceability import concurrent_ids, known_ids, next_ids
        if args.legacy:
            req, ac = next_ids(project, args.capability)
            print(f"{args.capability}/REQ-{req:03d} {args.capability}/AC-{ac:03d}")
        else:
            req, ac = concurrent_ids(args.capability, known_ids(project, args.capability))
            print(f"{args.capability}/{req} {args.capability}/{ac}")
            print("Number further requirements and criteria of this delivery with the same prefix: -002, -003.")
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
        print(f"AtipSpec: created {directory} ({'guided fix: defect, references, one-task plan and baseline' if args.kind == 'fix' else 'guided references, plan and baseline'})")
        created = Project.find(directory)
        if created.system is not None:
            from .teams import pin_system, system_pin_command
            try:
                for name, path, revision in pin_system(created, args.slug):
                    print(f"Pinned system {path} at {revision[:12]} as {name} (contracts.json)")
            except AtipSpecError as exc:
                print(f"warning: the system repository is not available ({exc}); before approving, run "
                      f"`{system_pin_command(args.slug)}`")
        if args.worktree:
            print(f"Worktree on branch {args.branch_name or 'delivery/' + args.slug}: cd {directory.parents[2]}")
        if not created.git.available:
            print("warning: not a git repository, so spec.md has no base commit and the proposal cannot be approved; "
                  "run `git init` and commit, then create the delivery again")
        print(f"Next: `atipspec {'fix' if args.kind == 'fix' else 'spec'} {args.slug}`")
        return 0
    if args.command == "spec-bind":
        from .migration import FORMATS
        from .specs import bind_spec
        bound = bind_spec(project, args.slug, Path(args.file))
        print(bound.target)
        if bound.source:
            print(f"Imported from {FORMATS[bound.form]}; original kept in {bound.source}")
            for note in bound.notes:
                print(f"note: {note}")
            print(f"Next: check the generated requirements, then present `atipspec proposal {args.slug}` with these "
                  "notes; they are listed under ## Import review notes in spec.md")
        return 0
    if args.command == "migrate":
        from .migration import apply_preview, prepare_migration, render_preview
        preview = prepare_migration(project, args.slug)
        if not args.apply:
            print(render_preview(project, preview), end="")
            print(f"Nothing written. Apply with `atipspec migrate {args.slug} --apply`; the delivery returns to "
                  "draft and needs proposal approval.")
            return 0
        archive = apply_preview(project, preview, preview["digest"])
        print(f"AtipSpec: migrated {args.slug} to a guided delivery; originals backed up in {project.rel(archive)}")
        print(f"Next: `atipspec proposal {args.slug}`")
        return 0
    if args.command == "proposal":
        from .proposal import render_contract_proposal, render_proposal
        print(render_contract_proposal(project) if args.slug == "contract" else render_proposal(project, args.slug), end="")
        return 0
    if args.command == "adapter":
        from .adapter import CommandAdapter
        import json
        print(json.dumps(CommandAdapter.load(project).capabilities(), indent=2))
        return 0
    if args.command == "team":
        from .teams import board
        import json
        data = board(project, fetch=args.fetch)
        for warning in data["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(data["visibility"])
            for change in data["changes"]:
                ticket = f" {change['ticket']}" + (f" ({change['ticket_url']})" if change["ticket_url"]
                                                   and change["ticket_url"] != change["ticket"] else "")
                print(f"{change['slug']} [{change['status']}] @{change['owner'] or 'unassigned'}"
                      f"{ticket if change['ticket'] else ''} "
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
        if not args.affects or any(str(item).split(":")[0] in ("contract", "*") for item in args.affects):
            print("Next: fill in context, decision, alternatives and consequences. It is accepted with the contract: "
                  "present `atipspec proposal contract`; never edit its status by hand")
        else:
            print("Next: fill in context, decision, alternatives and consequences; after the human explicitly approves "
                  "it in the conversation, set status: accepted (no code or record backs it; the next "
                  "`atipspec proposal` lists it)")
        return 0
    if args.command == "initiative":
        from .creators import new_initiative
        path = new_initiative(project, args.slug, args.title)
        print(f"AtipSpec: created {project.rel(path)}")
        print("Next: list its deliveries under ## Deliveries as `- <slug>: title`, and the interfaces between them")
        return 0
    if args.command == "status":
        from .status import show_status
        show_status(project, args.slug, args.format)
        return 0
    if args.command == "check":
        from .check import check_delivery
        report = check_delivery(project, args.slug, policy=policy)
        if args.json:
            import json
            from dataclasses import asdict
            print(json.dumps(asdict(report), indent=2, default=sorted))   # `proven` is a set
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
            Path(args.out).write_text(render_context(sections), encoding="utf-8", newline="\n")
            print(summary)
            print(f"written to {args.out}")
        elif args.summary:
            print(summary)
        else:
            print(render_context(sections))
            print(summary)
        return 0
    if args.command == "accept":
        from .accept import (accept_contract, accept_plan, accept_spec, accept_proposal, accept_result, channel_text,
                             read_contract_record, read_record)
        if args.slug == "contract" and args.phase is None:
            from .accept import approvals_reset_by_contract, is_current
            reset = approvals_reset_by_contract(project)
            accept_contract(project, args.by, args.code)
            record = read_contract_record(project)
            decisions = ", ".join(record["decisions"]) or "none"
            print(f"AtipSpec: contract and its decisions ({decisions}) accepted with code {record['code']}"
                  f"{channel_text(record)} ({project.rel(project.contract)} status: accepted)")
            print_channel_note(project, record)
            reset = [f"{slug} {phase}" for slug, phase in reset if not is_current(project, slug, phase)]
            if reset:
                print(f"warning: these approvals hashed the previous status lines and are now outdated: {', '.join(reset)}; "
                      "`atipspec check <slug>` names what to present again")
            print("Next: continue with the requested delivery; `atipspec spec <slug>` can start now")
            return 0
        if args.phase is None:
            raise AtipSpecError("Say what you accept: `atipspec accept <slug> proposal|result --code <code>` "
                                "(legacy deliveries: spec|plan), or `atipspec accept contract --code <code>`")
        action = {"spec": accept_spec, "plan": accept_plan, "proposal": accept_proposal, "result": accept_result}
        path = action[args.phase](project, args.slug, args.by, args.code)
        record = read_record(project, args.slug, args.phase)
        print(f"AtipSpec: {args.phase} of {args.slug} accepted for its current content with code {record['code']}"
              f"{channel_text(record)} ({project.rel(path)})")
        print_channel_note(project, record)
        next_command = "plan" if args.phase == "spec" else "deliver" if args.phase == "result" else "build"
        print(f"Next: `atipspec {next_command} {args.slug}`")
        return 0
    if args.command == "task-done":
        from .progress import mark_done
        path = mark_done(project, args.slug, args.task, args.note)
        print(f"AtipSpec: {args.task} of {args.slug} recorded as implemented (progress, not verification) in "
              f"{project.rel(path)}")
        from .check import check_delivery
        print(f"Next: {check_delivery(project, args.slug).next_action}")
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
        print("Before merging, `atipspec merge-check --base <target branch>` confirms the branch still matches this "
              "acceptance; any later change outside .atipspec/ requires reopening the delivery: revert the "
              "archive commit, then verify, review and accept again.")
        return 0
    if args.command == "merge-check":
        from .merge import merge_check, render_markdown
        report = merge_check(project, args.base, policy=policy)
        print(render_markdown(report) if args.format == "markdown" else report.render(next_action=False) + "\n", end="")
        return 1 if report.errors else 0
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


def print_channel_note(project, record: dict) -> None:
    from .install import CLIENTS, installed_clients, permission_overrides, permission_rules_state
    if record.get("channel") == "client-permission":
        print(f"note: channel client-permission: Claude Code's rules are in this project, and Claude Code applies "
              f"them only in a session opened in {project.root}, where .claude/settings.json is; the record cannot "
              "show who approved, and an external trust policy authenticates approvals")
    if record.get("channel") != "assistant":
        return
    installed = installed_clients(project.root)
    overrides = permission_overrides(project.root, "claude")
    if permission_rules_state(project.root, "claude") == "installed" and overrides:
        advice = f"{'; '.join(overrides)}, so Claude Code may not ask"
    elif permission_rules_state(project.root, "claude") == "installed":
        advice = ("Claude Code's rules ask only when a Claude Code session that shows you its prompts runs "
                  "`atipspec accept` itself, not another agent, the Agent SDK, `claude -p` or `python -m atipspec.cli`")
    elif "claude" in installed:
        advice = "`atipspec install --update` configures Claude Code to ask"
    else:
        clients = ", ".join(CLIENTS[key].label for key in installed)
        advice = ((f"{clients}: AtipSpec installs no permission rules for them" if clients
                   else "no client is installed here") + "; `atipspec install --client claude` adds Claude Code's")
    print("warning: channel assistant: no client permission rule asked the human before this command, so the "
          f"record shows only that the assistant ran it. {advice}; an external trust policy authenticates approvals")


def _utf8_output() -> None:
    """Write UTF-8 to a pipe or a file, whatever the locale: assistants read the
    output as UTF-8, and a Windows code page cannot encode every character of
    a spec. A console keeps its own encoding."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper) and not stream.isatty():
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_output()
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
