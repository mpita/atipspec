"""Portable acceptance dossiers and requirement-to-evidence matrices."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .check import check_delivery
from .delivery import load_evidence, parse_plan, parse_review, parse_spec
from .junit import find, recorded_cases
from .locale import code as language_code, strings
from .trust import approvals_for, timestamp, digest, read_regular
from .errors import AtipSpecError


def report_data(project, slug, policy=None, report=None):
    directory = project.delivery_dir(slug)
    report = report or check_delivery(project, slug, policy=policy)
    spec = parse_spec((directory / "spec.md").read_text())
    plan = parse_plan((directory / "plan.md").read_text())
    review_path = directory / "review.md"
    review = parse_review(review_path.read_text() if review_path.is_file() else "")
    evidence, _ = load_evidence(directory / "evidence")
    matrix = []
    capability = spec.capability or slug
    for req in spec.requirements:
        for ac in req.criteria:
            tasks = [task for task in plan.tasks if ac.id in task.tests + task.manual]
            matrix.append({"requirement": f"{capability}/{req.id}", "criterion": f"{capability}/{ac.id}",
                           "description": ac.text, "tasks": [t.id for t in tasks],
                           "tests": [{"task": t.id, "test": t.proof[ac.id],
                                      "status": (found := find(t.proof[ac.id], recorded_cases(evidence[t.id].data))) and found["status"]
                                      if t.id in evidence else None}
                                     for t in tasks if ac.id in t.proof],
                           "verification": [{"task": t.id, "mode": "manual" if ac.id in t.manual else "automated",
                                             "commands": t.verify, "evidence": evidence[t.id].path.name if t.id in evidence else None,
                                             "ci_run": evidence[t.id].data.get("ci_run_url") if t.id in evidence else None} for t in tasks],
                           "verdict": review.verdicts.get(ac.id, ("MISSING", ""))[0],
                           "proof": review.verdicts.get(ac.id, ("MISSING", ""))[1]})
    approvals = []
    if policy:
        phases = ["spec", "plan", "acceptance"] + ["exception:" + f.id for f in review.findings]
        for phase in phases:
            try:
                approvals.extend(approvals_for(project, slug, phase, policy, spec.meta.get("owner")))
            except (AtipSpecError, OSError):
                pass
    artifacts = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and "reports" not in path.relative_to(directory).parts:
            artifacts[str(path.relative_to(directory))] = digest(read_regular(path))
    return {"schema": 1, "generated_at": timestamp(), "delivery": slug, "title": spec.title,
            "owner": spec.meta.get("owner"), "ticket": spec.meta.get("ticket"),
            "status": report.status, "accepted": bool(policy and report.ok and report.status == "verified"),
            "head": project.git.head(), "tree": report.fingerprint, "policy_sha256": policy.sha256 if policy else None,
            "policy_version": policy.data["version"] if policy else None,
            "language": project.language,
            "scope": strings(project.language)["scope_trusted" if policy else "scope_local"],
            "checks": [{"level": item.level, "text": item.text} for item in report.items],
            "matrix": matrix, "approvals": approvals,
            "findings": [{"id": f.id, "severity": f.severity, "text": f.text} for f in review.findings],
            "artifacts_sha256": artifacts}


def _proof_cell(row, s):
    named = "; ".join(f'{t["test"]} ({t["status"] or s["not_run"]})' for t in row.get("tests", []))
    return row["proof"] + (f" [{s['tests']}: {named}]" if named else "")


def markdown_report(data):
    s = strings(data.get("language"))

    def cell(value):
        return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")
    lines = [f'# {s["title"]}: {cell(data["title"])}', "",
             f'**{s["status"]}:** {data["status"]}. **{s["accepted"]}:** {s["yes"] if data["accepted"] else s["no"]}.', "",
             f'{s["scope"]}: {data["scope"]}. {s["owner"]}: {cell(data["owner"])}. {s["ticket"]}: {cell(data["ticket"])}.', "",
             f'{s["candidate"]}: `{data["head"]}` · {s["content"]}: `{data["tree"]}`.', "",
             f'{s["policy"]}: {cell(data["policy_version"])} / `{data["policy_sha256"]}`.', "",
             f'## {s["criteria"]}', '',
             f'| {s["requirement"]} | {s["criterion"]} | {s["outcome"]} | {s["tasks"]} | {s["verdict"]} | {s["proof"]} |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in data["matrix"]:
        lines.append("| " + " | ".join(cell(v) for v in (row["requirement"], row["criterion"], row["description"],
                                                        ", ".join(row["tasks"]), row["verdict"], _proof_cell(row, s))) + " |")
    lines += ["", f'## {s["approvals"]}', ""]
    lines += [f'- {cell(a["phase"])}: {cell(a["identity"])} ({a["role"]}), {a["approved_at"]}; {s["expires"]}: {cell(a.get("expires"))}.'
              for a in data["approvals"]] or [f'- {s["no_approvals"]}']
    lines += ["", f'## {s["checks"]}', ""]
    lines += [f'- {item["level"]}: {cell(item["text"])}' for item in data["checks"]] or [f'- {s["all_passed"]}']
    lines += ["", f'## {s["evidence"]}', ""]
    for row in data["matrix"]:
        for v in row["verification"]:
            lines.append(f'- {row["criterion"]} / {v["task"]}: {v["mode"]}; {s["evidence_file"]}: {cell(v["evidence"])}; '
                         f'{s["ci"]}: {cell(v["ci_run"])}; {s["commands"]}: {cell(v["commands"])}')
    lines += ["", s["footer"], ""]
    return "\n".join(lines)


def render_report(data, format):
    if format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    markdown = markdown_report(data)
    if format == "markdown":
        return markdown
    s = strings(data.get("language"))
    lang = language_code(data.get("language")) or "en"

    # Escape every input; reports may contain untrusted test output and specs.
    def esc(value):
        return html.escape(str(value if value is not None else "—"))
    rows = "".join("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in
                   (row["requirement"], row["criterion"], row["description"], ", ".join(row["tasks"]), row["verdict"], _proof_cell(row, s))) + "</tr>"
                   for row in data["matrix"])
    approvals = "".join(f'<li><strong>{esc(a["phase"])}</strong>: {esc(a["identity"])} '
                        f'({esc(a["role"])}), {esc(a["approved_at"])}; {esc(s["expires"])}: {esc(a.get("expires"))}</li>'
                        for a in data["approvals"]) or f'<li>{esc(s["no_approvals"])}</li>'
    checks = "".join(f'<li><strong>{esc(item["level"])}</strong>: {esc(item["text"])}</li>' for item in data["checks"])
    evidence = "".join(f'<li>{esc(row["criterion"])} / {esc(v["task"])}: {esc(v["mode"])}; '
                       f'{esc(s["evidence_file"])}: {esc(v["evidence"])}; {esc(s["ci"])}: {esc(v["ci_run"])}; '
                       f'{esc(s["commands"])}: {esc(v["commands"])}</li>'
                       for row in data["matrix"] for v in row["verification"])
    return (f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            f'<title>{esc(s["title"])}</title><style>body{{max-width:1200px;margin:3rem auto;padding:0 1rem;font:16px/1.6 system-ui;color:#182235}}'
            'h1{line-height:1.15}h2{margin-top:2rem}.summary{background:#f0f5f7;border-left:4px solid #21786a;padding:1rem 1.5rem}'
            'table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;border:1px solid #dde3eb;padding:.65rem}'
            'th{background:#edf2f6}code{overflow-wrap:anywhere}.table{overflow:auto}li{margin:.45rem 0}@media print{body{margin:0}tr{break-inside:avoid}}</style>'
            f'<main><p>{esc(s["dossier"])}</p><h1>{esc(data["title"])}</h1><div class="summary">'
            f'<strong>{esc(data["status"])}</strong> · {esc(s["accepted"])}: {esc(s["yes"] if data["accepted"] else s["no"])}'
            f'<p>{esc(data["scope"])}</p>{esc(s["owner"])}: {esc(data["owner"])} · {esc(s["ticket"])}: {esc(data["ticket"])}</div>'
            f'<p>{esc(s["candidate"])}: <code>{esc(data["head"])}</code><br>{esc(s["content"])}: <code>{esc(data["tree"])}</code><br>'
            f'{esc(s["policy"])}: {esc(data["policy_version"])} / <code>{esc(data["policy_sha256"])}</code></p>'
            f'<h2>{esc(s["criteria"])}</h2><div class="table"><table><thead><tr><th>{esc(s["requirement"])}</th><th>{esc(s["criterion"])}</th>'
            f'<th>{esc(s["outcome"])}</th><th>{esc(s["tasks"])}</th><th>{esc(s["verdict"])}</th><th>{esc(s["proof"])}</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<h2>{esc(s["approvals"])}</h2><ul>{approvals}</ul><h2>{esc(s["checks"])}</h2><ul>{checks}</ul>'
            f'<h2>{esc(s["evidence"])}</h2><ul>{evidence}</ul><p>{esc(s["generated"])}: {esc(data["generated_at"])}. '
            f'{esc(s["footer_html"])}</p></main></html>\n')


def get_report(project, slug, policy=None):
    if slug in project.list_deliveries():
        return report_data(project, slug, policy)
    from .project import validate_slug
    validate_slug(slug)
    path = project.archive / slug / "reports" / "acceptance.json"
    if not path.is_file():
        raise AtipSpecError("No current delivery or archived acceptance receipt")
    data = json.loads(read_regular(path))
    data["language"] = data.get("language") or project.language
    data["scope"] = strings(data["language"])["scope_archived"]
    return data
