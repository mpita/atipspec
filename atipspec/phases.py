"""Enter a phase: the CLI decides whether the phase may start, then prints what
the model needs, so the active phase is a fact and not an interpretation.

Each delivery phase (explore, spec, plan, build, review, ship) checks its
prerequisites with the gate. When something required is missing the command
exits 1 with one line naming the missing step; otherwise it prints the phase
header, the project's copy of the workflow, the shared rules and the context.
"""
from __future__ import annotations

from pathlib import Path

from . import frontmatter
from .check import Report, check_delivery
from .context import build_context, render_context
from .errors import AtipSpecError
from .project import Project, resource_root

DELIVERY_PHASES = ("explore", "spec", "fix", "plan", "build", "review", "deliver", "ship")
PROJECT_PHASES = ("contract", "curate")
PHASES = DELIVERY_PHASES + PROJECT_PHASES
STOP_POINTS = {"spec": "the user approves the spec (stop point 1)",
               "deliver": "the user merges the branch (stop point 2)"}


class PhaseRefused(AtipSpecError):
    """The phase cannot start yet; the message names what is missing."""


def framework_text(project: Project, relative: str) -> str:
    """A framework file from the project's copy, or from the package when the
    project has not installed it."""
    path = project.framework / relative
    if not path.is_file():
        path = resource_root() / "framework" / relative
    return path.read_text(encoding="utf-8").rstrip() + "\n"


def workflow_text(project: Project, phase: str) -> str:
    return framework_text(project, f"workflows/{phase}.md")


def rules_text(project: Project) -> str:
    return framework_text(project, "rules.md")


def contract_accepted(project: Project) -> bool:
    if not project.contract.is_file():
        return False
    try:
        meta, _ = frontmatter.split(project.contract.read_text(encoding="utf-8"))
    except ValueError:
        return False
    return meta.get("status") == "accepted"


def _refuse(text: str) -> PhaseRefused:
    return PhaseRefused(text)


def _first(items) -> str:
    return items[0].text


def prerequisites(project: Project, phase: str, slug: str, report: Report) -> None:
    """Raise PhaseRefused when `phase` may not start for this delivery."""
    if phase == "explore":
        return
    if phase in ("spec", "fix"):
        from .delivery import parse_spec
        kind = parse_spec((project.delivery_dir(slug) / "spec.md").read_text(encoding="utf-8")).kind
        if phase == "fix" and kind != "fix":
            raise _refuse(f"{slug} is not a fix delivery: create one with `atipspec new <slug> --title ... --kind fix`, "
                          "or use `atipspec spec` for this one")
        if phase == "spec" and kind == "fix":
            raise _refuse(f"{slug} is a fix delivery: use `atipspec fix {slug}`; a fix has no interview")
        if not contract_accepted(project):
            raise _refuse("the architecture contract is not accepted yet: run the contract phase "
                          "(`atipspec contract`) and ask the user to run `atipspec accept contract`; "
                          "never set its status yourself")
        return
    if phase == "plan":
        blocked = report.blocking(("spec",))
        if report.status == "draft" or blocked:
            raise _refuse("the spec is not ready: " + (_first(blocked) if blocked else report.next_action))
        return
    if phase == "build":
        if report.status in ("draft", "ready"):
            raise _refuse("there is no plan to build from: " + report.next_action)
        # Contract definition problems block; file violations are what build fixes.
        blocked = report.blocking(("spec", "plan", "base", "contract"))
        if blocked:
            raise _refuse("the plan is not valid: " + _first(blocked))
        return
    if phase == "review":
        if report.status in ("draft", "ready"):
            raise _refuse("nothing to review yet: " + report.next_action)
        blocked = report.blocking(("spec", "plan", "base", "contract", "violation", "tasks", "evidence", "deferred"))
        if blocked:
            raise _refuse("the delivery is not ready for review: " + _first(blocked))
        if report.tasks_total and report.tasks_done < report.tasks_total:
            raise _refuse("the delivery is not ready for review: " + report.next_action)
        return
    raise AtipSpecError(f"Unknown phase {phase}")


