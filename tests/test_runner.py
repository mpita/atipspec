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
        'review_markdown': '---\ntree: ' + tree + '\nreviewer: fixture\n---\n- AC-001: PASS. app.greeting() returns Hola in final verification\n'}
print(json.dumps(response))
'''


@unittest.skipUnless(os.name == "posix", "POSIX runner")
class RunnerTests(ProjectCase):
    def prepare(self, adapter=ADAPTER, verification=None):
        self.new_delivery()
        project = self.project = Project.find(self.root)
        script = self.root / "adapter_fixture.py"
        script.write_text(adapter)
        (project.dot / "adapter.json").write_text(json.dumps({"schema": 1, "name": "test-fixture",
                                    "command": [sys.executable, str(script)], "isolated_review": True}))
        project.tmp.mkdir(parents=True, exist_ok=True)
        source = project.tmp / "auth.md"
        source.write_text("# Greeting\n### REQ-001: Greeting\n#### AC-001: Spanish greeting\n- WHEN greeting is requested\n- THEN the result is Hola\n")
        self.assertEqual(self.run_cli("spec-bind", "password-reset", "--file", str(source))[0], 0)
        command = verification or f'''{sys.executable} -c 'from app import greeting; assert greeting() == "Hola"' '''.strip()
        (self.delivery() / "plan.md").write_text("# Plan\n### T1: Greeting\nCovers: REQ-001\nTests: AC-001\n"
                                                  "## Final verification\nVerify:\n- `" + command + "`\n")
        (self.root / ".gitignore").write_text((self.root / ".gitignore").read_text() + "\n__pycache__/\n")
        code, out, err = self.run_cli("accept", "password-reset", "proposal", "--by", "human")
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
        spec.write_text(spec.read_text().replace("Hola", "Adiós"))
        state = run_delivery(project, "password-reset")
        self.assertEqual(state["status"], "awaiting_approval")
        self.assertFalse((project.tmp / "calls").exists())

    def test_interrupted_mutation_requires_explicit_retry(self):
        project = self.prepare()
        from atipspec.trust import subject
        checkpoint = {"schema": 1, "delivery": "password-reset", "status": "running", "phase": "implementer",
                      "agreement": subject(project, "password-reset", "plan"), "elapsed_s": 1, "rounds": 0}
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
            "status": "approved", "agreement": subject(project, "password-reset", "plan"), "elapsed_s": 500, "rounds": 0}))
        state = run_delivery(project, "password-reset", budget=100)
        self.assertEqual(state["status"], "failed", state)
        self.assertIn("budget exhausted", state["reason"])
        self.assertFalse((project.tmp / "calls").exists())

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
