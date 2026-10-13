"""Repository-wide audit: contract rules over every file, validity and size of
the living documents, decisions, initiatives and overlapping deliveries."""
from __future__ import annotations

from .specs import load_spec

from . import frontmatter
from .check import Report, load_contract
from .contract import evaluate
from .delivery import parse_roadmap, parse_spec
from .locale import LANGUAGES, code as language_code
from .project import Project

SIZE_CAPS = {"overview.md": 150, "glossary.md": 300, "contract.md": 400}
# What projects that keep a strict policy off let through.
STRICT = {"strict_scope": "a plan may omit its scope and a file outside it is only a warning",
          "strict_criteria": "a vague requirement or criterion, a criterion outside the EARS form, or a quality "
                             "attribute without a number is only a warning"}
LIVING_SPEC_CAP = 400
DECISION_STATUSES = ("proposed", "accepted", "superseded", "rejected")


def repository_files(project: Project) -> list[str]:
    git = project.git
    if git.available:
        names = set(git.tracked()) | set(git.untracked(include_atipspec=True))
    else:
        names = set()
        for path in project.root.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                names.add(project.rel(path))
    return sorted(name for name in names
                  if not name.startswith((".atipspec/archive/", ".atipspec/tmp/")) and (project.root / name).exists())


def audit_project(project: Project) -> Report:
    report = Report("project")
    from .install import framework_problem
    if problem := framework_problem(project.root, project.git):
        report.add("error", problem)
    for key, what in STRICT.items():
        if project.config.get(key) is False:
            report.add("info", f"config.yaml sets {key}: false: {what}; projects created since 0.3.0 default to true")
    if language_code(project.language) is None:
        report.add("warning", f"language {project.language!r} has no tables: criteria get the English vague-term list "
                              f"and no form check, and the dossier is in English (supported: {', '.join(LANGUAGES)})")
    contract = load_contract(project)
    if not project.contract.is_file():
        report.add("warning", "no contract.md: run the contract phase to define the architecture rules")
    for problem in contract.problems:
        report.add("error", problem)
    if not contract.rules and project.contract.is_file():
        report.add("info", "contract.md has no machine-checked rules yet (```rules block)")
    files = repository_files(project)
    source_files = [name for name in files if not name.startswith(".atipspec/")]
    for violation in evaluate(contract, project.root, source_files, manifests_always=True):
        report.add("error", f"contract: {violation.render()}")

    for name in project.list_capabilities():
        path = project.specs / f"{name}.md"
        text = path.read_text(encoding="utf-8")
        spec = parse_spec(text, f"specs/{name}.md")
        for problem in spec.problems:
            report.add("error", problem)
        lines = text.count("\n")
        if lines > LIVING_SPEC_CAP:
            report.add("warning", f"specs/{name}.md has {lines} lines; consider splitting the capability")
    for filename, cap in SIZE_CAPS.items():
        path = project.dot / filename
        if path.is_file():
            lines = path.read_text(encoding="utf-8").count("\n")
            if lines > cap:
                report.add("warning", f"{filename} has {lines} lines (cap {cap}); run the curate phase")

    for path in project.list_decisions():
        try:
            meta, _ = frontmatter.split(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            report.add("error", f"decisions/{path.name}: {exc}")
            continue
        if meta.get("status") not in DECISION_STATUSES:
            report.add("error", f"decisions/{path.name}: status must be one of {', '.join(DECISION_STATUSES)}")
    from .accept import contract_acceptance, describe_contract
    if contract_acceptance(project).state in ("unrecorded", "outdated"):
        report.add("warning", f"contract: {describe_contract(project)}")
    from .integration import unshared_default
    if warning := unshared_default(project):
        report.add("warning", warning)

    from .install import (CLIENTS, PERMISSION_RULES, installed_clients, missing_permission_rules,
                          permission_overrides, permission_rules_state)
    installed = installed_clients(project.root)
    for key in installed:
        rules = PERMISSION_RULES.get(key)
        if rules is None:
            continue
        state = permission_rules_state(project.root, key)
        overrides = permission_overrides(project.root, key)
        if state == "installed" and overrides:
            report.add("warning", f"{CLIENTS[key].label}: {'; '.join(overrides)}, so the client may run `atipspec "
                                  "accept` without asking the human and acceptances are recorded as channel assistant")
        elif state != "installed":
            absent = missing_permission_rules(project.root, key)
            named = f" (without {', '.join(absent)})" if state == "partial" and absent else ""
            report.add("warning", f"{CLIENTS[key].label}: the AtipSpec permission rules in {rules.settings} are "
                                  f"{state}{named}, so the client neither asks the human nor stops where a missing "
                                  "rule would, and acceptances are recorded as channel assistant; run `atipspec "
                                  "install --update`")
    others = [CLIENTS[key].label for key in installed if key not in PERMISSION_RULES]
    if others:
        report.add("info", f"{', '.join(others)}: no permission rules AtipSpec can install; their acceptances are "
                           "recorded as channel assistant")

    active: dict[str, list[str]] = {}
    for slug in project.list_deliveries():
        spec = load_spec(project, slug)
        active[slug] = spec.impact
    slugs = list(active)
    for index, first in enumerate(slugs):
        for second in slugs[index + 1:]:
            shared = sorted(set(active[first]) & set(active[second]))
            if shared:
                report.add("warning", f"deliveries {first} and {second} both touch {', '.join(shared)}; coordinate them")

    known = set(project.list_deliveries()) | set(project.list_archived())
    for name in project.list_initiatives():
        roadmap = parse_roadmap((project.initiatives / name / "roadmap.md").read_text(encoding="utf-8"))
        for problem in roadmap.problems:
            report.add("error", f"initiatives/{name}: {problem}")
        pending = [slug for slug, _ in roadmap.deliveries if slug not in known]
        if pending:
            report.add("info", f"initiative {name}: {len(pending)} delivery(ies) not started: {', '.join(pending)}")
    report.status = "clean" if not report.errors else "violations"
    return report