def header(phase: str, report: Report | None, slug: str | None) -> str:
    title = report.title or slug if report else None
    line = f"Phase {phase}" + (f": {title} ({slug})" if slug else "")
    if report is not None:
        line += f"\nstatus: {report.status}"
        if report.tasks_total:
            line += f"  tasks {report.tasks_done}/{report.tasks_total}"
    return line


def enter(project: Project, phase: str, slug: str, with_context: bool = True) -> str:
    """Text for a delivery phase, or PhaseRefused."""
    if phase not in ("explore", "spec", "fix", "plan", "build"):
        raise AtipSpecError(f"{phase} is not entered with this function")
    if not (project.delivery_dir(slug, must_exist=False) / "spec.md").is_file():
        raise _refuse(f"there is no delivery named {slug}: create it with `atipspec new {slug} --title \"...\"`")
    report = check_delivery(project, slug)
    prerequisites(project, phase, slug, report)
    parts = [header(phase, report, slug), "", workflow_text(project, phase)]
    if phase == "build":
        pending = [item.text for item in report.items if item.source == "tasks" and item.level == "todo"]
        parts += ["Next task: " + (pending[0] if pending else "all tasks are committed; continue with the review"), ""]
    parts += [rules_text(project)]
    if with_context:
        sections, summary = build_context(project, slug)
        parts += ["## Context", "", render_context(sections).rstrip(), "", summary, ""]
    return "\n".join(parts).rstrip() + "\n"


def enter_review(project: Project, slug: str, out: Path | None = None) -> str:
    """Check the review prerequisites, write the packet and print the workflow."""
    from .review import write_packet
    report = check_delivery(project, slug)
    prerequisites(project, "review", slug, report)
    path = write_packet(project, slug, out)
    parts = [header("review", report, slug), f"packet: {project.rel(path)}", "",
             workflow_text(project, "review"), rules_text(project)]
    return "\n".join(parts).rstrip() + "\n"


def enter_project_phase(project: Project, phase: str) -> str:
    """contract and curate: no prerequisites; the workflow plus the current document."""
    parts = [header(phase, None, None), "", workflow_text(project, phase)]
    if phase == "contract":
        text = project.contract.read_text(encoding="utf-8").rstrip() if project.contract.is_file() else "(no contract.md yet)"
        parts += ["## Contract (.atipspec/contract.md)", "", text, ""]
    parts += [rules_text(project)]
    return "\n".join(parts).rstrip() + "\n"


PREVIOUS = {"plan": "spec", "build": "plan", "review": "build"}


def next_phase(project: Project, slug: str) -> tuple[str, str]:
    """The phase ship mode should enter next, with the reason. The named phase
    always passes its own prerequisites: when it would refuse, the phase that
    fixes the problem is named instead."""
    report = check_delivery(project, slug)
    if report.status == "draft":
        from .delivery import parse_spec
        kind = parse_spec((project.delivery_dir(slug) / "spec.md").read_text(encoding="utf-8")).kind
        return ("fix" if kind == "fix" else "spec"), report.next_action
    if report.status == "ready":
        phase = "plan"
    elif report.status in ("planned", "in_progress"):
        phase = "build"
    elif report.status == "implemented":
        phase = "review"
    else:
        return "deliver", report.next_action
    while True:
        try:
            prerequisites(project, phase, slug, report)
        except PhaseRefused as refusal:
            phase = PREVIOUS[phase]
            if phase == "spec":
                return phase, str(refusal)
            continue
        return phase, report.next_action


def ship(project: Project, slug: str) -> str:
    phase, reason = next_phase(project, slug)
    lines = [f"Ship {slug}: next phase is {phase}", f"  because: {reason}"]
    if phase in ("spec", "fix"):
        lines.append(f"  stop point 1 follows: {STOP_POINTS['spec']}")
    if phase == "deliver":
        lines.append(f"  requires the external trust policy; then {STOP_POINTS['deliver']}")
    command = f"atipspec {phase} {slug}" + (" --policy <external policy>" if phase == "deliver" else "")
    lines.append(f"Run: {command}")
    return "\n".join(lines) + "\n"
