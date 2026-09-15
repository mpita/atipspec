"""Contract in the gate, audit, context, curate, decisions, initiatives and worktrees."""
from pathlib import Path
import unittest

from atipspec.audit import audit_project
from atipspec.check import check_delivery
from atipspec.context import build_context
from atipspec.curate import curate_project
from atipspec.project import Project
from tests.helpers import ProjectCase


class ContractGateTests(ProjectCase):
    def test_contract_rules_block_a_delivery(self):
        self.write_contract('forbid-pattern "**/*.py" "import requests"  # use httpx (DEC-001)\n'
                            'require-command "true"\nforbid-path "**/*.js"')
        self.new_delivery()
        self.write_spec()
        self.write_plan("python3 -c pass", "python3 -c pass")
        (self.root / "client.py").write_text("import requests\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("client.py:1" in e and "use httpx" in e for e in report.errors), report.render())
        self.assertTrue(any("verify with `true`" in e for e in report.errors))
        (self.root / "client.py").write_text("import httpx\n")
        self.write_plan("true", "python3 -c pass")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertFalse(report.errors, report.render())
        (self.root / "app.js").write_text("")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("app.js" in e for e in report.errors))

    def test_contract_change_needs_a_decision(self):
        self.write_contract("")
        self.commit("contract")
        self.new_delivery()
        self.write_spec()
        self.write_plan()
        self.write_contract('require-command "true"')
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertEqual(report.status, "draft", "a contract change invalidates the spec's acceptance")
        self.assertTrue(any("changed after the acceptance" in t for t in report.todos))
        self.accept("password-reset", "spec")
        self.accept("password-reset", "plan")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("without a new decision" in e for e in report.errors))
        code, out, _ = self.run_cli("decision", "allow-true", "--title", "Require true", "--affects", "contract")
        self.assertEqual(code, 0)
        self.assertTrue((self.root / ".atipspec/decisions/DEC-001-allow-true.md").is_file())
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("without a new decision" in e for e in report.errors))
        decision = self.root / ".atipspec/decisions/DEC-001-allow-true.md"
        decision.write_text(decision.read_text().replace("status: proposed", "status: accepted"))
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertFalse(any("without a new decision" in e for e in report.errors))
        self.run_cli("decision", "second", "--title", "Second")
        self.assertTrue((self.root / ".atipspec/decisions/DEC-002-second.md").is_file())


class AuditTests(ProjectCase):
    def test_audit_reports_repo_wide_violations_and_overlaps(self):
        project = Project.find(self.root)
        report = audit_project(project)
        self.assertFalse(report.errors, report.render(False))
        self.write_contract('dependencies package.json react\nforbid-path "**/*.js"')
        (self.root / "package.json").write_text('{"dependencies": {"react": "1", "lodash": "1"}}')
        (self.root / "old.js").write_text("")
        self.commit("code")
        self.new_delivery("one")
        self.new_delivery("two")
        report = audit_project(project)
        self.assertTrue(any("'lodash'" in e for e in report.errors))
        self.assertTrue(any("old.js" in e for e in report.errors))
        self.assertTrue(any("one and two both touch auth" in w for w in report.of("warning")))
        (self.root / ".atipspec/decisions/DEC-001-x.md").write_text("---\nstatus: maybe\n---\n")
        report = audit_project(project)
        self.assertTrue(any("status must be one of" in e for e in report.errors))
        code, out, _ = self.run_cli("audit")
        self.assertEqual(code, 1)


class ContextTests(ProjectCase):
    def test_context_loads_only_impacted_material(self):
        project = Project.find(self.root)
        (self.root / ".atipspec/specs").mkdir(exist_ok=True)
        (self.root / ".atipspec/specs/auth.md").write_text("# auth\n\n### Login\n")
        (self.root / ".atipspec/specs/billing.md").write_text("# billing\n\n### Invoices\n")
        (self.root / ".atipspec/specs/reports.md").write_text("# reports\n")
        self.run_cli("decision", "db", "--title", "Use Postgres", "--affects", "contract:stack")
        self.run_cli("decision", "bill", "--title", "Billing rounding", "--affects", "billing")
        self.run_cli("decision", "rep", "--title", "Reports engine", "--affects", "reports")
        for name in ("DEC-001-db", "DEC-002-bill", "DEC-003-rep"):
            path = self.root / f".atipspec/decisions/{name}.md"
            path.write_text(path.read_text().replace("status: proposed", "status: accepted"))
        self.new_delivery("password-reset", "--impact", "billing")
        self.write_spec(impact="[billing]")
        sections, summary = build_context(project, "password-reset")
        labels = [section.label for section in sections]
        self.assertIn("living spec auth (.atipspec/specs/auth.md)", labels)
        self.assertIn("living spec billing (.atipspec/specs/billing.md)", labels)
        self.assertFalse(any("reports" in label for label in labels))
        self.assertIn("decision DEC-001", labels)
        self.assertIn("decision DEC-002", labels)
        self.assertNotIn("decision DEC-003", labels)
        self.assertIn("Context for password-reset:", summary)
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\ncontext_budget: 5\n")
        _, summary = build_context(Project.find(self.root), "password-reset")
        self.assertIn("over budget", summary)
        code, out, _ = self.run_cli("context", "password-reset", "--summary")
        self.assertEqual(code, 0)
        self.assertIn("budget", out)


class CurateAndInitiativeTests(ProjectCase):
    def test_curate_index_and_initiative_status(self):
        project = Project.find(self.root)
        code, out, _ = self.run_cli("initiative", "orders", "--title", "Orders")
        self.assertEqual(code, 0)
        roadmap = self.root / ".atipspec/initiatives/orders/roadmap.md"
        roadmap.write_text(roadmap.read_text().replace("## Interfaces", "- orders-api: API\n- orders-screen: Screen\n\n## Interfaces"))
        code, _, err = self.run_cli("new", "orders-api", "--title", "API", "--initiative", "orders", "--owner", "ana")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.run_cli("new", "x", "--title", "x", "--initiative", "missing")[0], 1)
        self.assertEqual(self.run_cli("new", "orders-mail", "--title", "Mail", "--initiative", "orders")[0], 0)
        text = roadmap.read_text()
        self.assertEqual(text.count("- orders-api: "), 1, "a listed delivery is not duplicated")
        self.assertIn("- orders-screen: Screen\n- orders-mail: Mail\n\n## Interfaces", text)
        report = curate_project(project)
        self.assertEqual(report.status, "done")
        overview = (self.root / ".atipspec/overview.md").read_text()
        self.assertIn("- orders: 0/3 delivered", overview)
        self.assertIn("### Deliveries in progress: 2", overview)
        code, out, _ = self.run_cli("status")
        self.assertIn("- orders 0/3: orders-api draft; orders-screen pending; orders-mail draft", out)
        self.assertIn("@ana", out)
        self.assertIn("contract: not accepted yet", out)

    def test_worktree_creates_sibling_checkout(self):
        code, out, err = self.run_cli("new", "wt", "--title", "Worktree", "--worktree")
        self.assertEqual(code, 0, err)
        sibling = self.root.parent / f"{self.root.name}-wt"
        self.addCleanup(lambda: __import__("shutil").rmtree(sibling, ignore_errors=True))
        self.assertTrue((sibling / ".atipspec/deliveries/wt/spec.md").is_file())
        self.assertFalse((self.root / ".atipspec/deliveries/wt").exists())
        self.assertIn("delivery/wt", self.git("-C", str(sibling), "branch", "--show-current"))
        self.assertIn(f"cd {sibling}", out)


if __name__ == "__main__":
    unittest.main()
