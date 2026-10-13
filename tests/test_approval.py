"""Human approval without self-approval: the approval code of the presented
content, the channel each record states, the proposal record in guided
deliveries, and the contract's recorded acceptance with its decisions."""
import json
import os
import re
import shutil
import sys
import unittest
from unittest.mock import patch

from atipspec.accept import (approval_code, contract_acceptance, detect_channel, is_current, normalize_code,
                             read_record, short_code)
from atipspec.check import check_delivery
from atipspec.context import build_context
from atipspec.project import Project
from atipspec.reporting import get_report, render_report, report_data
from atipspec.trust import canonical, digest, subject, subject_content
from tests.helpers import ProjectCase

SCENARIOS = """# Auth
### REQ-001: Expired links are rejected
The system must reject a reset link after thirty minutes.
#### AC-001: Expired link
- **GIVEN** a link issued thirty-one minutes ago
- **WHEN** the user opens the link
- **THEN** the page displays "link expired"
"""
PLAN = "---\nscope: [\"*\", \"src/**\"]\n---\n# Plan\n### T1: Expiry\nCovers: REQ-001\nTests: AC-001\n## Final verification\nVerify:\n- `true`\n"
CODE = re.compile(r"Approval code: ([0-9A-Z]{4}-[0-9A-Z]{4})")


def installed_accept():
    """This process as the installed `atipspec accept` command."""
    line = ["/venv/bin/python3", "/venv/bin/atipspec", "accept"]
    return patch.multiple(sys, argv=line[1:], orig_argv=line)


class ApprovalCodeTests(unittest.TestCase):
    def test_code_is_forty_bits_in_crockford_base32(self):
        self.assertEqual(short_code("0" * 64), "0000-0000")
        self.assertEqual(short_code("f" * 64), "ZZZZ-ZZZZ")
        code = short_code(digest(b"content"))
        self.assertRegex(code, r"^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")
        self.assertNotEqual(code, short_code(digest(b"content changed")))

    def test_typed_codes_ignore_case_hyphen_and_lookalikes(self):
        self.assertEqual(normalize_code("k7m2-qx4p"), "K7M2QX4P")
        self.assertEqual(normalize_code(" K7M2QX4P "), "K7M2QX4P")
        self.assertEqual(normalize_code("O1IL-0000"), normalize_code("0111-0000"))


class GuidedCase(ProjectCase):
    """A guided delivery whose scenarios live in specs/auth.md, planned and ready to present."""

    def guided(self, slug="password-reset"):
        self.new_delivery(slug)
        project = Project.find(self.root)
        project.tmp.mkdir(parents=True, exist_ok=True)
        (project.tmp / "auth.md").write_text(SCENARIOS)
        code, out, err = self.run_cli("spec-bind", slug, "--file", str(project.tmp / "auth.md"))
        self.assertEqual(code, 0, out + err)
        (self.delivery(slug) / "plan.md").write_text(PLAN)
        return project

    def presented_code(self, *args):
        code, out, err = self.run_cli("proposal", *args)
        self.assertEqual(code, 0, out + err)
        match = CODE.search(out)
        self.assertIsNotNone(match, out)
        return match.group(1)

    def finish(self, project, slug="password-reset"):
        self.assertEqual(self.run_cli("task-done", slug, "T1", "--note", "Implemented expiry")[0], 0)
        self.assertEqual(self.run_cli("verify", slug)[0], 0)
        self.assertEqual(self.run_cli("review", slug)[0], 0)
        (self.delivery(slug) / "review.md").write_text(
            f"---\ntree: {project.fingerprint()}\nreviewer: r\nsession: isolated\n---\n- AC-001: PASS. README.md:1\n")


