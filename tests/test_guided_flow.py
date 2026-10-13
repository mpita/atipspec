"""Behavioral regressions for the low-ceremony delivery flow."""
import json
import unittest

from atipspec.accept import is_current
from atipspec.check import check_delivery
from atipspec.delivery import load_evidence, parse_plan, parse_spec, parse_review
from atipspec.project import Project
from tests.helpers import GuidedSteps, ProjectCase, python_command


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
        self.assertRegex(req, r"^REQ-CUSTOMER-API-[0-9A-HJKMNP-TV-Z]{5}-001$")
        self.assertEqual(ac, "AC" + req[3:], "a requirement and its first criterion share the token")
        parsed = parse_spec(f"# Customers\n### {req}: Create\n#### {ac}: Success\n- WHEN submitted\n- THEN created\n")
        self.assertEqual(parsed.problems, [])
        self.assertEqual(parsed.criteria[0].requirement, req)

    def test_concurrent_ids_avoid_known_tokens(self):
        from unittest.mock import patch
        from atipspec.traceability import ALPHABET, concurrent_ids
        used, fresh = 0, 1   # tokens 00000 and 00001
        with patch("atipspec.traceability.secrets.randbits", side_effect=[used, fresh]) as draw:
            req, _ = concurrent_ids("auth", {"AC-AUTH-00000-004"})
        self.assertEqual((req, draw.call_count), ("REQ-AUTH-00001-001", 2))
        self.assertEqual(len(ALPHABET), 32)

    def test_long_legacy_concurrent_ids_still_parse(self):
        req = "REQ-PRICING-7DD868F39D6641F888C8A6FA904F36F1-001"
        parsed = parse_spec(f"# Pricing\n### {req}: Price\n#### AC{req[3:]}: Shown\n- WHEN a product opens\n"
                            "- THEN the price is 12.00\n")
        self.assertEqual(parsed.problems, [])
        self.assertEqual(parsed.criteria[0].requirement, req)
        plan = parse_plan(f"### T1: Price\nCovers: {req}\nTests: AC{req[3:]}\nVerify: none\n")
        self.assertEqual(plan.tasks[0].covers, [req])


class GuidedFlowTests(GuidedSteps, ProjectCase):
    def test_two_human_acceptances_and_local_close_without_any_commit(self):
        self.prepare()
        initial_head = self.project.git.head()
        # Effectful commands are executed as written. Sharing is an explicit
        # plan decision, not string-based deduplication of arbitrary commands.
        self.shared_plan(python_command("import os\nos.makedirs('.atipspec/tmp', exist_ok=True)\n"
                                        "open('.atipspec/tmp/count', 'a', encoding='utf-8', newline='\\n').write('run\\n')\n"))
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
        self.assertEqual(self.accept("password-reset", "result", by="human")[0], 0)
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
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)
        self.assertEqual(parse_spec((self.delivery() / "spec.md").read_text()).status, "draft")
        self.assertFalse((self.delivery() / "approvals").exists())

    def test_drift_invalidates_completion_and_final_acceptance(self):
        self.prepare()
        self.shared_plan()
        self.approve()
        self.complete()
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.write_review(self.project.fingerprint())
        self.assertEqual(self.accept("password-reset", "result")[0], 0)
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
        self.assertEqual(self.accept("password-reset", "result")[0], 1)
        self.assertEqual(self.run_cli("deliver", "password-reset")[0], 1)

    def test_manual_cannot_be_passed_off_as_automated(self):
        self.prepare()
        self.shared_plan()
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("- AC-003:", "- AC-003 [manual]:"))
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)

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
        self.assertEqual(self.accept("password-reset", "result")[0], 1)


