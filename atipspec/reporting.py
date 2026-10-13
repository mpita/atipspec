"""Portable acceptance dossiers and requirement-to-evidence matrices."""
from __future__ import annotations

from .specs import load_spec

import html
import json
from pathlib import Path
import re

from .check import check_delivery, outside_scope, review_cases
from .delivery import load_evidence, parse_plan, parse_review, parse_spec, verification_task
from .junit import find, recorded_cases
from .locale import code as language_code, strings
from .pointers import observation, resolve
from .review import MAX_DIFF_BYTES
from .trust import approvals_for, timestamp, digest, read_regular
from .errors import AtipSpecError

MAX_MARKDOWN_DIFF_BYTES = 50_000   # the dossier the assistant presents in the conversation


def _cut(text: str, limit: int) -> str:
    return text.encode("utf-8")[:limit].decode("utf-8", "ignore")


def candidate_changes(project, slug, spec, plan, tree, policy=None):
    """What the candidate changes from the delivery's base commit (HEAD when
    the base is missing or unusable): every file but this delivery's own
    folder and what the integration branch brought (`integrated`, with its
    ref), with its status, lines and new content's object id, and the diff
    of those files, so a change to config.yaml or the contract shows too; a
    file that branch changed and the candidate changed too, putting it back
    as the base had it included, against the merge base with that branch, as
    a pull request shows it. It compares the fingerprint
    tree the evidence, the review and the result acceptance are bound to,
    untracked files included, ignored ones left out."""
    git = project.git
    if not git.available or tree is None:
        return None
    from .integration import brought_paths
    from .specs import base_problem
    problem = base_problem(project, spec, slug)
    base = git.head() if problem else spec.meta["base"]
    if base is None:
        return None
    found, brought, rebased = (None, set(), set()) if problem else brought_paths(project, slug, base, policy)
    before = project.fingerprint_at(base)
    own = f".atipspec/deliveries/{slug}/"
    files = [entry for entry in git.diff_files(before, tree)
             if not entry["path"].startswith(own) and entry["path"] not in brought | rebased]
    diff = git.diff(before, tree, exclude=(own.rstrip("/"),), omit=tuple(sorted(brought | rebased)))
    if rebased:
        merged = project.fingerprint_at(found.commit)
        files = sorted(files + git.diff_files(merged, tree, only=tuple(sorted(rebased))),
                       key=lambda entry: entry["path"])
        diff += git.diff(merged, tree, exclude=(own.rstrip("/"),), only=tuple(sorted(rebased)))
    stray = set(outside_scope(plan, [entry["path"] for entry in files], project, base))
    for entry in files:
        entry["outside_scope"] = entry["path"] in stray
    raw = diff.encode("utf-8")
    return {"base": git.run("rev-parse", base).strip(), "files": files, "diff": _cut(diff, MAX_DIFF_BYTES),
            "diff_bytes": len(raw), "diff_sha256": digest(raw), "truncated": len(raw) > MAX_DIFF_BYTES,
            "integrated": {"ref": found.ref, "files": sorted(brought)} if brought else None}