class LocalApprovalTests(GuidedCase):
    def test_proposal_shows_the_code_and_accept_needs_it(self):
        project = self.guided()
        code, out, _ = self.run_cli("proposal", "password-reset")
        presented = self.presented_code("password-reset")
        self.assertIn(f"`atipspec accept password-reset proposal --code {presented}`", out)
        self.assertIn(f"sha256 `{subject(project, 'password-reset', 'plan')}`", out)
        approvals = self.delivery() / "approvals"
        code, out, err = self.run_cli("accept", "password-reset", "proposal")
        self.assertEqual(code, 1, "no terminal and no code: nothing is recorded")
        self.assertIn("--code", err)
        self.assertFalse(approvals.exists())
        code, _, err = self.run_cli("accept", "password-reset", "proposal", "--code", "0000-0000")
        self.assertEqual(code, 1)
        self.assertIn("does not match the current content", err)
        self.assertNotIn(presented, err, "a mismatch never reveals the current code")
        self.assertNotIn(presented.replace("-", ""), err)
        self.assertFalse(approvals.exists())
        # The plan changes after the code was shown: the old code no longer records anything.
        plan = self.delivery() / "plan.md"
        plan.write_text(plan.read_text().replace("### T1: Expiry", "## Approach\nReject at the API.\n### T1: Expiry"))
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal", "--code", presented)[0], 1)
        self.assertFalse(approvals.exists())
        fresh = self.presented_code("password-reset")
        self.assertNotEqual(fresh, presented)
        code, out, err = self.run_cli("accept", "password-reset", "proposal", "--code", fresh.lower(), "--by", "ana")
        self.assertEqual(code, 0, out + err)
        self.assertIn("via assistant", out)
        self.assertIn("warning: channel assistant", out)
        self.assertNotIn("install --update", out, "the rules are installed; they were not what was missing")
        record = read_record(project, "password-reset", "proposal")
        self.assertEqual((record["schema"], record["code"], record["channel"], record["client"], record["by"]),
                         (2, fresh, "assistant", None, "ana"))
        self.assertEqual(record["files"], subject_content(project, "password-reset", "plan"))
        self.assertEqual(subject(project, "password-reset", "plan"),
                         digest(canonical({"delivery": "password-reset", "phase": "plan",
                                           "content": subject_content(project, "password-reset", "plan")})),
                         "per-file digests keep the subject that existing records and signatures name")


