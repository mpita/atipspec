"""Tickets link a delivery to its tracker; status speaks JSON and Markdown."""
import json
import re
import unittest

from atipspec.accept import is_current
from atipspec.errors import AtipSpecError
from atipspec.project import Project
from atipspec.tickets import link, validate
from tests.helpers import INTENT, GuidedSteps, ProjectCase


class TicketFormTests(unittest.TestCase):
    def test_new_validates_ticket_forms(self):
        for value in ("SHOP-9", "#42", "https://tracker.example/issues/9"):
            with self.subTest(value=value):
                self.assertEqual(validate(value), value)
        for value in ("foo bar", "http://tracker.example/9", "javascript:alert(1)", "https://user:pw@x.example/9",
                      "shop-9", "#", "https://"):
            with self.subTest(value=value), self.assertRaisesRegex(AtipSpecError, "use a key like PROJ-123"):
                validate(value)


class TicketTests(GuidedSteps, ProjectCase):
    URL = "https://example.atlassian.net/browse/{ticket}"

    def ticketed(self, ticket="SHOP-12", url=URL):
        project = Project.find(self.root)
        if url:
            (project.dot / "teams.json").write_text(json.dumps({"schema": 1, "ticket_url": url}))
        code, out, err = self.run_cli("new", "password-reset", "--title", "Password reset", "--capability", "auth",
                                      "--ticket", ticket)
        self.assertEqual(code, 0, out + err)
        return project

    def test_new_refuses_free_text(self):
        code, _, err = self.run_cli("new", "x", "--title", "X", "--ticket", "fix the login")
        self.assertEqual(code, 1)
        self.assertIn("Invalid ticket 'fix the login'", err)
        self.assertFalse((self.root / ".atipspec/deliveries/x").exists())
        code, out, err = self.run_cli("new", "y", "--title", "Y", "--ticket", "#42")
        self.assertEqual(code, 0, out + err)
        self.assertIn('ticket: "#42"', (self.root / ".atipspec/deliveries/y/spec.md").read_text())

    def test_ticket_shown_in_status_team_report_and_proposal(self):
        project = self.ticketed()
        url = "https://example.atlassian.net/browse/SHOP-12"
        self.assertEqual(link(project, "SHOP-12"), url)
        self.assertEqual(link(project, "#7"), "https://example.atlassian.net/browse/7")
        self.assertIn(f"SHOP-12 ({url})", self.run_cli("status")[1])
        self.assertIn(f"ticket: SHOP-12 ({url})", self.run_cli("status", "password-reset")[1])
        data = json.loads(self.run_cli("status", "--format", "json")[1])
        self.assertEqual((data["deliveries"][0]["ticket"], data["deliveries"][0]["ticket_url"]), ("SHOP-12", url))
        self.assertIn(f"| password-reset | [SHOP-12](<{url}>) |", self.run_cli("status", "--format", "markdown")[1])
        self.assertIn(f"@unassigned SHOP-12 ({url})", self.run_cli("team")[1])
        self.assertEqual(json.loads(self.run_cli("team", "--json")[1])["changes"][0]["ticket_url"], url)
        self.assertIn(f"Ticket: SHOP-12 ({url})", self.run_cli("proposal", "password-reset")[1])
        self.assertEqual(json.loads(self.run_cli("report", "password-reset", "--format", "json")[1])["ticket_url"], url)
        self.assertIn(f"[SHOP-12](<{url}>)", self.run_cli("report", "password-reset")[1])
        self.assertIn(f'<a href="{url}">SHOP-12</a>', self.run_cli("report", "password-reset", "--format", "html")[1])

    def test_html_links_only_https_and_escapes(self):
        project = self.ticketed("https://tracker.example/i?a=1&b=<2>", url=None)
        html = self.run_cli("report", "password-reset", "--format", "html")[1]
        self.assertNotIn("<2>", html)
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace('ticket: "https://tracker.example/i?a=1&b=<2>"',
                                                 'ticket: "javascript:alert(1)"'))
        self.assertIsNone(link(project, "javascript:alert(1)"))
        html = self.run_cli("report", "password-reset", "--format", "html")[1]
        self.assertIn("javascript:alert(1)", html)
        self.assertNotIn('href="javascript', html)

    def test_markdown_tables_keep_a_link_whole(self):
        self.ticketed("https://tracker.example/a|b)c<d>", url=None)
        row = next(line for line in self.run_cli("status", "--format", "markdown")[1].splitlines()
                   if line.startswith("| password-reset |"))
        self.assertEqual(len(re.split(r"(?<!\\)\|", row)), 7, row)
        self.assertIn("](<https://tracker.example/a%7Cb)c%3Cd%3E>) |", row)
        self.commit("draft delivery")
        out = self.run_cli("merge-check", "--base", "HEAD~1", "--format", "markdown")[1]
        self.assertIn("(<https://tracker.example/a%7Cb)c%3Cd%3E>) | draft |", out)

    def test_legacy_free_ticket_is_shown_without_a_link(self):
        project = self.ticketed()
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text().replace("ticket: SHOP-12", 'ticket: "the login bug"'))
        self.assertIsNone(link(project, "the login bug"))
        self.assertIn("@unassigned the login bug ", self.run_cli("team")[1])
        data = json.loads(self.run_cli("status", "--format", "json")[1])
        self.assertEqual((data["deliveries"][0]["ticket"], data["deliveries"][0]["ticket_url"]), ("the login bug", None))

    def test_ticket_is_outside_the_proposal_approval(self):
        project = self.ticketed()
        spec = self.delivery() / "spec.md"
        spec.write_text(re.sub(r"(## Intent\n\n)<!--.*?-->", r"\1" + INTENT, spec.read_text(), count=1, flags=re.S))
        project.tmp.mkdir(parents=True, exist_ok=True)
        (project.tmp / "auth.md").write_text("# Auth\n### REQ-001: Access\n#### AC-001: Access result\n"
                                             "- WHEN accessing\n- THEN success\n")
        code, out, err = self.run_cli("spec-bind", "password-reset", "--file", str(project.tmp / "auth.md"))
        self.assertEqual(code, 0, out + err)
        (self.delivery() / "plan.md").write_text("---\nscope: [\"*\"]\n---\n# Plan\n### T1: Access\nCovers: REQ-001\n"
                                                 "Tests: AC-001\n## Final verification\nVerify:\n- `true`\n")
        self.approve()
        spec.write_text(spec.read_text().replace("ticket: SHOP-12", "ticket: SHOP-13"))
        self.assertTrue(is_current(project, "password-reset", "proposal"))
        spec.write_text(spec.read_text().replace("A user who forgot", "A customer who forgot"))
        self.assertFalse(is_current(project, "password-reset", "proposal"))

    def test_merge_check_shows_the_ticket_of_each_delivery(self):
        self.ticketed()
        self.commit("draft delivery")
        code, out, _ = self.run_cli("merge-check", "--base", "HEAD~1")
        self.assertEqual(code, 1)
        self.assertIn("deliveries:\n  - password-reset [draft] ticket SHOP-12 "
                      "(https://example.atlassian.net/browse/SHOP-12)", out)
        code, out, _ = self.run_cli("merge-check", "--base", "HEAD~1", "--format", "markdown")
        self.assertIn("| password-reset | [SHOP-12](<https://example.atlassian.net/browse/SHOP-12>) | draft |", out)