def report_data(project, slug, policy=None, report=None):
    directory = project.delivery_dir(slug)
    report = report or check_delivery(project, slug, policy=policy)
    spec = load_spec(project, slug)
    plan = parse_plan((directory / "plan.md").read_text(encoding="utf-8"))
    review_path = directory / "review.md"
    review = parse_review(review_path.read_text(encoding="utf-8") if review_path.is_file() else "")
    evidence, _ = load_evidence(directory / "evidence")
    from dataclasses import replace
    task_views = [replace(verification_task(plan, task), id=task.id) for task in plan.tasks]
    cases = review_cases(project, plan, evidence, report.fingerprint)
    if plan.final:
        shared = evidence.get("FINAL")
        evidence = {task.id: shared for task in plan.tasks} if shared else {}
    matrix = []
    capability = spec.capability or slug
    for req in spec.requirements:
        for ac in req.criteria:
            tasks = [task for task in task_views if ac.id in task.tests + task.manual]
            # Risk low takes a criterion's named test that passed instead of a verdict.
            verdict = review.verdicts.get(ac.id) or (("NOT NEEDED", "") if ac.id in report.proven else ("MISSING", ""))
            matrix.append({"requirement": f"{capability}/{req.id}", "criterion": f"{capability}/{ac.id}",
                           "description": ac.text, "tasks": [t.id for t in tasks],
                           "tests": [{"task": t.id, "test": t.proof[ac.id],
                                      "status": (found := find(t.proof[ac.id], recorded_cases(evidence[t.id].data))) and found["status"]
                                      if t.id in evidence else None}
                                     for t in tasks if ac.id in t.proof],
                           "verification": [{"task": t.id, "mode": "manual" if ac.id in t.manual else "automated",
                                             "commands": t.verify, "evidence": evidence[t.id].path.name if t.id in evidence else None,
                                             "ci_run": evidence[t.id].data.get("ci_run_url") if t.id in evidence else None} for t in tasks],
                           "verdict": verdict[0], "proof": verdict[1],
                           "pointer": _pointer(project, review.verdicts.get(ac.id), ac, cases, directory)})
    approvals = []
    if policy:
        phases = ["spec", "plan", "acceptance"] + ["exception:" + f.id for f in review.findings]
        for phase in phases:
            try:
                approvals.extend(approvals_for(project, slug, phase, policy, spec.meta.get("owner")))
            except (AtipSpecError, OSError):
                pass
    else:
        from .accept import is_current, phases_for, read_record
        for phase in phases_for(spec):
            if is_current(project, slug, phase):
                record = read_record(project, slug, phase)
                approvals.append({"phase": phase, "identity": record["by"], "role": "local declaration",
                                  "approved_at": record["accepted_at"], "subject": record["subject"],
                                  "source": "local", "authenticated": False, "channel": record.get("channel"),
                                  "client": record.get("client"), "code": record.get("code")})
    artifacts = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and "reports" not in path.relative_to(directory).parts:
            artifacts[path.relative_to(directory).as_posix()] = digest(read_regular(path))
    from .risk import level
    from .status import lead_time
    lead = report.lead_time or lead_time(project, slug, spec, policy)
    from .tickets import link
    data = {"schema": 1, "generated_at": timestamp(), "delivery": slug, "title": spec.title,
            "owner": spec.meta.get("owner"), "ticket": spec.meta.get("ticket"),
            "ticket_url": link(project, spec.meta.get("ticket")),
            "kind": spec.kind, "risk": level(spec), "lead_time": lead,
            "status": report.status, "accepted": bool(report.ok and report.status in ("verified", "accepted")),
            "acceptance_mode": "trusted" if policy else "local", "authenticated": bool(policy),
            "head": project.git.head(), "tree": report.fingerprint, "policy_sha256": policy.sha256 if policy else None,
            "policy_version": policy.data["version"] if policy else None,
            "language": project.language,
            "scope": strings(project.language)["scope_trusted" if policy else "scope_local"],
            "checks": [{"level": item.level, "text": item.text} for item in report.items],
            "matrix": matrix, "approvals": approvals,
            "findings": [{"id": f.id, "severity": f.severity, "text": f.text} for f in review.findings],
            "review": {"reviewer": review.reviewer, "session": review.session, "tree": review.tree}
            if review_path.is_file() else None,
            "review_rounds": _rounds(project, slug),
            "changes": candidate_changes(project, slug, spec, plan, report.fingerprint, policy),
            "artifacts_sha256": artifacts}
    if policy is None and report.status == "checked":
        from .accept import approval_code
        data["approval_code"] = approval_code(project, slug, "result")
    return data


def _rounds(project, slug):
    """The reviews counted for the current agreement and review_rounds, once
    `atipspec review` has counted one."""
    from .rounds import FILE, read
    if not (project.delivery_dir(slug) / FILE).exists():
        return None
    try:
        data = read(project, slug)
    except (AtipSpecError, OSError):
        return None
    if data["packet_tree"] is None:
        return None
    return {"used": data["rounds"], "limit": int(project.policy("review_rounds"))}


def _pointer(project, verdict, criterion, cases, directory):
    """What a PASS verdict's pointer resolved to, `observation` for a manual
    criterion's description, or None."""
    if not verdict or verdict[0] != "PASS":
        return None
    found = resolve(project, verdict[1], cases, directory)
    if found is None and criterion.method == "manual" and observation(verdict[1]):
        return "observation"
    return found


