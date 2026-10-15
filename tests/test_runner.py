"""Real subprocess fixtures exercise orchestration, not model intelligence."""
import json
import os
from pathlib import Path
import sys
import unittest

from atipspec.project import Project
from atipspec.runner import read_state, run_delivery, _lock
from atipspec.errors import AtipSpecError
from tests.helpers import ProjectCase


ADAPTER = r'''
import json, sys
from pathlib import Path
request = json.load(sys.stdin)
calls = Path('.atipspec/tmp/calls')
with calls.open('a') as out:
    out.write(request['role'] + '\n')
if request['role'] == 'implementer':
    Path('app.py').write_text('def greeting():\n    return "Hola"\n')
    response = {'schema': 1, 'status': 'done', 'summary': 'Implemented the requested greeting'}
else:
    packet = request['review_packet']
    tree = packet.split('tree: ')[1].split()[0].strip('`')
    response = {'schema': 1, 'status': 'done', 'summary': 'Reviewed greeting and executable verification',
        'review_markdown': '---\ntree: ' + tree + '\nreviewer: fixture\nsession: isolated\n---\n- AC-001: PASS. app.py:2 returns Hola in final verification\n'}
print(json.dumps(response))
'''


@unittest.skipUnless(os.name == "posix", "the runner stops an adapter by its process group, POSIX only")
class RunnerTests(ProjectCase):
    def prepare(self, adapter=ADAPTER, verification=None, isolated=True, risk="normal"):
        self.new_delivery()
        project = self.project = Project.find(self.root)
        script = self.root / "adapter_fixture.py"
        script.write_text(adapter)
        (project.dot / "adapter.json").write_text(json.dumps({"schema": 1, "name": "test-fixture",
                                    "command": [sys.executable, str(script)], "isolated_review": isolated}))
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("risk: normal", f"risk: {risk}"))
        project.tmp.mkdir(parents=True, exist_ok=True)
        source = project.tmp / "auth.md"
        source.write_text("# Greeting\n### REQ-001: Greeting\n#### AC-001: Spanish greeting\n- WHEN greeting is requested\n- THEN the result is Hola\n")
        self.assertEqual(self.run_cli("spec-bind", "password-reset", "--file", str(source))[0], 0)
        command = verification or f'''{sys.executable} -c 'from app import greeting; assert greeting() == "Hola"' '''.strip()
        # risk: high names the test of every automated criterion before the proposal can be approved.
        proof = "Report: .atipspec/tmp/junit.xml\nProof:\n- AC-001: tests.test_greeting\n" if risk == "high" else ""
        (self.delivery() / "plan.md").write_text("---\nscope: [\"*\"]\n---\n# Plan\n### T1: Greeting\nCovers: REQ-001\nTests: AC-001\n"
                                                  "## Final verification\n" + proof + "Verify:\n- `" + command + "`\n")
        (self.root / ".gitignore").write_text((self.root / ".gitignore").read_text() + "\n__pycache__/\n")
        code, out, err = self.accept("password-reset", "proposal", by="human")
        self.assertEqual(code, 0, out + err)
        return project

    def test_run_reaches_acceptance_and_resume_reuses_valid_results(self):
        project = self.prepare()
        head = project.git.head()
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "ready_for_acceptance", state)
        self.assertEqual(project.git.head(), head)
        self.assertEqual((project.tmp / "calls").read_text().splitlines(), ["implementer", "reviewer"])
        records = list((self.delivery() / "evidence").glob("*.json"))
        self.assertEqual(len(records), 1)
        again = run_delivery(project, "password-reset")
        self.assertEqual(again["status"], "ready_for_acceptance", again)
        self.assertEqual(len(list((self.delivery() / "evidence").glob("*.json"))), 1)
        self.assertEqual((project.tmp / "calls").read_text().splitlines(), ["implementer", "reviewer"])
        self.assertFalse((self.delivery() / "approvals/local-result.json").exists())
        self.assertIsNone(state["capabilities"]["cost"])

    def test_cannot_start_after_unapproved_spec_change(self):
        project = self.prepare()
        spec = project.specs / "auth.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Hola", "Adiós"), encoding="utf-8")
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertFalse((project.tmp / "calls").exists())

    def test_interrupted_mutation_requires_explicit_retry(self):
        project = self.prepare()
        from atipspec.trust import subject
        checkpoint = {"schema": 1, "delivery": "password-reset", "status": "running", "phase": "implementer",
                      "agreement": subject(project, "password-reset", "plan"), "subject_version": 2, "elapsed_s": 1,
                      "rounds": 0}
        (self.delivery() / "run.json").write_text(json.dumps(checkpoint))
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "needs_decision")
        self.assertFalse((project.tmp / "calls").exists())
        self.assertEqual(run_delivery(project, "password-reset", retry_interrupted=True)["status"], "ready_for_acceptance")

    def test_adapter_cannot_change_agreement_and_continue(self):
        adapter = ADAPTER.replace("Path('app.py').write_text", "spec = Path('.atipspec/specs/auth.md'); spec.write_text(spec.read_text().replace('Hola', 'Bonjour'))\n    Path('app.py').write_text")
        project = self.prepare(adapter)
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "needs_decision", state)
        self.assertFalse((self.delivery() / "evidence").exists())

    def test_failed_check_and_no_progress_stop_without_endless_retries(self):
        project = self.prepare(verification="false")
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "blocked", state)
        self.assertIn("no candidate progress", state["reason"])
        self.assertEqual(state["rounds"], 1)
        self.assertEqual((project.tmp / "calls").read_text().splitlines(), ["implementer", "implementer"])

    def test_budget_expiry_stops_before_agent_call(self):
        project = self.prepare()
        from atipspec.trust import subject
        (self.delivery() / "run.json").write_text(json.dumps({"schema": 1, "delivery": "password-reset",
            "status": "approved", "agreement": subject(project, "password-reset", "plan"), "subject_version": 2,
            "elapsed_s": 500, "rounds": 0}))
        state = run_delivery(project, "password-reset", budget=100)
        self.assertEqual(state["status"], "failed", state)
        self.assertIn("budget exhausted", state["reason"])
        self.assertFalse((project.tmp / "calls").exists())

    def test_a_checkpoint_from_0_2_keeps_its_budget(self):
        project = self.prepare()
        from atipspec.trust import subject
        (self.delivery() / "run.json").write_text(json.dumps({"schema": 1, "delivery": "password-reset",
            "status": "approved", "agreement": subject(project, "password-reset", "plan", version=1),
            "elapsed_s": 500, "rounds": 0}))
        state = run_delivery(project, "password-reset", budget=100)
        self.assertEqual(state["status"], "failed", state)
        self.assertIn("budget exhausted", state["reason"])

    def test_only_one_writer_per_checkout(self):
        project = self.prepare()
        with _lock(project):
            with self.assertRaisesRegex(AtipSpecError, "Another runner"):
                run_delivery(project, "password-reset")

    def test_operational_subtask_does_not_reopen_approval_but_commitment_does(self):
        project = self.prepare()
        from atipspec.accept import is_current
        from atipspec.progress import mark_done, completed_tasks
        from atipspec.delivery import parse_plan
        mark_done(project, "password-reset", "T1", "Implemented")
        path = self.delivery() / "plan.md"
        text = path.read_text().replace("## Final verification", "### T2: Add a boundary test\nCovers: REQ-001\nTests: AC-001\n\n## Final verification")
        path.write_text(text)
        self.assertTrue(is_current(project, "password-reset", "proposal"))
        self.assertEqual(completed_tasks(project, "password-reset", parse_plan(text)), {"T1"})
        path.write_text(text.replace("## Final verification", "## Approach\nChange the public API.\n\n## Final verification"))
        self.assertFalse(is_current(project, "password-reset", "proposal"))

    def test_timeout_requires_inspection_before_retry(self):
        adapter = "import time\ntime.sleep(10)\n"
        project = self.prepare(adapter)
        state = run_delivery(project, "password-reset", timeout=0.05)
        self.assertEqual(state["status"], "needs_decision", state)
        self.assertEqual(state["phase"], "implementer")
        state = run_delivery(project, "password-reset", resume=True)
        self.assertEqual(state["status"], "needs_decision", state)
        self.assertIn("--retry-interrupted", state["reason"])

    def test_max_rounds_defaults_to_review_rounds_less_the_first_review(self):
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text().replace("review_rounds: 3", "review_rounds: 2"))
        adapter = ADAPTER.replace("Path('app.py').write_text('def greeting():\\n    return \"Hola\"\\n')",
                                  "Path('app.py').write_text('# ' + str(len(calls.read_text().split())) + '\\n')")
        project = self.prepare(adapter, verification="false")
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "blocked", state)
        self.assertIn("Correction budget exhausted", state["reason"])
        self.assertEqual(state["rounds"], 1)
        self.assertEqual((project.tmp / "calls").read_text().splitlines(), ["implementer", "implementer"])

    def test_max_rounds_cannot_exceed_review_rounds(self):
        project = self.prepare()
        with self.assertRaisesRegex(AtipSpecError, r"--max-rounds cannot exceed 2, review_rounds less the first review"):
            run_delivery(project, "password-reset", max_rounds=3)
        self.assertFalse((project.tmp / "calls").exists())

    def test_runner_counts_review_rounds_and_stops_when_used_up(self):
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text().replace("review_rounds: 3", "review_rounds: 2"))
        adapter = (ADAPTER.replace("Path('app.py').write_text('def greeting():\\n    return \"Hola\"\\n')",
                                   "Path('app.py').write_text('def greeting():\\n    return \"Hola\"\\n# '"
                                   " + str(len(calls.read_text().split())) + '\\n')")
                   .replace("- AC-001: PASS. app.py:2 returns Hola in final verification", "- AC-001: FAIL. wrong greeting"))
        project = self.prepare(adapter)
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "blocked", state)
        self.assertIn("Correction budget exhausted", state["reason"])
        self.assertIn("review 2 of 2", self.run_cli("status", "password-reset")[1])
        # A correction made outside the runner does not buy another review.
        (self.root / "app.py").write_text('def greeting():\n    return "Hola"\n# by hand\n')
        state = run_delivery(project, "password-reset", resume=True)
        self.assertEqual(state["status"], "needs_decision", state)
        self.assertIn("review 2 of 2 was the last, and the candidate changed after it", state["reason"])
        calls = ["implementer", "reviewer", "implementer", "reviewer"]
        self.assertEqual((project.tmp / "calls").read_text().splitlines(), calls)
        state = run_delivery(project, "password-reset", resume=True)
        self.assertEqual(state["status"], "needs_decision", state)
        self.assertIn("review rounds are used up", state["reason"])
        self.assertEqual((project.tmp / "calls").read_text().splitlines(), calls)

    def test_isolated_claim_needs_isolated_adapter(self):
        project = self.prepare(isolated=False)
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "failed", state)
        self.assertIn("does not declare isolated_review", state["reason"])
        self.assertFalse((self.delivery() / "review.md").exists())

    def test_require_isolated_review_needs_isolated_adapter(self):
        config = self.root / ".atipspec/config.yaml"
        lines = [line for line in config.read_text().splitlines() if not line.startswith("require_isolated_review:")]
        config.write_text("\n".join(lines + ["require_isolated_review: true"]) + "\n")
        project = self.prepare(isolated=False)
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "needs_decision", state)
        self.assertIn("require_isolated_review requires a review from an isolated session", state["reason"])
        self.assertFalse((project.tmp / "calls").exists(), "refused before any role works")

    def test_high_risk_needs_isolated_adapter(self):
        project = self.prepare(isolated=False, risk="high")
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "needs_decision", state)
        self.assertIn("risk: high requires a review from an isolated session", state["reason"])
        self.assertFalse((project.tmp / "calls").exists(), "refused before any role works")
