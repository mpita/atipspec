"""End-to-end: new, spec, plan, verify, commit, review, check, deliver."""
import json
from pathlib import Path
import unittest

from atipspec.deliver import merge_requirements
from atipspec.delivery import parse_spec
from atipspec.check import check_delivery
from atipspec.project import Project
from tests.helpers import SPEC, ProjectCase


class FlowTests(ProjectCase):
    def test_gate_progresses_from_draft_to_deliver(self):
        self.new_delivery()
        project = Project.find(self.root)
        code, out, _ = self.run_cli("check", "password-reset")
        self.assertEqual(code, 2)
        self.assertIn("[draft]", out)

        self.write_spec(status="ready", question="How long?")
        self.assertEqual(self.run_cli("check", "password-reset")[0], 1)
        self.write_spec(status="ready", accept=False)
        code, out, _ = self.run_cli("check", "password-reset")
        self.assertEqual((code, check_delivery(project, "password-reset").status), (2, "draft"),
                         "a hand-written ready status is not an acceptance")
        self.assertIn("request human confirmation in the conversation", out)
        self.assertIn("`atipspec accept password-reset spec`", out)
        self.assertEqual(self.accept()[0], 0)
        code, out, _ = self.run_cli("check", "password-reset")
        self.assertEqual((code, check_delivery(project, "password-reset").status), (2, "ready"))
        self.assertIn("Write plan.md", out)

        self.write_plan("python3 -c \"open('a.txt').read()\"", "true")
        report = check_delivery(project, "password-reset")
        self.assertEqual((report.status, report.tasks_total, report.tasks_done), ("planned", 2, 0))
        self.assertFalse(any("Tests or Manual" in t for t in report.todos), "every criterion is mapped")

        (self.root / "a.txt").write_text("hello")
        code, out, _ = self.run_cli("verify", "password-reset", "--task", "T1")
        self.assertEqual(code, 0, out)
        evidence = list((self.delivery() / "evidence").glob("T1-*.json"))
        self.assertEqual(len(evidence), 1)
        record = json.loads(evidence[0].read_text())
        self.assertEqual((record["result"], record["commands"][0]["exit_code"]), ("pass", 0))
        self.assertEqual(record["tree"], project.fingerprint(), "writing evidence must not change the fingerprint")

        self.commit("feat: request link [password-reset:T1]")
        report = check_delivery(project, "password-reset")
        self.assertEqual((report.status, report.tasks_done), ("in_progress", 1))
        self.assertFalse([t for t in report.todos if "T1" in t], "committed T1 with fresh evidence needs nothing")

        self.assertEqual(self.run_cli("verify", "password-reset", "--task", "T2")[0], 0)
        self.commit("feat: expiry [password-reset:T2]")
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "implemented")
        self.assertEqual(len(report.todos), 1)
        self.assertIn("No review.md", report.todos[0])

        code, out, _ = self.run_cli("review", "password-reset")
        self.assertEqual(code, 0)
        packet = (self.root / ".atipspec/tmp/password-reset-review-packet.md").read_text()
        self.assertIn(f"tree: {report.fingerprint}", packet)
        self.assertIn("+hello", packet)
        self.assertIn("## Architecture contract", packet)
        self.assertIn("## Evidence summary", packet)
        self.assertEqual(self.git("status", "--porcelain").strip(), "", "the packet must be ignored by git")

        self.write_review(report.fingerprint, v3="FAIL", findings="- F1 [blocker]: token reuse\n- F2 [minor]: typo")
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.exit_code, 1)
        self.assertTrue(any("AC-003 FAIL" in e for e in report.errors))
        self.assertTrue(any("F1 [blocker]" in e for e in report.errors))

        (self.delivery() / "deferred.md").write_text("# Deferred\n\n- F1: handled in change/single-use\n- AC-003: never\n")
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("AC-003 cannot be deferred" in e for e in report.errors))

        (self.delivery() / "deferred.md").write_text("# Deferred\n\n- F1: handled in change/single-use\n")
        self.write_review(report.fingerprint, findings="- F1 [blocker]: token reuse\n- F2 [minor]: typo")
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.exit_code, 1, "An unsigned deferral cannot unblock the gate")
        self.write_review(report.fingerprint)
        (self.delivery() / "deferred.md").write_text("# Deferred\n")
        report = check_delivery(project, "password-reset")
        self.assertEqual((report.exit_code, report.status), (0, "checked"), report.render())

        (self.root / "a.txt").write_text("changed")
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "implemented")
        self.assertTrue(any("stale" in t for t in report.todos))
        self.assertEqual(self.run_cli("deliver", "password-reset")[0], 1)
        (self.root / "a.txt").write_text("hello")

        code, out, err = self.run_cli("deliver", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("accept the current result", err)
        self.assertTrue(self.delivery().exists())

    def test_verify_records_failures_and_unknown_tasks(self):
        self.new_delivery()
        self.write_spec()
        self.write_plan("false", "true")
        code, out, _ = self.run_cli("verify", "password-reset", "--task", "T1")
        self.assertEqual(code, 1)
        self.assertIn("T1: fail", out)
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("last verification failed" in e for e in report.errors))
        code, _, err = self.run_cli("verify", "password-reset", "--task", "T9")
        self.assertEqual(code, 1)
        self.assertIn("Unknown task", err)

    def test_plan_errors_are_reported(self):
        self.new_delivery()
        self.write_spec()
        (self.delivery() / "plan.md").write_text("# Plan\n\n### T1: Only one\n\nCovers: REQ-001, REQ-009\nVerify: none\n\n### T1: Dup\n\nCovers: REQ-002\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("REQ-009" in e for e in report.errors))
        self.assertTrue(any("duplicate task id T1" in e for e in report.errors))
        self.assertTrue(any("no Verify commands" in w for w in report.of("warning")))

    def test_size_and_age_policies_warn_without_blocking(self):
        from atipspec.status import age_hours, created_at, format_age
        self.assertEqual(format_age(7.9), "7h")
        self.assertEqual(format_age(31.9), "1d 7h")
        self.assertEqual(format_age(76), "3d 4h")
        self.assertIsNone(created_at(None))
        self.assertEqual(created_at("2026-09-12").isoformat(), "2026-09-12T00:00:00+00:00")
        self.assertEqual(created_at("2026-09-12T10:00:00Z").hour, 10)
        self.new_delivery()
        spec = self.delivery() / "spec.md"
        self.assertRegex(spec.read_text(), r"created: \"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\"")
        self.write_spec()
        extra = "".join(f"\n### REQ-00{n}: Requirement {n}\n\nAcceptance criteria:\n- AC-00{n}: When x, the system does y.\n" for n in range(3, 9))
        spec.write_text(spec.read_text().replace("## Out of scope", extra + "\n## Out of scope"))
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("8 requirements (policy 5)" in w for w in report.of("warning")), report.render())
        spec.write_text(spec.read_text().replace("status: ready", "status: draft"))
        self.assertFalse(any("requirements (policy" in w for w in check_delivery(project, "password-reset").of("warning")),
                         "a draft is still being written; the size warning starts at ready")
        spec.write_text(spec.read_text().replace("status: draft", "status: ready"))
        self.assertFalse(any("requirements (policy" in e for e in report.errors))
        self.write_spec()
        tasks = "".join(f"\n### T{n}: Task {n}\n\nCovers: REQ-002\nTests: AC-003\nVerify:\n- `true`\n" for n in range(3, 12))
        plan = self.delivery() / "plan.md"
        self.write_plan(accept=False)
        plan.write_text(plan.read_text() + tasks)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("11 tasks (policy 8)" in w for w in report.of("warning")), report.render())
        spec.write_text(spec.read_text().replace(spec.read_text().split("created: ")[1].split("\n")[0], "2026-01-01T09:00:00Z"))
        code, out, _ = self.run_cli("status")
        self.assertIn("open for", out)
        self.assertIn("(policy 48h); finish it or split it", out)
        self.assertRegex(out, r"password-reset \[[a-z_]+\].*, open \d+d \d+h: Password reset")
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\nmax_age_hours: 1000000\n")
        code, out, _ = self.run_cli("status")
        self.assertNotIn("finish it or split it", out)
        spec.write_text(spec.read_text().replace("2026-01-01T09:00:00Z", "garbage"))
        self.assertIn("created unreadable", self.run_cli("status")[1])

    def test_new_validates_slug_and_records_base(self):
        code, _, err = self.run_cli("new", "Bad_Slug", "--title", "x")
        self.assertEqual(code, 1)
        self.assertIn("Invalid slug", err)
        self.new_delivery()
        spec = parse_spec((self.delivery() / "spec.md").read_text())
        self.assertEqual(spec.meta["base"], self.git("rev-parse", "HEAD").strip())
        self.assertEqual(spec.meta["status"], "draft")
        self.assertEqual(spec.title, "Password reset")
        self.assertEqual(self.run_cli("new", "password-reset", "--title", "again")[0], 1)
        code, out, _ = self.run_cli("new", "with-branch", "--title", "b", "--branch")
        self.assertEqual(code, 0)
        self.assertEqual(self.git("branch", "--show-current").strip(), "delivery/with-branch")