def _proof_cell(row, s):
    named = "; ".join(f'{t["test"]} ({t["status"] or s["not_run"]})' for t in row.get("tests", []))
    cell = row["proof"] + (f" [{s['tests']}: {named}]" if named else "")
    if row.get("verdict") == "PASS" and "pointer" in row:
        pointer = s["observation"] if row["pointer"] == "observation" else row["pointer"] or s["unresolved"]
        cell += f" [{s['pointer']}: {pointer}]"
    elif row.get("verdict") == "NOT NEEDED":
        cell += f" [{s['not_needed']}]"
    return cell


def _review_lines(data, s):
    """The reviewer and session, with a warning for a shared session; none for
    receipts written before 0.3.0."""
    if "review" not in data:
        return []
    review = data["review"]
    if not review:
        lines = [s["no_review"]]
    else:
        lines = [f'{s["reviewer"]}: {review.get("reviewer") or "—"} · {s["session"]}: {review.get("session")}']
        lines += [s["session_shared"]] if review.get("session") != "isolated" else []
    rounds = data.get("review_rounds")
    return lines + ([s["review_rounds"].format(**rounds)] if rounds else [])


STATUS_KEYS = {"A": "added", "M": "modified", "D": "deleted", "T": "type_changed"}


def _change_rows(changes, s):
    return [(entry["path"], s[STATUS_KEYS.get(entry["status"], "modified")],
             s["binary"] if entry.get("added") is None else f'+{entry["added"]} −{entry["deleted"]}',
             s["yes"] if entry.get("outside_scope") else s["no"]) for entry in changes["files"]]


def _binary_note(changes, s):
    """The binary files the candidate adds or changes, whose content the diff
    does not show, or None."""
    names = [entry["path"] for entry in changes["files"] if entry.get("added") is None and entry["status"] != "D"]
    return s["binary_files"].format(names=", ".join(names)) if names else None


def _harness_note(changes, s):
    """The files the candidate changes that configure how the tests run, or None."""
    from .verify import harness_files
    names = harness_files(entry["path"] for entry in changes["files"] if entry["status"] != "D")
    return s["harness_files"].format(names=", ".join(names)) if names else None


def _integrated_note(changes, s):
    """The files the integration branch brought, left out of the changes, or None."""
    integrated = changes.get("integrated")
    if not integrated or not integrated.get("files"):
        return None
    names = [name for name in integrated["files"] if not name.startswith(".atipspec/")]
    rest = len(integrated["files"]) - len(names)
    return s["integrated_files"].format(ref=integrated["ref"], names=", ".join(
        names + ([s["integrated_rest"].format(count=rest)] if rest else [])))


def _ticket_markdown(data, cell):
    """The ticket for Markdown, as a link when it has one."""
    url = data.get("ticket_url")
    if not data.get("ticket") or not url:
        return cell(data.get("ticket"))
    return f"[{cell(data['ticket'])}](<{url.replace('<', '%3C').replace('>', '%3E')}>)"


def _ticket_html(data, esc):
    """The ticket for HTML: a link only to an https address."""
    url = data.get("ticket_url")
    if not data.get("ticket") or not isinstance(url, str) or not url.startswith("https://"):
        return esc(data.get("ticket"))
    return f'<a href="{esc(url)}">{esc(data["ticket"])}</a>'


def _diff_note(changes, shown, s):
    """Why the diff is incomplete, or None when it is all there."""
    if "diff" not in changes:
        return s["diff_not_retained"].format(total=changes["diff_bytes"], sha=changes["diff_sha256"])
    if shown < changes["diff_bytes"]:
        return s["diff_truncated"].format(shown=shown, total=changes["diff_bytes"], sha=changes["diff_sha256"],
                                          base=changes["base"][:12])
    return None


