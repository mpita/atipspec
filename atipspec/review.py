"""Build the packet a reviewer in an isolated session works from: rubric, risk,
contract, the living specs and decisions the delivery declares, spec, plan,
deferred items, evidence summary, files outside the declared scope and the diff
against the change base."""
from __future__ import annotations

from .specs import load_spec

from pathlib import Path

from .context import decisions_for
from .delivery import load_evidence, parse_plan, parse_spec
from .project import Project, template

MAX_UNTRACKED_BYTES = 64_000
MAX_UNTRACKED_TOTAL = 400_000
MAX_DIFF_BYTES = 200_000    # the packet's diff, and the dossier's


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def build_packet(project: Project, slug: str) -> str:
    directory = project.delivery_dir(slug)
    spec_text = _read(directory / "spec.md")
    spec = load_spec(project, slug)
    tree = project.fingerprint()
    review_path = project.rel(directory / "review.md")
    rubric = template("review-rubric.md")
    rubric = rubric.replace("{slug}", slug).replace("{review_path}", review_path)
    rubric = rubric.replace("{tree}", tree or "unknown").replace("{title}", spec.title or slug)

    from .risk import describe, level
    risk = level(spec)
    parts = [f"# AtipSpec review packet: {slug}", "", rubric.rstrip(), ""]
    if risk:
        parts += ["## Risk", "", describe(risk) + ".", ""]
    contract = _read(project.contract).rstrip()
    parts += ["## Architecture contract (.atipspec/contract.md)", "", contract or "(no contract defined)", ""]
    parts += ["## Living specs in the impact list", ""]
    if not spec.impact:
        parts.append("(the spec declares no capability or impact)")
    for name in spec.impact:
        if name.split(":")[0] == "contract":
            parts += [f"### {name}", "", "(a section of the architecture contract above)", ""]
            continue
        living = _read(project.specs / f"{name}.md").rstrip()
        if living:
            parts += [f"### {name} (.atipspec/specs/{name}.md)", "", living, ""]
        elif name == spec.capability:
            parts += [f"### {name} (.atipspec/specs/{name}.md)", "", "(no living spec yet: this delivery creates it)", ""]
        else:
            parts += [f"### {name}", "", f"(no living spec named {name} in .atipspec/specs/)", ""]
    parts += ["", "## Accepted decisions affecting this delivery", ""]
    decisions = decisions_for(project, spec.impact)
    if not decisions:
        parts.append("(none)")
    for path, meta in decisions:
        parts += [f"### {meta.get('id') or path.stem} ({project.rel(path)})", "", _read(path).rstrip(), ""]
    parts += ["", "## Spec (.atipspec/deliveries/%s/spec.md)" % slug, "", spec_text.rstrip(), ""]
    plan_text = _read(directory / "plan.md")
    plan = parse_plan(plan_text)
    parts += ["## Plan (.atipspec/deliveries/%s/plan.md)" % slug, "", plan_text.rstrip() or "(no plan)", ""]
    deferred = _read(directory / "deferred.md").rstrip()
    parts += ["## Deferred", "", deferred or "(nothing deferred)", ""]

    evidence, problems = load_evidence(directory / "evidence")
    parts += ["## Evidence summary", ""]
    if not evidence:
        parts.append("(no evidence recorded)")
    for task in sorted(evidence, key=lambda ident: 0 if ident == "FINAL" else int(ident[1:])):
        record = evidence[task]
        fresh = "fresh" if project.same_candidate(record.tree, tree) else "stale"
        parts.append(f"- {task}: {record.result} ({fresh}, {record.finished})")
        for command in record.commands:
            parts.append(f"  - `{command.get('command')}` exit {command.get('exit_code')}")
        task_plan = plan.final if task == "FINAL" else next((item for item in plan.tasks if item.id == task), None)
        for ident, proof in (task_plan.proof.items() if task_plan else []):
            from .junit import find, recorded_cases
            case = find(proof, recorded_cases(record.data))
            parts.append(f"  - {ident}: {proof} {case['status'] if case else 'not found in the report'}")
    parts += [problem for problem in problems] + [""]

    git = project.git
    if git.available:
        from .specs import base_problem
        if base_problem(project, spec, slug):
            label = "HEAD (the recorded base is missing or unusable, so committed work is not in this diff)"
            base = None
        else:
            base = spec.meta["base"]
            label = f"base {base[:12]}"
        from .check import outside_scope, touched_files
        from .integration import brought_paths
        from .trust import selected_policy
        found, brought, rebased = (brought_paths(project, slug, base, selected_policy(project)) if base
                                   else (None, set(), set()))
        touched = sorted(set(touched_files(project, base)) - brought | rebased)
        stray = outside_scope(plan, touched, project, base)
        if brought:
            parts += [f"## Brought by {found.ref}", "",
                      "These files changed since the base only as the integration branch changed them, which "
                      "counts them as accepted, as a pull request's diff does, so they are not in the diff below:", ""]
            parts += [f"- {name}" for name in sorted(brought)] + [""]
        parts += ["## Files outside the declared scope", ""]
        if not plan.scope:
            parts.append("(the plan declares no scope)")
        elif not stray:
            parts.append("(none: every changed file matches the plan's scope)")
        else:
            parts += [f"- {name}" for name in stray]
            parts.append("")
            parts.append("The plan did not announce these changes. Judge each one: is it needed by a task, or drift?")
        parts.append("")
        from .verify import harness_files
        harness = harness_files(touched)
        if harness:
            parts += ["## Test harness changed", "",
                      "These files configure how the tests run and report, so a change in them can change what the "
                      "evidence says. Read their diff and judge whether a task needs it:", ""]
            parts += [f"- {name}" for name in harness] + [""]
        diff = git.diff(base, omit=tuple(sorted(brought | rebased)))
        if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
            shown = diff.encode("utf-8")[:MAX_DIFF_BYTES].decode("utf-8", "ignore")
            omitted = len(diff.encode("utf-8")) - len(shown.encode("utf-8"))
            parts += [f"## Diff against {label} (truncated)", "", "```text", git.diff_stat(base).rstrip(), "```", "",
                      "```diff", shown.rstrip(), "```", "",
                      f"{omitted} bytes of diff omitted: the diff exceeds {MAX_DIFF_BYTES} bytes. "
                      "Inspect the repository directly for the files above.", ""]
        else:
            parts += [f"## Diff against {label}", "", "```diff", diff.rstrip() or "(no differences)", "```", ""]
        code = sorted(name for name in rebased if not name.startswith(".atipspec/"))
        if code:
            parts += [f"## Changed by {found.ref} and by this delivery", "",
                      f"{found.ref} changed these files since the base, and this delivery changes them too, or puts "
                      "them back as the base had them, so the diff above leaves them out. Their diff against "
                      f"{found.commit[:12]}, the merge base with {found.ref}, as a pull request shows it: a line this "
                      f"delivery takes back from {found.ref} shows here.", ""]
            parts += [f"- {name}" for name in code]
            merged = git.diff(found.commit, project.fingerprint(), only=tuple(code))
            parts += ["", "```diff", merged.rstrip(), "```", ""]
        untracked = [name for name in git.untracked() if name not in code]
        if untracked:
            parts += ["## Untracked files (not in the diff)", ""]
            total = 0
            for name in untracked:
                path = project.root / name
                try:
                    size = path.stat().st_size
                    if size > MAX_UNTRACKED_BYTES or total + size > MAX_UNTRACKED_TOTAL:
                        parts.append(f"- {name} ({size} bytes, omitted)")
                        continue
                    content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    parts.append(f"- {name} (binary or unreadable, omitted)")
                    continue
                total += size
                parts += [f"### {name}", "", "```", content.rstrip(), "```", ""]
    else:
        parts += ["## Diff", "", "(git unavailable: inspect the repository directly)", ""]
    return "\n".join(parts).rstrip() + "\n"


def write_packet(project: Project, slug: str, packet: str, out: Path | None = None) -> Path:
    path = out or project.tmp / f"{slug}-review-packet.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(packet, encoding="utf-8", newline="\n")
    return path