class AcceptanceTests(ProjectCase):
    """A person accepts the spec, the plan and the contract; the gate detects
    any later change to what was accepted (drift detection, not authentication)."""

    def test_accept_sets_ready_records_content_and_detects_drift(self):
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        project = Project.find(self.root)
        before = project.fingerprint()
        code, _, err = self.accept()
        self.assertEqual(code, 0, err)
        spec = self.delivery() / "spec.md"
        self.assertIn("status: ready", spec.read_text())
        record = json.loads((self.delivery() / "approvals/local-spec.json").read_text())
        self.assertEqual((record["kind"], record["phase"], record["by"]), ("local-acceptance", "spec", "tester"))
        self.assertEqual(check_delivery(project, "password-reset").status, "ready")
        self.assertNotEqual(before, project.fingerprint(), "the status line changed, so the tree changed")
        (self.delivery() / "approvals/local-spec.json").unlink()
        without = project.fingerprint()
        self.accept()
        self.assertEqual(without, project.fingerprint(), "the acceptance record itself never changes the fingerprint")
        # One byte of drift after the acceptance, and the gate asks the person again.
        spec.write_text(spec.read_text().replace("30 minutes", "31 minutes"))
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "draft")
        self.assertTrue(any("changed after the acceptance" in t for t in report.todos), report.render())
        code, _, err = self.run_cli("plan", "password-reset")
        self.assertEqual((code, "the spec is not ready" in err), (1, True))
        self.assertEqual(self.accept()[0], 0)
        self.assertEqual(check_delivery(project, "password-reset").status, "ready")
        # The contract is part of what was accepted.
        self.write_contract('require-command "true"')
        self.assertTrue(any("or the contract changed" in t for t in check_delivery(project, "password-reset").todos))
        code, out, _ = self.run_cli("status")
        self.assertIn("accepted: spec accepted by tester", out)
        self.assertIn("outdated", out)

    def test_accept_refuses_an_incomplete_spec_and_never_touches_a_policy(self):
        self.new_delivery()
        self.write_spec(status="draft", question="How long?", accept=False)
        code, _, err = self.accept()
        self.assertEqual(code, 1)
        self.assertIn("open question", err)
        self.assertIn("status: draft", (self.delivery() / "spec.md").read_text())
        self.assertFalse((self.delivery() / "approvals").exists())
        code, _, err = self.run_cli("accept", "password-reset")
        self.assertEqual((code, "spec|plan" in err), (1, True))

    def test_plan_acceptance_follows_approve_plan_and_task_additions(self):
        self.new_delivery()
        self.write_spec()
        self.write_plan(accept=False)
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("plan.md is not accepted" in t for t in report.todos))
        code, _, err = self.run_cli("build", "password-reset")
        self.assertEqual((code, "not accepted" in err), (1, True))
        self.assertIn("next phase is plan", self.run_cli("ship", "password-reset")[1])
        self.assertEqual(self.accept("password-reset", "plan")[0], 0)
        self.assertFalse(any("accept" in t for t in check_delivery(project, "password-reset").todos))
        self.assertEqual(self.run_cli("build", "password-reset", "--no-context")[0], 0)
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text() + "\n### T3: Unforeseen\n\nCovers: REQ-002\nVerify:\n- `true`\n")
        self.assertTrue(any("changed after the plan's acceptance" in t for t in check_delivery(project, "password-reset").todos))
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\napprove_plan: false\n")
        self.assertFalse(any("accept" in t for t in check_delivery(Project.find(self.root), "password-reset").todos),
                         "approve_plan: false asks for no plan acceptance")
        self.assertEqual(self.run_cli("accept", "password-reset", "plan")[0], 0)

    def test_accept_uses_the_gate_and_the_git_identity(self):
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("### REQ-002: The link expires", "### REQ-001: The link expires"))
        code, _, err = self.accept()
        self.assertEqual((code, "duplicate requirement id REQ-001" in err), (1, True))
        self.write_spec(status="draft", accept=False)
        code, out, _ = self.run_cli("accept", "password-reset", "spec")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.delivery() / "approvals/local-spec.json").read_text())["by"], "t@t")
        code, out, _ = self.run_cli("status")
        self.assertIn("contract: not accepted yet", out)

    def test_accept_contract_refuses_a_broken_or_missing_contract(self):
        self.write_contract("bogus-rule x")
        (self.root / ".atipspec/contract.md").write_text((self.root / ".atipspec/contract.md").read_text().replace("status: accepted", "status: draft"))
        code, _, err = self.run_cli("accept", "contract")
        self.assertEqual((code, "unknown rule" in err), (1, True))
        (self.root / ".atipspec/contract.md").unlink()
        self.assertEqual(self.run_cli("accept", "contract")[0], 1)

    def test_accept_contract_sets_its_status(self):
        self.assertIn("status: draft", (self.root / ".atipspec/contract.md").read_text())
        code, out, _ = self.run_cli("accept", "contract")
        self.assertEqual(code, 0)
        self.assertIn("status: accepted", (self.root / ".atipspec/contract.md").read_text())
        self.new_delivery()
        self.assertEqual(self.run_cli("spec", "password-reset", "--no-context")[0], 0)


