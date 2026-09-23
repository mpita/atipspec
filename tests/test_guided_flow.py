"""Behavioral regressions for the low-ceremony delivery flow."""
import json
import unittest

from atipspec.accept import is_current
from atipspec.check import check_delivery
from atipspec.delivery import load_evidence, parse_plan, parse_spec, parse_review
from atipspec.project import Project
from tests.helpers import ProjectCase


class ScenarioTests(unittest.TestCase):
    def test_scenario_normalizes_steps_preserves_source_and_method(self):
        source = """# Navegación
### REQ-NAV-A1B2-001: Acceso a herramientas
El portal DEBE ofrecer acceso a Herramientas.
#### AC-NAV-A1B2-001 [manual]: Navegar desde el inicio
- **DADO** un empleado en Inicio
- **CUANDO** selecciona Herramientas
- **ENTONCES** accede a `/herramientas`
- **Y** ve el título esperado
"""
        spec = parse_spec(source)
        self.assertEqual(spec.problems, [])
        criterion = spec.criteria[0]
        self.assertEqual(criterion.method, "manual")
        self.assertEqual(criterion.requirement, "REQ-NAV-A1B2-001")
        self.assertEqual([word for word, _ in criterion.steps], ["GIVEN", "WHEN", "THEN", "AND"])
        self.assertIn("#### AC-NAV-A1B2-001 [manual]", "\n".join(spec.requirements[0].body))
        self.assertIn("When selecciona", criterion.text)
        plan = parse_plan("### T1: Link\nCovers: REQ-NAV-A1B2-001\nManual: AC-NAV-A1B2-001\nVerify: none\n")
        self.assertEqual(plan.tasks[0].manual, [criterion.id])
        self.assertEqual(parse_review("- AC-NAV-A1B2-001: PASS. Browser").verdicts[criterion.id][0], "PASS")

    def test_when_then_without_given_is_valid(self):
        spec = parse_spec("# S\n### REQ-001: S\n#### AC-001: Action\n- **WHEN** clicked\n- **THEN** opens\n")
        self.assertFalse(spec.problems)

    def test_incomplete_and_reversed_scenarios_are_errors(self):
        for steps in ("- WHEN clicked", "- THEN opens\n- WHEN clicked", "- WHEN\n- THEN opens", "- AND first\n- WHEN clicked\n- THEN opens"):
            with self.subTest(steps=steps):
                self.assertTrue(parse_spec("# S\n### REQ-001: S\n#### AC-001: Action\n" + steps).problems)

    def test_orphan_scenario_and_unmarked_prose_are_errors(self):
        self.assertTrue(parse_spec("# S\n#### AC-001: Action\n- WHEN x\n- THEN y").problems)
        self.assertTrue(parse_spec("# S\n### REQ-001: S\n#### AC-001: Action\nJust a title").problems)

    def test_invariants_do_not_need_fake_actions(self):
        spec = parse_spec("# S\n### REQ-001: Isolation\n#### AC-001 [invariant]: Tenant boundary\n- INVARIANT every returned record belongs to the active tenant\n")
        self.assertEqual(spec.problems, [])
        self.assertEqual(spec.criteria[0].form, "invariant")

    def test_concurrent_ids_parse_without_a_shared_counter(self):
        from atipspec.traceability import concurrent_ids
        one, two = concurrent_ids("customer-api"), concurrent_ids("customer-api")
        self.assertNotEqual(one, two)
        req, ac = one
        parsed = parse_spec(f"# Customers\n### {req}: Create\n#### {ac}: Success\n- WHEN submitted\n- THEN created\n")
        self.assertEqual(parsed.problems, [])
        self.assertEqual(parsed.criteria[0].requirement, req)


