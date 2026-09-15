import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from atipspec.assurance import attest
from atipspec.check import check_delivery
from atipspec.delivery import load_evidence
from atipspec.deliver import deliver
from atipspec.errors import AtipSpecError
from atipspec.reporting import report_data, render_report
from atipspec.trust import TrustPolicy, valid_approvals
from tests.trust_helpers import TrustedCase


class ProviderModeTests(TrustedCase):
    """C8: approvals read live from the provider and evidence proven by an
    artifact attestation; no human key, no collector key."""

    def provider_policy(self, **overrides):
        text = ('schema = 2\nversion = "provider-1"\nmode = "provider"\nrepository = "example/demo"\n'
                'contract_rules = [\'require-command "true"\']\n\n[provider]\nkind = "github"\nrepository = "example/demo"\n\n'
                '[provider.roles]\nproduct = ["po"]\nengineering = ["arch"]\nqa = ["qa"]\n\n'
                '[attestation]\ntool = "gh"\nowner = "example"\nsigner_workflow = "example/demo/.github/workflows/atipspec-evidence.yml"\n')
        for old, new in overrides.items():
            text = text.replace(old, new)
        path = self.trust_root / "provider.toml"
        path.write_text(text)
        return path

    def test_policy_validation(self):
        from atipspec.trust import TrustPolicy
        policy = TrustPolicy.load(self.provider_policy(), self.root)
        self.assertEqual((policy.mode, policy.data["schema"]), ("provider", 2))
        for broken in ({"mode = \"provider\"": "mode = \"provider\"\nschema = 1"},
                       {"[attestation]": "[attestation-not]"},
                       {"example/demo/.github/workflows/atipspec-evidence.yml": "example/other/.github/workflows/atipspec-evidence.yml"},
                       {'owner = "example"': 'owner = "someone-else"'},
                       {'qa = ["qa"]': 'qa = ["qa"]\n[[signers]]\nidentity = "qa"\nroles = ["qa"]\npublic_key = "ssh-ed25519 AAAA"'}):
            with self.assertRaises(AtipSpecError):
                TrustPolicy.load(self.provider_policy(**broken), self.root)
        ssh_policy = TrustPolicy.load(self.policy_path, self.root)
        self.assertEqual(ssh_policy.mode, "ssh")

    def test_live_approvals_and_attestation_verify_a_delivery(self):
        import hashlib
        from unittest.mock import patch
        from atipspec.providers import marker
        from atipspec.trust import TrustPolicy, subject
        from atipspec.verify import verify_delivery
        self.write_contract('require-command "true"')
        self.commit("accepted architecture")
        self.new_delivery()
        self.write_spec()
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("capability: auth", "owner: author\ncapability: auth"))
        self.write_plan()
        self.commit("implementation [password-reset:T1,T2]")
        self.assertEqual(verify_delivery(self.project, "password-reset"), 0)
        self.write_review(self.project.fingerprint())
        policy = TrustPolicy.load(self.provider_policy(), self.root)
        policy.number = 1
        head = self.project.git.head()
        body = "\n".join(marker("password-reset", phase, subject(self.project, "password-reset", phase), head)
                         for phase in ("spec", "plan", "acceptance"))
        pull = {"state": "open", "head": {"sha": head}, "base": {"repo": {"full_name": "example/demo"}}, "user": {"login": "author"}}
        reviews = [{"id": n, "state": "APPROVED", "commit_id": head, "user": {"login": login, "type": "User"},
                    "body": body, "submitted_at": "2026-01-01T00:00:00Z", "html_url": f"https://github.com/example/demo/pull/1#review-{n}"}
                   for n, login in ((1, "po"), (2, "arch"), (3, "qa"))]
        digests = {}

        def fake_tool(arguments):
            target = arguments[3]
            digests.setdefault(target, hashlib.sha256(Path(target).read_bytes()).hexdigest())
            return json.dumps([{"verificationResult": {"statement": {"subject": [{"digest": {"sha256": digests[target]}}]}}}])

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-only"}), patch("atipspec.providers.API.get", return_value=pull), \
             patch("atipspec.providers.API.pages", return_value=reviews) as pages, \
             patch("atipspec.attestation.tool_path", return_value="gh"), patch("atipspec.attestation.run_tool", side_effect=fake_tool):
            report = check_delivery(self.project, "password-reset", policy=policy)
            self.assertEqual((report.exit_code, report.status), (0, "verified"), report.render())
            self.assertFalse(list((self.delivery() / "approvals").glob("*.sig")), "no signature is written in provider mode")
            data = report_data(self.project, "password-reset", policy)
            self.assertEqual(sorted(a["identity"] for a in data["approvals"]), ["arch", "po", "qa"])
            # A revoked review fails closed; so does an altered evidence record.
            pages.return_value = reviews[:2] + [{**reviews[2], "state": "CHANGES_REQUESTED"}]
            report = check_delivery(self.project, "password-reset", policy=policy)
            self.assertTrue(any("acceptance approval" in t for t in report.todos), report.render())
            pages.return_value = reviews
            evidence = next((self.delivery() / "evidence").glob("T1-*.json"))
            evidence.write_text(evidence.read_text().replace('"result": "pass"', '"result": "pass" '))
            report = check_delivery(self.project, "password-reset", policy=policy)
            self.assertTrue(any("subject digest does not match" in e for e in report.errors), report.render())
            # A deferred blocker cannot be excused in provider mode.
            evidence.write_text(evidence.read_text().replace('"result": "pass" ', '"result": "pass"'))
            self.write_review(self.project.fingerprint(), findings="- F1 [blocker]: risk")
            (self.delivery() / "deferred.md").write_text("- F1: later\n")
            report = check_delivery(self.project, "password-reset", policy=policy)
            self.assertTrue(any("deferral needs a trusted risk approval" in e for e in report.errors))
            policy.number = None
            report = check_delivery(self.project, "password-reset", policy=policy)
            self.assertTrue(any("needs the PR or MR number" in e for e in report.errors), "fails closed without the PR number")


