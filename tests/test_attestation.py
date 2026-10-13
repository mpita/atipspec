"""C10: provider-mode evidence is attested by a trusted workflow outside the
candidate repository, pinned to a commit, for this pull request, and only the
records the run wrote are attested."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from atipspec.attestation import records_to_attest, verify_attestation
from atipspec.errors import AtipSpecError
from atipspec.project import Project, resource_root
from atipspec.trust import TrustPolicy, digest
from atipspec.verify import clear_evidence, verify_delivery
from tests.helpers import ProjectCase
from tests.test_merge import template_step
from tests.trust_helpers import TrustedCase


class AttestationPinningTests(TrustedCase):
    def verify(self, policy):
        record = self.root / "record.json"
        record.write_text("{}\n", encoding="utf-8")
        calls = []

        def tool(arguments):
            calls.append(arguments)
            return json.dumps([{"verificationResult": {"statement": {"subject": [
                {"digest": {"sha256": digest(record.read_bytes())}}]}}}])
        with patch("atipspec.attestation.tool_path", return_value="gh"), \
                patch("atipspec.attestation.run_tool", side_effect=tool):
            verify_attestation(record, policy)
        return calls[0]

    def test_verification_pins_repository_pull_request_and_signer_commit(self):
        policy = TrustPolicy.load(self.provider_policy(), self.root)
        policy.number = 42
        arguments = self.verify(policy)
        pairs = dict(zip(arguments[4::2], arguments[5::2]))
        self.assertEqual(pairs["--repo"], "example/demo")
        self.assertEqual(pairs["--signer-workflow"], "example/atipspec-trusted/.github/workflows/atipspec-evidence.yml")
        self.assertEqual(pairs["--signer-digest"], "a" * 40)
        self.assertEqual(pairs["--source-ref"], "refs/pull/42/merge")
        self.assertIn("--deny-self-hosted-runners", arguments)
        self.assertNotIn("--owner", arguments)
        allowed = TrustPolicy.load(self.provider_policy(**{'signer_digest = "': 'allow_self_hosted_runners = true\n'
                                                          'signer_digest = "'}), self.root)
        allowed.number = 42
        self.assertNotIn("--deny-self-hosted-runners", self.verify(allowed))
        policy.number = None
        with self.assertRaisesRegex(AtipSpecError, "needs the PR number"):
            self.verify(policy)


class EvidenceSelectionTests(ProjectCase):
    def setUp(self):
        super().setUp()
        self.write_contract('require-command "true"')
        self.new_delivery()
        self.write_spec()
        self.write_plan()
        self.commit("implementation [password-reset:T1,T2]")
        self.project = Project.find(self.root)
        self.assertEqual(verify_delivery(self.project, "password-reset"), 0)

    def record(self, task):
        return next((self.delivery() / "evidence").glob(f"{task}-*.json"))

    def test_only_this_runs_records_are_attested(self):
        self.assertEqual(sorted(path.name[:2] for path in records_to_attest(self.project)), ["T1", "T2"])
        # A record committed to the branch, named after this run's, would win in load_evidence.
        planted = self.delivery() / "evidence/T1-29990101T000000Z-planted.json"
        planted.write_text(self.record("T1").read_text(encoding="utf-8"), encoding="utf-8")
        with self.assertRaisesRegex(AtipSpecError, "holds records this run did not write"):
            records_to_attest(self.project)
        self.assertEqual(clear_evidence(self.project), ["password-reset"])
        self.assertFalse((self.delivery() / "evidence").exists())
        self.assertEqual(verify_delivery(self.project, "password-reset"), 0)
        paths = records_to_attest(self.project)
        self.assertEqual(sorted(path.name[:2] for path in paths), ["T1", "T2"])
        self.assertNotIn(planted, paths)

    def test_record_from_another_head_is_refused(self):
        path = self.record("T1")
        data = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**data, "head": "0" * 40}), encoding="utf-8")
        with self.assertRaisesRegex(AtipSpecError, "cannot attest T1: it was not written on the checked-out head"):
            records_to_attest(self.project)

    def test_missing_record_and_failed_record_are_refused(self):
        self.record("T2").unlink()
        with self.assertRaisesRegex(AtipSpecError, "no evidence record for T2"):
            records_to_attest(self.project)
        clear_evidence(self.project)
        self.write_plan(command1="false")
        self.commit("T1 now fails")
        self.assertEqual(verify_delivery(self.project, "password-reset"), 1)
        with self.assertRaisesRegex(AtipSpecError, "cannot attest T1: its result is fail"):
            records_to_attest(self.project)

    def test_a_symlinked_evidence_folder_is_refused(self):
        outside = Path(tempfile.mkdtemp(prefix="atipspec-outside-"))
        self.addCleanup(shutil.rmtree, outside, True)
        shutil.rmtree(self.delivery() / "evidence")
        (self.delivery() / "evidence").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(AtipSpecError, "symlinked evidence folder"):
            records_to_attest(self.project)
        with self.assertRaisesRegex(AtipSpecError, "symlinked evidence folder"):
            clear_evidence(self.project)
        self.assertTrue(outside.is_dir())


@unittest.skipIf(os.name == "nt" or not shutil.which("bash"), "runs the trusted workflow's bash steps, as its ubuntu "
                                                              "runner does")
class TrustedWorkflowTests(ProjectCase):
    def bash(self, script, tools=(), **env):
        """Run a script as the GitHub runner would, with `python` and each of `tools`, (name, sh body), on PATH."""
        shim = Path(tempfile.mkdtemp(prefix="atipspec-ci-"))
        self.addCleanup(shutil.rmtree, shim, True)
        for name, body in (("python", f'exec "{sys.executable}" "$@"'), *tools):
            (shim / name).write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8", newline="\n")
            (shim / name).chmod(0o755)
        env = {**self.env, "PATH": f"{shim}{os.pathsep}{self.env['PATH']}", "RUNNER_TEMP": str(shim), **env}
        return subprocess.run(["bash", "-eo", "pipefail", "-c", script], cwd=self.root, env=env, capture_output=True,
                              text=True, encoding="utf-8", stdin=subprocess.DEVNULL)

    def step(self, name, output):
        """Run a `run: |` step of github-evidence-trusted.yml."""
        return self.bash(template_step("github-evidence-trusted.yml", name), GITHUB_OUTPUT=str(output))

    def test_the_trusted_workflow_attests_only_this_runs_records(self):
        self.write_contract('require-command "true"')
        self.new_delivery()
        self.write_spec()
        self.write_plan()
        evidence = self.delivery() / "evidence"
        evidence.mkdir(exist_ok=True)
        (evidence / "T1-29990101T000000Z-planted.json").write_text('{"task": "T1", "result": "pass"}\n',
                                                                    encoding="utf-8")
        self.commit("implementation [password-reset:T1,T2] with planted evidence")
        output = self.root.parent / f"{self.root.name}-output"
        self.addCleanup(lambda: output.unlink(missing_ok=True))
        result = self.step("- name: Verify active deliveries from clean evidence", output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("records=true", output.read_text(encoding="utf-8"))
        self.assertEqual(sorted(path.name[:2] for path in evidence.glob("*.json")), ["T1", "T2"])
        # The attest job: a fresh checkout, which holds the planted record again, then the uploaded artifact.
        artifact = Path(tempfile.mkdtemp(prefix="atipspec-artifact-"))
        self.addCleanup(shutil.rmtree, artifact, True)
        shutil.copytree(evidence, artifact / "evidence")
        shutil.rmtree(evidence)
        self.git("checkout", "--", ".atipspec/deliveries/password-reset/evidence")
        self.assertTrue((evidence / "T1-29990101T000000Z-planted.json").is_file())
        result = self.step("- name: Clear committed evidence", output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(evidence.exists())
        shutil.copytree(artifact / "evidence", evidence)
        result = self.step("- name: Select this run's records", output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = output.read_text(encoding="utf-8")
        paths = text.split("paths<<ATIPSPEC_PATHS\n", 1)[1].split("\nATIPSPEC_PATHS\n", 1)[0].splitlines()
        self.assertEqual(sorted(Path(path).name[:2] for path in paths), ["T1", "T2"])
        self.assertTrue(all(path.startswith(".atipspec/deliveries/password-reset/evidence/T") for path in paths))

    def test_the_worker_takes_only_the_evidence_the_trusted_job_uploaded(self):
        """ADOPTION.md's worker commands. The caller, which the pull request
        edits, may upload to the same run a later-numbered artifact, and any
        artifact may carry files the gate reads besides evidence/."""
        self.new_delivery()
        evidence = self.delivery() / "evidence"
        evidence.mkdir()
        (evidence / "T1-29990101T000000Z-planted.json").write_text("{}\n", encoding="utf-8")
        self.commit("planted evidence")
        artifacts = Path(tempfile.mkdtemp(prefix="atipspec-artifacts-"))
        self.addCleanup(shutil.rmtree, artifacts, True)
        for name, files in (("atipspec-evidence-2", ("evidence/T1-a.json", "evidence/logs/T1-a-1.log", "review.md")),
                            ("atipspec-evidence-99", ("evidence/T1-z.json", "deferred.md"))):
            for file in files:
                path = artifacts / name / "password-reset" / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"{name}\n", encoding="utf-8")
        # Run 7, attempt 2, whose artifacts the API lists, highest last; `gh run download <run> --name <artifact> --dir <dir>`.
        gh = ('case "$1 $2" in\n"run list") echo "7 2" ;;\n"api "*) echo atipspec-evidence-99 ;;\n'
              '"run download") cp -R "$ARTIFACTS/$5/." "$7/" ;;\n*) exit 1 ;;\nesac')
        adoption = (resource_root() / "enterprise" / "ADOPTION.md").read_text(encoding="utf-8")
        worker = next(block.split("```", 1)[0] for block in adoption.split("```sh\n") if block.startswith("# HEAD_SHA"))
        worker = worker.split("python -I -m atipspec check", 1)[0]
        result = self.bash(worker, tools=[("gh", gh)], HEAD_SHA=self.git("rev-parse", "HEAD").strip(),
                           ARTIFACTS=str(artifacts))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sorted(path.relative_to(self.delivery()).as_posix() for path in evidence.rglob("*")),
                         ["evidence/T1-a.json", "evidence/logs", "evidence/logs/T1-a-1.log"])
        taken = {path.relative_to(self.delivery()).as_posix(): path.read_text(encoding="utf-8").strip()
                 for path in self.delivery().rglob("*") if path.is_file()
                 and "atipspec-evidence-" in path.read_text(encoding="utf-8")}
        self.assertEqual(taken, {"evidence/T1-a.json": "atipspec-evidence-2",
                                 "evidence/logs/T1-a-1.log": "atipspec-evidence-2"})
