import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from atipspec.cli import main
from atipspec.install import CLIENT_PATHS, CLIENTS, installed_clients, shipped_skills, write_installation
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
                         "name: Demo\nlanguage: es\napprove_plan: true\nreview_rounds: 2\ncontext_budget: 800\nstrict_scope: false\ncriteria_syntax: ears\nstrict_criteria: false\nmax_requirements: 5\nmax_tasks: 8\nmax_age_hours: 48\n")
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
        Path(".atipspec/config.yaml").write_text("name: Demo\nlanguage: es\ncontext_budget: 300\n")
        self.assertEqual(main(["init", "--language", "en"]), 0)
        self.assertEqual(Path(".atipspec/config.yaml").read_text(),
                         "name: Demo\nlanguage: en\napprove_plan: true\nreview_rounds: 2\ncontext_budget: 300\nstrict_scope: false\ncriteria_syntax: ears\nstrict_criteria: false\nmax_requirements: 5\nmax_tasks: 8\nmax_age_hours: 48\n")
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
