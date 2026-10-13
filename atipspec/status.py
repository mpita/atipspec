"""Derived project state: nothing here is stored, everything is computed."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

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


def measure(created, agreed: str | None, accepted: str | None, now: datetime | None = None) -> dict:
    """Lead time: wall-clock hours from `created` to the result's acceptance,
    or to now while it is not accepted. Clock time, not effort."""
    started, ended = created_at(created), created_at(accepted)
    hours = None
    if started is not None:
        hours = round(max(0.0, ((ended or now or datetime.now(timezone.utc)) - started).total_seconds() / 3600), 2)
    return {"created": (created if isinstance(created, str) else started.isoformat()) if started else None,
            "proposal_accepted_at": agreed, "result_accepted_at": accepted if ended else None,
            "hours": hours, "complete": bool(started and ended)}


def _accepted_at(folder: Path, phase: str) -> str | None:
    try:
        data = json.loads((folder / "approvals" / f"local-{phase}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = data.get("accepted_at") if isinstance(data, dict) else None
    return value if isinstance(value, str) else None


def lead_time_from(folder: Path, accepted_at: str | None = None) -> dict:
    """The lead time of a delivery folder, active or archived, from its spec.md
    and its local approval records; `accepted_at` replaces the result's record."""
    spec = parse_spec((folder / "spec.md").read_text(encoding="utf-8"))
    agreed = _accepted_at(folder, "proposal") or _accepted_at(folder, "spec")
    return measure(spec.meta.get("created"), agreed, accepted_at or _accepted_at(folder, "result"))


def lead_time(project: Project, slug: str, spec=None, policy=None, accepted_at: str | None = None) -> dict:
    """The lead time of an open delivery. Without a trust policy its result
    counts as accepted when the local record is current for its content; under
    one, at `accepted_at`, when the acceptance was signed."""
    from .accept import is_current, read_record
    if spec is None:
        from .specs import load_spec
        spec = load_spec(project, slug)
    record = read_record(project, slug, "result") if policy is None and accepted_at is None else None
    if record and is_current(project, slug, "result"):
        accepted_at = record.get("accepted_at")
    agreed = None if policy else read_record(project, slug, "proposal") or read_record(project, slug, "spec")
    return measure(spec.meta.get("created"), agreed.get("accepted_at") if agreed else None, accepted_at)


def delivered_lead_time(project: Project, slug: str) -> dict | None:
    """An archived delivery's lead time: its receipt's, or one computed from
    the records archived with it (receipts written before 0.3.0 have none),
    with `origin` saying which. None when it cannot be told."""
    from .errors import AtipSpecError
    folder = project.archive / slug
    try:
        receipt = json.loads((folder / "reports" / "acceptance.json").read_text(encoding="utf-8"))
        lead = receipt.get("lead_time") if isinstance(receipt, dict) else None
    except (OSError, ValueError):
        lead = None
    if isinstance(lead, dict) and lead.get("complete") and isinstance(lead.get("hours"), (int, float)):
        return {**lead, "origin": "receipt"}
    try:
        lead = lead_time_from(folder)
    except (OSError, ValueError, AtipSpecError):
        return None
    return {**lead, "origin": "records"} if lead["complete"] else None


def age_warning(project: Project, hours: float | None) -> str | None:
    """The `max_age_hours` warning for a delivery open `hours`, or None."""
    limit = float(project.policy("max_age_hours"))
    if hours is None or hours <= limit:
        return None
    return (f"open for {format_age(hours)} (policy {limit:g}h): a delivery should fit in a working day; finish it "
            "or split what remains into another delivery under an initiative")


def delivery_entry(project: Project, name: str, report) -> dict:
    """One open delivery as `status` shows it."""
    from .tickets import link
    spec = parse_spec((project.deliveries / name / "spec.md").read_text(encoding="utf-8"))
    lead = report.lead_time or lead_time(project, name)
    return {"slug": name, "title": report.title, "kind": spec.kind, "state": report.status,
            "exit_code": report.exit_code, "owner": spec.meta.get("owner"), "ticket": spec.meta.get("ticket"),
            "ticket_url": link(project, spec.meta.get("ticket")),
            "tasks": {"done": report.tasks_done, "total": report.tasks_total}, "lead_time": lead,
            "age_warning": age_warning(project, lead["hours"]), "created": spec.meta.get("created"),
            "impact": list(spec.impact), "acceptances": describe(project, name), "next": report.next_action}


