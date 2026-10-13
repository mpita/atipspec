"""Importing acceptance-criteria documents, and migrating legacy deliveries."""
import json
import re

from atipspec.accept import is_current
from atipspec.delivery import parse_spec
from atipspec.frontmatter import split
from atipspec.migration import _ident
from atipspec.project import Project
from tests.helpers import ProjectCase

SHORT = r"REQ-AUTH-[0-9A-HJKMNP-TV-Z]{5}-001"

CRITERIA = """# Export orders

## Intent

An accountant exports the month's orders.

## Acceptance Criteria

1. **GIVEN** orders in March **WHEN** the accountant exports March **THEN** the file lists 12 orders
2. The system shall name the file "orders-2026-03.csv".
"""


class ImportTests(ProjectCase):
    def bind(self, text, name="source.md", expect=0):
        project = Project.find(self.root)
        source = self.root / name
        source.write_text(text)
        code, out, err = self.run_cli("spec-bind", "password-reset", "--file", str(source))
        self.assertEqual(code, expect, out + err)
        return project, out, err

    def meta(self):
        return split((self.delivery() / "spec.md").read_text())[0]

    def test_spec_bind_imports_acceptance_criteria_document(self):
        self.new_delivery()
        project, out, _ = self.bind(CRITERIA)
        self.assertIn("Imported from acceptance criteria", out)
        living = (project.specs / "auth.md").read_text()
        spec = parse_spec(living)
        self.assertEqual([req.title for req in spec.requirements], ["Export orders"])
        self.assertEqual(sorted(criterion.form for criterion in spec.criteria), ["scenario", "statement"])
        self.assertEqual(spec.problems, [])
        ids = re.findall(SHORT, living)
        self.assertEqual(len(ids), 1)
        meta = self.meta()
        self.assertEqual(meta["requirements"], ids)
        source = meta["sources"][0]
        self.assertRegex(source, r"^\.atipspec/deliveries/password-reset/sources/[0-9a-f]{64}\.md$")
        self.assertEqual((self.root / source).read_text(), CRITERIA)
        text = (self.delivery() / "spec.md").read_text()
        self.assertEqual(text.count("## Import review notes"), 1)
        self.assertIn("Only explicit acceptance criteria were converted", text)
        self.bind(CRITERIA)
        self.assertEqual(re.findall(SHORT, (project.specs / "auth.md").read_text()), ids, "the same source, the same IDs")
        self.assertEqual((self.delivery() / "spec.md").read_text().count("## Import review notes"), 1)
        proposal = self.run_cli("proposal", "password-reset")[1]
        self.assertIn(f"+### {ids[0]}: Export orders", proposal)
        self.assertIn("## Import review notes", proposal)
        tests = ", ".join(criterion.id for criterion in spec.criteria)
        (self.delivery() / "plan.md").write_text(f"---\nscope: [\"src/**\"]\n---\n# Plan\n### T1: Export\n"
                                                 f"Covers: {ids[0]}\nTests: {tests}\n## Final verification\n"
                                                 "Verify:\n- `true`\n")
        code, out, err = self.accept("password-reset", "proposal")
        self.assertEqual(code, 0, out + err)

    def test_an_inline_acceptance_heading_is_recognized(self):
        self.new_delivery()
        project, out, _ = self.bind("# Export orders\n\n**Acceptance Criteria:**\n\n"
                                    "- **WHEN** the accountant exports March **THEN** the file lists 12 orders\n")
        self.assertIn("Imported from acceptance criteria", out)
        spec = parse_spec((project.specs / "auth.md").read_text())
        self.assertEqual([criterion.form for criterion in spec.criteria], ["scenario"])

    def test_generated_id_collision_with_different_title_is_refused(self):
        self.new_delivery()
        project = Project.find(self.root)
        project.specs.mkdir(parents=True, exist_ok=True)
        clash = _ident("REQ", "auth", "Export orders")
        living = (f"# auth\n\n## Requirements\n\n### {clash}: Session timeout\n\n"
                  f"#### AC-AUTH-00000-001: Idle\n- WHEN idle for an hour\n- THEN the page shows \"Signed out\"\n")
        (project.specs / "auth.md").write_text(living)
        _, _, err = self.bind(CRITERIA, expect=1)
        self.assertIn("A generated ID already names another requirement", err)
        self.assertIn("'Session timeout' there, 'Export orders' here", err)
        self.assertEqual((project.specs / "auth.md").read_text(), living)

    def test_a_document_without_requirements_or_criteria_is_refused_without_writes(self):
        self.new_delivery()
        before = (self.delivery() / "spec.md").read_text()
        _, _, err = self.bind("# Notes\n\nSome thoughts.\n", expect=1)
        self.assertIn("No supported requirements or acceptance section found", err)
        self.assertIn("criteria under an Acceptance Criteria heading", err)
        self.assertFalse((self.root / ".atipspec/specs/auth.md").exists())
        self.assertEqual((self.delivery() / "spec.md").read_text(), before)
        self.assertFalse((self.delivery() / "sources").exists())


class MigrateTests(ProjectCase):
    def legacy(self):
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        self.commit("legacy delivery")
        return Project.find(self.root)

    def test_migrate_preview_writes_nothing(self):
        self.legacy()
        before = self.git("status", "--porcelain")
        code, out, err = self.run_cli("migrate", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn("migration preview for password-reset", out)
        self.assertIn("+### REQ-001: The user can request a reset link", out)
        self.assertIn("Nothing written. Apply with `atipspec migrate password-reset --apply`", out)
        self.assertEqual(self.git("status", "--porcelain"), before)

    def test_migrate_apply_backs_up_and_returns_to_draft(self):
        project = self.legacy()
        original = (self.delivery() / "spec.md").read_text()
        code, out, err = self.run_cli("migrate", "password-reset", "--apply")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Next: `atipspec proposal password-reset`", out)
        backups = list((project.dot / "migrations").glob("*/originals/.atipspec/deliveries/password-reset/spec.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        meta, body = split((self.delivery() / "spec.md").read_text())
        self.assertEqual((meta["schema"], meta["status"], meta["requirements"]), (2, "draft", ["REQ-001", "REQ-002"]))
        self.assertNotIn("## Requirements", body)
        self.assertIn("## Out of scope", body)
        self.assertIn("### REQ-001: The user can request a reset link", (project.specs / "auth.md").read_text())
        self.assertFalse(is_current(project, "password-reset", "proposal"))
        self.assertIn("[draft]", self.run_cli("check", "password-reset")[1])
        code, _, err = self.run_cli("migrate", "password-reset", "--apply")
        self.assertEqual(code, 1)
        self.assertIn("already uses canonical specifications", err)

    def test_migrate_refuses_fix_deliveries(self):
        self.legacy()
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("capability: auth", "capability: auth\nkind: fix"))
        code, _, err = self.run_cli("migrate", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("A legacy fix keeps its legacy flow", err)
        self.assertFalse((Project.find(self.root).dot / "migrations").exists())
        self.assertEqual(json.loads(json.dumps(split(spec.read_text())[0])).get("schema"), None)