class StatusFormatTests(ProjectCase):
    def test_status_json_and_markdown_list_open_and_archived_deliveries(self):
        self.new_delivery()
        project = Project.find(self.root)
        archived = project.archive / "old"
        (archived / "reports").mkdir(parents=True)
        (archived / "spec.md").write_text("---\ntitle: Old\nticket: SHOP-1\nowner: ana\n---\n# Old\n")
        (archived / "reports" / "acceptance.json").write_text(json.dumps({"delivery": "old", "accepted": True}))
        code, out, err = self.run_cli("status", "--format", "json")
        self.assertEqual(code, 0, out + err)
        data = json.loads(out)
        self.assertEqual(data["schema"], 1)
        entry = data["deliveries"][0]
        self.assertEqual((entry["slug"], entry["state"], entry["exit_code"]), ("password-reset", "draft", 2))
        self.assertIn("next", entry)
        self.assertEqual(data["archived"], [{"slug": "old", "title": "Old", "owner": "ana", "ticket": "SHOP-1",
                                             "ticket_url": None, "accepted": True, "lead_time": None}])
        code, out, _ = self.run_cli("status", "--format", "markdown")
        self.assertIn("| Delivery | Ticket | Owner | State | Next |", out)
        self.assertIn("| old | SHOP-1 | ana | yes |", out)
        code, out, _ = self.run_cli("status", "password-reset", "--format", "json")
        self.assertEqual(json.loads(out)["delivery"]["slug"], "password-reset")
        self.assertEqual(code, 0)