class ChannelTests(GuidedCase):
    def accept_with(self, env=None, interactive=False, typed=None, code=True):
        args = ["accept", "password-reset", "proposal"]
        if code:
            args += ["--code", self.presented_code("password-reset")]
        prompt = patch("builtins.input", return_value=typed) if typed is not None else \
            patch("builtins.input", side_effect=AssertionError("unexpected prompt"))
        with patch.dict(os.environ, env or {}), patch("atipspec.ui.interactive", return_value=interactive), prompt as asked:
            result = self.run_cli(*args)
        return result, asked

    def test_claude_code_with_intact_rules_records_client_permission(self):
        project = self.guided()
        (code, out, err), _ = self.accept_with({"CLAUDECODE": "1"})
        self.assertEqual(code, 0, out + err)
        record = read_record(project, "password-reset", "proposal")
        self.assertEqual((record["channel"], record["client"]), ("client-permission", "claude"))
        self.assertIn("via client-permission (Claude Code)", out)
        self.assertNotIn("warning", out)
        self.assertIn("note: channel client-permission: Claude Code's rules are in this project, and Claude Code "
                      f"applies them only in a session opened in {self.root}", out, "the channel says what it shows")

    def test_a_hook_that_can_answer_the_prompt_lowers_the_channel(self):
        from atipspec.audit import audit_project
        project = self.guided()
        (self.root / ".claude/settings.local.json").write_text(json.dumps(
            {"hooks": {"PermissionRequest": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "ok"}]}]}}))
        (code, out, err), _ = self.accept_with({"CLAUDECODE": "1"})
        self.assertEqual(code, 0, out + err)
        record = read_record(project, "password-reset", "proposal")
        self.assertEqual((record["channel"], record["client"]), ("assistant", "claude"))
        self.assertIn(".claude/settings.local.json has a PermissionRequest hook that runs for Bash, so Claude Code "
                      "may not ask", out)
        self.assertIn("Claude Code may not ask before `atipspec accept`", self.run_cli("status")[1])
        self.assertTrue(any("PermissionRequest hook" in text for text in audit_project(project).of("warning")))

    def test_without_claude_code_the_note_names_the_client_to_add(self):
        self.guided()
        shutil.rmtree(self.root / ".claude")
        (code, out, err), _ = self.accept_with()
        self.assertEqual(code, 0, out + err)
        self.assertIn("no client is installed here; `atipspec install --client claude` adds Claude Code's", out)
        self.assertNotIn("install --update", out, "updating configures no client that is not installed")

    def test_altered_rules_lower_the_channel_to_assistant(self):
        project = self.guided()
        settings = self.root / ".claude/settings.json"
        data = json.loads(settings.read_text())
        data["permissions"]["ask"] = []
        settings.write_text(json.dumps(data))
        (code, out, err), _ = self.accept_with({"CLAUDECODE": "1"})
        self.assertEqual(code, 0, out + err)
        record = read_record(project, "password-reset", "proposal")
        self.assertEqual((record["channel"], record["client"]), ("assistant", "claude"))
        self.assertIn("warning: channel assistant", out)
        self.assertIn("`atipspec install --update` configures Claude Code to ask", out)

    def test_another_agent_inside_claude_code_records_assistant(self):
        project = self.guided()
        cases = [({"CLAUDECODE": "1", "CODEX_SANDBOX": "seatbelt"}, ("assistant", "codex")),
                 ({"CLAUDECODE": "1", "CODEX_THREAD_ID": "019a-demo"}, ("assistant", "codex")),
                 ({"CLAUDECODE": "1", "COPILOT_CLI": "1"}, ("assistant", "github-copilot")),
                 ({"CLAUDECODE": "1", "GEMINI_CLI": "1"}, ("assistant", "gemini")),
                 ({"CLAUDECODE": "1", "AI_AGENT": "some-agent"}, ("assistant", None)),
                 ({"CLAUDECODE": "1", "AI_AGENT": "claude-code_2-1-295_agent"}, ("client-permission", "claude"))]
        for env, expected in cases:
            with patch.dict(os.environ, env), installed_accept():
                self.assertEqual(detect_channel(project), expected, env)
        (code, out, err), _ = self.accept_with({"CLAUDECODE": "1", "CODEX_SANDBOX": "seatbelt"})
        self.assertEqual(code, 0, out + err)
        record = read_record(project, "password-reset", "proposal")
        self.assertEqual((record["channel"], record["client"]), ("assistant", "codex"),
                         "Claude Code's marker reaches the agents it starts; its rules never saw their commands")
        self.assertIn("via assistant (Codex)", out)

    def test_claude_code_without_a_person_at_its_prompts_records_assistant(self):
        project = self.guided()
        cases = {"sdk-ts": "assistant", "sdk-py": "assistant", "sdk-cli": "assistant",
                 "cli": "client-permission", "claude-desktop": "client-permission", "claude-vscode": "client-permission"}
        for entrypoint, channel in cases.items():
            with patch.dict(os.environ, {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": entrypoint}), installed_accept():
                self.assertEqual(detect_channel(project), (channel, "claude"), entrypoint)
        (code, out, err), _ = self.accept_with({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "sdk-py"})
        self.assertEqual(code, 0, out + err)
        record = read_record(project, "password-reset", "proposal")
        self.assertEqual((record["channel"], record["client"]), ("assistant", "claude"),
                         "the Agent SDK loads no project settings unless its program asks, and answers its own prompts")
        self.assertIn("the Agent SDK, `claude -p`", out)

    def test_only_the_command_line_the_ask_rule_matches_records_client_permission(self):
        project = self.guided()
        args = ["accept", "password-reset", "proposal"]
        rewrite = "import sys; sys.argv = ['atipspec', 'accept', 'password-reset', 'proposal']; ..."
        cases = [(["/venv/bin/python3", "/venv/bin/atipspec", *args], "/venv/bin/atipspec", "client-permission"),
                 (["python3", "-I", "-m", "atipspec", *args], "/venv/lib/atipspec/__main__.py", "client-permission"),
                 (["python3", "-matipspec", *args], "/venv/lib/atipspec/__main__.py", "client-permission"),
                 (["python.exe", "C:/venv/Scripts/atipspec.exe", *args], "C:/venv/Scripts/atipspec", "client-permission"),
                 (["python3", "-m", "atipspec.cli", *args], "/venv/lib/atipspec/cli.py", "assistant"),
                 (["python3", "-m", "atipspec.__main__", *args], "/venv/lib/atipspec/__main__.py", "assistant"),
                 (["python3", "-c", "from atipspec.cli import main; main()", *args], "-c", "assistant"),
                 (["python3", "-c", rewrite], "atipspec", "assistant"),
                 (["python3", "approve.py", *args], "approve.py", "assistant"),
                 (["/venv/bin/python3", "/venv/bin/atipspec", "accept", "other", "proposal"], "/venv/bin/atipspec",
                  "assistant")]
        with patch.dict(os.environ, {"CLAUDECODE": "1"}):
            for line, program, channel in cases:
                with patch.multiple(sys, argv=[program, *args], orig_argv=line):
                    self.assertEqual(detect_channel(project), (channel, "claude"), line)
            line = ["/venv/bin/python3", "/venv/bin/atipspec", "run", "password-reset"]
            with patch.multiple(sys, argv=line[1:], orig_argv=line):
                self.assertEqual(detect_channel(project), ("assistant", "claude"), "another command reached accept")

    def test_terminal_asks_to_type_the_code(self):
        project = self.guided()
        typed = self.presented_code("password-reset")
        (code, out, err), asked = self.accept_with(interactive=True, typed=typed.lower(), code=False)
        self.assertEqual(code, 0, out + err)
        asked.assert_called_once()
        self.assertEqual(read_record(project, "password-reset", "proposal")["channel"], "terminal")

    def test_agent_markers_only_lower_the_channel(self):
        self.guided()
        (code, out, err), _ = self.accept_with({"AI_AGENT": "some-agent"}, interactive=True, code=False)
        self.assertEqual(code, 1, "an agent in a terminal is not a person at the prompt")
        self.assertIn("--code", err)
        (code, out, err), _ = self.accept_with({"AI_AGENT": "0"}, interactive=True, typed="0000-0000")
        self.assertEqual(code, 1, "a false marker is ignored, and the typed code must match --code")
        self.assertIn("differs from --code", err)
        self.assertFalse((self.delivery() / "approvals").exists())


class GuidedGateTests(GuidedCase):
    def test_the_legacy_pair_does_not_replace_the_proposal(self):
        project = self.guided()
        code, out, _ = self.run_cli("check", "password-reset")
        self.assertIn("Present `atipspec proposal password-reset`", out, "a complete draft: only the approval is left")
        self.assertIn("`atipspec accept password-reset proposal --code <code>`", out)
        self.assertNotIn("accept password-reset spec", out)
        for phase in ("spec", "plan"):
            code, _, err = self.run_cli("accept", "password-reset", phase, "--code", self.code(phase=phase))
            self.assertEqual(code, 1)
            self.assertIn("accept password-reset proposal", err)
        # Records written by hand with valid subjects, and a ready status: still a draft.
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("status: draft", "status: ready"))
        from atipspec.accept import acceptance_subject, record_path
        for phase in ("spec", "plan"):
            path = record_path(project, "password-reset", phase)
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps({"schema": 1, "kind": "local-acceptance", "delivery": "password-reset",
                                        "phase": phase, "subject": acceptance_subject(project, "password-reset", phase),
                                        "accepted_at": "2026-01-01T00:00:00Z", "by": "x", "head": None}))
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "draft")
        self.assertTrue(any("the proposal is not accepted" in t for t in report.todos), report.render())
        code, _, err = self.run_cli("build", "password-reset")
        self.assertEqual((code, "nothing approved to build yet" in err), (1, True))
        for path in (self.delivery() / "approvals").iterdir():
            path.unlink()
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        self.assertEqual(sorted(path.name for path in (self.delivery() / "approvals").iterdir()), ["local-proposal.json"])
        self.assertEqual(self.run_cli("build", "password-reset", "--no-context")[0], 0)

    def test_drift_names_the_changed_file(self):
        project = self.guided()
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text() + "max_tasks: 9\n")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(report.todos[0].startswith(".atipspec/config.yaml changed after the proposal's acceptance"),
                        report.render())
        self.assertIn("(outdated: .atipspec/config.yaml changed)", self.run_cli("status")[1])
        config.write_text(config.read_text().replace("max_tasks: 9\n", ""))
        canonical_spec = project.specs / "auth.md"
        canonical_spec.write_text(canonical_spec.read_text().replace("thirty minutes", "forty minutes"))
        report = check_delivery(project, "password-reset")
        self.assertTrue(report.todos[0].startswith(".atipspec/specs/auth.md REQ-001 changed after the proposal's acceptance"),
                        report.render())

    def test_no_approval_hashes_exempt_paths(self):
        self.commit("initialized")
        self.guided()
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        config = self.root / ".atipspec/config.yaml"
        original = config.read_text()
        approved = check_delivery(Project.find(self.root), "password-reset").status
        self.assertNotEqual(approved, "draft")
        for exempt in ('exempt_paths: ["docs/**"]', 'exempt_paths:\n  - "docs/**"\n  - "*.md"'):
            # As main sets it and a branch with an open delivery takes main in: only merge-check reads it.
            config.write_text(original.replace("exempt_paths: []", exempt))
            self.assertEqual(check_delivery(Project.find(self.root), "password-reset").status, approved, exempt)
            out = self.run_cli("proposal", "password-reset")[1]
            self.assertIn("This content is already accepted", out)
            self.assertNotIn("exempt_paths", out)
        config.write_text(original.replace("exempt_paths: []", 'exempt_paths: ["docs/**"]\nmax_tasks: 9')
                          .replace("max_tasks: 8\n", ""))
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(report.todos[0].startswith(".atipspec/config.yaml changed after the proposal's acceptance"),
                        report.render())
        self.assertIn("Policy changes since the base commit, in .atipspec/config.yaml: max_tasks 8 → 9",
                      self.run_cli("proposal", "password-reset")[1])

    def test_records_without_file_digests_still_detect_drift(self):
        project = self.guided()
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        path = self.delivery() / "approvals/local-proposal.json"
        data = json.loads(path.read_text())
        for key in ("files", "code", "channel", "client"):
            data.pop(key)
        data["schema"] = 1
        path.write_text(json.dumps(data))
        self.assertTrue(is_current(project, "password-reset", "proposal"), "a 0.2.x record stays valid")
        self.assertIn("channel not recorded (current)", self.run_cli("status")[1])
        canonical_spec = project.specs / "auth.md"
        canonical_spec.write_text(canonical_spec.read_text().replace("thirty minutes", "forty minutes"))
        report = check_delivery(project, "password-reset")
        self.assertTrue(report.todos[0].startswith("the approved content changed after the proposal's acceptance"),
                        report.render())


