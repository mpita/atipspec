"""Concurrent intents and immutable cross-repository inputs."""
import json
from pathlib import Path
import subprocess
import tempfile

from atipspec.accept import is_current
from atipspec.check import check_delivery
from atipspec.context import build_context, render_context
from atipspec.project import Project
from atipspec.teams import board, conflicts, pin_contract, read_contracts, dependencies
from atipspec.errors import AtipSpecError
from tests.helpers import ProjectCase


class TeamTests(ProjectCase):
    def proposal(self, slug, requirement="REQ-001", criterion="AC-001", outcome="success"):
        self.new_delivery(slug)
        project = Project.find(self.root)
        project.tmp.mkdir(parents=True, exist_ok=True)
        source = project.tmp / f"{slug}.md"
        source.write_text(f"# Auth\n### {requirement}: Access\n#### {criterion}: Access result\n- WHEN accessing\n- THEN {outcome}\n")
        code, out, err = self.run_cli("spec-bind", slug, "--file", str(source))
        self.assertEqual(code, 0, out + err)
        (self.delivery(slug) / "plan.md").write_text(f"# Plan\n### T1: Access\nCovers: {requirement}\nTests: {criterion}\n## Final verification\nVerify:\n- `true`\n")
        return project

    def two_branches(self, other_requirement="REQ-001", other_criterion="AC-001", outcome="other"):
        self.commit("fixture baseline")
        base = self.git("rev-parse", "HEAD").strip()
        self.proposal("team-a", outcome="first")
        self.commit("fixture: team A declared proposal")
        self.git("branch", "team-a")
        self.git("switch", "-q", "-c", "team-b", base)
        project = self.proposal("team-b", other_requirement, other_criterion, outcome)
        (project.dot / "teams.json").write_text(json.dumps({"schema": 1, "refs": ["refs/heads/team-a"]}))
        return project

    def test_incompatible_shared_requirement_blocks_approval(self):
        project = self.two_branches()
        issues = conflicts(project, "team-b")
        self.assertEqual(len(issues), 1)
        self.assertIn("auth/REQ-001", issues[0])
        code, out, err = self.run_cli("accept", "team-b", "proposal")
        self.assertEqual(code, 1)
        self.assertIn("incompatible declared behavior", err)
        data = board(project)
        self.assertEqual({row["slug"] for row in data["changes"]}, {"team-a", "team-b"})
        self.assertIn("unpublished", data["visibility"])

    def test_independent_requirements_do_not_block_each_other(self):
        project = self.two_branches("REQ-002", "AC-002")
        self.assertEqual(conflicts(project, "team-b"), [])
        code, out, err = self.run_cli("accept", "team-b", "proposal")
        self.assertEqual(code, 0, out + err)

    def test_reconciled_behavior_can_proceed(self):
        project = self.two_branches(outcome="first")
        self.assertEqual(conflicts(project, "team-b"), [])
        code, out, err = self.run_cli("accept", "team-b", "proposal")
        self.assertEqual(code, 0, out + err)

    def test_owner_is_required_when_capability_has_ownership(self):
        project = self.proposal("auth-change")
        (project.dot / "teams.json").write_text(json.dumps({"schema": 1, "owners": {"auth": ["ana"]}}))
        self.assertEqual(self.run_cli("accept", "auth-change", "proposal")[0], 1)
        spec = self.delivery("auth-change") / "spec.md"
        spec.write_text(spec.read_text().replace("owner: null", "owner: ana"))
        self.assertEqual(self.run_cli("accept", "auth-change", "proposal")[0], 0)

    def test_dependency_blocks_acceptance_but_not_proposal(self):
        project = self.proposal("frontend")
        spec = self.delivery("frontend") / "spec.md"
        spec.write_text(spec.read_text().replace("schema: 2", "schema: 2\ndepends_on: [api]"))
        self.assertEqual(dependencies(project, "frontend"), ["Waiting for accepted dependency api"])
        self.assertEqual(self.run_cli("accept", "frontend", "proposal")[0], 0)
        report = check_delivery(project, "frontend")
        self.assertTrue(report.blocking(("integration",)))
        receipt = project.archive / "api/reports/acceptance.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({"schema": 1, "delivery": "api", "accepted": False}))
        self.assertTrue(dependencies(project, "frontend"))
        receipt.write_text(json.dumps({"schema": 1, "delivery": "api", "accepted": True}))
        self.assertEqual(dependencies(project, "frontend"), [])

    def test_existing_branch_names_are_preserved(self):
        self.commit("fixture initialized")
        self.git("branch", "bug/SHOP-42")
        code, out, err = self.run_cli("new", "bug-42", "--title", "Bug", "--branch", "--branch-name", "bug/SHOP-42", "--reuse-branch")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.git("branch", "--show-current").strip(), "bug/SHOP-42")
        code, _, err = self.run_cli("new", "bad", "--title", "Bad", "--branch-name", "ignored")
        self.assertEqual(code, 1)
        self.assertIn("need --branch or --worktree", err)

    def test_contract_uses_pinned_commit_not_mutable_checkout(self):
        project = self.proposal("frontend")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        api = Path(temp.name)
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=api, env=self.env, text=True).strip()
        git("init", "-q", "-b", "main")
        (api / "customers.json").write_text('{"version": 1}\n')
        git("add", "customers.json")
        git("commit", "-q", "-m", "fixture contract v1")
        first = git("rev-parse", "HEAD")
        (project.dot / "teams.json").write_text(json.dumps({"schema": 1, "repositories": {"api": str(api)}}))
        self.assertEqual(pin_contract(project, "frontend", "customers", "api", "main", "customers.json"), first)
        self.assertEqual(self.run_cli("accept", "frontend", "proposal")[0], 0)
        (api / "customers.json").write_text('{"version": 2}\n')
        git("add", "customers.json")
        git("commit", "-q", "-m", "fixture contract v2")
        self.assertEqual(read_contracts(project, "frontend")[0]["content"], '{"version": 1}\n')
        self.assertTrue(is_current(project, "frontend", "proposal"))
        context = render_context(build_context(project, "frontend")[0])
        self.assertIn(first, context)
        self.assertIn('{"version": 1}', context)
        self.assertNotIn('{"version": 2}', context)
        pin_contract(project, "frontend", "customers", "api", "main", "customers.json")
        self.assertFalse(is_current(project, "frontend", "proposal"))
        data_path = self.delivery("frontend") / "contracts.json"
        data = json.loads(data_path.read_text())
        data["contracts"][0]["revision"] = "main"
        data_path.write_text(json.dumps(data))
        with self.assertRaisesRegex(AtipSpecError, "immutable"):
            read_contracts(project, "frontend")