class SpecQualityTests(ProjectCase):
    """C4: criteria in EARS or scenario form without vague terms, a method per
    criterion the plan must respect, and assumptions the user confirms."""

    def test_method_tags_survive_delivery_and_bind_the_plan(self):
        from atipspec.delivery import parse_spec
        spec = parse_spec("# T\n\n### REQ-001: X\n- AC-001 [ MANUAL ]: When printed, the label shows the code.\n- AC-002 [test]: When saved, the record exists.\n- AC-003 [manuel]: typo\n")
        self.assertEqual([ac.method for ac in spec.criteria], ["manual", "test"])
        self.assertEqual(spec.problems, ["spec.md line 6: malformed criterion line; use `- AC-001: text` or `- AC-001 [manual]: text`"])
        spec = parse_spec("# T\n\n### REQ-001: X\n- AC-001 [manual]: When printed, the label shows the code.\n- AC-002: When saved, the record exists.\n")
        self.assertEqual(spec.criteria[0].text, "When printed, the label shows the code.")
        merged = merge_requirements("# auth\n\n## Requirements\n", spec.requirements)
        self.assertIn("- AC-001 [manual]: When printed", merged)
        self.new_delivery()
        self.write_spec()
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("- AC-003:", "- AC-003 [manual]:"))
        self.accept()
        self.write_plan(accept=False)
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("T2 lists AC-003 under Tests, but the spec marks it [manual]" in e for e in report.errors), report.render())
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text().replace("Tests: AC-003", "Manual: AC-003").replace("Tests: AC-001, AC-002", "Tests: AC-001"))
        report = check_delivery(project, "password-reset")
        self.assertFalse(any("marks it" in e for e in report.errors))
        self.assertTrue(any("AC-002: no task lists it under Tests or Manual" in t for t in report.todos))
        code, _, err = self.run_cli("build", "password-reset")
        self.assertEqual((code, "AC-002" in err), (1, True), "an unmapped criterion is not a valid plan")
        plan.write_text(plan.read_text().replace("Tests: AC-001", "Tests: AC-001, AC-002"))
        self.assertFalse(any("Tests or Manual" in t for t in check_delivery(project, "password-reset").todos))

    def test_lint_warns_about_form_and_vague_terms_per_language(self):
        from atipspec.lint import lint_criterion
        self.assertEqual(lint_criterion("AC-001", "El sistema responde rápido", "es", "ears"),
                         ["AC-001 does not follow the EARS or scenario form (when/while/if/given ..., or a shall statement); set criteria_syntax: free to disable",
                          "AC-001 uses vague terms (rápido); state the observable value instead"])
        self.assertEqual(lint_criterion("AC-001", "Cuando el usuario envía un correo registrado, el sistema envía el enlace en menos de 60 segundos", "es", "ears"), [])
        self.assertEqual(lint_criterion("AC-001", "The system shall reject a password shorter than 12 characters", "en", "ears"), [])
        self.assertEqual(lint_criterion("AC-001", "The response is fast and/or intuitive", "en", "free"),
                         ["AC-001 uses vague terms (fast, and/or, intuitive); state the observable value instead"])
        self.assertEqual(lint_criterion("AC-001", "Les tentatives cessent après 3 essais", "fr", "ears"), [],
                         "a language without tables gets no form check")
        self.assertEqual(lint_criterion("AC-001", "Les tentatives sont fast", "fr", "ears"),
                         ["AC-001 uses vague terms (fast); state the observable value instead"])
        self.assertEqual(lint_criterion("AC-001", "The report, which someone must review, needs no action", "en", "ears")[0][:36],
                         "AC-001 does not follow the EARS or s", "a shall in the middle is not the ubiquitous form")
        self.assertEqual(lint_criterion("AC-001", "Fasten someone's seatbelt", "en", "free"), [],
                         "vague terms match whole words only")
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace(
            "- AC-003: If a link is older than 30 minutes, then the system returns \"link expired\".",
            "- AC-003: Expired links are handled quickly.").replace("## Open questions", "## Assumptions\n\n- Links expire after 30 minutes\n\n## Open questions"))
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("AC-003 does not follow" in w for w in report.of("warning")), report.render())
        self.assertTrue(any("AC-003 uses vague terms (quickly)" in w for w in report.of("warning")))
        self.assertTrue(any("1 assumption(s) for the user to confirm" in i for i in report.of("info")))
        self.assertFalse(report.errors)
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\nstrict_criteria: true\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("AC-003 uses vague terms" in e for e in report.errors))
        self.assertEqual(self.accept()[0], 1, "strict criteria block the acceptance")
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\ncriteria_syntax: free\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertFalse(any("does not follow" in w for w in report.of("warning")))