class ResultCodeTests(GuidedCase):
    def test_report_shows_the_result_code_only_when_checked(self):
        project = self.guided()
        self.assertNotIn("approval_code", report_data(project, "password-reset"))
        self.assertEqual(self.accept("password-reset", "proposal", by="ana")[0], 0)
        self.finish(project)
        self.assertEqual(check_delivery(project, "password-reset").status, "checked")
        code, out, err = self.run_cli("deliver", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("--code", err)
        markdown = self.run_cli("report", "password-reset")[1]
        data = json.loads(self.run_cli("report", "password-reset", "--format", "json")[1])
        expected = approval_code(project, "password-reset", "result")
        self.assertEqual(data["approval_code"], expected)
        self.assertIn(f"`atipspec accept password-reset result --code {expected}`", markdown)
        self.assertIn("proposal: ana (local declaration)", markdown)
        self.assertIn("canal: assistant; código:", markdown, "labels follow the project language; identifiers do not")
        with patch.dict(os.environ, {"CLAUDECODE": "1"}):
            code, out, err = self.run_cli("accept", "password-reset", "result", "--code", data["approval_code"])
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("approval_code", report_data(project, "password-reset"), "accepted, not checked")
        status = self.run_cli("status")[1]
        self.assertIn("result accepted by t@t", status)
        self.assertIn("via client-permission (Claude Code) (current)", status)
        self.assertEqual(self.run_cli("deliver", "password-reset")[0], 0)
        receipt = json.loads((project.archive / "password-reset/reports/acceptance.json").read_text())
        self.assertEqual([(a["phase"], a["channel"], a["client"]) for a in receipt["approvals"]],
                         [("proposal", "assistant", None), ("result", "client-permission", "claude")])
        self.assertIn("canal: client-permission (Claude Code)", render_report(get_report(project, "password-reset"), "markdown"))

    def test_archived_receipts_without_a_channel_still_render(self):
        project = Project.find(self.root)
        receipt = project.archive / "old-change/reports/acceptance.json"
        receipt.parent.mkdir(parents=True)
        (project.archive / "old-change/spec.md").write_text("# Old\n")
        receipt.write_text(json.dumps({
            "schema": 1, "generated_at": "2026-01-01T00:00:00Z", "delivery": "old-change", "title": "Old", "owner": None,
            "ticket": None, "status": "accepted", "accepted": True, "acceptance_mode": "local", "authenticated": False,
            "head": None, "tree": None, "policy_sha256": None, "policy_version": None, "language": "en", "checks": [],
            "matrix": [], "findings": [], "artifacts_sha256": {},
            "approvals": [{"phase": "result", "identity": "ana", "role": "local declaration", "approved_at": "2026-01-01",
                           "subject": "x", "source": "local", "authenticated": False}]}))
        markdown = render_report(get_report(project, "old-change"), "markdown")
        self.assertIn("- result: ana (local declaration), 2026-01-01; channel: not recorded.", markdown)
        self.assertIn("channel: not recorded", render_report(get_report(project, "old-change"), "html"))


class ContractAcceptanceTests(GuidedCase):
    def test_decisions_are_accepted_with_the_contract_and_a_self_accepted_one_invalidates_it(self):
        project = Project.find(self.root)
        code, out, err = self.run_cli("decision", "stack", "--title", "Python stdlib", "--affects", "contract")
        self.assertIn("present `atipspec proposal contract`", out)
        out = self.run_cli("proposal", "contract")[1]
        self.assertIn("DEC-001 (proposed): Python stdlib", out)
        self.assertIn("- DEC-001 (.atipspec/decisions/DEC-001-stack.md) has no Context or Decision yet: write what it "
                      "decides before presenting it", out, "an approval of the template's comments decides nothing")
        code, _, err = self.accept_contract()
        self.assertEqual(code, 1)
        self.assertIn("Cannot accept the contract: DEC-001", err)
        self.fill_decisions()
        out = self.run_cli("proposal", "contract")[1]
        self.assertNotIn("Not ready for approval", out)
        presented = self.presented_code("contract")
        self.assertEqual(self.run_cli("accept", "contract", "--code", "0000-0000")[0], 1)
        code, out, err = self.run_cli("accept", "contract", "--code", presented, "--by", "ana")
        self.assertEqual(code, 0, out + err)
        self.assertIn("contract and its decisions (DEC-001) accepted", out)
        self.assertIn("status: accepted", project.contract.read_text())
        decision = next(project.decisions.glob("DEC-001-*.md"))
        self.assertIn("status: accepted", decision.read_text(), "the CLI, not the model, writes the status")
        record = json.loads((project.dot / "approvals/contract.json").read_text())
        self.assertEqual((record["kind"], record["code"], record["decisions"], record["by"], record["channel"]),
                         ("contract-acceptance", presented, ["DEC-001"], "ana", "assistant"))
        self.assertEqual(set(record["content"]), {".atipspec/contract.md", project.rel(decision)})
        self.assertEqual(contract_acceptance(project).state, "accepted")
        self.assertIn("contract: accepted by ana", self.run_cli("status")[1])
        before = project.fingerprint()
        (project.dot / "approvals/contract.json").write_text(json.dumps({**record, "by": "other"}))
        self.assertEqual(before, project.fingerprint(), "the record itself never changes the fingerprint")

        # A decision the assistant marks accepted by hand is not part of the accepted contract.
        self.run_cli("decision", "db", "--title", "Postgres", "--affects", "contract:stack")
        self.fill_decisions()
        later = next(project.decisions.glob("DEC-002-*.md"))
        later.write_text(later.read_text().replace("status: proposed", "status: accepted"))
        acceptance = contract_acceptance(project)
        self.assertEqual((acceptance.state, acceptance.changes), ("outdated", ["DEC-002 new"]))
        self.assertIn("contract: outdated since its acceptance (DEC-002 new)", self.run_cli("status")[1])
        code, out, _ = self.run_cli("audit")
        self.assertEqual(code, 0)
        self.assertIn("warning contract: outdated since its acceptance", out)
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        code, _, err = self.run_cli("spec", "password-reset", "--no-context")
        self.assertEqual(code, 1)
        self.assertIn("outdated since its acceptance (DEC-002 new)", err)
        labels = [section.label for section in build_context(project, "password-reset")[0]]
        self.assertIn("decision DEC-001", labels)
        self.assertNotIn("decision DEC-002", labels)
        self.assertEqual(self.accept_contract()[0], 0)
        self.assertEqual(contract_acceptance(project).state, "accepted")
        self.assertIn("decision DEC-002", [section.label for section in build_context(project, "password-reset")[0]])
        self.assertEqual(self.run_cli("spec", "password-reset", "--no-context")[0], 0)

    def test_a_status_written_by_hand_is_not_an_acceptance(self):
        project = Project.find(self.root)
        project.contract.write_text(project.contract.read_text().replace("status: draft", "status: accepted"))
        self.assertEqual(contract_acceptance(project).state, "unrecorded")
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        code, _, err = self.run_cli("spec", "password-reset", "--no-context")
        self.assertEqual(code, 1)
        self.assertIn("accepted without a record", err)
        self.assertIn("atipspec proposal contract", err)
        self.assertIn("warning contract: accepted without a record", self.run_cli("audit")[1])

    def test_guided_deliveries_warn_about_an_unaccepted_contract_without_blocking(self):
        self.guided()
        report = check_delivery(Project.find(self.root), "password-reset", preapproval=True)
        self.assertTrue(any(w.startswith("contract: not accepted yet") for w in report.of("warning")), report.render())
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        self.write_contract("")
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertFalse(any(w.startswith("contract:") for w in report.of("warning")), report.render())

    def test_the_contract_slug_is_reserved(self):
        code, _, err = self.run_cli("new", "contract", "--title", "Contract")
        self.assertEqual(code, 1)
        self.assertIn("reserved", err)

    def test_a_decision_for_everything_is_accepted_with_the_contract(self):
        project = Project.find(self.root)
        self.assertEqual(self.accept_contract()[0], 0)
        code, out, _ = self.run_cli("decision", "relax", "--title", "Skip tests for auth")
        self.assertIn("present `atipspec proposal contract`", out, "no affects means everything, the contract included")
        self.assertNotIn("set status: accepted", out)
        self.fill_decisions()
        decision = next(project.decisions.glob("DEC-001-*.md"))
        decision.write_text(decision.read_text().replace("status: proposed", "status: accepted"))
        acceptance = contract_acceptance(project)
        self.assertEqual((acceptance.state, acceptance.changes), ("outdated", ["DEC-001 new"]))
        self.new_delivery()
        self.assertNotIn("decision DEC-001", [section.label for section in build_context(project, "password-reset")[0]])
        self.assertIn("DEC-001 (accepted): Skip tests for auth", self.run_cli("proposal", "contract")[1])
        self.assertEqual(self.accept_contract()[0], 0)
        self.assertIn("decision DEC-001", [section.label for section in build_context(project, "password-reset")[0]])

    def test_contract_decisions_need_a_recorded_acceptance_unless_the_contract_predates_records(self):
        project = Project.find(self.root)
        self.run_cli("decision", "nolint", "--title", "No linter", "--affects", "contract")
        decision = next(project.decisions.glob("DEC-001-*.md"))
        decision.write_text(decision.read_text().replace("status: proposed", "status: accepted"))
        self.new_delivery()
        self.assertEqual(contract_acceptance(project).state, "draft")
        self.assertNotIn("decision DEC-001", [section.label for section in build_context(project, "password-reset")[0]],
                         "a draft contract has no accepted decisions, whatever their status says")
        # A contract accepted in 0.2.x by its status alone keeps loading its decisions by theirs.
        project.contract.write_text(project.contract.read_text().replace("status: draft", "status: accepted"))
        self.assertEqual(contract_acceptance(project).state, "unrecorded")
        self.assertIn("decision DEC-001", [section.label for section in build_context(project, "password-reset")[0]])

    def test_the_contract_view_and_acceptance_name_the_approvals_its_statuses_reset(self):
        project = self.guided()
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        out = self.run_cli("proposal", "contract")[1]
        self.assertIn("they become outdated and must be presented again: password-reset proposal", out)
        code, out, err = self.accept_contract()
        self.assertEqual(code, 0, out + err)
        self.assertIn("warning: these approvals hashed the previous status lines and are now outdated: "
                      "password-reset proposal", out)
        self.assertFalse(is_current(project, "password-reset", "proposal"))
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)
        out = self.run_cli("proposal", "contract")[1]
        self.assertNotIn("must be presented again", out, "accepting the same contract again changes no status")
        self.assertNotIn("warning: these approvals", self.accept_contract()[1])
        self.assertTrue(is_current(project, "password-reset", "proposal"))

    def test_statuses_are_not_written_when_the_record_cannot_be(self):
        project = Project.find(self.root)
        outside = self.root / "outside"
        outside.mkdir()
        (project.dot / "approvals").symlink_to(outside)
        code, _, err = self.accept_contract()
        self.assertEqual(code, 1)
        self.assertIn("symlinked acceptance path", err)
        self.assertIn("status: draft", project.contract.read_text())
        self.assertEqual(list(outside.iterdir()), [])


