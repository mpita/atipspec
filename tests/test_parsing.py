import json
from pathlib import Path
import tempfile
import unittest

from atipspec.delivery import load_evidence, parse_deferred, parse_plan, parse_review, parse_roadmap, parse_spec
from tests.helpers import PLAN, REVIEW, SPEC


class SpecParsingTests(unittest.TestCase):
    def test_requirements_criteria_and_open_questions(self):
        spec = parse_spec(SPEC.format(status="draft", base="null", question="How long is the link valid?", impact="[]"))
        self.assertEqual(spec.title, "Password reset")
        self.assertEqual([req.id for req in spec.requirements], ["REQ-001", "REQ-002"])
        self.assertEqual([ac.id for ac in spec.criteria], ["AC-001", "AC-002", "AC-003"])
        self.assertEqual(spec.criteria[2].requirement, "REQ-002")
        self.assertEqual(spec.open_questions, ["How long is the link valid?"])
        self.assertEqual(spec.status, "draft")
        self.assertEqual(spec.problems, [])

    def test_none_marker_comments_and_code_are_ignored(self):
        text = SPEC.format(status="ready", base="null", question="Ninguna", impact="[]") + \
            "\n<!--\n### REQ-009: Commented\n- AC-009: hidden\n-->\n```\n### REQ-010: In code\n```\n"
        spec = parse_spec(text)
        self.assertEqual(spec.open_questions, [])
        self.assertEqual(len(spec.requirements), 2)

    def test_criterion_outside_requirement_and_remove_marker(self):
        spec = parse_spec("# T\n\n- AC-001: lost\n\n### REQ-001 [remove]: Old behavior\n")
        self.assertEqual(len(spec.problems), 1)
        self.assertTrue(spec.requirements[0].remove)
        self.assertEqual(spec.requirements[0].title, "Old behavior")

    def test_untouched_template_has_no_requirements(self):
        template = Path(__file__).resolve().parent.parent / "atipspec/resources/framework/templates/spec.md"
        spec = parse_spec(template.read_text(encoding="utf-8"))
        self.assertEqual(spec.requirements, [])
        self.assertEqual(spec.problems, [])


class RoadmapParsingTests(unittest.TestCase):
    def test_deliveries_in_order(self):
        roadmap = parse_roadmap("---\ntitle: Orders\n---\n\n# Roadmap: Orders\n\n## Deliveries\n\n- orders-api: API\n- orders-screen: Screen\n\n## Interfaces\n\n- not-a-delivery: x\n")
        self.assertEqual(roadmap.title, "Roadmap: Orders")
        self.assertEqual(roadmap.deliveries, [("orders-api", "API"), ("orders-screen", "Screen")])

    def test_impact_includes_capability_first(self):
        spec = parse_spec("---\ncapability: auth\nimpact: [billing, auth]\n---\n# T\n")
        self.assertEqual(spec.impact, ["auth", "billing"])


class PlanParsingTests(unittest.TestCase):
    def test_tasks_covers_and_verify_variants(self):
        plan = parse_plan(PLAN.format(command1="npm test", command2="make check") +
                          "\n### T3: Docs\n\n- Covers: REQ-001, req-002\n- **Verify**: none\n\n### T4: Inline\nVerify: `pytest -q`\nCovers: REQ-002\n")
        self.assertEqual([task.id for task in plan.tasks], ["T1", "T2", "T3", "T4"])
        self.assertEqual(plan.tasks[0].verify, ["npm test"])
        self.assertEqual(plan.tasks[2].covers, ["REQ-001", "REQ-002"])
        self.assertTrue(plan.tasks[2].verify_none)
        self.assertEqual(plan.tasks[3].verify, ["pytest -q"])
        self.assertEqual(plan.tasks[3].covers, ["REQ-002"])

    def test_untouched_template_has_no_tasks(self):
        template = Path(__file__).resolve().parent.parent / "atipspec/resources/framework/templates/plan.md"
        self.assertEqual(parse_plan(template.read_text(encoding="utf-8")).tasks, [])


class ReviewAndDeferredTests(unittest.TestCase):
    def test_verdicts_and_findings(self):
        review = parse_review(REVIEW.format(tree="abc", v1="PASS", v2="fail", v3="PASS",
                                            findings="- F1 [blocker]: token never expires\n- F2 [Minor]: typo"))
        self.assertEqual(review.tree, "abc")
        self.assertEqual(review.verdicts["AC-002"][0], "FAIL")
        self.assertEqual(review.verdicts["AC-001"], ("PASS", "proof"))
        self.assertEqual([(f.id, f.severity) for f in review.findings], [("F1", "blocker"), ("F2", "minor")])

    def test_deferred_entries(self):
        entries, problems = parse_deferred("# Deferred\n\n- F1: later\n- ac-002: no\n- F1: twice\n")
        self.assertEqual(entries, {"F1": "twice", "AC-002": "no"})
        self.assertEqual(len(problems), 1)

    def test_latest_evidence_per_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name, finished, result in (("T1-a", "2026-01-01T00:00:00Z", "fail"), ("T1-b", "2026-01-02T00:00:00Z", "pass")):
                (directory / f"{name}.json").write_text(json.dumps({"task": "T1", "result": result, "finished": finished, "tree": "t"}))
            (directory / "bad.json").write_text("{")
            latest, problems = load_evidence(directory)
            self.assertEqual(latest["T1"].result, "pass")
            self.assertEqual(len(problems), 1)


if __name__ == "__main__":
    unittest.main()

class MalformedReviewTests(unittest.TestCase):
    def test_malformed_or_duplicate_findings_do_not_disappear(self):
        self.assertTrue(parse_review('- F1 [blocker] missing colon').problems)
        self.assertTrue(parse_review('- F1 [minor]: first\n- F1 [blocker]: second').problems)
        self.assertTrue(parse_review('- AC-001: MAYBE. unknown').problems)