class AssuranceTests(TrustedCase):
    def test_signed_delivery_and_stable_dossier(self):
        self.prepare()
        report = check_delivery(self.project, "password-reset", policy=self.policy)
        self.assertEqual((report.exit_code, report.status), (0, "verified"), report.render())
        data = report_data(self.project, "password-reset", self.policy)
        self.assertTrue(data["accepted"])
        self.assertEqual(data["matrix"][0]["criterion"], "auth/AC-001")
        self.assertEqual(len(data["approvals"]), 3)
        living, archive = deliver(self.project, "password-reset", self.policy)
        self.assertIn("### REQ-001:", living.read_text())
        self.assertIn("AC-003:", living.read_text())
        receipt = json.loads((archive / "reports/acceptance.json").read_text())
        self.assertTrue(receipt["accepted"])
        self.assertIn("review.md", receipt["artifacts_sha256"])

    def test_local_is_checked_and_cannot_deliver(self):
        self.prepare()
        report = check_delivery(self.project, "password-reset")
        self.assertEqual(report.status, "checked")
        with self.assertRaises(AtipSpecError):
            deliver(self.project, "password-reset")

    def test_fabricated_evidence_and_tampering_fail(self):
        self.prepare()
        evidence, _ = load_evidence(self.delivery() / "evidence")
        path = evidence["T1"].path
        original = path.read_text()
        for change in ({"commands": []}, {"result": "pass", "commands": [{"command": "false", "exit_code": 1}]},
                       {"delivery": "different"}, {"tree_after": "other"}):
            data = json.loads(original)
            data.update(change)
            path.write_text(json.dumps(data))
            report = check_delivery(self.project, "password-reset", policy=self.policy)
            self.assertFalse(report.ok, report.render())
        path.write_text(original.replace('"platform":', '"changed":'))
        report = check_delivery(self.project, "password-reset", policy=self.policy)
        self.assertTrue(any("attestation" in e for e in report.errors))

    def test_attest_refuses_an_altered_test_report(self):
        self.prepare()
        evidence, _ = load_evidence(self.delivery() / "evidence")
        path = evidence["T1"].path
        data = json.loads(path.read_text())
        data["reports"] = [{"path": ".atipspec/tmp/junit.xml", "copy": "logs/missing-report.xml", "sha256": "0", "total": 1, "failed": 0}]
        data["tests"] = [{"id": "t", "status": "passed"}]
        path.write_text(json.dumps(data))
        with self.assertRaises(AtipSpecError) as caught:
            attest(self.project, "password-reset", self.policy, "ci", self.keys["ci"], "https://ci.example/runs/2")
        self.assertIn("test report is missing or altered", str(caught.exception))

    def test_approval_identity_role_tampering_and_revocation(self):
        self.prepare()
        path = self.delivery() / "approvals/acceptance-qa.json"
        data = json.loads(path.read_text())
        data["identity"] = "author"
        path.write_text(json.dumps(data))
        self.assertFalse(valid_approvals(self.project, "password-reset", "acceptance", self.policy, "author"))
        self.approve("acceptance", "qa")
        # Same identity, different externally enrolled key: old approval no longer trusted.
        self.policy.data["signers"] = [s for s in self.policy.data["signers"] if s["identity"] != "qa"]
        self.assertFalse(valid_approvals(self.project, "password-reset", "acceptance", self.policy, "author"))
        with self.assertRaises(AtipSpecError):
            self.approve("acceptance", "ci")

    def test_deferral_needs_risk_expiry_and_reacceptance(self):
        self.prepare()
        self.write_review(self.project.fingerprint(), findings="- F1 [blocker]: known risk")
        (self.delivery() / "deferred.md").write_text("- F1: owner risk, resolve in follow-up ticket QA-12\n")
        self.assertFalse(check_delivery(self.project, "password-reset", policy=self.policy).ok)
        with self.assertRaises(AtipSpecError):
            self.approve("exception:F1", "risk")
        expiry = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        self.approve("exception:F1", "risk", expiry)
        self.approve("acceptance", "qa")
        report = check_delivery(self.project, "password-reset", policy=self.policy)
        self.assertTrue(report.ok, report.render())
        (self.delivery() / "deferred.md").write_text("- F1: changed terms\n")
        self.assertFalse(check_delivery(self.project, "password-reset", policy=self.policy).ok)

    def test_missing_contract_proposed_decision_and_missing_base(self):
        self.prepare()
        self.write_contract('require-command "true"\nforbid-path "bad.js"')
        self.run_cli("decision", "changed", "--title", "Changed", "--affects", "contract")
        # Under a policy the signed approvals rule, so the local acceptance drift does not hide these errors.
        self.assertTrue(any("without a new decision" in e for e in check_delivery(self.project, "password-reset", policy=self.policy).errors))
        self.project.contract.unlink()
        self.assertTrue(any("missing" in e for e in check_delivery(self.project, "password-reset", policy=self.policy).errors))
        self.write_contract('require-command "true"')
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("base: ", "unused: "))
        self.assertTrue(any("base commit" in e for e in check_delivery(self.project, "password-reset", policy=self.policy).errors))

    def test_policy_location_pin_and_corporate_rule(self):
        self.prepare()
        inside = self.root / "policy.toml"
        inside.write_text(self.policy_path.read_text())
        with self.assertRaises(AtipSpecError):
            TrustPolicy.load(inside, self.root)
        with self.assertRaises(AtipSpecError):
            TrustPolicy.load(self.policy_path, self.root, "0" * 64)
        self.policy.data["contract_rules"] = ['forbid-path "README.md"']
        self.assertTrue(any("corporate policy" in e for e in check_delivery(self.project, "password-reset", policy=self.policy).errors))

    def test_report_escapes_html(self):
        self.prepare()
        data = report_data(self.project, "password-reset")
        data["title"] = "<script>alert(1)</script>"
        rendered = render_report(data, "html")
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_output_log_tampering_blocks_acceptance(self):
        self.prepare()
        records, _ = load_evidence(self.delivery() / "evidence")
        record = records["T1"]
        log = record.path.parent / record.commands[0]["output_path"]
        log.write_text("fabricated output")
        report = check_delivery(self.project, "password-reset", policy=self.policy)
        self.assertTrue(any("output log" in e for e in report.errors))
        self.assertTrue(any("acceptance approval" in t for t in report.todos))

    def test_expired_signed_exception_is_rejected(self):
        from atipspec.trust import sign_document
        self.prepare()
        self.write_review(self.project.fingerprint(), findings="- F1 [major]: risk")
        (self.delivery() / "deferred.md").write_text("- F1: resolve in QA-12\n")
        expiry = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        path = self.approve("exception:F1", "risk", expiry)
        data = json.loads(path.read_text())
        data["expires"] = "2020-01-01T00:00:00Z"
        sign_document(path, data, "risk", self.keys["risk"], self.policy, "risk", self.root)
        self.assertFalse(valid_approvals(self.project, "password-reset", "exception:F1", self.policy, "author"))

    def test_unknown_test_mapping_and_dirty_source_fail(self):
        self.prepare()
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text().replace("Tests: AC-003", "Tests: AC-999"))
        report = check_delivery(self.project, "password-reset", policy=self.policy)
        self.assertTrue(any("AC-999" in e for e in report.errors))
        self.assertTrue(any("Commit the candidate" in e for e in report.errors))

    def test_export_does_not_invalidate_candidate(self):
        self.prepare()
        code, out, err = self.run_cli("report", "password-reset", "--format", "html", "--out", ".atipspec/tmp/report.html", "--policy", str(self.policy_path))
        self.assertEqual(code, 0, err)
        self.assertTrue(check_delivery(self.project, "password-reset", policy=self.policy).ok)
        code, _, err = self.run_cli("report", "password-reset", "--out", "source-changing-report.md")
        self.assertEqual(code, 1)
        self.assertIn("do not invalidate", err)