def archived_entry(project: Project, name: str) -> dict:
    """One archived delivery: its receipt's word, as `status` shows it."""
    from .tickets import link
    try:
        spec = parse_spec((project.archive / name / "spec.md").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        spec = parse_spec("")
    try:
        receipt = json.loads((project.archive / name / "reports" / "acceptance.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        receipt = {}
    return {"slug": name, "title": spec.title, "owner": spec.meta.get("owner"), "ticket": spec.meta.get("ticket"),
            "ticket_url": link(project, spec.meta.get("ticket")),
            "accepted": isinstance(receipt, dict) and receipt.get("accepted") is True,
            "lead_time": delivered_lead_time(project, name)}


def status_data(project: Project) -> dict:
    """The project's derived state, for `status --format json|markdown`."""
    from .accept import describe_contract
    from .install import permission_summary
    branch = project.git.current_branch() if project.git.available else None
    deliveries = project.list_deliveries()
    fingerprint = project.fingerprint() if deliveries else None
    entries = [delivery_entry(project, name, check_delivery(project, name, fingerprint=fingerprint))
               for name in deliveries]
    archived = project.list_archived()
    initiatives = []
    states = {entry["slug"]: entry["state"] for entry in entries}
    for name in project.list_initiatives():
        roadmap = parse_roadmap((project.initiatives / name / "roadmap.md").read_text(encoding="utf-8"))
        initiatives.append({"slug": name, "deliveries": [
            {"slug": item, "state": "delivered" if item in archived else states.get(item, "pending")}
            for item, _ in roadmap.deliveries]})
    from .integration import unshared_default
    return {"schema": 1, "project": project.name, "language": project.language, "branch": branch,
            "git": project.git.available, "contract": describe_contract(project),
            "approvals": permission_summary(project.root), "trust": project.policy("trust"),
            "integration_warning": unshared_default(project),
            "living_specs": project.list_capabilities(), "deliveries": entries, "initiatives": initiatives,
            "archived": [archived_entry(project, name) for name in archived]}


def _ticket(entry: dict) -> str:
    if not entry.get("ticket"):
        return ""
    url = entry.get("ticket_url")
    return f" {entry['ticket']}" + (f" ({url})" if url and url != entry["ticket"] else "")


def _age(entry: dict) -> str:
    hours = entry["lead_time"]["hours"]
    if hours is not None:
        return (", accepted after " if entry["lead_time"]["complete"] else ", open ") + format_age(hours)
    return ", created unreadable" if entry.get("created") else ""


def render_text(data: dict) -> str:
    lines = [f"AtipSpec: {data['project']} ({data['language']})",
             f"git: {'branch ' + data['branch'] if data['branch'] else 'available' if data['git'] else 'not a repository'}",
             f"contract: {data['contract']}", f"approvals: {data['approvals']}"]
    if data["trust"] == "required":
        lines.append("trust: required: local acceptance is disabled; the gate needs an external trust policy")
    if data.get("integration_warning"):
        lines.append(f"warning: {data['integration_warning']}")
    lines.append(f"living specs: {', '.join(data['living_specs']) if data['living_specs'] else 'none'}")
    if not data["deliveries"]:
        lines.append("deliveries: none. Create one with `atipspec new <slug> --title \"...\"`")
    for entry in data["deliveries"]:
        tasks = f" tasks {entry['tasks']['done']}/{entry['tasks']['total']}" if entry["tasks"]["total"] else ""
        owner = f" @{entry['owner']}" if entry["owner"] else ""
        kind = " [fix]" if entry["kind"] == "fix" else ""
        lines.append(f"- {entry['slug']} [{entry['state']}]{kind}{tasks}{owner}{_ticket(entry)}{_age(entry)}: "
                     f"{entry['title'] or ''}")
        lines += [f"    accepted: {line}" for line in entry["acceptances"]]
        if entry["age_warning"]:
            lines.append(f"    warning: {entry['age_warning']}")
        lines.append(f"    next: {entry['next']}")
    entries = data["deliveries"]
    for index, first in enumerate(entries):
        for second in entries[index + 1:]:
            shared = sorted(set(first["impact"]) & set(second["impact"]))
            if shared:
                lines.append(f"  warning: {first['slug']} and {second['slug']} both touch {', '.join(shared)}")
    if data["initiatives"]:
        lines.append("initiatives:")
        for initiative in data["initiatives"]:
            items = initiative["deliveries"]
            done = sum(1 for item in items if item["state"] == "delivered")
            states = "; ".join(f"{item['slug']} {item['state']}" for item in items)
            lines.append(f"- {initiative['slug']} {done}/{len(items)}: {states or 'no deliveries listed'}")
    if data["archived"]:
        delivered = [f"{entry['slug']} ({format_age(entry['lead_time']['hours'])})" if entry["lead_time"]
                     else entry["slug"] for entry in data["archived"]]
        lines.append(f"delivered: {', '.join(delivered)}")
    return "\n".join(lines) + "\n"


def _cell(value) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def _ticket_cell(entry: dict) -> str:
    if not entry.get("ticket"):
        return "—"
    url = entry.get("ticket_url")
    if not url:
        return _cell(entry["ticket"])
    return f"[{_cell(entry['ticket'])}](<{url.replace('<', '%3C').replace('>', '%3E').replace('|', '%7C')}>)"


def render_markdown(data: dict) -> str:
    """The deliveries as Markdown tables, for a pull request or a job summary."""
    lines = [f"## AtipSpec status: {_cell(data['project'])}", "",
             f"Branch: {_cell(data['branch'])} · Contract: {_cell(data['contract'])}", ""]
    if data["deliveries"]:
        lines += ["| Delivery | Ticket | Owner | State | Next |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {_cell(entry['slug'])} | {_ticket_cell(entry)} | {_cell(entry['owner'])} | "
                  f"{_cell(entry['state'])} | {_cell(entry['next'])} |" for entry in data["deliveries"]]
    else:
        lines.append("No open delivery.")
    if data["archived"]:
        lines += ["", "| Delivered | Ticket | Owner | Accepted |", "| --- | --- | --- | --- |"]
        lines += [f"| {_cell(entry['slug'])} | {_ticket_cell(entry)} | {_cell(entry['owner'])} | "
                  f"{'yes' if entry['accepted'] else 'no'} |" for entry in data["archived"]]
    return "\n".join(lines) + "\n"


def show_status(project: Project, slug: str | None = None, fmt: str = "text") -> None:
    if slug:
        report = check_delivery(project, slug)
        entry = delivery_entry(project, slug, report)
        from .rounds import describe as rounds
        line = rounds(project, slug)
        if fmt == "json":
            print(json.dumps({"schema": 1, "delivery": {**entry, "review_rounds": line, "checks": [
                {"level": item.level, "text": item.text} for item in report.items]}}, indent=2, ensure_ascii=False))
            return
        if fmt == "markdown":
            print(render_markdown({"project": project.name, "branch": project.git.current_branch()
                                   if project.git.available else None, "contract": None,
                                   "deliveries": [entry], "archived": []}), end="")
            print("".join(f"\n- **{item.level}** {_cell(item.text)}" for item in report.items) + "\n")
            return
        print(report.render(next_action=False))
        if entry["ticket"]:
            print(f"ticket:{_ticket(entry)}")
        for accepted in entry["acceptances"]:
            print(f"accepted: {accepted}")
        if line:
            print(line)
        print(f"Next: {report.next_action}")
        if (project.delivery_dir(slug) / "run.json").exists():
            from .runner import read_state
            state = read_state(project, slug)
            print(f"execution checkpoint: {state['status']} — {state.get('reason', '')}")
            print(f"elapsed: {state['elapsed_s']}s; correction rounds: {state['rounds']}")
            print("Current gate results above take precedence over this saved checkpoint.")
        return
    data = status_data(project)
    if fmt == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif fmt == "markdown":
        print(render_markdown(data), end="")
    else:
        print(render_text(data), end="")