def _fence(text):
    """A code fence longer than any run of backticks in the text."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _approval_detail(approval, s):
    """How a local approval was recorded, or when a signed one expires."""
    if approval.get("source") != "local":
        return f'{s["expires"]}: {approval.get("expires") if approval.get("expires") is not None else "—"}'
    channel = approval.get("channel")
    if channel:
        from .accept import client_label
        label = client_label(approval.get("client"))
        channel += f" ({label})" if label else ""
    detail = f'{s["channel"]}: {channel or s["channel_unrecorded"]}'
    return detail + (f'; {s["code"]}: {approval["code"]}' if approval.get("code") else "")


def _profile_line(data, s):
    """Kind, risk and lead time; None for receipts written before 0.3.0."""
    if "lead_time" not in data:
        return None
    lead = data.get("lead_time") or {}
    hours = lead.get("hours")
    if not isinstance(hours, (int, float)):
        time = s["lead_time_unknown"]
    else:
        time = s["lead_time_done" if lead.get("complete") else "lead_time_open"].format(hours=f"{hours:.1f}")
    return f'{s["kind"]}: {data.get("kind") or "—"}. {s["risk"]}: {data.get("risk") or "—"}. {s["lead_time"]}: {time}.'


def _code_line(data, s):
    return (f'{s["approval_code"]}: {data["approval_code"]}. '
            + s["approval_code_hint"].format(slug=data["delivery"], code=data["approval_code"]))


def markdown_report(data):
    s = strings(data.get("language"))

    def cell(value):
        return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")
    lines = [f'# {s["title"]}: {cell(data["title"])}', "",
             f'**{s["status"]}:** {data["status"]}. **{s["accepted"]}:** {s["yes"] if data["accepted"] else s["no"]}.', ""]
    if data.get("approval_code"):
        lines += [_code_line(data, s), ""]
    lines += [f'{s["scope"]}: {data["scope"]}. {s["owner"]}: {cell(data["owner"])}. '
              f'{s["ticket"]}: {_ticket_markdown(data, cell)}.', ""]
    profile = _profile_line(data, s)
    if profile:
        lines += [profile, ""]
    lines += [f'{s["candidate"]}: `{data["head"]}` · {s["content"]}: `{data["tree"]}`.', "",
              f'{s["policy"]}: {cell(data["policy_version"])} / `{data["policy_sha256"]}`.', "",
              f'## {s["criteria"]}', '',
              f'| {s["requirement"]} | {s["criterion"]} | {s["outcome"]} | {s["tasks"]} | {s["verdict"]} | {s["proof"]} |',
              '| --- | --- | --- | --- | --- | --- |']
    for row in data["matrix"]:
        lines.append("| " + " | ".join(cell(v) for v in (row["requirement"], row["criterion"], row["description"],
                                                        ", ".join(row["tasks"]), row["verdict"], _proof_cell(row, s))) + " |")
    review = _review_lines(data, s)
    if review:
        lines += ["", f'## {s["review"]}', ""] + [line for text in review for line in (text, "")][:-1]
    lines += ["", f'## {s["approvals"]}', ""]
    lines += [f'- {cell(a["phase"])}: {cell(a["identity"])} ({a["role"]}), {a["approved_at"]}; {cell(_approval_detail(a, s))}.'
              for a in data["approvals"]] or [f'- {s["no_approvals"]}']
    lines += ["", f'## {s["checks"]}', ""]
    lines += [f'- {item["level"]}: {cell(item["text"])}' for item in data["checks"]] or [f'- {s["all_passed"]}']
    lines += ["", f'## {s["evidence"]}', ""]
    for row in data["matrix"]:
        for v in row["verification"]:
            lines.append(f'- {row["criterion"]} / {v["task"]}: {v["mode"]}; {s["evidence_file"]}: {cell(v["evidence"])}; '
                         f'{s["ci"]}: {cell(v["ci_run"])}; {s["commands"]}: {cell(v["commands"])}')
    changes = data.get("changes")
    if changes:
        lines += ["", f'## {s["changes"]}', "",
                  f'{s["base"]}: `{changes["base"]}`. {s["files_count"].format(count=len(changes["files"]))}.', ""]
        if changes["files"]:
            lines += [f'| {s["file"]} | {s["change"]} | {s["lines"]} | {s["outside_scope"]} |', "| --- | --- | --- | --- |"]
            lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in _change_rows(changes, s)]
        else:
            lines.append(s["no_changes"])
        for note in (_integrated_note(changes, s), _binary_note(changes, s), _harness_note(changes, s)):
            if note:
                lines += ["", note]
        diff = _cut(changes.get("diff", ""), MAX_MARKDOWN_DIFF_BYTES)
        if diff.strip():
            fence = _fence(diff)
            lines += ["", fence + "diff", diff.rstrip("\n"), fence]
        note = _diff_note(changes, len(diff.encode("utf-8")), s)
        if note:
            lines += ["", note]
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
                        f'({esc(a["role"])}), {esc(a["approved_at"])}; {esc(_approval_detail(a, s))}</li>'
                        for a in data["approvals"]) or f'<li>{esc(s["no_approvals"])}</li>'
    checks = "".join(f'<li><strong>{esc(item["level"])}</strong>: {esc(item["text"])}</li>' for item in data["checks"])
    evidence = "".join(f'<li>{esc(row["criterion"])} / {esc(v["task"])}: {esc(v["mode"])}; '
                       f'{esc(s["evidence_file"])}: {esc(v["evidence"])}; {esc(s["ci"])}: {esc(v["ci_run"])}; '
                       f'{esc(s["commands"])}: {esc(v["commands"])}</li>'
                       for row in data["matrix"] for v in row["verification"])
    review = _review_lines(data, s)
    review = (f'<h2>{esc(s["review"])}</h2>' + "".join(f"<p>{esc(text)}</p>" for text in review)) if review else ""
    profile = _profile_line(data, s)
    profile = f"<p>{esc(profile)}</p>" if profile else ""
    changes, diff = data.get("changes"), ""
    if changes:
        files = "".join("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in row) + "</tr>"
                        for row in _change_rows(changes, s))
        diff = (f'<h2>{esc(s["changes"])}</h2><p>{esc(s["base"])}: <code>{esc(changes["base"])}</code>. '
                f'{esc(s["files_count"].format(count=len(changes["files"])))}.</p>')
        diff += (f'<div class="table"><table><thead><tr><th>{esc(s["file"])}</th><th>{esc(s["change"])}</th>'
                 f'<th>{esc(s["lines"])}</th><th>{esc(s["outside_scope"])}</th></tr></thead><tbody>{files}</tbody></table></div>'
                 if changes["files"] else f'<p>{esc(s["no_changes"])}</p>')
        for note in (_integrated_note(changes, s), _binary_note(changes, s), _harness_note(changes, s)):
            diff += f"<p>{esc(note)}</p>" if note else ""
        if changes.get("diff", "").strip():
            diff += f'<pre class="diff">{esc(changes["diff"])}</pre>'
        note = _diff_note(changes, len(changes.get("diff", "").encode("utf-8")), s)
        diff += f"<p>{esc(note)}</p>" if note else ""
    return (f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            f'<title>{esc(s["title"])}</title><style>body{{max-width:1200px;margin:3rem auto;padding:0 1rem;font:16px/1.6 system-ui;color:#182235}}'
            'h1{line-height:1.15}h2{margin-top:2rem}.summary{background:#f0f5f7;border-left:4px solid #21786a;padding:1rem 1.5rem}'
            'table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;border:1px solid #dde3eb;padding:.65rem}'
            'th{background:#edf2f6}code{overflow-wrap:anywhere}.table{overflow:auto}li{margin:.45rem 0}'
            'pre.diff{background:#f6f8fa;padding:1rem;overflow:auto;font-size:13px;white-space:pre}'
            '@media print{body{margin:0}tr{break-inside:avoid}pre.diff{white-space:pre-wrap}}</style>'
            f'<main><p>{esc(s["dossier"])}</p><h1>{esc(data["title"])}</h1><div class="summary">'
            f'<strong>{esc(data["status"])}</strong> · {esc(s["accepted"])}: {esc(s["yes"] if data["accepted"] else s["no"])}'
            + (f'<p>{esc(_code_line(data, s))}</p>' if data.get("approval_code") else "") +
            f'<p>{esc(data["scope"])}</p>{esc(s["owner"])}: {esc(data["owner"])} · {esc(s["ticket"])}: {_ticket_html(data, esc)}{profile}</div>'
            f'<p>{esc(s["candidate"])}: <code>{esc(data["head"])}</code><br>{esc(s["content"])}: <code>{esc(data["tree"])}</code><br>'
            f'{esc(s["policy"])}: {esc(data["policy_version"])} / <code>{esc(data["policy_sha256"])}</code></p>'
            f'<h2>{esc(s["criteria"])}</h2><div class="table"><table><thead><tr><th>{esc(s["requirement"])}</th><th>{esc(s["criterion"])}</th>'
            f'<th>{esc(s["outcome"])}</th><th>{esc(s["tasks"])}</th><th>{esc(s["verdict"])}</th><th>{esc(s["proof"])}</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'{review}<h2>{esc(s["approvals"])}</h2><ul>{approvals}</ul><h2>{esc(s["checks"])}</h2><ul>{checks}</ul>'
            f'<h2>{esc(s["evidence"])}</h2><ul>{evidence}</ul>{diff}<p>{esc(s["generated"])}: {esc(data["generated_at"])}. '
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