JUNIT = ("python3 -c \"import os,sys;os.makedirs('.atipspec/tmp',exist_ok=True);"
         "open('.atipspec/tmp/junit.xml','w').write(sys.argv[1])\" "
         "'<testsuite><testcase classname=\"tests.test_reset\" name=\"test_link\"/>"
         "<testcase classname=\"tests.test_reset\" name=\"test_expiry\"><failure>boom</failure></testcase></testsuite>'")


class ProofTests(ProjectCase):
    """C7: a criterion names its test; the evidence proves the test ran and passed."""

    def test_report_and_proof_lines_are_parsed(self):
        from atipspec.delivery import parse_plan
        plan = parse_plan("# P\n\n### T1: A\n\nCovers: REQ-001\nTests: AC-001, AC-002\nReport: `.atipspec/tmp/junit.xml`\nProof:\n- AC-001: test_link\n- AC-002: tests/test_reset.py::test_expiry\nVerify:\n- `true`\n\n### T2: B\n\nCovers: REQ-002\nProof: AC-003: test_x\nVerify: none\n")
        self.assertEqual(plan.tasks[0].report, ".atipspec/tmp/junit.xml")
        self.assertEqual(plan.tasks[0].proof, {"AC-001": "test_link", "AC-002": "tests/test_reset.py::test_expiry"})
        self.assertEqual(plan.tasks[0].verify, ["true"])
        self.assertEqual(plan.tasks[1].proof, {"AC-003": "test_x"})
        self.assertEqual(plan.problems, [])
        plan = parse_plan("# P\n\n### T1: A\n\nCovers: REQ-001\nReport:\nProof:\n- not a proof\n")
        self.assertEqual(len(plan.problems), 2)
        from atipspec.junit import matches
        case = {"id": "tests.test_reset.TestReset.test_link", "name": "test_link", "classname": "tests.test_reset.TestReset", "status": "passed"}
        for proof in ("test_link", "TestReset.test_link", "tests.test_reset.TestReset.test_link",
                      "tests/test_reset.py::TestReset::test_link", "tests.test_reset.TestReset::test_link"):
            self.assertTrue(matches(proof, case), proof)
        self.assertFalse(matches("test_links", case))
        self.assertFalse(matches("other.test_link", case))

    def test_evidence_binds_criteria_to_tests_that_ran_and_passed(self):
        self.new_delivery()
        self.write_spec()
        plan = self.delivery() / "plan.md"
        plan.write_text(f"# Plan\n\n### T1: Request link\n\nCovers: REQ-001\nTests: AC-001, AC-002\n"
                        f"Report: .atipspec/tmp/junit.xml\nProof:\n- AC-001: test_link\n- AC-002: tests.test_reset.test_missing\n"
                        f"Verify:\n- `{JUNIT}`\n\n### T2: Expiry\n\nCovers: REQ-002\nTests: AC-003\nVerify:\n- `true`\n")
        self.accept("password-reset", "plan")
        code, out, err = self.run_cli("verify", "password-reset", "--task", "T1")
        self.assertEqual(code, 1, out + err)
        self.assertIn("report .atipspec/tmp/junit.xml: 2 test(s), 1 failed", out)
        evidence = json.loads(next((self.delivery() / "evidence").glob("T1-*.json")).read_text())
        self.assertEqual([t["status"] for t in evidence["tests"]], ["passed", "failed"])
        self.assertTrue((self.delivery() / "evidence" / evidence["reports"][0]["copy"]).is_file())
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("AC-002: the named test tests.test_reset.test_missing did not run" in e for e in report.errors), report.render())
        self.assertFalse(any("AC-001" in e for e in report.errors))
        plan.write_text(plan.read_text().replace("tests.test_reset.test_missing", "test_expiry"))
        self.accept("password-reset", "plan")
        self.assertEqual(self.run_cli("verify", "password-reset", "--task", "T1")[0], 1)
        evidence = json.loads(max((self.delivery() / "evidence").glob("T1-*.json"), key=lambda p: p.stat().st_mtime).read_text())
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("AC-002: the named test test_expiry failed" in e for e in report.errors), report.render())
        # The copied report is part of the evidence: altering it is detected, and attestation refuses it.
        copy = self.delivery() / "evidence" / evidence["reports"][0]["copy"]
        copy.write_text(copy.read_text().replace("<failure>boom</failure>", ""))
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("test report is missing or altered" in e for e in report.errors), report.render())
        from atipspec.assurance import evidence_problems
        from atipspec.delivery import load_evidence, parse_plan
        record = load_evidence(self.delivery() / "evidence")[0]["T1"]
        self.assertTrue(any("altered" in p for p in evidence_problems(record, parse_plan(plan.read_text()).tasks[0], "password-reset")))
        # Without Report and Proof nothing changes; a Report without Proof for a criterion is only informative.
        plan.write_text(plan.read_text().replace("Proof:\n- AC-001: test_link\n- AC-002: test_expiry\n", ""))
        self.accept("password-reset", "plan")
        self.assertEqual(self.run_cli("verify", "password-reset", "--task", "T1")[0], 1)
        report = check_delivery(project, "password-reset")
        self.assertFalse(any("named test" in e for e in report.errors))
        self.assertTrue(any("AC-001 has no named test in T1's Proof" in i for i in report.of("info")))
        code, out, _ = self.run_cli("review", "password-reset")
        self.assertEqual(code, 1)   # T2 has no evidence yet; the packet is refused, but the summary format is tested below
        from atipspec.review import build_packet
        packet = build_packet(project, "password-reset")
        self.assertIn("`" + JUNIT.split(" ")[0], packet)

    def test_report_path_cannot_leave_the_project(self):
        from atipspec.delivery import parse_plan
        plan = parse_plan("# P\n\n### T1: A\n\nCovers: REQ-001\nReport: /etc/hosts\nVerify:\n- `true`\n")
        self.assertIsNone(plan.tasks[0].report)
        self.assertTrue(any("relative path inside the project" in p for p in plan.problems))
        plan = parse_plan("# P\n\n### T1: A\n\nCovers: REQ-001\nReport: ../outside.xml\nVerify:\n- `true`\n")
        self.assertIsNone(plan.tasks[0].report)
        outside = self.root.parent / f"{self.root.name}-outside.xml"
        outside.write_text("<testsuite><testcase name='t'/></testsuite>")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        (self.root / "link.xml").symlink_to(outside)
        self.new_delivery()
        self.write_spec()
        plan_path = self.delivery() / "plan.md"
        plan_path.write_text("# Plan\n\n### T1: A\n\nCovers: REQ-001, REQ-002\nTests: AC-001, AC-002, AC-003\nReport: link.xml\nProof:\n- AC-001: t\nVerify:\n- `true`\n")
        self.accept("password-reset", "plan")
        code, out, _ = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("regular file inside the project", out)
        self.assertEqual(list((self.delivery() / "evidence/logs").glob("*report.xml")), [], "nothing outside is copied in")

    def test_dossier_shows_the_named_tests(self):
        self.new_delivery()
        self.write_spec()
        plan = self.delivery() / "plan.md"
        plan.write_text(f"# Plan\n\n### T1: A\n\nCovers: REQ-001, REQ-002\nTests: AC-001, AC-002, AC-003\n"
                        f"Report: .atipspec/tmp/junit.xml\nProof:\n- AC-001: test_link\nVerify:\n- `{JUNIT}`\n")
        self.accept("password-reset", "plan")
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 1,
                         "a report with failed tests fails verification even if the writer exits zero")
        from atipspec.reporting import report_data, render_report
        data = report_data(Project.find(self.root), "password-reset")
        self.assertEqual(data["matrix"][0]["tests"], [{"task": "T1", "test": "test_link", "status": "passed"}])
        self.assertIn("[tests: test_link (passed)]", render_report(data, "markdown"))
        self.assertIn("[tests: test_link (passed)]", render_report(data, "html"))

    def test_missing_report_fails_the_verification(self):
        self.new_delivery()
        self.write_spec()
        plan = self.delivery() / "plan.md"
        plan.write_text("# Plan\n\n### T1: A\n\nCovers: REQ-001, REQ-002\nTests: AC-001, AC-002, AC-003\nReport: .atipspec/tmp/none.xml\nProof:\n- AC-001: test_link\nVerify:\n- `true`\n")
        self.accept("password-reset", "plan")
        code, out, _ = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("test report not found", out)
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("last verification failed" in e for e in report.errors))


