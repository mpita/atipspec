import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from atipspec.cli import main
from atipspec.enterprise import scaffold
from atipspec.errors import AtipSpecError
from atipspec.install import (CLIENT_PATHS, CLIENTS, PERMISSION_RULES, framework_changes, installed_clients,
                              permission_rules_state, shipped_skills, write_installation)
from atipspec.project import resource_root
from atipspec.trust import TrustPolicy
from atipspec.ui import NoRawTerminal


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.enterContext(contextlib.chdir(self.root))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        self.enterContext(patch("builtins.input", side_effect=AssertionError("unexpected prompt")))
        self.enterContext(patch("atipspec.ui.interactive", return_value=False))

    def test_init_creates_layout_framework_and_selected_skill(self):
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "codex"]), 0)
        self.assertTrue(Path(CLIENT_PATHS["codex"]).is_file())
        self.assertFalse(Path(CLIENT_PATHS["claude"]).exists())
        self.assertFalse(Path(".claude/settings.json").exists(), "Codex rules are not installed until verified")
        # Installed skills must match the shipped content, including updates.
        skills = shipped_skills()
        self.assertEqual(set(skills), {"atipspec", "atipspec-explore", "atipspec-spec", "atipspec-fix", "atipspec-plan",
                                       "atipspec-build", "atipspec-review", "atipspec-deliver",
                                       "atipspec-contract", "atipspec-curate", "atipspec-ship"})
        for name, content in skills.items():
            path = Path(CLIENTS["codex"].skill_path(name))
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.read_bytes(), content)
        self.assertTrue(Path(".atipspec/framework/rules.md").is_file())
        for folder in ("specs", "deliveries", "archive", "decisions", "initiatives"):
            self.assertTrue(Path(".atipspec", folder).is_dir())
        for document in ("contract.md", "overview.md", "glossary.md"):
            self.assertIn("Demo", Path(".atipspec", document).read_text())
        for resource in ("workflows/explore.md", "workflows/spec.md", "workflows/plan.md", "workflows/build.md",
                         "workflows/review.md", "workflows/contract.md", "workflows/curate.md",
                         "templates/spec.md", "templates/review-rubric.md", "templates/decision.md"):
            self.assertTrue(Path(".atipspec/framework", resource).is_file(), resource)
        self.assertEqual(Path(".atipspec/config.yaml").read_text(),
                         "name: Demo\nlanguage: es\napprove_plan: true\nreview_rounds: 3\ncontext_budget: 800\nstrict_scope: true\ncriteria_syntax: ears\nstrict_criteria: true\nmax_requirements: 5\nmax_tasks: 8\nmax_age_hours: 8\ntrust: optional\nrequire_proof: false\nrequire_isolated_review: false\nexempt_paths: []\n")
        self.assertIn("tmp/", Path(".atipspec/.gitignore").read_text())

    def test_prompts_are_used_when_flags_are_missing(self):
        # A terminal without raw key reading falls back to the numbered selector.
        with patch("atipspec.ui.interactive", return_value=True), \
             patch("atipspec.ui.key_reader", side_effect=NoRawTerminal), \
             patch("builtins.input", side_effect=["Mi proyecto", "3", "9", "1, 3"]):
            self.assertEqual(main(["init"]), 0)
        self.assertTrue(Path(".atipspec/config.yaml").read_text().startswith('name: "Mi proyecto"\nlanguage: pt\n'))
        self.assertTrue(Path(CLIENT_PATHS["claude"]).is_file())
        self.assertTrue(Path(CLIENT_PATHS["cursor"]).is_file())
        self.assertFalse(Path(CLIENT_PATHS["codex"]).exists())

    def test_without_a_terminal_init_uses_defaults_and_install_asks_for_a_flag(self):
        self.assertEqual(main(["init"]), 0)
        self.assertTrue(Path(".atipspec/config.yaml").read_text().startswith(f"name: {self.root.name}\nlanguage: en\n"))
        self.assertEqual(list(Path(".").rglob("SKILL.md")), [])
        self.assertEqual(main(["install"]), 1)
        self.assertEqual(main(["install", "--client", "gemini"]), 0)
        self.assertTrue(Path(CLIENT_PATHS["gemini"]).is_file())

    def test_reinstall_is_idempotent_and_preserves_project_files(self):
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es"]), 0)
        Path("AGENTS.md").write_text("Existing instructions")
        args = ["install"]
        for client in CLIENT_PATHS:
            args += ["--client", client]
        self.assertEqual(main(args), 0)
        self.assertEqual(len(list(Path(".").rglob("SKILL.md"))),
                         len(set(CLIENT_PATHS.values())) * len(shipped_skills()))
        before = {p: p.read_bytes() for p in Path(".").rglob("*") if p.is_file()}
        self.assertEqual(main(args), 0)
        self.assertEqual(before, {p: p.read_bytes() for p in Path(".").rglob("*") if p.is_file()})
        self.assertEqual(Path("AGENTS.md").read_text(), "Existing instructions")

    def test_existing_custom_skill_is_kept_and_reported_as_outdated(self):
        skill = Path(CLIENT_PATHS["codex"])
        skill.parent.mkdir(parents=True)
        skill.write_text("User customization")
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "codex"]), 0)
        self.assertTrue(Path(".atipspec/config.yaml").is_file())
        self.assertEqual(skill.read_text(), "User customization")
        self.assertEqual(installed_clients(self.root), {"codex": "outdated", "antigravity": "outdated"})

    def test_init_again_shows_state_and_applies_flags(self):
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "codex"]), 0)
        before = {p: p.read_bytes() for p in Path(".").rglob("*") if p.is_file()}
        self.assertEqual(main(["init"]), 0)
        self.assertEqual(before, {p: p.read_bytes() for p in Path(".").rglob("*") if p.is_file()})
        self.assertEqual(main(["init", "--client", "cursor"]), 0)
        self.assertTrue(Path(CLIENT_PATHS["cursor"]).is_file())
        Path(".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\ncontext_budget: 300\nstrict_criteria: false\n")
        self.assertEqual(main(["init", "--language", "en"]), 0)
        self.assertEqual(Path(".atipspec/config.yaml").read_text(),
                         "name: Demo\nlanguage: en\napprove_plan: true\nreview_rounds: 3\ncontext_budget: 300\nstrict_scope: true\ncriteria_syntax: ears\nstrict_criteria: false\nmax_requirements: 5\nmax_tasks: 8\nmax_age_hours: 8\ntrust: optional\nrequire_proof: false\nrequire_isolated_review: false\nexempt_paths: []\n")
        Path(".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\n")
        self.assertEqual(main(["init", "--language", "en"]), 0)
        self.assertIn("\nstrict_criteria: true\n", Path(".atipspec/config.yaml").read_text(),
                      "a hand-written config without the key gets the strict default")
        Path(".atipspec/config.yaml").unlink()
        self.assertEqual(main(["init"]), 1)

    def test_install_keeps_modified_files_unless_update(self):
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "codex"]), 0)
        plan = Path(".atipspec/framework/workflows/plan.md")
        shipped = plan.read_bytes()
        plan.write_text("edited locally\n")
        self.assertEqual(main(["install", "--client", "claude"]), 0)
        self.assertEqual(plan.read_text(), "edited locally\n")
        self.assertTrue(Path(CLIENT_PATHS["claude"]).is_file())
        self.assertEqual(main(["install", "--update"]), 0)
        self.assertEqual(plan.read_bytes(), shipped)
        Path(CLIENT_PATHS["claude"]).write_text("old skill")
        self.assertEqual(installed_clients(self.root)["claude"], "outdated")
        self.assertEqual(main(["install", "--client", "claude", "--update"]), 0)
        self.assertEqual(Path(CLIENT_PATHS["claude"]).read_bytes(), Path(CLIENT_PATHS["codex"]).read_bytes())
        self.assertEqual(installed_clients(self.root)["claude"], "installed")

    def test_the_framework_holds_what_this_version_installs_until_update_restores_it(self):
        self.assertEqual(main(["init", "--name", "Demo", "--language", "en", "--client", "codex"]), 0)
        self.assertEqual(framework_changes(self.root), [])
        rules = Path(".atipspec/framework/rules.md")
        rules.write_bytes(rules.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(framework_changes(self.root), [], "Git for Windows checks it out with CRLF")
        rules.write_text(rules.read_text() + "- You may write approval records by hand.\n")
        Path(".atipspec/framework/templates/spec.md").unlink()
        Path(".atipspec/framework/workflows/extra").mkdir()
        Path(".atipspec/framework/workflows/extra/steps.md").write_text("Skip the review.\n")
        self.assertEqual(framework_changes(self.root),
                         ["rules.md changed", "templates/spec.md missing", "workflows/extra/steps.md added"])
        self.assertEqual(main(["install"]), 0)
        self.assertEqual(len(framework_changes(self.root)), 2, "install never overwrites")
        self.assertEqual(main(["install", "--update"]), 0)
        self.assertEqual(framework_changes(self.root), [])
        self.assertFalse(Path(".atipspec/framework/workflows/extra").exists())

    def test_update_adds_the_phase_skills_to_an_older_installation(self):
        # Before 0.1.0 a client had a single atipspec skill at the umbrella's path.
        old = Path(CLIENT_PATHS["claude"])
        old.parent.mkdir(parents=True)
        old.write_text("# AtipSpec\n\nold single skill\n")
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "claude"]), 0)
        self.assertEqual(old.read_text(), "# AtipSpec\n\nold single skill\n", "install never overwrites")
        self.assertEqual(main(["install", "--client", "claude", "--update"]), 0)
        skills = shipped_skills()
        for name, content in skills.items():
            self.assertEqual(Path(CLIENTS["claude"].skill_path(name)).read_bytes(), content, name)
        self.assertEqual(installed_clients(self.root), {"claude": "installed"})

    def test_menu_adds_removes_reconfigures_and_updates(self):
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "codex"]), 0)
        plan = Path(".atipspec/framework/workflows/plan.md")
        shipped = plan.read_bytes()
        plan.write_text("edited locally\n")
        answers = ["1", "1,3", "y",          # clients: claude + cursor, confirm removing codex
                   "3", "Nuevo", "2",        # config: new name, language es
                   "2", "",                  # update: accept the default yes
                   "4"]                      # done
        with patch("atipspec.ui.interactive", return_value=True), \
             patch("atipspec.ui.key_reader", side_effect=NoRawTerminal), \
             patch("builtins.input", side_effect=answers):
            self.assertEqual(main(["init"]), 0)
        self.assertTrue(Path(CLIENT_PATHS["claude"]).is_file())
        self.assertTrue(Path(CLIENT_PATHS["cursor"]).is_file())
        self.assertFalse(Path(CLIENT_PATHS["codex"]).exists())
        self.assertTrue(Path(".atipspec/config.yaml").read_text().startswith("name: Nuevo\nlanguage: es\n"))
        self.assertEqual(plan.read_bytes(), shipped)

    def test_claude_permission_rules_merge_into_existing_settings(self):
        rules = PERMISSION_RULES["claude"]
        settings = Path(".claude/settings.json")
        settings.parent.mkdir()
        existing = {"model": "opus", "permissions": {"allow": ["Bash(npm test)"], "deny": ["Read(./.env)"]},
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo done"}]}]}}
        settings.write_text(json.dumps(existing))
        self.assertEqual(main(["init", "--name", "Demo", "--language", "en", "--client", "claude"]), 0)
        data = json.loads(settings.read_text())
        self.assertEqual((data["model"], data["hooks"]), (existing["model"], existing["hooks"]))
        self.assertEqual(data["permissions"]["allow"], ["Bash(npm test)"])
        self.assertEqual(data["permissions"]["ask"], list(rules.ask))
        self.assertEqual(data["permissions"]["deny"], ["Read(./.env)", *rules.deny])
        self.assertEqual(permission_rules_state(self.root, "claude"), "installed")
        before = settings.read_bytes()
        self.assertEqual(main(["install", "--client", "claude"]), 0)
        self.assertEqual(main(["install", "--update"]), 0)
        self.assertEqual(settings.read_bytes(), before, "reinstalling changes no byte")
        # A removed rule makes the client outdated; --update puts it back without touching the rest.
        data["permissions"]["ask"] = []
        settings.write_text(json.dumps(data))
        self.assertEqual(permission_rules_state(self.root, "claude"), "partial")
        self.assertEqual(installed_clients(self.root), {"claude": "outdated"})
        self.assertEqual(main(["install", "--update"]), 0)
        self.assertEqual(json.loads(settings.read_text())["permissions"]["ask"], list(rules.ask))
        self.assertEqual(installed_clients(self.root), {"claude": "installed"})

    def test_claude_code_asks_before_editing_the_ci_and_its_settings(self):
        from atipspec.audit import audit_project
        from atipspec.project import Project
        rules = ("Edit(/.github/workflows/**)", "Edit(/.gitlab-ci.yml)", "Edit(/.claude/settings*.json)")
        self.assertEqual(main(["init", "--name", "Demo", "--language", "en", "--client", "claude"]), 0)
        settings = Path(".claude/settings.json")
        data = json.loads(settings.read_text())
        for rule in rules:
            self.assertIn(rule, data["permissions"]["ask"])
        data["permissions"]["ask"].remove("Edit(/.github/workflows/**)")
        settings.write_text(json.dumps(data))
        self.assertEqual(permission_rules_state(self.root, "claude"), "partial")
        warnings = audit_project(Project.find(self.root)).of("warning")
        self.assertTrue(any("are partial (without ask Edit(/.github/workflows/**))" in text for text in warnings),
                        warnings)
        self.assertEqual(main(["install", "--update"]), 0)
        self.assertEqual(permission_rules_state(self.root, "claude"), "installed")
        self.assertFalse([text for text in audit_project(Project.find(self.root)).of("warning")
                          if "permission rules" in text])

    def test_settings_that_are_not_plain_json_are_left_alone(self):
        settings = Path(".claude/settings.json")
        settings.parent.mkdir()
        settings.write_text('{\n  // the team model\n  "model": "opus"\n}\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["init", "--name", "Demo", "--language", "en", "--client", "claude"]), 0)
        self.assertEqual(settings.read_text(), '{\n  // the team model\n  "model": "opus"\n}\n')
        self.assertIn("is not plain JSON", out.getvalue())
        self.assertIn("Bash(*atipspec accept *)", out.getvalue(), "the rules to add by hand are printed")
        self.assertEqual(permission_rules_state(self.root, "claude"), "invalid")
        Path("outside.json").write_text("{}")
        settings.unlink()
        settings.symlink_to(self.root / "outside.json")
        self.assertEqual(permission_rules_state(self.root, "claude"), "invalid")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["install", "--update"]), 0)
        self.assertIn(".claude/settings.json is a symlink", out.getvalue())
        self.assertTrue(settings.is_symlink(), "a symlinked settings file is never replaced")
        self.assertEqual(Path("outside.json").read_text(), "{}", "nor is its target written")

    def test_removing_claude_removes_only_the_atipspec_rules(self):
        settings = Path(".claude/settings.json")
        settings.parent.mkdir()
        settings.write_text(json.dumps({"permissions": {"deny": ["Read(./.env)"]}}))
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "claude", "--client", "codex"]), 0)
        answers = ["1", "2", "y",          # clients: keep codex only, confirm removing claude
                   "4"]                    # done
        with patch("atipspec.ui.interactive", return_value=True), \
             patch("atipspec.ui.key_reader", side_effect=NoRawTerminal), \
             patch("builtins.input", side_effect=answers):
            self.assertEqual(main(["init"]), 0)
        self.assertFalse(Path(CLIENT_PATHS["claude"]).exists())
        self.assertEqual(json.loads(settings.read_text()), {"permissions": {"deny": ["Read(./.env)"]}})

    def test_symlink_parent_is_not_followed(self):
        Path("outside").mkdir()
        Path(".agents").symlink_to(self.root / "outside", target_is_directory=True)
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "codex"]), 1)
        self.assertEqual(list(Path("outside").iterdir()), [])
        self.assertFalse(Path(".atipspec").exists())

    def test_write_failure_removes_only_new_files(self):
        first, second = self.root / "new/first.md", self.root / "new/second.md"
        Path("existing.txt").write_text("Keep me")
        original_open = Path.open

        def fail_second(path, *args, **kwargs):
            if path == second:
                raise OSError("Simulated write failure")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", fail_second), self.assertRaises(OSError):
            write_installation(self.root, {first: b"first", second: b"second"})
        self.assertFalse(Path("new").exists())
        self.assertEqual(Path("existing.txt").read_text(), "Keep me")
        self.assertEqual(write_installation(self.root, {self.root / "existing.txt": b"other"}),
                         (0, [self.root / "existing.txt"]))
        self.assertEqual(Path("existing.txt").read_text(), "Keep me")

    def test_init_warns_when_a_git_repository_has_no_gitignore(self):
        import subprocess
        subprocess.run(["git", "init", "-q", "."], check=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["init", "--name", "Demo", "--language", "en", "--client", "codex"]), 0)
        self.assertIn("No .gitignore", out.getvalue())
        Path(".gitignore").write_text("__pycache__/\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["install", "--client", "codex"]), 0)
        self.assertNotIn("No .gitignore", out.getvalue())

    def test_commands_need_an_initialized_project(self):
        self.assertEqual(main(["status"]), 1)
        self.assertEqual(main(["init", "--name", "Demo", "--language", "es", "--client", "nope"]), 1)


if __name__ == "__main__":
    unittest.main()


class EnterpriseTemplateTests(unittest.TestCase):
    def test_evidence_templates_attest_only_this_run(self):
        folder = resource_root() / "enterprise"
        trusted = (folder / "github-evidence-trusted.yml").read_text(encoding="utf-8")
        caller = (folder / "github-evidence-caller.yml").read_text(encoding="utf-8")
        for text in ("workflow_call", "ref: ${{ github.event.pull_request.head.sha }}", "clear_evidence(project)",
                     "records_to_attest(project)", "python -I -m pip install"):
            self.assertIn(text, trusted)
        produce = trusted.split("\n  produce:\n", 1)[1].split("\n  attest:\n", 1)[0]
        self.assertNotIn("id-token", produce, "the job that runs candidate commands holds no OIDC token")
        self.assertNotIn("attestations:", produce)
        self.assertEqual(trusted.split("subject-path:", 1)[1].strip(), "${{ steps.records.outputs.paths }}",
                         "no glob attests what the branch committed")
        # A job the pull request adds to the caller runs in the same run and can replace an artifact of that name.
        upload = produce.split("- uses: actions/upload-artifact@v4\n", 1)[1].split("\n      - ", 1)[0]
        self.assertIn("        id: upload\n", upload)
        self.assertIn("      artifact-id: ${{ steps.upload.outputs.artifact-id }}\n", produce)
        attest = trusted.split("\n  attest:\n", 1)[1]
        download = attest.split("- uses: actions/download-artifact@v4\n", 1)[1].split("\n      - ", 1)[0]
        self.assertIn("artifact-ids: ${{ needs.produce.outputs.artifact-id }}\n", download)
        self.assertIn("merge-multiple: true\n", download, "by ID, v4 extracts under the artifact's name without it")
        self.assertNotRegex(download, r"\n\s+name:")
        workflow = caller.split("\nname:", 1)[1]
        self.assertIn("on: pull_request\n", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("workflow_dispatch", workflow)
        self.assertRegex(workflow, r"uses: [\w-]+/atipspec-trusted/\.github/workflows/atipspec-evidence\.yml@REPLACE_WITH_40_HEX_COMMIT")
        with tempfile.TemporaryDirectory() as temporary:
            written = {path.name for path in scaffold(Path(temporary).resolve() / "enterprise")}
        self.assertLessEqual({"github-evidence-trusted.yml", "github-evidence-caller.yml", "policy.provider.example.toml"},
                             written)
        self.assertNotIn("github-evidence.yml", written)

    def test_the_ssh_collector_signs_no_committed_record(self):
        adoption = (resource_root() / "enterprise" / "ADOPTION.md").read_text(encoding="utf-8")
        collector = adoption.split("\n6. ", 1)[1].split("\n7. ", 1)[0]
        self.assertIn("clear_evidence(Project.find())", collector)
        self.assertLess(collector.index("clear_evidence(Project.find())"), collector.index("calls `attest`"))

    def test_the_provider_policy_example_loads_only_with_a_pinned_commit(self):
        with tempfile.TemporaryDirectory() as candidate, tempfile.TemporaryDirectory() as secure:
            policy = Path(secure) / "provider.toml"
            text = (resource_root() / "enterprise" / "policy.provider.example.toml").read_text(encoding="utf-8")
            policy.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AtipSpecError, "signer_digest must pin"):
                TrustPolicy.load(policy, Path(candidate))
            policy.write_text(text.replace("REPLACE_WITH_40_HEX_COMMIT", "0123456789abcdef0123456789abcdef01234567"),
                              encoding="utf-8")
            self.assertEqual(TrustPolicy.load(policy, Path(candidate)).mode, "provider")
