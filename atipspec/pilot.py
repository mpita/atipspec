"""Measured pilot records. Missing data stays missing; no synthetic ROI claims."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from statistics import median
import math

from .errors import AtipSpecError
from .project import validate_slug
from .trust import timestamp

METRICS = ("lead_hours", "human_review_minutes", "rework_minutes", "escaped_defects", "criteria_total", "criteria_tested", "observation_days")


def initialize(project, name):
    validate_slug(name, "pilot")
    folder = project.dot / "pilots" / name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "protocol.md"
    if path.exists():
        raise AtipSpecError("Pilot already exists")
    path.write_text(f'''# Pilot: {name}

Created: {date.today().isoformat()}

## Hypothesis

AtipSpec reduces escaped defects and rework without an unacceptable increase
in human review time. Define acceptable thresholds before collecting data.

## Design to complete with the team

- Accountable owner and human acceptance reviewer:
- Repository and comparable change types:
- Baseline process and AtipSpec version / policy version:
- Start, end, and the same defect observation window for both cohorts:
- Target sample size and exclusion rules (agree before starting):
- Success thresholds and stop conditions:

Use matched changes or alternate comparable changes between baseline and
AtipSpec. Keep team, scope, risk and observation windows comparable. Record
scope differences; do not interpret an uncontrolled before/after as causal.

## Measurements

For each real delivery record lead hours (work start to acceptance), active
human review minutes, rework minutes, escaped defects during the agreed window,
acceptance criteria total, and criteria mapped to executed tests. Add a source
(ticket, time log, CI/report link) and collector identity. Never use zero for
unknown data. `pilot record` requires a complete observation.

## Decision

Review the report with the team. Document adopt / extend pilot / stop and why.
A small sample is exploratory; do not claim proven productivity or ROI.
''')
    return path


def record(project, name, delivery, cohort, metrics, source, collector):
    validate_slug(name, "pilot")
    validate_slug(delivery, "delivery")
    if cohort not in ("baseline", "atipspec"):
        raise AtipSpecError("Cohort must be baseline or atipspec")
    if not source.strip() or not collector.strip():
        raise AtipSpecError("Measured observations require a source and collector")
    if set(metrics) != set(METRICS):
        raise AtipSpecError("All pilot metrics are required; unknown values must not be recorded as zero")
    for key, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise AtipSpecError(f"Invalid metric {key}")
    for key in ("escaped_defects", "criteria_total", "criteria_tested", "observation_days"):
        if int(metrics[key]) != metrics[key]:
            raise AtipSpecError(f"{key} must be an integer")
    if metrics["criteria_tested"] > metrics["criteria_total"] or metrics["observation_days"] <= 0 or metrics["criteria_total"] <= 0:
        raise AtipSpecError("Invalid criteria counts or observation window")
    folder = project.dot / "pilots" / name
    if not (folder / "protocol.md").is_file():
        raise AtipSpecError("Initialize the pilot first")
    path = folder / f"{cohort}-{delivery}.json"
    data = {"schema": 1, "delivery": delivery, "cohort": cohort, **metrics,
            "source": source, "collector": collector, "recorded_at": timestamp()}
    try:
        with path.open("x") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise AtipSpecError("Observation already exists; correct it through a reviewed Git change") from exc
    return path


def pilot_report(project, name):
    validate_slug(name, "pilot")
    folder = project.dot / "pilots" / name
    if not (folder / "protocol.md").is_file():
        raise AtipSpecError("Pilot not found")
    rows = [json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))]
    result = {"pilot": name, "observations": len(rows), "cohorts": {},
              "limitations": ["Observational comparison, not proof of causality. Validate source records and comparable scope."]}
    windows = {row["observation_days"] for row in rows}
    comparable = len(windows) == 1
    result["comparable_observation_windows"] = comparable
    for cohort in ("baseline", "atipspec"):
        group = [row for row in rows if row["cohort"] == cohort]
        result["cohorts"][cohort] = {"n": len(group)}
        if group:
            result["cohorts"][cohort].update({f"median_{key}": median(row[key] for row in group) for key in METRICS[:3]})
            result["cohorts"][cohort]["escaped_defects_per_delivery"] = sum(row["escaped_defects"] for row in group) / len(group)
            result["cohorts"][cohort]["tested_criteria_fraction"] = sum(row["criteria_tested"] for row in group) / sum(row["criteria_total"] for row in group)
    if not comparable:
        result["limitations"].append("No comparison: missing or unequal observation windows.")
    if any(result["cohorts"][cohort]["n"] == 0 for cohort in ("baseline", "atipspec")):
        result["limitations"].append("Both cohorts need real observations before comparing results.")
    return result