class FixTests(ProjectCase):
    """C6: a defect gets a regression criterion, a one-task plan and the same gate."""

    def test_fix_delivery_flows_to_checked_without_plan_acceptance(self):
        self.write_contract('require-command "true"\nrequire-command "python3 -c pass"')
        self.commit("contract")
        code, out, err = self.run_cli("new", "bug-123", "--title", "Reset link never expires", "--capability", "auth",
                                      "--kind", "fix", "--ticket", "SHOP-9")
        self.assertEqual(code, 0, err)
        self.assertIn("kind fix", out)
        self.assertIn("Next: `atipspec fix bug-123`", out)
        spec_path = self.delivery("bug-123") / "spec.md"
        plan_path = self.delivery("bug-123") / "plan.md"
        from atipspec.delivery import parse_plan, parse_spec
        spec, plan = parse_spec(spec_path.read_text()), parse_plan(plan_path.read_text())
        self.assertEqual((spec.kind, spec.meta.get("ticket"), len(spec.requirements)), ("fix", "SHOP-9", 1))
        self.assertEqual(spec.requirements[0].title, "Reset link never expires")
        self.assertEqual([task.id for task in plan.tasks], ["T1"])
        self.assertEqual(plan.tasks[0].verify, ["true", "python3 -c pass"], "the contract's commands are prefilled")
        self.assertEqual((plan.tasks[0].covers, plan.tasks[0].tests), (["REQ-001"], ["AC-001"]))
        code, out, _ = self.run_cli("status")
        self.assertIn("- bug-123 [draft] [fix]", out)
        code, out, _ = self.run_cli("ship", "bug-123")
        self.assertIn("next phase is fix", out)
        self.assertIn("Run: atipspec fix bug-123", out)
        code, out, _ = self.run_cli("fix", "bug-123", "--no-context")
        self.assertEqual(code, 0)
        self.assertIn("# Phase fix", out)
        code, _, err = self.run_cli("fix", "password-reset")
        self.assertEqual(code, 1)
        self.new_delivery()
        code, _, err = self.run_cli("fix", "password-reset")
        self.assertEqual((code, "is not a fix delivery" in err), (1, True))
        code, _, err = self.run_cli("spec", "bug-123")
        self.assertEqual((code, "is a fix delivery: use `atipspec fix bug-123`" in err), (1, True))
        # Fill the regression criterion, accept, build with approve_plan on: no plan acceptance is asked.
        text = spec_path.read_text()
        text = text.replace("- AC-001: When <!-- the steps that reproduce the defect -->, the system <!-- the expected outcome with concrete values -->.",
                            "- AC-001: When a reset link is 31 minutes old, the system returns \"link expired\".")
        spec_path.write_text(text)
        self.assertEqual(self.accept("bug-123", "spec")[0], 0)
        project = Project.find(self.root)
        report = check_delivery(project, "bug-123")
        self.assertFalse(any("accept bug-123 plan" in t for t in report.todos), report.render())
        self.assertEqual(report.status, "planned")
        self.assertEqual(self.run_cli("build", "bug-123", "--no-context")[0], 0)
        self.assertEqual(self.run_cli("verify", "bug-123")[0], 0)
        self.commit("fix [bug-123:T1]")
        self.assertEqual(self.run_cli("review", "bug-123")[0], 0)
        report = check_delivery(project, "bug-123")
        self.write_review(report.fingerprint, slug="bug-123")
        (self.delivery("bug-123") / "review.md").write_text(f"---\ntree: {report.fingerprint}\nreviewer: t\n---\n\n- AC-001: PASS. tests/test_reset.py::test_expired\n")
        report = check_delivery(project, "bug-123")
        self.assertEqual((report.exit_code, report.status), (0, "checked"), report.render())


