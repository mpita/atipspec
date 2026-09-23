"""Reviewable, content-addressed proposal view; presentation grants no approval."""
from __future__ import annotations

import difflib

from .check import check_delivery
from .delivery import parse_plan
from .specs import load_spec, baseline_text, canonical_path
from .trust import subject


def render_proposal(project, slug):
    directory = project.delivery_dir(slug)
    spec = load_spec(project, slug)
    plan_path = directory / "plan.md"
    plan_text = plan_path.read_text() if plan_path.exists() else ""
    plan = parse_plan(plan_text)
    report = check_delivery(project, slug, preapproval=True)
    blocking = report.blocking(("spec", "plan", "contract", "base", "coordination"))
    lines = [f"# Proposal: {spec.title or slug}", "",
             f"Change: {slug} · Owner: {spec.meta.get('owner') or 'not assigned'} · Ticket: {spec.meta.get('ticket') or 'none'}", "",
             f"{len(spec.requirements)} requirements · {len(spec.criteria)} criteria · {len(plan.tasks)} tasks", ""]
    if blocking or spec.open_questions:
        lines += ["Not ready for approval:", ""]
        lines += [f"- {item.text}" for item in blocking]
        lines += [f"- Open question: {question}" for question in spec.open_questions]
    else:
        lines += [f"Content digest (current draft): `{subject(project, slug, 'plan')}`", "",
                  f"The user approves scope, approach and tests together: `atipspec accept {slug} proposal`.",
                  "Approval authorizes implementation within this agreement. Result acceptance, merge and deployment remain separate."]
    lines += ["", "## Change intent", "", (directory / "spec.md").read_text().strip(), "", "## Behaviors", ""]
    for req in spec.requirements:
        lines += [f"### {req.id}: {req.title}", "", "\n".join(req.body).strip(), ""]
    lines += ["## Approach and verification", "", plan_text.strip(), ""]
    if spec.meta.get("schema") == 2 and spec.requirements:
        before = baseline_text(project, slug)
        after = canonical_path(project, spec).read_text()
        delta = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                             fromfile="accepted baseline", tofile="working proposal"))
        lines += ["## Specification changes", "", "```diff", delta.rstrip() or "(no behavior change; restores existing requirements)", "```", ""]
    return "\n".join(lines).rstrip() + "\n"