class LegacyAndFixPresentationTests(GuidedCase):
    def test_legacy_check_points_to_the_approval_the_view_presents(self):
        self.new_delivery()
        self.write_spec(status="draft", accept=False)
        self.write_plan(accept=False)
        out = self.run_cli("check", "password-reset")[1]
        self.assertIn("present `atipspec proposal password-reset`", out)
        self.assertNotIn("accept password-reset spec", out)
        view = self.run_cli("proposal", "password-reset")[1]
        command = re.search(r"`(atipspec accept password-reset \w+ --code [0-9A-Z-]+)`", view).group(1)
        self.assertIn(" proposal --code ", command, "spec and plan are complete: the view presents them together")
        code, out, err = self.run_cli(*command.split()[1:])
        self.assertEqual(code, 0, out + err)
        view = self.run_cli("proposal", "password-reset")[1]
        self.assertIn("No approval pending", view, "spec and plan are accepted")
        self.assertNotIn("Approval code", view)

    def test_the_view_offers_no_approval_that_nothing_requires(self):
        # A fix created before 0.3.0: its embedded requirement, and no plan acceptance.
        self.new_delivery("link-bug")
        (self.delivery("link-bug") / "baseline.json").unlink()
        (self.delivery("link-bug") / "spec.md").write_text(
            "---\ntitle: Link bug\nstatus: draft\nkind: fix\ncapability: auth\nbase: "
            + self.git("rev-parse", "HEAD").strip() + "\ncreated: 2026-09-12\n---\n\n# Link bug\n\n"
            "### REQ-001: Reset links expire\n\nAcceptance criteria:\n"
            '- AC-001: When a reset link is 31 minutes old, the system returns "link expired".\n')
        (self.delivery("link-bug") / "plan.md").write_text(
            "---\nscope: [\"auth/**\"]\n---\n# Plan\n### T1: Fix\nCovers: REQ-001\nTests: AC-001\nVerify:\n- `true`\n")
        self.assertIn("`atipspec accept link-bug spec --code", self.run_cli("proposal", "link-bug")[1])
        self.assertEqual(self.accept("link-bug", "spec")[0], 0)
        view = self.run_cli("proposal", "link-bug")[1]
        self.assertIn("No approval pending", view, "a fix needs no plan acceptance, complete or not")
        self.assertNotIn("Not ready for approval", view)
        self.assertNotIn("accept link-bug plan", view)
        # A legacy delivery presents its plan only while approve_plan asks for it.
        self.new_delivery()
        self.write_spec()
        self.write_plan(accept=False)
        self.assertIn("`atipspec accept password-reset plan --code", self.run_cli("proposal", "password-reset")[1])
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text() + "approve_plan: false\n")
        self.assertIn("No approval pending", self.run_cli("proposal", "password-reset")[1])


if __name__ == "__main__":
    unittest.main()