class IdsCommandTests(ProjectCase):
    def test_ids_cli_prints_short_prefix_and_numbering_hint(self):
        project = Project.find(self.root)
        project.specs.mkdir(parents=True, exist_ok=True)
        (project.specs / "auth.md").write_text("# auth\n\n### REQ-AUTH-00000-001: Sign in\n")
        from unittest.mock import patch
        with patch("atipspec.traceability.secrets.randbits", side_effect=[0, 32 ** 5 - 1]):
            code, out, err = self.run_cli("ids", "auth")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(out.splitlines(), [
            "auth/REQ-AUTH-ZZZZZ-001 auth/AC-AUTH-ZZZZZ-001",
            "Number further requirements and criteria of this delivery with the same prefix: -002, -003."])


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
        (self.delivery() / "plan.md").write_text("""---
scope: ["*", "src/**"]
---
# Plan
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
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        self.assertTrue(is_current(project, "password-reset", "proposal"))
        canonical = project.specs / "auth.md"
        canonical.write_text(canonical.read_text().replace("thirty minutes", "forty minutes"))
        self.assertFalse(is_current(project, "password-reset", "proposal"), "canonical edits invalidate approval")
        self.assertEqual(self.run_cli("build", "password-reset")[0], 1)

    def test_a_draft_names_what_the_proposal_still_lacks_and_the_proposal_shows_every_warning(self):
        self.write_contract('require-command "python -m pytest"')
        self.commit("initialized")
        self.new_delivery()
        project = Project.find(self.root)
        source = project.tmp / "auth-draft.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("# Auth\n### REQ-AUTH-A19F-001: Reject an expired link\n"
                          "The system must reject a link after thirty minutes.\n#### AC-AUTH-A19F-001: Expired link\n"
                          "- **WHEN** the user opens a link issued thirty-one minutes ago\n"
                          "- **THEN** the page displays \"link expired\"\n")
        self.assertEqual(self.run_cli("spec-bind", "password-reset", "--file", str(source))[0], 0)
        tasks = "".join(f"### T{n}: Step {n}\nCovers: REQ-AUTH-A19F-001\n" + ("Tests: AC-AUTH-A19F-001\n" if n == 1 else "")
                        for n in range(1, 10))
        plan = self.delivery() / "plan.md"
        plan.write_text('---\nscope: ["src/**"]\n---\n# Plan\n## Approach\nOne check.\n## Tasks\n' + tasks
                        + "## Final verification\nVerify:\n- `true`\n")
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "draft")
        self.assertIn("contract requires every plan to verify with `python -m pytest` (contract.md line 11)",
                      report.todos, "check names what `proposal` would refuse")
        self.assertIn("9 tasks (policy 8): a delivery should fit in a working day; split it into deliveries under an "
                      "initiative", report.of("warning"))
        plan.write_text(plan.read_text().replace("- `true`", "- `python -m pytest -q`"))
        self.run_cli("decision", "pool", "--title", "Connection pool", "--affects", "contract")
        decision = next(project.decisions.glob("DEC-001-*.md"))
        decision.write_text(decision.read_text().replace("status: proposed", "status: accepted"))
        self.run_cli("decision", "tokens", "--title", "Opaque tokens", "--affects", "auth")
        capability = next(project.decisions.glob("DEC-002-*.md"))
        capability.write_text(capability.read_text().replace("status: proposed", "status: accepted"))
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text().replace("strict_scope: true", "strict_scope: false"))
        code, out, err = self.run_cli("proposal", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Approval code:", out)
        self.assertIn("Policy changes since the base commit, in .atipspec/config.yaml: strict_scope true → false", out)
        self.assertIn("Capability decisions the implementation and the review follow, marked accepted in the "
                      "conversation without a record: DEC-002 (Opaque tokens)", out)
        warnings = out[out.index("Warnings; resolve them, or name each one when presenting:"):out.index("## Change intent")]
        self.assertIn("- 9 tasks (policy 8)", warnings, "the human sees the size before approving")
        self.assertIn("- contract: outdated since its acceptance (DEC-001 new)", warnings,
                      "the approval hashes the contract, so the human sees that it changed")

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


class MessageTests(GuidedSteps, ProjectCase):
    """C12: what the CLI tells the assistant names the files, the steps and the
    stop points of the flow the delivery is in."""

    def living_spec(self, text: str) -> Project:
        project = Project.find(self.root)
        project.specs.mkdir(parents=True, exist_ok=True)
        (project.specs / "auth.md").write_text(text)
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("requirements: []", "requirements: [REQ-AUTH-00000-001]"))
        return project

    def test_new_writes_the_guided_spec_from_the_installed_template(self):
        self.new_delivery()
        text = (self.delivery() / "spec.md").read_text()
        self.assertIn("Requirements and their scenarios live in .atipspec/specs/<capability>.md", text)
        spec = parse_spec(text)
        self.assertEqual((spec.requirements, spec.problems), ([], []))
        self.assertEqual((spec.meta["schema"], spec.meta["requirements"], spec.meta["risk"], spec.capability),
                         (2, [], "normal", "auth"))
        self.assertEqual(spec.title, "Password reset")
        self.assertNotRegex((self.delivery() / "plan.md").read_text(), r"\b(?:REQ|AC)-\d",
                            "the guided plan takes its IDs from the living spec, not from legacy numbering")

    def test_a_guided_draft_points_to_the_living_spec_and_the_proposal(self):
        self.new_delivery()
        text = "\n".join(check_delivery(Project.find(self.root), "password-reset").todos)
        for expected in (".atipspec/specs/auth.md", "`atipspec spec-bind password-reset --file <authored.md>`",
                         "`atipspec accept password-reset proposal --code <code>`"):
            self.assertIn(expected, text)
        for retired in ("### REQ-001", "accept password-reset spec"):
            self.assertNotIn(retired, text)

    def test_a_complete_draft_asks_only_for_the_proposal_s_approval(self):
        self.new_delivery()
        project = Project.find(self.root)
        source = project.tmp / "auth-draft.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("# Auth\n### REQ-AUTH-A19F-001: Reject an expired link\n"
                          "The system must reject a link after thirty minutes.\n#### AC-AUTH-A19F-001: Expired link\n"
                          "- **WHEN** the user opens a link issued thirty-one minutes ago\n"
                          "- **THEN** the page displays \"link expired\"\n")
        self.assertEqual(self.run_cli("spec-bind", "password-reset", "--file", str(source))[0], 0)
        plan = self.delivery() / "plan.md"
        plan.write_text('---\nscope: ["src/**"]\n---\n# Plan\n## Approach\nOne check.\n## Tasks\n'
                        "### T1: Reject the link\nCovers: REQ-AUTH-A19F-001\nTests: AC-AUTH-A19F-001\n"
                        "## Final verification\nVerify:\n- `true`\n")
        approval = ("present `atipspec proposal password-reset` and, after explicit human approval in the "
                    "conversation, record it with `atipspec accept password-reset proposal --code <code>`")
        report = check_delivery(project, "password-reset")
        self.assertEqual((report.status, report.errors), ("draft", []), report.render())
        self.assertEqual(report.todos, ["P" + approval[1:]], "nothing is missing: no generic todo")
        plan.write_text(plan.read_text().replace("Tests: AC-AUTH-A19F-001\n", ""))
        todos = check_delivery(project, "password-reset").todos
        self.assertIn("AC-AUTH-A19F-001: no task lists it under Tests or Manual", todos)
        self.assertIn("Finish the scenarios, approach and tests; " + approval, todos)

    def test_status_of_a_delivery_shows_its_approvals_with_their_channel(self):
        self.prepare()
        self.shared_plan()
        self.approve()
        out = self.run_cli("status", "password-reset")[1]
        accepted = [line for line in out.splitlines() if line.startswith("accepted: ")]
        self.assertTrue(accepted, out)
        self.assertRegex(accepted[-1], r"^accepted: proposal accepted by human at \S+ via assistant \(current\)$")
        project = self.run_cli("status")[1]
        for line in accepted:
            self.assertIn("    " + line, project, "the lines the project's status shows")
        self.assertTrue(out.rstrip().splitlines()[-1].startswith("Next: "), out)

    def test_a_guided_delivery_without_its_schema_line_is_an_error(self):
        self.new_delivery()
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("schema: 2\n", ""))
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertIn("spec.md has a change_id and no `schema: 2`: a guided delivery stays guided; restore the line "
                      "`schema: 2` in its frontmatter", report.errors, report.render())

    def test_a_requirement_without_scenarios_asks_for_one_in_the_living_spec(self):
        self.new_delivery()
        project = self.living_spec("# auth\n\n### REQ-AUTH-00000-001: Sign in\n\nThe user signs in with a password.\n")
        todos = check_delivery(project, "password-reset").todos
        self.assertIn("REQ-AUTH-00000-001 has no acceptance criteria; add a scenario under it in "
                      ".atipspec/specs/auth.md: `#### AC-...: Title` with WHEN and THEN steps", todos)

    def test_a_listed_requirement_the_living_spec_lacks_is_named_not_asked_for(self):
        self.new_delivery()
        project = self.living_spec("# auth\n")
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("REQ-AUTH-00000-001", "REQ-AUTH-ZZZZZ-001"))
        report = check_delivery(project, "password-reset")
        self.assertIn("Unknown canonical requirement auth/REQ-AUTH-ZZZZZ-001", report.errors)
        self.assertFalse([todo for todo in report.todos if todo.startswith("no requirements referenced")],
                         report.render())

    def test_a_problem_in_the_living_spec_names_that_file(self):
        self.new_delivery()
        project = self.living_spec("# auth\n\n### REQ-AUTH-00000-001: Sign in\n\n"
                                   "#### AC-AUTH-00000-001: Password\n- **WHEN** the user signs in\n")
        errors = check_delivery(project, "password-reset").errors
        self.assertIn(".atipspec/specs/auth.md line 5: AC-AUTH-00000-001 scenario needs WHEN and THEN with "
                      "observable outcomes", errors)
        self.assertFalse([error for error in errors if error.startswith("spec.md line")], errors)
        code, out, _ = self.run_cli("audit")
        self.assertEqual(code, 1)
        self.assertIn("specs/auth.md line 5: AC-AUTH-00000-001", out)
        self.assertNotIn("specs/auth.md: spec.md line", out)

    def test_ship_names_the_stop_points_of_the_flow(self):
        self.new_delivery("sign-in")
        out = self.run_cli("ship", "sign-in")[1]
        self.assertIn("stop point 1 follows: the user approves the proposal: behavior, approach and tests\n", out)
        self.prepare()
        self.shared_plan()
        self.approve()
        self.complete()
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.write_review(self.project.fingerprint())
        self.assertEqual(check_delivery(self.project, "password-reset").status, "checked")
        out = self.run_cli("ship", "password-reset")[1]
        self.assertIn("next phase is deliver", out)
        self.assertIn("  the user accepts the reviewed result before it is archived (stop point 2); commit, merge and "
                      "deployment follow the repository's policy", out)
        self.assertNotIn("merges the branch", out)

    def test_task_done_names_its_record_and_the_task_left(self):
        self.prepare()
        self.shared_plan()
        self.approve()
        code, out, err = self.run_cli("task-done", "password-reset", "T1", "--note", "Implemented the link")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), [
            "AtipSpec: T1 of password-reset recorded as implemented (progress, not verification) in "
            ".atipspec/deliveries/password-reset/progress.json",
            "Next: T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`"])

    def test_the_final_verification_is_judged_once_after_the_tasks(self):
        self.prepare()
        self.shared_plan()
        self.approve()
        self.assertEqual(self.run_cli("task-done", "password-reset", "T1", "--note", "Implemented the link")[0], 0)
        report = check_delivery(self.project, "password-reset")
        self.assertEqual([todo for todo in report.todos if todo.startswith("FINAL:")],
                         ["FINAL: no evidence; run `atipspec verify password-reset`"])
        self.assertTrue(report.next_action.startswith("T2 is not complete"), report.render())
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        (self.root / "README.md").write_text("# changed\n")
        stale = [todo for todo in check_delivery(self.project, "password-reset").todos if todo.startswith("FINAL:")]
        self.assertEqual(stale, ["FINAL: evidence is stale (the working tree changed); verify again"])

    def test_accept_without_a_phase_names_the_forms(self):
        self.new_delivery()
        code, _, err = self.run_cli("accept", "password-reset")
        self.assertEqual(code, 1)
        for form in ("`atipspec accept <slug> proposal|result --code <code>`", "(legacy deliveries: spec|plan)",
                     "`atipspec accept contract --code <code>`"):
            self.assertIn(form, err)
