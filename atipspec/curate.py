"""Keep the living documents small. The CLI regenerates the mechanical index in
overview.md and reports sizes; the curate workflow rewrites the prose."""
from __future__ import annotations

from .specs import load_spec

from . import frontmatter
from .audit import SIZE_CAPS
from .check import Report, check_delivery
from .delivery import parse_roadmap, parse_spec
from .deliver import split_sections
from .project import Project, template

INDEX_START = "<!-- atipspec:index -->"
INDEX_END = "<!-- /atipspec:index -->"


def build_index(project: Project) -> str:
    lines = [INDEX_START, "", "### Capabilities", ""]
    capabilities = project.list_capabilities()
    for name in capabilities:
        _, sections = split_sections((project.specs / f"{name}.md").read_text(encoding="utf-8"))
        lines.append(f"- {name}: {len(sections)} requirement(s)")
    if not capabilities:
        lines.append("- none yet")
    lines += ["", "### Accepted decisions", ""]
    count = 0
    for path in project.list_decisions():
        try:
            meta, _ = frontmatter.split(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if meta.get("status") == "accepted":
            lines.append(f"- {meta.get('id') or path.stem}: {meta.get('title') or ''}")
            count += 1
    if not count:
        lines.append("- none yet")
    lines += ["", "### Initiatives", ""]
    initiatives = project.list_initiatives()
    archived = set(project.list_archived())
    for name in initiatives:
        roadmap = parse_roadmap((project.initiatives / name / "roadmap.md").read_text(encoding="utf-8"))
        done = sum(1 for slug, _ in roadmap.deliveries if slug in archived)
        lines.append(f"- {name}: {done}/{len(roadmap.deliveries)} delivered")
    if not initiatives:
        lines.append("- none")
    lines += ["", f"### Deliveries in progress: {len(project.list_deliveries())}", "", INDEX_END]
    return "\n".join(lines)


def curate_project(project: Project) -> Report:
    report = Report("curate")
    for path, name in ((project.overview, "overview.md"), (project.glossary, "glossary.md")):
        if not path.is_file():
            path.write_text(template(name).replace("{{name}}", project.name), encoding="utf-8")
            report.add("info", f"created .atipspec/{name} from the template")
    text = project.overview.read_text(encoding="utf-8")
    index = build_index(project)
    start, end = text.find(INDEX_START), text.find(INDEX_END)
    if start != -1 and end != -1:
        text = text[:start] + index + text[end + len(INDEX_END):]
    else:
        text = text.rstrip() + "\n\n## Index\n\n" + index + "\n"
    project.overview.write_text(text, encoding="utf-8")
    report.add("info", "overview.md index regenerated")
    for filename, cap in SIZE_CAPS.items():
        path = project.dot / filename
        if path.is_file():
            lines = path.read_text(encoding="utf-8").count("\n")
            level = "warning" if lines > cap else "info"
            report.add(level, f"{filename}: {lines} lines (cap {cap})")
    for slug in project.list_deliveries():
        spec = load_spec(project, slug)
        for name in spec.impact:
            if not (project.specs / f"{name}.md").is_file():
                report.add("info", f"{slug} names {name!r} in its impact but there is no living spec for it yet")
    report.status = "done"
    return report