class LanguageTests(ProjectCase):
    """C10: English primary, Spanish and Portuguese in the parser, the lint and the dossier."""

    def test_portuguese_sections_lint_and_dossier(self):
        from atipspec.delivery import parse_spec
        spec = parse_spec("# T\n\n### REQ-001: X\n- AC-001: Quando x, o sistema faz y.\n\n## Suposições\n\n- Links expiram\n\n## Perguntas em aberto\n\n- Nenhuma\n")
        self.assertEqual((spec.open_questions, spec.assumptions), ([], ["Links expiram"]))
        spec = parse_spec("# T\n\n### REQ-001: X\n- AC-001: y\n\n## Questões em aberto\n\n- Qual prazo?\n")
        self.assertEqual(spec.open_questions, ["Qual prazo?"])
        from atipspec.delivery import parse_plan
        plan = parse_plan("# P\n\n### T1: A\n\nCovers: REQ-001\nVerify: nenhum\n")
        self.assertTrue(plan.tasks[0].verify_none)
        from atipspec.lint import lint_criterion
        self.assertEqual(len(lint_criterion("AC-001", "O sistema responde rápido", "pt", "ears")), 2)
        self.assertEqual(lint_criterion("AC-001", "Quando o usuário envia um e-mail cadastrado, o sistema envia o link em menos de 60 segundos", "pt", "ears"), [])
        self.assertEqual(lint_criterion("AC-001", "O sistema deve rejeitar senhas com menos de 12 caracteres", "pt", "ears"), [])
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\n")
        self.new_delivery()
        self.write_spec()
        self.write_plan()
        from atipspec.reporting import report_data, render_report
        data = report_data(Project.find(self.root), "password-reset")
        markdown = render_report(data, "markdown")
        self.assertIn("# Aceptación de la entrega: Password reset", markdown)
        self.assertIn("| Requisito | Criterio | Resultado | Tareas | Veredicto | Prueba |", markdown)
        self.assertIn("auth/AC-001", markdown, "identifiers are never translated")
        self.assertIn("**Estado:** planned", markdown, "statuses are never translated")
        html = render_report(data, "html")
        self.assertIn('<html lang="es">', html)
        data["language"] = "PT-br"
        self.assertIn('<html lang="pt">', render_report(data, "html"))
        data["language"] = 'en" onmouseover="x'
        self.assertIn('<html lang="en">', render_report(data, "html"))
        self.assertIn("EXPEDIENTE DE ACEPTACIÓN DE LA ENTREGA", html)
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: fr\n")
        data = report_data(Project.find(self.root), "password-reset")
        self.assertIn("# Delivery acceptance", render_report(data, "markdown"))
        code, out, _ = self.run_cli("audit")
        self.assertIn("language 'fr' has no tables", out)