class GuidedFlowTests(ProjectCase):
    def prepare(self):
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        self.write_plan(accept=False)
        self.project = Project.find(self.root)

    def shared_plan(self, command="true"):
        path = self.delivery() / "plan.md"
        path.write_text("""# Plan
## Tasks
### T1: Request link
Covers: REQ-001
Tests: AC-001, AC-002
### T2: Expiry
Covers: REQ-002
Tests: AC-003
## Final verification
Verify:
- `""" + command + "`\n")

    def approve(self):
        code, out, err = self.run_cli("accept", "password-reset", "proposal", "--by", "human")
        self.assertEqual(code, 0, out + err)

    def complete(self):
        for task in ("T1", "T2"):
            code, out, err = self.run_cli("task-done", "password-reset", task, "--note", "Implemented the approved behavior")
            self.assertEqual(code, 0, out + err)

    def test_two_human_acceptances_and_local_close_without_any_commit(self):
        self.prepare()
        initial_head = self.project.git.head()
        # Effectful commands are executed as written. Sharing is an explicit
        # plan decision, not string-based deduplication of arbitrary commands.
        self.shared_plan("mkdir -p .atipspec/tmp; echo run >> .atipspec/tmp/count")
        self.approve()
        self.complete()
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.assertEqual((self.project.tmp / "count").read_text(), "run\n")
        evidence, problems = load_evidence(self.delivery() / "evidence")
        self.assertEqual(set(evidence), {"FINAL"})
        self.assertEqual(problems, [])
        self.assertEqual(self.run_cli("review", "password-reset")[0], 0)
        self.write_review(self.project.fingerprint())
        report = check_delivery(self.project, "password-reset")
        self.assertEqual((report.status, report.tasks_done, report.exit_code), ("checked", 2, 0), report.render())
        code, _, err = self.run_cli("deliver", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("accept the current result", err)
        self.assertEqual(self.run_cli("accept", "password-reset", "result", "--by", "human")[0], 0)
        self.assertEqual(check_delivery(self.project, "password-reset").status, "accepted")
        code, out, err = self.run_cli("deliver", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.project.git.head(), initial_head)
        self.assertEqual(len(parse_spec((self.project.specs / "auth.md").read_text()).requirements), 2)
        receipt = json.loads((self.project.archive / "password-reset/reports/acceptance.json").read_text())
        self.assertTrue(receipt["accepted"])
        self.assertFalse(receipt["authenticated"])
        self.assertEqual(receipt["acceptance_mode"], "local")
        self.assertTrue(all(row["verification"][0]["evidence"].startswith("FINAL-") for row in receipt["matrix"]))

    def test_proposal_with_invalid_plan_writes_no_partial_acceptance(self):
        self.prepare()
        path = self.delivery() / "plan.md"
        path.write_text(path.read_text().replace("Covers: REQ-002", "Covers: REQ-999"))
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal")[0], 1)
        self.assertEqual(parse_spec((self.delivery() / "spec.md").read_text()).status, "draft")
        self.assertFalse((self.delivery() / "approvals").exists())

    def test_drift_invalidates_completion_and_final_acceptance(self):
        self.prepare()
        self.shared_plan()
        self.approve()
        self.complete()
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.write_review(self.project.fingerprint())
        self.assertEqual(self.run_cli("accept", "password-reset", "result")[0], 0)
        (self.root / "README.md").write_text("new behavior")
        self.assertFalse(is_current(self.project, "password-reset", "result"))
        self.assertEqual(self.run_cli("deliver", "password-reset")[0], 1)
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text().replace("`true`", "`false`"))
        self.assertFalse(is_current(self.project, "password-reset", "proposal"))
        self.approve()
        self.assertEqual(check_delivery(self.project, "password-reset").tasks_done, 0)

    def test_failed_shared_check_blocks_every_task_and_acceptance(self):
        self.prepare()
        self.shared_plan("false")
        self.approve()
        self.complete()
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 1)
        self.write_review(self.project.fingerprint())
        self.assertEqual(self.run_cli("accept", "password-reset", "result")[0], 1)
        self.assertEqual(self.run_cli("deliver", "password-reset")[0], 1)

    def test_manual_cannot_be_passed_off_as_automated(self):
        self.prepare()
        self.shared_plan()
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("- AC-003:", "- AC-003 [manual]:"))
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal")[0], 1)

    def test_shared_check_does_not_use_targeted_development_evidence(self):
        self.prepare()
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text() + "\n## Final verification\nVerify:\n- `false`\n")
        self.approve()
        self.complete()
        self.assertEqual(self.run_cli("verify", "password-reset", "--task", "T1")[0], 0)
        self.write_review(self.project.fingerprint())
        report = check_delivery(self.project, "password-reset")
        self.assertTrue(any("FINAL: no evidence" in item for item in report.todos), report.render())
        self.assertEqual(self.run_cli("accept", "password-reset", "result")[0], 1)


class CanonicalFlowTests(ProjectCase):
    def test_requirement_lives_in_specs_before_approval_and_is_bound_by_it(self):
        self.new_delivery()
        project = Project.find(self.root)
        self.assertFalse(list(project.specs.glob("*.md")), "do not scaffold empty capabilities")
        source = project.tmp / "auth-draft.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("""# Auth
### REQ-AUTH-A19F-001: Reject an expired link
The system must reject a link after thirty minutes.
#### AC-AUTH-A19F-001: Expired link
- **GIVEN** a link issued thirty-one minutes ago
- **WHEN** the user opens the link
- **THEN** the page displays "link expired"
""")
        code, out, err = self.run_cli("spec-bind", "password-reset", "--file", str(source))
        self.assertEqual(code, 0, out + err)
        self.assertIn("link expired", (project.specs / "auth.md").read_text())
        self.assertNotIn("link expired", (self.delivery() / "spec.md").read_text())
        code, out, err = self.run_cli("plan", "password-reset", "--no-context")
        self.assertEqual(code, 0, out + err)
        (self.delivery() / "plan.md").write_text("""# Plan
### T1: Validate expiration
Covers: REQ-AUTH-A19F-001
Tests: AC-AUTH-A19F-001
## Final verification
Verify:
- `true`
""")
        code, out, err = self.run_cli("proposal", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn('+The system must reject', out)
        self.assertIn("link expired", out)
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal")[0], 0)
        self.assertTrue(is_current(project, "password-reset", "proposal"))
        canonical = project.specs / "auth.md"
        canonical.write_text(canonical.read_text().replace("thirty minutes", "forty minutes"))
        self.assertFalse(is_current(project, "password-reset", "proposal"), "canonical edits invalidate approval")
        self.assertEqual(self.run_cli("build", "password-reset")[0], 1)

    def test_incomplete_import_has_no_partial_writes(self):
        self.new_delivery()
        project = Project.find(self.root)
        original = (self.delivery() / "spec.md").read_bytes()
        source = project.tmp / "bad.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("# Auth\n### REQ-001: Incomplete\n#### AC-001: Only action\n- WHEN x\n")
        self.assertEqual(self.run_cli("spec-bind", "password-reset", "--file", str(source))[0], 1)
        self.assertFalse((project.specs / "auth.md").exists())
        self.assertEqual((self.delivery() / "spec.md").read_bytes(), original)
