"""Derived project state: nothing here is stored, everything is computed."""
from __future__ import annotations

from datetime import date, datetime, timezone

from .accept import describe
from .check import check_delivery
from .delivery import parse_roadmap, parse_spec
from .project import Project


def created_at(value) -> datetime | None:
    """The `created` frontmatter value as an aware datetime: a full timestamp,
    or a date taken at midnight UTC for deliveries created before 0.1.0."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def age_hours(value, now: datetime | None = None) -> float | None:
    started = created_at(value)
    if started is None:
        return None
    return max(0.0, ((now or datetime.now(timezone.utc)) - started).total_seconds() / 3600)


def format_age(hours: float) -> str:
    days, rest = divmod(int(hours), 24)
    return f"{days}d {rest}h" if days else f"{rest}h"


def show_status(project: Project, slug: str | None = None) -> None:
    if slug:
        print(check_delivery(project, slug).render())
        return
    deliveries = project.list_deliveries()
    archived = project.list_archived()
    print(f"AtipSpec: {project.name} ({project.language})")
    branch = project.git.current_branch() if project.git.available else None
    print(f"git: {'branch ' + branch if branch else 'available' if project.git.available else 'not a repository'}")
    from .phases import contract_accepted
    if not project.contract.is_file():
        print("contract: missing (run the contract phase)")
    else:
        print("contract: " + ("accepted" if contract_accepted(project) else "not accepted yet (`atipspec accept contract`)"))
    capabilities = project.list_capabilities()
    print(f"living specs: {', '.join(capabilities) if capabilities else 'none'}")
    reports = {}
    if not deliveries:
        print("deliveries: none. Create one with `atipspec new <slug> --title \"...\"`")
    else:
        fingerprint = project.fingerprint()
        impacts = {}
        for name in deliveries:
            report = check_delivery(project, name, fingerprint=fingerprint)
            reports[name] = report
            spec = parse_spec((project.deliveries / name / "spec.md").read_text(encoding="utf-8"))
            impacts[name] = set(spec.impact)
            tasks = f" tasks {report.tasks_done}/{report.tasks_total}" if report.tasks_total else ""
            owner = f" @{spec.meta['owner']}" if spec.meta.get("owner") else ""
            hours = age_hours(spec.meta.get("created"))
            age = f", open {format_age(hours)}" if hours is not None else (", created unreadable" if spec.meta.get("created") else "")
            kind = " [fix]" if spec.kind == "fix" else ""
            print(f"- {name} [{report.status}]{kind}{tasks}{owner}{age}: {report.title or ''}")
            for line in describe(project, name):
                print(f"    accepted: {line}")
            limit = float(project.policy("max_age_hours"))
            if hours is not None and hours > limit:
                print(f"    warning: open for {format_age(hours)} (policy {int(limit)}h); finish it or split it into an initiative")
            print(f"    next: {report.next_action}")
        for index, first in enumerate(deliveries):
            for second in deliveries[index + 1:]:
                shared = sorted(impacts[first] & impacts[second])
                if shared:
                    print(f"  warning: {first} and {second} both touch {', '.join(shared)}")
    initiatives = project.list_initiatives()
    if initiatives:
        print("initiatives:")
        for name in initiatives:
            roadmap = parse_roadmap((project.initiatives / name / "roadmap.md").read_text(encoding="utf-8"))
            states = []
            for item, _ in roadmap.deliveries:
                if item in archived:
                    states.append(f"{item} delivered")
                elif item in reports:
                    states.append(f"{item} {reports[item].status}")
                else:
                    states.append(f"{item} pending")
            done = sum(1 for item, _ in roadmap.deliveries if item in archived)
            print(f"- {name} {done}/{len(roadmap.deliveries)}: {'; '.join(states) or 'no deliveries listed'}")
    if archived:
        print(f"delivered: {', '.join(archived)}")