class PacketAndScopeTests(ProjectCase):
    def test_packet_includes_living_specs_decisions_and_scope(self):
        (self.root / ".atipspec/specs").mkdir(exist_ok=True)
        (self.root / ".atipspec/specs/auth.md").write_text("---\ncapability: auth\n---\n\n# auth\n\n## Requirements\n\n### REQ-001: Existing login\n\n- AC-001: the living criterion\n")
        self.assertEqual(self.run_cli("decision", "tokens", "--title", "Opaque tokens", "--affects", "auth")[0], 0)
        decision = next((self.root / ".atipspec/decisions").glob("DEC-*.md"))
        decision.write_text(decision.read_text().replace("status: proposed", "status: accepted") + "\nUse opaque tokens.\n")
        self.commit("living spec and decision")
        self.new_delivery()
        self.write_spec()
        (self.delivery() / "plan.md").write_text("---\nscope: [\"shop/**\"]\n---\n\n# Plan\n\n### T1: A\n\nCovers: REQ-001, REQ-002\nVerify:\n- `true`\n")
        (self.root / "shop").mkdir()
        (self.root / "shop/auth.py").write_text("inside\n")
        (self.root / "stray.py").write_text("outside\n")
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("files outside the declared scope: stray.py" in w for w in report.of("warning")), report.render())
        self.assertFalse(any("stray" in e for e in report.errors))
        code, _, _ = self.run_cli("review", "password-reset", "--out", str(self.root / ".atipspec/tmp/p.md"))
        self.assertEqual(code, 1, "review still refuses while T1 is not committed")
        from atipspec.review import build_packet
        packet = build_packet(project, "password-reset")
        self.assertIn("### auth (.atipspec/specs/auth.md)", packet)
        self.assertIn("the living criterion", packet)
        self.assertIn("Use opaque tokens.", packet)
        self.assertIn("## Files outside the declared scope\n\n- stray.py", packet)
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\nstrict_scope: true\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("files outside the declared scope" in e for e in report.errors))
        (self.delivery() / "plan.md").write_text("# Plan\n\n### T1: A\n\nCovers: REQ-001, REQ-002\nVerify:\n- `true`\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertFalse(any("scope" in item.text for item in report.items), "no scope, no warning")

    def test_scope_sees_deletions_and_packet_names_impact_entries_honestly(self):
        self.commit("initialized")
        self.new_delivery()
        self.write_spec(impact="[billing, contract:dependencies]")
        (self.delivery() / "plan.md").write_text("---\nscope: [\"shop/**\"]\n---\n\n# Plan\n\n### T1: A\n\nCovers: REQ-001, REQ-002\nVerify:\n- `true`\n")
        (self.root / "README.md").unlink()
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertTrue(any("files outside the declared scope: README.md" in w for w in report.of("warning")),
                        "a deletion outside the scope is drift too")
        from atipspec.review import build_packet
        packet = build_packet(project, "password-reset")
        self.assertIn("### auth (.atipspec/specs/auth.md)\n\n(no living spec yet: this delivery creates it)", packet)
        self.assertIn("### billing\n\n(no living spec named billing", packet)
        self.assertIn("### contract:dependencies\n\n(a section of the architecture contract above)", packet)
        self.assertNotIn("specs/contract", packet)
        (self.root / ".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\nstrict_scope: true\n")
        code, _, err = self.run_cli("check", "password-reset")
        self.assertEqual(code, 1)

    def test_packet_caps_a_large_diff(self):
        self.new_delivery()
        self.write_spec()
        self.write_plan()
        (self.root / "README.md").write_text("x" * 300_000 + "\n")
        from atipspec.review import build_packet, MAX_DIFF_BYTES
        packet = build_packet(Project.find(self.root), "password-reset")
        self.assertIn("(truncated)", packet)
        self.assertIn("README.md |", packet)
        self.assertIn(f"bytes of diff omitted: the diff exceeds {MAX_DIFF_BYTES} bytes", packet)
        (self.root / "README.md").write_text("small change\n")
        packet = build_packet(Project.find(self.root), "password-reset")
        self.assertNotIn("(truncated)", packet)
        self.assertIn("+small change", packet)


class PhaseTests(ProjectCase):
    """A phase command refuses while a required step is missing, and otherwise
    prints the phase, its workflow, the shared rules and the context."""

    def test_phases_refuse_until_their_prerequisites_hold(self):
        self.new_delivery()
        code, _, err = self.run_cli("spec", "password-reset")
        self.assertEqual(code, 0, "guided proposals include project constraints in one approval")
        self.write_contract("")
        code, out, _ = self.run_cli("spec", "password-reset")
        self.assertEqual(code, 0)
        for text in ("Phase spec: Password reset (password-reset)", "status: draft", "# Phase spec",
                     "## Rules, every phase", "## Context", "atipspec context: contract"):
            self.assertIn(text, out)
        code, _, err = self.run_cli("plan", "password-reset")
        self.assertEqual((code, "the spec is not ready" in err), (1, True))
        code, out, _ = self.run_cli("ship", "password-reset")
        self.assertIn("next phase is spec", out)
        self.assertIn("stop point 1", out)

        self.write_spec(status="ready")
        code, out, _ = self.run_cli("plan", "password-reset", "--no-context")
        self.assertEqual(code, 0)
        self.assertIn("# Phase plan", out)
        self.assertNotIn("## Context", out)
        code, _, err = self.run_cli("build", "password-reset")
        self.assertEqual((code, "no plan to build from" in err), (1, True))
        self.assertIn("next phase is plan", self.run_cli("ship", "password-reset")[1])

        self.write_plan("true", "true")
        code, out, _ = self.run_cli("build", "password-reset", "--no-context")
        self.assertEqual(code, 0)
        self.assertIn("Next task: T1 is not complete", out)
        self.assertIn("next phase is build", self.run_cli("ship", "password-reset")[1])
        code, _, err = self.run_cli("review", "password-reset")
        self.assertEqual((code, "not ready for review" in err), (1, True))
        self.assertFalse((self.root / ".atipspec/tmp/password-reset-review-packet.md").exists(),
                         "a refused review must not write the packet")

        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.commit("both tasks [password-reset:T1,T2]")
        self.assertIn("next phase is review", self.run_cli("ship", "password-reset")[1])
        code, out, _ = self.run_cli("review", "password-reset")
        self.assertEqual(code, 0)
        self.assertIn("packet: .atipspec/tmp/password-reset-review-packet.md", out)
        self.assertIn("# Phase review", out)
        self.assertTrue((self.root / ".atipspec/tmp/password-reset-review-packet.md").is_file())
        fingerprint = check_delivery(Project.find(self.root), "password-reset").fingerprint
        self.write_review(fingerprint)
        self.assertIn("next phase is deliver", self.run_cli("ship", "password-reset")[1])

    def test_ship_names_a_phase_that_will_open_and_build_blocks_on_contract_defects(self):
        self.new_delivery()
        self.write_contract('require-command "true"')
        self.write_spec(status="ready", question="How long?")
        code, out, _ = self.run_cli("ship", "password-reset")
        self.assertEqual(code, 0)
        self.assertIn("next phase is spec", out, "an unanswered question sends ship back to the spec phase")
        self.write_spec(status="ready")
        (self.delivery() / "plan.md").write_text("# Plan\n\n### T1: Only\n\nCovers: REQ-009\nVerify:\n- `true`\n")
        self.assertIn("next phase is plan", self.run_cli("ship", "password-reset")[1],
                      "a plan with errors sends ship back to the plan phase")
        self.write_plan("true", "false")
        self.assertIn("next phase is build", self.run_cli("ship", "password-reset")[1])
        self.write_contract('require-command "python -m nothing"')
        self.accept()   # the contract changed, so the person accepts the spec again
        self.assertEqual(self.accept("password-reset", "plan")[0], 1, "a plan the contract rejects cannot be accepted")
        code, _, err = self.run_cli("build", "password-reset")
        self.assertEqual((code, "contract requires every plan" in err), (1, True))
        self.write_contract('forbid-path "*.txt"')
        self.accept()
        self.assertEqual(self.accept("password-reset", "plan")[0], 0)
        (self.root / "bad.txt").write_text("x")
        self.assertEqual(self.run_cli("build", "password-reset", "--no-context")[0], 0,
                         "a file violation is what build fixes, so it must not block the phase")
        code, _, err = self.run_cli("review", "password-reset")
        self.assertEqual((code, "not ready for review" in err), (1, True))
        (self.root / "bad.txt").unlink()
        code, _, err = self.run_cli("explore", "nope")
        self.assertEqual((code, "atipspec new nope" in err), (1, True))

    def test_review_refuses_stale_evidence(self):
        self.new_delivery()
        self.write_spec()
        self.write_plan("true", "true")
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        (self.root / "README.md").write_text("changed after verifying\n")
        self.commit("both [password-reset:T1,T2]")
        code, _, err = self.run_cli("review", "password-reset")
        self.assertEqual((code, "evidence is stale" in err), (1, True))
        self.assertFalse((self.root / ".atipspec/tmp").exists())

    def test_project_phases_print_their_workflow(self):
        code, out, _ = self.run_cli("contract")
        self.assertEqual(code, 0)
        self.assertIn("# Phase contract", out)
        self.assertIn("## Contract (.atipspec/contract.md)", out)
        code, out, _ = self.run_cli("curate")
        self.assertEqual(code, 0)
        self.assertIn("overview.md index regenerated", out)
        self.assertIn("# Phase curate", out)
        self.new_delivery()
        code, out, _ = self.run_cli("explore", "password-reset", "--no-context")
        self.assertEqual(code, 0)
        self.assertIn("# Phase explore", out)


class MergeTests(unittest.TestCase):
    def test_merge_replaces_by_id_and_removes(self):
        living = "---\ncapability: auth\n---\n\n# auth\n\n## Requirements\n\n### REQ-001: Old\n\nold body\n\n### REQ-002: Keep\n\nkeep body\n"
        spec = parse_spec("# T\n\n### REQ-001: old\n\nnew body\n\nAcceptance criteria:\n- AC-001: outcome\n\n### REQ-002 [remove]: Keep\n\n### REQ-003: Added\n\n- AC-002: x\n")
        merged = merge_requirements(living, spec.requirements)
        self.assertIn("### REQ-001: old\n\nnew body\n\nAcceptance criteria:\n- AC-001: outcome", merged)
        self.assertNotIn("Keep", merged)
        self.assertTrue(merged.endswith("### REQ-003: Added\n\n- AC-002: x\n"))
        self.assertTrue(merged.startswith("---\ncapability: auth\n---\n\n# auth\n\n## Requirements\n\n### REQ-001: old"))


if __name__ == "__main__":
    unittest.main()
