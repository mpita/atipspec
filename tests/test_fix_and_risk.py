"""C7: a fix corrects the accepted requirement with one approval and no
contract; the risk level changes what the gate asks; the lead time is measured
from the records the CLI writes."""
import json
import re

from atipspec import frontmatter
from atipspec.accept import is_current
from atipspec.check import check_delivery
from atipspec.delivery import parse_spec
from atipspec.errors import AtipSpecError
from atipspec.project import Project
from tests.helpers import ProjectCase, junit_command

LIVING = """# Auth

## Requirements

### REQ-001: Reset links expire

A reset link stops working thirty minutes after it is issued.

#### AC-001: Expired link
- **GIVEN** a link issued thirty-one minutes ago
- **WHEN** the user opens it
- **THEN** the page shows "link expired"
"""
LOCKOUT = """
### REQ-002: Login lockout

The account locks after five failed logins.

#### AC-009: Fifth failure
- **GIVEN** four failed logins
- **WHEN** the user fails a fifth time
- **THEN** the page shows "account locked"
"""
BYPASS = """
### REQ-003: Admin bypass

An admin may open any reset link at any age.

#### AC-010: Admin opens an old link
- **GIVEN** an admin and a link issued two days ago
- **WHEN** the admin opens it
- **THEN** the page shows "choose a new password"
"""
SESSIONS = """
### REQ-004: Sessions expire

A session ends after one hour without activity.

#### AC-020: Idle session
- **GIVEN** a session idle for sixty-one minutes
- **WHEN** the user opens a page
- **THEN** the page shows "session expired"
"""
BILLING = """# Billing

## Requirements

### REQ-001: Invoices carry tax

Every invoice adds the tax of the buyer's country.

#### AC-001: Spanish buyer
- **GIVEN** a buyer in Spain and an order of 100 euros
- **WHEN** the invoice is issued
- **THEN** the invoice total is 121 euros
"""
TAX_FREE = """# Billing

## Requirements

### REQ-002: Invoices are tax free

No invoice adds tax.

#### AC-002: Spanish buyer
- **GIVEN** a buyer in Spain and an order of 100 euros
- **WHEN** the invoice is issued
- **THEN** the invoice total is 100 euros
"""
REGRESSION = """
#### AC-002: Link issued the day before
- **GIVEN** a link issued twenty-six hours ago
- **WHEN** the user opens it
- **THEN** the page shows "link expired"
"""
JUNIT = junit_command('<testsuite><testcase classname="tests.test_reset" name="test_expired"/>'
                      '<testcase classname="tests.test_reset" name="test_day_before"/></testsuite>')
REPORT = "Report: .atipspec/tmp/junit.xml\n"
PROOF = REPORT + "Proof:\n- AC-001: test_expired\n- AC-002: test_day_before\n"
PLAN = """---
scope: {scope}
---
# Plan
## Approach
Compare the age of the link in minutes.
## Tasks
### T1: Regression test and fix
Covers: REQ-001
Tests: {tests}
## Final verification
{proof}Verify:
- `{command}`
"""


def approval_code(output: str) -> str:
    """The code a view prints in the `accept` command it names."""
    return re.search(r"--code ([0-9A-Z]{4}-[0-9A-Z]{4})", output).group(1)


class GuidedCase(ProjectCase):
    """A guided delivery of the auth capability, created with `new`."""

    def living(self, text: str = LIVING) -> None:
        project = Project.find(self.root)
        project.specs.mkdir(parents=True, exist_ok=True)
        (project.specs / "auth.md").write_text(text)

    def edit_spec(self, slug: str, **meta) -> None:
        path = self.delivery(slug) / "spec.md"
        current, body = frontmatter.split(path.read_text())
        current.update(meta)
        path.write_text(frontmatter.compose(current, body))

    def plan(self, slug: str, tests: str = "AC-001, AC-002", proof: str = "", command: str = "true",
             scope: str = '["app.py", "tests/**"]') -> None:
        (self.delivery(slug) / "plan.md").write_text(PLAN.format(tests=tests, proof=proof, command=command, scope=scope))

    def review(self, slug: str, verdicts: str, session: str = "isolated") -> None:
        tree = Project.find(self.root).fingerprint()
        (self.delivery(slug) / "review.md").write_text(
            f"---\ntree: {tree}\nreviewer: subagent\nsession: {session}\n---\n\n## Criteria\n\n{verdicts}\n")

    def fix(self, risk: str = "normal", requirements=("REQ-001",)) -> Project:
        """A fix created on the accepted auth spec, its defect stated, its
        requirement listed and the regression criterion added in specs/."""
        code, out, err = self.run_cli("new", "bug-1", "--title", "Link works after a day", "--capability", "auth",
                                      "--kind", "fix", "--ticket", "SHOP-9")
        self.assertEqual(code, 0, err)
        return self.fill(risk, requirements)

    def finish(self, slug: str, verdicts: str, commit: bool = True) -> None:
        """Approve the proposal, build, verify and review the delivery, accept its
        result, deliver it and commit, as the human and the assistant would."""
        code, out, err = self.accept(slug, "proposal", by="human")
        self.assertEqual(code, 0, out + err)
        (self.root / "app.py").write_text("def expired(minutes):\n    return minutes > 30\n")
        for args in (("task-done", slug, "T1", "--note", "Implemented the approved behavior"), ("verify", slug),
                     ("review", slug)):
            code, out, err = self.run_cli(*args)
            self.assertEqual(code, 0, out + err)
        self.review(slug, verdicts)
        code, out, err = self.accept(slug, "result", by="human")
        self.assertEqual(code, 0, out + err)
        code, out, err = self.run_cli("deliver", slug)
        self.assertEqual(code, 0, out + err)
        if commit:
            self.commit(f"deliver {slug}")

    def lock_fix(self) -> None:
        """A second fix, of the lockout, whose criterion was already right: it
        leaves the living spec as it was."""
        code, out, err = self.run_cli("new", "lock", "--title", "Lockout counts", "--capability", "auth",
                                      "--kind", "fix")
        self.assertEqual(code, 0, err)
        path = self.delivery("lock") / "spec.md"
        path.write_text(re.sub(r"Expected: <!--.*?-->", 'Expected: the page shows "account locked".', re.sub(
            r"Observed: <!--.*?-->", "Observed: the fifth failed login lets the user try again.", path.read_text())))
        self.edit_spec("lock", requirements=["REQ-002"])
        self.plan("lock", tests="AC-009")
        plan = self.delivery("lock") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-002"))

    def fill(self, risk: str = "normal", requirements=("REQ-001",)) -> Project:
        path = self.delivery("bug-1") / "spec.md"
        text = re.sub(r"Observed: <!--.*?-->", "Observed: a link issued 26 hours ago still opens the reset form.",
                      path.read_text())
        path.write_text(re.sub(r"Expected: <!--.*?-->", 'Expected: the page shows "link expired", as REQ-001 states.', text))
        self.edit_spec("bug-1", requirements=list(requirements), risk=risk)
        project = Project.find(self.root)
        (project.specs / "auth.md").write_text((project.specs / "auth.md").read_text() + REGRESSION)
        return project


class GuidedFixTests(GuidedCase):
    def test_fix_corrects_the_accepted_requirement_in_ten_commands_with_one_approval_and_no_contract(self):
        self.living()
        self.commit("accepted auth spec")
        steps = []

        def step(*args):
            code, out, err = self.run_cli(*args)
            self.assertEqual(code, 0, out + err)
            steps.append(args[0] + (" " + args[2] if args[0] == "accept" else ""))
            return out

        out = step("new", "bug-1", "--title", "Link works after a day", "--capability", "auth", "--kind", "fix")
        self.assertIn("guided fix", out)
        spec = parse_spec((self.delivery("bug-1") / "spec.md").read_text())
        self.assertEqual((spec.kind, spec.meta.get("schema"), spec.meta.get("requirements"), spec.meta.get("risk")),
                         ("fix", 2, [], "normal"))
        self.assertIn("## Defect", (self.delivery("bug-1") / "spec.md").read_text())
        self.assertEqual(json.loads((self.delivery("bug-1") / "baseline.json").read_text())["content"], LIVING)
        self.assertIn("## Final verification", (self.delivery("bug-1") / "plan.md").read_text())
        self.assertIn("not accepted yet", self.run_cli("status")[1], "the contract was never accepted")
        self.assertIn("# Phase fix", step("fix", "bug-1", "--no-context"))
        # What the model writes in the fix phase: the defect, the reference and the corrected requirement.
        path = self.delivery("bug-1") / "spec.md"
        path.write_text(re.sub(r"Expected: <!--.*?-->", 'Expected: the page shows "link expired".', re.sub(
            r"Observed: <!--.*?-->", "Observed: a link issued 26 hours ago still opens the reset form.", path.read_text())))
        self.edit_spec("bug-1", requirements=["REQ-001"])
        project = Project.find(self.root)
        (project.specs / "auth.md").write_text(LIVING + REGRESSION)
        self.plan("bug-1")
        out = step("proposal", "bug-1")
        self.assertIn("Kind: fix · Risk: normal — every criterion needs a reviewer verdict", out)
        self.assertIn("Corrects: REQ-001 (accepted requirement)", out)
        self.assertIn("+#### AC-002: Link issued the day before", out)
        step("accept", "bug-1", "proposal", "--code", approval_code(out), "--by", "human")
        self.assertEqual(sorted(p.name for p in (self.delivery("bug-1") / "approvals").iterdir()), ["local-proposal.json"])
        self.assertEqual(self.accept("bug-1", "spec")[0], 1, "a guided fix approves its proposal, not a spec")
        (self.root / "app.py").write_text("def expired(minutes):\n    return minutes > 30\n")
        step("task-done", "bug-1", "T1", "--note", "Compare the age in minutes")
        step("verify", "bug-1")
        step("review", "bug-1")
        self.review("bug-1", "- AC-001: PASS. app.py:2\n- AC-002: PASS. app.py:2")
        out = step("report", "bug-1", "--format", "markdown")
        self.assertIn("Tipo: fix. Riesgo: normal. Tiempo de entrega: 0.0 h desde la creación", out)
        step("accept", "bug-1", "result", "--code", approval_code(out), "--by", "human")
        step("deliver", "bug-1")
        self.assertEqual(steps, ["new", "fix", "proposal", "accept proposal", "task-done", "verify", "review", "report",
                                 "accept result", "deliver"])
        text = (project.specs / "auth.md").read_text()
        living = parse_spec(text)
        self.assertEqual([req.id for req in living.requirements], ["REQ-001"], "the fix adds no requirement")
        self.assertEqual([ac.id for ac in living.criteria], ["AC-001", "AC-002"])
        self.assertNotIn("Observed", text, "the defect's story stays in the archived delivery")
        self.assertIn("Observed:", (project.archive / "bug-1/spec.md").read_text())
        receipt = json.loads((project.archive / "bug-1/reports/acceptance.json").read_text())
        self.assertEqual((receipt["kind"], receipt["risk"], receipt["lead_time"]["complete"]), ("fix", "normal", True))
        self.assertIsInstance(receipt["lead_time"]["hours"], float)
        self.assertRegex(self.run_cli("status")[1], r"delivered: bug-1 \(\d+h\)")

    def test_fix_cannot_add_a_requirement_or_skip_the_regression_test(self):
        self.living()
        self.commit("accepted auth spec")
        project = self.fix(requirements=["REQ-002"])
        (project.specs / "auth.md").write_text(LIVING + REGRESSION + "\n### REQ-002: Links are single use\n\n"
                                               "#### AC-003: Second use\n- **WHEN** a used link is opened\n"
                                               '- **THEN** the page shows "link already used"\n')
        self.plan("bug-1", tests="AC-003")
        (self.delivery("bug-1") / "plan.md").write_text(
            (self.delivery("bug-1") / "plan.md").read_text().replace("Covers: REQ-001", "Covers: REQ-002"))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any("REQ-002 is not an accepted requirement of auth" in e for e in report.errors), report.render())
        self.assertEqual(self.accept("bug-1", "proposal")[0], 1)
        self.assertIn("Corrects: REQ-002 (not accepted: a fix cannot add it)", self.run_cli("proposal", "bug-1")[1])
        self.edit_spec("bug-1", requirements=["REQ-001"])
        (project.specs / "auth.md").write_text(LIVING + REGRESSION)
        self.plan("bug-1", tests="")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertFalse(any("not an accepted requirement" in e for e in report.errors), report.render())
        self.assertTrue(any("a fix needs an automated regression criterion" in e for e in report.errors), report.render())
        self.assertEqual(self.accept("bug-1", "proposal")[0], 1)
        self.plan("bug-1")
        self.assertEqual(self.accept("bug-1", "proposal")[0], 0)

    def test_fix_states_the_defect_and_cannot_remove_a_requirement(self):
        self.living()
        self.commit("accepted auth spec")
        self.run_cli("new", "bug-1", "--title", "Link works after a day", "--capability", "auth", "--kind", "fix")
        report = check_delivery(Project.find(self.root), "bug-1", preapproval=True)
        self.assertIn("spec.md lists no requirement: a fix names under `requirements` the accepted requirement of "
                      "specs/auth.md it corrects", report.todos)
        self.assertTrue(any("## Defect does not state `Observed:` and `Expected:`" in t for t in report.todos))
        project = self.fill()
        self.assertIn("- `<!-- the test command that reproduces the defect, red then green -->`",
                      (self.delivery("bug-1") / "plan.md").read_text(), "the contract requires no command")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("Final verification needs executable Verify commands: list under `Verify:` the commands that "
                      "run the tests, or omit the section for manual-only changes", report.errors, report.render())
        self.plan("bug-1")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertFalse(any("Defect" in t for t in report.todos + report.errors), report.render())
        self.assertFalse(any("Intent" in item.text or "Out of scope" in item.text for item in report.items),
                         "a fix states its defect, not an intent")
        (project.specs / "auth.md").write_text((LIVING + REGRESSION).replace("### REQ-001:", "### REQ-001 [remove]:"))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any("a fix cannot remove REQ-001" in e for e in report.errors), report.render())

    def test_fix_cannot_delete_add_or_change_a_requirement_it_does_not_list(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        project = self.fix()
        path = project.specs / "auth.md"
        path.write_text(corrected := LIVING + REGRESSION + LOCKOUT)
        self.plan("bug-1")
        self.assertEqual(self.accept("bug-1", "proposal")[0], 0, "the fix changes only REQ-001")
        path.write_text(corrected.replace(LOCKOUT, "") + BYPASS)
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("a fix cannot remove REQ-002, deleted or marked `[remove]` in .atipspec/specs/auth.md: restore "
                      "it; removing a behavior is a feature delivery", report.errors, report.render())
        self.assertIn("REQ-003 is new in .atipspec/specs/auth.md, and a fix adds no requirement: remove it; a "
                      "behavior no requirement covers is a feature delivery", report.errors, report.render())
        self.assertEqual(self.accept("bug-1", "proposal")[0], 1)
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Not ready for approval", out)
        self.assertNotIn("Approval code", out)
        path.write_text(corrected.replace("### REQ-002:", "### REQ-002 [remove]:"))
        self.assertTrue(any("a fix cannot remove REQ-002" in e for e in check_delivery(project, "bug-1").errors))
        path.write_text(corrected.replace("five failed logins", "three failed logins"))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any(e.startswith("REQ-002 differs in .atipspec/specs/auth.md from the requirements accepted "
                                         "before this delivery") and "a fix changes only the requirements it lists" in e
                            for e in report.errors), report.render())
        path.write_text(corrected)
        self.assertEqual(self.accept("bug-1", "proposal")[0], 0)

    def test_fix_compares_with_the_requirements_committed_at_its_base(self):
        self.living()
        self.commit("accepted auth spec")
        # Written before `new`, never committed: nothing accepted it, and `new` does not start over it.
        self.living(LIVING + BYPASS)
        code, out, err = self.run_cli("new", "bug-1", "--title", "Link works after a day", "--capability", "auth",
                                      "--kind", "fix")
        self.assertEqual(code, 1, out + err)
        self.assertIn(".atipspec/specs/auth.md has changes that are not committed: the delivery compares the living "
                      "spec with the commit it starts from", err)
        self.assertIn("committed outside a delivery, merge-check blocks them. Discard them; or, to make them in this "
                      "delivery, set them aside, discard them, run `atipspec new` again and write them back in the "
                      "delivery", err)
        self.assertNotIn("Commit them", err, "merge-check blocks a living spec committed outside a delivery")
        self.assertFalse(self.delivery("bug-1").exists(), "nothing is written")
        self.living()
        project = self.fix(requirements=["REQ-003"])
        (project.specs / "auth.md").write_text(LIVING + BYPASS + REGRESSION)
        self.plan("bug-1", tests="AC-010")
        plan = self.delivery("bug-1") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-003"))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any(e.startswith("REQ-003 is not an accepted requirement of auth: a fix corrects one that "
                                         "specs/auth.md held at the delivery's base commit") for e in report.errors),
                        report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Corrects: REQ-003 (not accepted: a fix cannot add it)", out)
        self.assertIn("+### REQ-003: Admin bypass", out, "the diff shows the requirement the fix would add")
        self.assertNotIn("Approval code", out)
        # Nor does a baseline.json edited to hold it.
        baseline = self.delivery("bug-1") / "baseline.json"
        data = json.loads(baseline.read_text())
        baseline.write_text(json.dumps({**data, "content": (project.specs / "auth.md").read_text()}))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any(e.startswith("REQ-003 is not an accepted requirement of auth") for e in report.errors),
                        report.render())
        self.assertEqual(self.accept("bug-1", "proposal")[0], 1)

    def test_fix_created_without_its_capability_compares_with_the_one_it_names(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        self.assertEqual(self.run_cli("new", "bug-1", "--title", "Link works after a day", "--kind", "fix")[0], 0)
        self.assertEqual(json.loads((self.delivery("bug-1") / "baseline.json").read_text())["content"], "")
        project = self.fill(requirements=["REQ-003"])
        self.edit_spec("bug-1", capability="auth")
        (project.specs / "auth.md").write_text(LIVING + LOCKOUT + BYPASS)
        self.plan("bug-1", tests="AC-010")
        plan = self.delivery("bug-1") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-003"))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any(e.startswith("REQ-003 is not an accepted requirement of auth") for e in report.errors),
                        report.render())
        self.assertFalse(any("for the first time" in i for i in report.of("info")), report.render())
        self.assertIn("Corrects: REQ-003 (not accepted: a fix cannot add it)", self.run_cli("proposal", "bug-1")[1])
        self.edit_spec("bug-1", requirements=["REQ-001"])
        (project.specs / "auth.md").write_text(LIVING + REGRESSION + LOCKOUT)
        self.plan("bug-1")
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Corrects: REQ-001 (accepted requirement)", out)
        self.assertIn("+#### AC-002: Link issued the day before", out)
        self.assertNotIn("+### REQ-002", out, "the diff compares with auth as committed, not the empty baseline")
        self.assertEqual(self.accept("bug-1", "proposal")[0], 0)

    def test_fix_may_write_the_first_requirement_of_an_empty_capability(self):
        self.run_cli("new", "bug-1", "--title", "Link works after a day", "--capability", "auth", "--kind", "fix")
        self.living()
        project = self.fix_existing()
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("REQ-001 specifies auth for the first time: no living spec held a requirement at the "
                      "delivery's base commit", report.of("info"))
        self.assertFalse(any("REQ-001" in e for e in report.errors), report.render())
        self.assertIn("Corrects: REQ-001 (new: no living spec held a requirement)", self.run_cli("proposal", "bug-1")[1])

    def fix_existing(self) -> Project:
        path = self.delivery("bug-1") / "spec.md"
        text = re.sub(r"Observed: <!--.*?-->", "Observed: a link issued 26 hours ago still opens the reset form.",
                      path.read_text())
        path.write_text(re.sub(r"Expected: <!--.*?-->", 'Expected: the page shows "link expired".', text))
        self.edit_spec("bug-1", requirements=["REQ-001"])
        self.plan("bug-1", tests="AC-001")
        return Project.find(self.root)

    def test_fix_cannot_specify_a_new_capability_while_other_living_specs_hold_requirements(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        self.assertEqual(self.run_cli("new", "bug-1", "--title", "Admin cannot open old link", "--kind", "fix")[0], 0)
        project = self.fix_existing()
        (project.specs / "bug-1.md").write_text("# bug-1\n\n## Requirements\n" + BYPASS.replace("REQ-003", "REQ-001")
                                                .replace("AC-010", "AC-001"))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("REQ-001 is not an accepted requirement of bug-1: specs/bug-1.md held none at the delivery's "
                      "base commit, while other living specs did; set `capability:` in spec.md to the capability "
                      "whose requirement this fix corrects, or deliver the behavior as a feature", report.errors,
                      report.render())
        self.assertFalse(any("for the first time" in i for i in report.of("info")), report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Corrects: REQ-001 (not accepted: a fix cannot add it)", out)
        self.assertNotIn("Approval code", out)

    def test_base_is_the_full_commit_new_recorded(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        base = self.git("rev-parse", "HEAD").strip()
        project = self.fix()
        path = project.specs / "auth.md"
        path.write_text(LIVING + REGRESSION + LOCKOUT)
        self.plan("bug-1")
        self.assertEqual(check_delivery(project, "bug-1", preapproval=True).errors, [])
        # A name moves with every commit: committed work would leave the scope, the diff and the dossier.
        self.edit_spec("bug-1", base="HEAD")
        report = check_delivery(project, "bug-1", preapproval=True)
        moving = ("base must be the full id of the commit the delivery started from, as `atipspec new` recorded it, "
                  "not 'HEAD', which moves with new commits: restore it")
        self.assertEqual(report.errors, [moving], report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn(f"- {moving}", out)
        self.assertNotIn("Approval code", out)
        # A requirement committed after `new`, with the base moved onto that commit.
        path.write_text(LIVING + REGRESSION + LOCKOUT + BYPASS)
        self.commit("wip")
        self.edit_spec("bug-1", base=self.git("rev-parse", "HEAD").strip())
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn(f"the base commit {self.git('rev-parse', 'HEAD').strip()[:12]} is not the head `atipspec new` "
                      f"recorded in baseline.json, {base[:12]}: restore `base: {base}`", report.errors,
                      report.render())
        self.assertEqual(self.accept("bug-1", "proposal")[0], 1)
        other = self.git("commit-tree", f"{base}^{{tree}}", "-p", base, "-m", "elsewhere").strip()
        self.edit_spec("bug-1", base=other)
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn(f"the base commit {other[:12]} is not in the history of HEAD, as after a rebase that rewrote it: "
                      "restore the history the delivery was created on (`git reflog` lists the branch before the "
                      "rebase) and take in the target branch with a merge", report.errors, report.render())
        # With the recorded base, the committed requirement is the fix's own addition.
        self.edit_spec("bug-1", base=base)
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("REQ-003 is new in .atipspec/specs/auth.md, and a fix adds no requirement: remove it if this "
                      "delivery made that change; if another change committed it, that change needs a delivery of "
                      "its own; a behavior no requirement covers is a feature delivery", report.errors, report.render())

    def test_base_cannot_move_to_an_earlier_commit(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        base = self.git("rev-parse", "HEAD").strip()
        project = self.fix(requirements=["REQ-001", "REQ-003"])
        (project.specs / "auth.md").write_text(LIVING + REGRESSION + LOCKOUT + BYPASS)
        self.plan("bug-1")
        # Before the living specs were committed: no requirement held there, so the fix could add one.
        earlier = self.git("rev-parse", f"{base}~1").strip()
        self.edit_spec("bug-1", base=earlier)
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn(f"the base commit {earlier[:12]} is not the head `atipspec new` recorded in baseline.json, "
                      f"{base[:12]}: restore `base: {base}`", report.errors, report.render())
        self.assertFalse(any("for the first time" in item.text for item in report.items), report.render())
        self.assertNotIn("Approval code", self.run_cli("proposal", "bug-1")[1])
        # A delivery migrated from a legacy one keeps its earlier base: its baseline.json records no sections.
        baseline = self.delivery("bug-1") / "baseline.json"
        data = json.loads(baseline.read_text())
        del data["sections"]
        baseline.write_text(json.dumps(data))
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertFalse(any("base commit" in e for e in report.errors), report.render())

    def test_a_fix_of_a_requirement_committed_outside_a_delivery_does_not_pass_merge_check(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        accepted = self.git("rev-parse", "HEAD").strip()
        # Committed before `new`: the base holds it, but no delivery wrote it.
        self.living(LIVING + LOCKOUT + BYPASS)
        self.commit("wip")
        wip = self.git("rev-parse", "HEAD").strip()
        project = self.fix(requirements=["REQ-003"])
        (project.specs / "auth.md").write_text(LIVING + LOCKOUT + BYPASS)
        self.plan("bug-1", tests="AC-010")
        plan = self.delivery("bug-1") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-003"))
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Corrects: REQ-003 (accepted requirement)", out)
        self.finish("bug-1", "- AC-010: PASS. app.py:2")
        code, out, _ = self.run_cli("merge-check", "--base", accepted)
        self.assertEqual(code, 1, out)
        self.assertIn("bug-1: a fix corrects a requirement accepted before it, and REQ-003 was not in "
                      ".atipspec/specs/auth.md at the merge base nor written by an earlier delivery of this branch",
                      out)
        self.assertEqual(self.run_cli("merge-check", "--base", wip)[0], 0, "a target that holds it accepted it")

    def test_merge_check_reads_each_requirement_the_receipt_vouches_for(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        accepted = self.git("rev-parse", "HEAD").strip()
        # Removed before `new`, outside a delivery: the fix's receipt vouches for the text without it.
        self.living()
        self.commit("wip")
        project = self.fix()
        self.plan("bug-1")
        self.assertEqual(check_delivery(project, "bug-1", preapproval=True).errors, [])
        self.finish("bug-1", "- AC-001: PASS. app.py:2\n- AC-002: PASS. app.py:2")
        code, out, _ = self.run_cli("merge-check", "--base", accepted)
        self.assertEqual(code, 1, out)
        self.assertIn(".atipspec/specs/auth.md: REQ-002 is removed in this branch outside the deliveries that list "
                      "it; a living spec changes through a delivery the human accepts: revert the edit, or make it in "
                      "a delivery", out)

    def test_requirements_the_integration_branch_brought_are_not_the_fixs_changes(self):
        self.living(LIVING + LOCKOUT)
        (self.root / ".atipspec/teams.json").write_text(json.dumps({"schema": 1, "integration": "refs/heads/side"}))
        self.commit("accepted auth spec")
        start = self.git("rev-parse", "HEAD").strip()
        project = self.fix()
        path = project.specs / "auth.md"
        path.write_text(LIVING + REGRESSION + LOCKOUT)
        self.plan("bug-1")
        self.commit("fix in progress")
        self.git("checkout", "-q", "-b", "side", start)
        self.living(LIVING + LOCKOUT + SESSIONS)
        self.commit("sessions")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-edit", "side")
        merged = path.read_text()
        self.assertIn("### REQ-004: Sessions expire", merged)
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertFalse(any("REQ-004" in item.text for item in report.items), report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        changes = out.split("## Specification changes")[1]
        self.assertIn("+#### AC-002: Link issued the day before", changes)
        self.assertNotIn("REQ-004", changes, "the integration branch brought it, not the fix")
        # Deleting it is the fix's change, which a fix cannot make.
        path.write_text(merged[:merged.index("\n### REQ-004")] + "\n")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("a fix cannot remove REQ-004, deleted or marked `[remove]` in .atipspec/specs/auth.md: restore "
                      "it; removing a behavior is a feature delivery", report.errors, report.render())
        path.write_text(merged)
        self.finish("bug-1", "- AC-001: PASS. app.py:2\n- AC-002: PASS. app.py:2")
        code, out, _ = self.run_cli("merge-check", "--base", "side")
        self.assertEqual(code, 0, out)
        # Against a target without the side branch, its requirement came in outside a delivery.
        code, out, _ = self.run_cli("merge-check", "--base", start)
        self.assertEqual(code, 1, out)
        self.assertIn(".atipspec/specs/auth.md: REQ-004 is added in this branch outside the deliveries that list it",
                      out)

    def test_what_a_merge_of_another_branch_brings_is_the_fixs_change(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        project = self.fix(requirements=["REQ-003"])
        path = project.specs / "auth.md"
        path.write_text(LIVING + LOCKOUT)
        self.plan("bug-1", tests="AC-010")
        plan = self.delivery("bug-1") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-003"))
        self.commit("fix in progress")
        # A branch of the fix's own, not the integration branch: neither it nor a delivery accepted what it brings.
        self.git("checkout", "-q", "-b", "side")
        self.living(LIVING + LOCKOUT.replace("five failed logins", "three failed logins") + BYPASS)
        self.commit("bypass")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "--no-edit", "side")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any(e.startswith("REQ-002 differs in .atipspec/specs/auth.md from the requirements accepted "
                                         "before this delivery") for e in report.errors), report.render())
        self.assertTrue(any(e.startswith("REQ-003 is not an accepted requirement of auth") for e in report.errors),
                        report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Corrects: REQ-003 (not accepted: a fix cannot add it)", out)
        self.assertNotIn("Approval code", out)

    def test_a_merge_of_what_a_delivery_wrote_is_not_the_fixs_change(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        project = self.fix()
        (project.specs / "auth.md").write_text(LIVING + REGRESSION + LOCKOUT)
        self.plan("bug-1")
        self.commit("fix in progress")
        self.git("checkout", "-q", "-b", "side", "HEAD~1")
        self.new_delivery("sessions")
        self.edit_spec("sessions", requirements=["REQ-004"])
        (project.specs / "auth.md").write_text(LIVING + LOCKOUT + SESSIONS)
        self.plan("sessions", tests="AC-020")
        plan = self.delivery("sessions") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-004"))
        self.finish("sessions", "- AC-020: PASS. app.py:2")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-edit", "side")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertFalse(any("REQ-004" in item.text for item in report.items), report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Corrects: REQ-001 (accepted requirement)", out)
        self.assertNotIn("REQ-004", out.split("## Specification changes")[1])

    def test_a_delivery_archived_after_the_fix_started_is_not_its_change(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        start = self.git("rev-parse", "HEAD").strip()
        project = self.fix()
        path = project.specs / "auth.md"
        path.write_text(LIVING + REGRESSION + LOCKOUT)
        self.plan("bug-1")
        self.commit("fix in progress")
        self.new_delivery("sessions")
        self.edit_spec("sessions", requirements=["REQ-004"])
        path.write_text(LIVING + REGRESSION + LOCKOUT + SESSIONS)
        self.plan("sessions", tests="AC-020")
        plan = self.delivery("sessions") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-004"))
        self.finish("sessions", "- AC-020: PASS. app.py:2")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertFalse(any("REQ-004" in item.text for item in report.items), report.render())
        self.finish("bug-1", "- AC-001: PASS. app.py:2\n- AC-002: PASS. app.py:2")
        code, out, _ = self.run_cli("merge-check", "--base", start)
        self.assertEqual(code, 0, out)

    def test_a_requirement_a_delivery_left_as_it_was_stays_as_it_wrote_it(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        start = self.git("rev-parse", "HEAD").strip()
        project = self.fix()
        path = project.specs / "auth.md"
        path.write_text(LIVING + LOCKOUT)
        self.plan("bug-1", tests="AC-001")
        self.lock_fix()
        self.commit("two fixes")
        self.finish("lock", "- AC-009: PASS. app.py:2")
        self.assertEqual(self.git("diff", "--name-only", "HEAD~1", "HEAD", "--", str(path)), "",
                         "deliver left the living spec as it was")
        path.write_text(LIVING + LOCKOUT.replace("five failed logins", "fifty failed logins"))
        self.commit("tidy wording")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("REQ-002 differs in .atipspec/specs/auth.md from the requirements accepted before this delivery "
                      "but is not listed in `requirements`: a fix changes only the requirements it lists; list it if "
                      "this change writes it, or restore it if this delivery made that change; if another change "
                      "committed it, that change needs a delivery of its own", report.errors, report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("-The account locks after five failed logins.\n+The account locks after fifty failed logins.",
                      out.split("## Specification changes")[1])
        self.assertNotIn("Approval code", out)
        path.write_text(LIVING)
        self.commit("drop the lockout")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertIn("a fix cannot remove REQ-002, deleted or marked `[remove]` in .atipspec/specs/auth.md: restore "
                      "it; removing a behavior is a feature delivery", report.errors, report.render())
        code, out, _ = self.run_cli("merge-check", "--base", start)
        self.assertEqual(code, 1, out)
        self.assertIn(".atipspec/specs/auth.md: REQ-002 is removed in this branch outside the deliveries that list it",
                      out)

    def test_a_receipt_vouches_for_each_requirement_as_it_wrote_it_even_when_that_text_is_never_committed(self):
        self.living(LIVING + LOCKOUT)
        self.commit("accepted auth spec")
        start = self.git("rev-parse", "HEAD").strip()
        project = self.fix()
        path = project.specs / "auth.md"
        path.write_text(LIVING + LOCKOUT)
        self.plan("bug-1")
        self.new_delivery("sessions")
        self.edit_spec("sessions", requirements=["REQ-004"])
        self.plan("sessions", tests="AC-020")
        plan = self.delivery("sessions") / "plan.md"
        plan.write_text(plan.read_text().replace("Covers: REQ-001", "Covers: REQ-004"))
        self.lock_fix()
        self.commit("three deliveries")
        # Two deliveries before one commit: the text the first wrote is in no commit.
        path.write_text(LIVING + LOCKOUT + SESSIONS)
        self.finish("sessions", "- AC-020: PASS. app.py:2", commit=False)
        path.write_text(LIVING + REGRESSION + LOCKOUT + SESSIONS)
        self.finish("bug-1", "- AC-001: PASS. app.py:2\n- AC-002: PASS. app.py:2", commit=False)
        self.commit("deliver both")
        self.assertEqual(check_delivery(project, "lock", preapproval=True).errors, [])
        code, out, _ = self.run_cli("merge-check", "--base", start)
        self.assertEqual(code, 1, out)
        self.assertNotIn("REQ-004", out)
        self.assertNotIn(".atipspec/specs/auth.md:", out, "only the open fix, not yet accepted, blocks")
        # An edit while the delivery that wrote it is not yet committed.
        self.git("reset", "-q", "--hard", "HEAD~1")
        path.write_text(LIVING + LOCKOUT + SESSIONS)
        self.finish("sessions", "- AC-020: PASS. app.py:2", commit=False)
        path.write_text(LIVING + LOCKOUT + SESSIONS.replace("one hour", "one day"))
        self.commit("deliver sessions")
        report = check_delivery(project, "lock", preapproval=True)
        self.assertTrue(any(e.startswith("REQ-004 differs in .atipspec/specs/auth.md from the requirements accepted "
                                         "before this delivery") for e in report.errors), report.render())
        code, out, _ = self.run_cli("merge-check", "--base", start)
        self.assertEqual(code, 1, out)
        self.assertIn(".atipspec/specs/auth.md: REQ-004 is changed in this branch outside the deliveries that list it",
                      out)

    def test_fix_and_low_risk_cannot_change_another_capabilitys_requirements(self):
        self.living(LIVING + LOCKOUT)
        billing = Project.find(self.root).specs / "billing.md"
        billing.write_text(BILLING)
        self.commit("accepted specs")
        project = self.fix(risk="low")
        (project.specs / "auth.md").write_text(LIVING + REGRESSION + LOCKOUT)
        self.plan("bug-1")
        billing.write_text(TAX_FREE)
        report = check_delivery(project, "bug-1", preapproval=True)
        for change, undo in (("REQ-001 is removed", "restore it"), ("REQ-002 is added", "remove it")):
            self.assertIn(f"{change} in .atipspec/specs/billing.md, the living spec of another capability: a fix "
                          f"changes only the requirements of .atipspec/specs/auth.md it lists; {undo}",
                          report.errors, report.render())
        out = self.run_cli("proposal", "bug-1")[1]
        self.assertIn("Another capability's living spec, .atipspec/specs/billing.md, changes too:", out)
        self.assertIn("+### REQ-002: Invoices are tax free", out)
        self.assertNotIn("Approval code", out)
        # At risk normal, an error too: the delivery does not deliver it, and merge-check would block it.
        self.git("commit", "-q", "-m", "fix in progress", "--", ".atipspec/specs/auth.md")
        self.new_delivery("feat")
        self.edit_spec("feat", requirements=["REQ-001"])
        self.plan("feat")
        report = check_delivery(project, "feat", preapproval=True)
        self.assertIn("REQ-001 is removed in .atipspec/specs/billing.md, the living spec of another capability, which "
                      "this delivery does not deliver: restore it, or make that change in a delivery of that capability",
                      report.errors, report.render())

    def test_ship_names_the_fix_phase(self):
        self.living()
        self.commit("accepted auth spec")
        self.run_cli("new", "bug-1", "--title", "Link works after a day", "--capability", "auth", "--kind", "fix")
        code, out, _ = self.run_cli("ship", "bug-1")
        self.assertIn("next phase is fix", out)
        self.assertIn("stop point 1 follows: the user approves the proposal", out)


class LegacyFixTests(GuidedCase):
    def test_legacy_fix_keeps_its_contract_spec_acceptance_and_embedded_requirement(self):
        self.new_delivery("bug-0")
        base = self.git("rev-parse", "HEAD").strip()
        (self.delivery("bug-0") / "spec.md").write_text(f"""---
title: "Old fix"
status: draft
kind: fix
capability: auth
created: 2026-09-12
base: {base}
---

# Old fix

## Requirements

### REQ-001: Reset links expire after thirty minutes

Observed: a link issued 26 hours ago still opens the reset form.

Acceptance criteria:
- AC-001: When a link issued 26 hours ago is opened, the system shows "link expired".

## Open questions

- None
""")
        (self.delivery("bug-0") / "baseline.json").unlink()
        code, _, err = self.run_cli("fix", "bug-0", "--no-context")
        self.assertEqual(code, 1)
        self.assertIn("contract", err)
        self.write_contract('require-command "true"')
        self.commit("contract")
        self.assertEqual(self.run_cli("fix", "bug-0", "--no-context")[0], 0)
        self.assertIn("Approval code", self.run_cli("proposal", "bug-0")[1])
        self.assertEqual(self.accept("bug-0", "spec")[0], 0)
        (self.delivery("bug-0") / "plan.md").write_text(
            "---\nscope: [\"app.py\"]\n---\n# Plan\n### T1: Fix\nCovers: REQ-001\nTests: AC-001\nVerify:\n- `true`\n")
        project = Project.find(self.root)
        report = check_delivery(project, "bug-0")
        self.assertFalse(any("accept bug-0 plan" in t or "proposal" in t for t in report.todos), report.render())
        self.assertEqual(report.status, "planned")
        self.assertFalse(any(item.text.startswith("risk ") for item in report.items), "legacy deliveries show no risk")
        (self.root / "app.py").write_text("x = 1\n")
        self.assertEqual(self.run_cli("task-done", "bug-0", "T1", "--note", "Compare minutes")[0], 0)
        self.assertEqual(self.run_cli("verify", "bug-0")[0], 0)
        self.assertEqual(self.run_cli("review", "bug-0")[0], 0)
        self.review("bug-0", "- AC-001: PASS. app.py:1")
        self.assertEqual(self.accept("bug-0", "result")[0], 0)
        self.assertEqual(self.run_cli("deliver", "bug-0")[0], 0)
        self.assertIn("Observed: a link issued 26 hours ago", (project.specs / "auth.md").read_text(),
                      "a legacy fix merges its embedded requirement as before")


    def test_legacy_delivery_shows_the_risk_it_sets(self):
        self.new_delivery("bug-0")
        (self.delivery("bug-0") / "baseline.json").unlink()
        (self.delivery("bug-0") / "spec.md").write_text(
            "---\ntitle: Old fix\nstatus: draft\nkind: fix\ncapability: auth\nrisk: high\nbase: "
            + self.git("rev-parse", "HEAD").strip() + "\ncreated: 2026-09-12\n---\n\n# Old fix\n\n"
            "### REQ-001: Reset links expire\n\nAcceptance criteria:\n"
            '- AC-001: When a reset link is 31 minutes old, the system returns "link expired".\n')
        report = check_delivery(Project.find(self.root), "bug-0", preapproval=True)
        self.assertTrue(any(i.startswith("risk high: plan.md declares a scope") for i in report.of("info")),
                        report.render())


class RiskTests(GuidedCase):
    def feature(self, risk: str) -> Project:
        self.living(LIVING + REGRESSION)
        self.commit("accepted auth spec")
        self.new_delivery("feat")
        self.edit_spec("feat", requirements=["REQ-001"], risk=risk)
        return Project.find(self.root)

    def build(self, verdicts: str, session: str = "isolated"):
        self.assertEqual(self.run_cli("task-done", "feat", "T1", "--note", "Compare minutes")[0], 0)
        self.assertEqual(self.run_cli("verify", "feat")[0], 0)
        self.assertEqual(self.run_cli("review", "feat")[0], 0)
        self.review("feat", verdicts, session)
        return check_delivery(Project.find(self.root), "feat")

    def test_high_risk_requires_scope_proof_and_an_isolated_review(self):
        project = self.feature("high")
        self.plan("feat", command=JUNIT)
        report = check_delivery(project, "feat", preapproval=True)
        self.assertIn("risk high: plan.md declares a scope and a file outside it is an error; every criterion under "
                      "Tests names its test in Proof, with a Report; the review comes from an isolated session "
                      "(`session: isolated`)", report.of("info"))
        for text in ("Final verification: risk is high, so the Verify commands write a JUnit XML report",
                     "AC-001: risk is high: name the test", "AC-002: risk is high: name the test"):
            self.assertTrue(any(text in e for e in report.errors), report.render())
        self.assertEqual(self.accept("feat", "proposal")[0], 1)
        out = self.run_cli("proposal", "feat")[1]
        self.assertIn("Kind: feature · Risk: high — plan.md declares a scope", out)
        self.assertIn("each criterion under Tests names its test in Proof (risk: high)", out)
        # A project that keeps strict_scope off still needs the scope at risk high.
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text().replace("strict_scope: true", "strict_scope: false"))
        self.plan("feat", proof=PROOF, command=JUNIT, scope="[]")
        project = Project.find(self.root)
        report = check_delivery(project, "feat", preapproval=True)
        self.assertTrue(any("plan.md declares no scope" in e and "risk: high requires it" in e for e in report.errors),
                        report.render())
        self.plan("feat", proof=PROOF, command=JUNIT)
        code, out, err = self.accept("feat", "proposal")
        self.assertEqual(code, 0, out + err)
        (self.root / "app.py").write_text("def expired(minutes):\n    return minutes > 30\n")
        report = self.build("- AC-001: PASS. test_expired\n- AC-002: PASS. test_day_before", session="shared")
        self.assertTrue(any("risk: high requires it" in e for e in report.errors), report.render())
        self.assertIn("## Risk\n\nrisk high:", (project.tmp / "feat-review-packet.md").read_text())
        self.review("feat", "- AC-001: PASS. test_expired\n- AC-002: PASS. test_day_before")
        report = check_delivery(project, "feat")
        self.assertEqual((report.exit_code, report.status), (0, "checked"), report.render())
        (self.root / "stray.py").write_text("x = 1\n")
        report = check_delivery(project, "feat")
        self.assertTrue(any("files outside the declared scope: stray.py" in e for e in report.errors), report.render())

    def test_low_risk_takes_a_named_test_that_passed_instead_of_a_verdict(self):
        project = self.feature("low")
        self.plan("feat", proof=REPORT + "Proof:\n- AC-002: test_day_before\n", command=JUNIT)
        self.assertEqual(self.accept("feat", "proposal")[0], 0)
        (self.root / "app.py").write_text("def expired(minutes):\n    return minutes > 30\n")
        report = self.build("- AC-001: PASS. app.py:2", session="shared")
        self.assertEqual(report.exit_code, 0, report.render())
        self.assertIn("AC-002: its test named in Proof passed in the current evidence, so risk low needs no reviewer "
                      "verdict", report.of("info"))
        self.assertTrue(any("session: shared" in w for w in report.of("warning")), "a shared review still warns")
        self.review("feat", "- AC-002: PASS. test_day_before")
        self.assertIn("AC-001 has no verdict in review.md", check_delivery(project, "feat").errors,
                      "a criterion without a named test still needs its verdict")
        self.review("feat", "- AC-001: PASS. app.py:2\n- AC-002: FAIL. a link of 26 hours still opens")
        self.assertTrue(any("AC-002 FAIL" in e for e in check_delivery(project, "feat").errors), "a FAIL still blocks")
        self.review("feat", "- AC-001: PASS. app.py:2")
        (self.root / "app.py").write_text("def expired(minutes):\n    return minutes >= 30\n")
        report = check_delivery(project, "feat")
        self.assertTrue(any("evidence is stale" in t for t in report.todos), report.render())
        self.assertIn("AC-002 has no verdict in review.md", report.errors, "stale evidence proves nothing")

    def test_low_risk_cannot_remove_a_requirement_or_change_the_contract(self):
        project = self.feature("low")
        self.plan("feat")
        (project.specs / "auth.md").write_text((LIVING + REGRESSION).replace("### REQ-001:", "### REQ-001 [remove]:"))
        report = check_delivery(project, "feat", preapproval=True)
        self.assertTrue(any("risk low does not apply to a change that removes REQ-001" in e for e in report.errors),
                        report.render())
        (project.specs / "auth.md").write_text(LIVING + REGRESSION)
        project.contract.write_text(project.contract.read_text() + "\nA new paragraph.\n")
        report = check_delivery(project, "feat", preapproval=True)
        self.assertTrue(any("risk low does not apply to a change of the architecture contract" in e
                            for e in report.errors), report.render())
        self.assertEqual(self.accept("feat", "proposal")[0], 1, "the human cannot approve it at risk low")
        self.edit_spec("feat", risk="normal")
        self.assertEqual(self.accept("feat", "proposal")[0], 0)

    def test_low_risk_cannot_delete_or_change_a_requirement_it_does_not_list(self):
        self.living(LIVING + REGRESSION + LOCKOUT)
        self.commit("accepted auth spec")
        self.new_delivery("feat")
        self.edit_spec("feat", requirements=["REQ-001"], risk="low")
        project = Project.find(self.root)
        self.plan("feat")
        path = project.specs / "auth.md"
        path.write_text(LIVING + REGRESSION)
        report = check_delivery(project, "feat", preapproval=True)
        self.assertTrue(any(e.startswith("risk low does not apply to a change that removes REQ-002, deleted or marked "
                                         "`[remove]` in .atipspec/specs/auth.md") for e in report.errors), report.render())
        self.assertEqual(self.accept("feat", "proposal")[0], 1)
        path.write_text(LIVING + REGRESSION + LOCKOUT + BYPASS)
        report = check_delivery(project, "feat", preapproval=True)
        self.assertTrue(any(e.startswith("REQ-003 differs in .atipspec/specs/auth.md from the requirements accepted "
                                         "before this delivery") and "risk low reads only the listed requirements" in e
                            for e in report.errors), report.render())
        self.assertEqual(self.accept("feat", "proposal")[0], 1)
        # At risk normal they are errors too, which the proposal lists for the human.
        self.edit_spec("feat", risk="normal")
        path.write_text(LIVING + REGRESSION + BYPASS)
        report = check_delivery(project, "feat", preapproval=True)
        removed = ("REQ-002 is deleted or marked `[remove]` in .atipspec/specs/auth.md but is not listed in "
                   "`requirements`: restore it, or keep it as `### REQ-002 [remove]: <title>` and list it, so check "
                   "reads the removal")
        self.assertIn(removed, report.errors, report.render())
        self.assertTrue(any(e.startswith("REQ-003 differs in .atipspec/specs/auth.md from the requirements accepted "
                                         "before this delivery") for e in report.errors), report.render())
        self.assertIn(f"- {removed}", self.run_cli("proposal", "feat")[1].split("Not ready for approval:")[1])
        self.assertEqual(self.accept("feat", "proposal")[0], 1)
        self.edit_spec("feat", requirements=["REQ-001", "REQ-002", "REQ-003"])
        path.write_text(LIVING + REGRESSION + LOCKOUT.replace("### REQ-002:", "### REQ-002 [remove]:") + BYPASS)
        self.assertFalse([e for e in check_delivery(project, "feat", preapproval=True).errors
                          if "not listed in `requirements`" in e], "listed, check reads them")

    def test_an_unlisted_change_at_risk_normal_is_an_error_in_check_and_in_merge_check(self):
        self.living(LIVING + REGRESSION + LOCKOUT)
        self.commit("accepted auth spec")
        start = self.git("rev-parse", "HEAD").strip()
        self.new_delivery("feat")
        self.edit_spec("feat", requirements=["REQ-001"])
        project = Project.find(self.root)
        self.plan("feat")
        path = project.specs / "auth.md"
        path.write_text(edited := LIVING + REGRESSION + LOCKOUT.replace("five failed logins", "three failed logins"))
        report = check_delivery(project, "feat", preapproval=True)
        error = ("REQ-002 differs in .atipspec/specs/auth.md from the requirements accepted before this delivery but "
                 "is not listed in `requirements`: list it if this change writes it, so check reads it, or restore it")
        self.assertIn(error, report.errors, report.render())
        out = self.run_cli("proposal", "feat")[1]
        self.assertIn(f"- {error}", out.split("Not ready for approval:")[1])
        self.assertNotIn("Approval code", out)
        self.commit("feat open, with the edit")
        code, out, _ = self.run_cli("merge-check", "--base", start)
        self.assertEqual(code, 1, out)
        self.assertIn(".atipspec/specs/auth.md: REQ-002 is changed in this branch outside the deliveries that list it",
                      out, "the open delivery lists only REQ-001")
        path.write_text(LIVING + REGRESSION + LOCKOUT)
        self.finish("feat", "- AC-001: PASS. app.py:2\n- AC-002: PASS. app.py:2")
        self.assertEqual(self.run_cli("merge-check", "--base", start)[0], 0)
        path.write_text(edited)
        self.commit("tidy wording")
        code, out, _ = self.run_cli("merge-check", "--base", start)
        self.assertEqual(code, 1, out)
        self.assertIn(".atipspec/specs/auth.md: changed in this branch outside `atipspec deliver`", out)

    def test_low_risk_takes_a_named_test_only_for_a_criterion_under_tests(self):
        project = self.feature("low")
        code, out, err = self.run_cli("check", "feat", "--json")
        self.assertEqual((code, json.loads(out)["status"]), (2, "draft"), out + err)
        (project.specs / "auth.md").write_text(
            LIVING + REGRESSION + "\n#### AC-003 [manual]: Wording on a phone\n- **GIVEN** an expired link\n"
            "- **WHEN** the user opens it on a phone\n- **THEN** the page shows \"link expired\" in 16 px text\n")
        (self.delivery("feat") / "plan.md").write_text(
            '---\nscope: ["app.py", "tests/**"]\n---\n# Plan\n## Approach\nCompare the age of the link in minutes.\n'
            "## Tasks\n### T1: Regression test and fix\nCovers: REQ-001\nTests: AC-001, AC-002\nManual: AC-003\n"
            + REPORT + "Proof:\n- AC-001: test_expired\n- AC-002: test_day_before\n- AC-003: test_expired\n"
            f"Verify:\n- `{JUNIT}`\n")
        code, out, err = self.accept("feat", "proposal")
        self.assertEqual(code, 0, out + err)
        (self.root / "app.py").write_text("def expired(minutes):\n    return minutes > 30\n")
        report = self.build("")
        self.assertIn("AC-003 has no verdict in review.md", report.errors, "a manual criterion needs its observation")
        self.assertIn("AC-001: its test named in Proof passed in the current evidence, so risk low needs no reviewer "
                      "verdict", report.of("info"))
        self.review("feat", "- AC-003: PASS. Opened an expired link on a phone and read the 16 px wording")
        report = check_delivery(project, "feat")
        self.assertEqual((report.exit_code, report.status), (0, "checked"), report.render())
        code, out, err = self.run_cli("check", "feat", "--json")
        self.assertEqual((code, json.loads(out)["proven"]), (0, ["AC-001", "AC-002"]), out + err)
        from atipspec.reporting import report_data
        verdicts = {row["criterion"]: row["verdict"] for row in report_data(project, "feat")["matrix"]}
        self.assertEqual(verdicts, {"auth/AC-001": "NOT NEEDED", "auth/AC-002": "NOT NEEDED", "auth/AC-003": "PASS"})
        out = self.run_cli("report", "feat", "--format", "markdown")[1]
        self.assertIn("| NOT NEEDED |", out)
        self.assertIn("riesgo bajo: su test nombrado pasó en la evidencia actual", out, "the dossier says why")

    def test_changing_the_risk_voids_the_approval_and_an_unknown_level_is_an_error(self):
        project = self.feature("normal")
        self.plan("feat")
        self.assertEqual(self.accept("feat", "proposal")[0], 0)
        self.edit_spec("feat", risk="low")
        self.assertFalse(is_current(project, "feat", "proposal"))
        report = check_delivery(project, "feat")
        self.assertEqual(report.status, "draft", report.render())
        self.assertTrue(any("spec.md" in t and "changed after the proposal's acceptance" in t for t in report.todos))
        self.edit_spec("feat", risk="extreme")
        report = check_delivery(project, "feat", preapproval=True)
        self.assertIn("risk must be low, normal or high, found 'extreme'", report.errors)
        self.assertIn("Kind: feature · Risk: invalid — 'extreme' is not a level", self.run_cli("proposal", "feat")[1])


class LeadTimeTests(GuidedCase):
    def test_lead_time_runs_from_creation_to_result_acceptance(self):
        from atipspec.status import measure
        lead = measure("2026-10-01T08:00:00Z", None, "2026-10-01T13:30:00Z")
        self.assertEqual((lead["hours"], lead["complete"]), (5.5, True))
        self.assertEqual(measure("garbage", None, None)["hours"], None)
        self.assertFalse(measure("2026-10-01T08:00:00Z", None, None)["complete"])
        self.living()
        self.commit("accepted auth spec")
        project = self.fix()
        self.edit_spec("bug-1", created="2026-01-01T09:00:00Z")
        self.plan("bug-1")
        report = check_delivery(project, "bug-1", preapproval=True)
        self.assertTrue(any(w.startswith("open for ") and "(policy 8h)" in w for w in report.of("warning")),
                        report.render())
        self.assertEqual(self.accept("bug-1", "proposal")[0], 0)
        (self.root / "app.py").write_text("x = 1\n")
        self.assertEqual(self.run_cli("task-done", "bug-1", "T1", "--note", "Compare minutes")[0], 0)
        self.assertEqual(self.run_cli("verify", "bug-1")[0], 0)
        self.assertEqual(self.run_cli("review", "bug-1")[0], 0)
        self.review("bug-1", "- AC-001: PASS. app.py:1\n- AC-002: PASS. app.py:1")
        self.assertEqual(self.accept("bug-1", "result")[0], 0)
        report = check_delivery(project, "bug-1")
        record = json.loads((self.delivery("bug-1") / "approvals/local-result.json").read_text())
        self.assertEqual((report.lead_time["complete"], report.lead_time["result_accepted_at"]),
                         (True, record["accepted_at"]), "the clock stops at the result's acceptance")
        self.assertTrue(any(w.startswith("open for ") for w in report.of("warning")), report.render())
        self.assertRegex(self.run_cli("status")[1], r"bug-1 \[accepted\] \[fix\].*, accepted after \d+d \d+h")
        (self.root / ".atipspec/config.yaml").write_text(
            (self.root / ".atipspec/config.yaml").read_text().replace("max_age_hours: 8", "max_age_hours: 1000000"))
        report = check_delivery(Project.find(self.root), "bug-1")
        self.assertFalse(any("open for" in w for w in report.of("warning")))
        self.assertTrue(any(re.match(r"lead time \d+d \d+h: ", i) for i in report.of("info")), report.render())

    def test_pilot_reads_lead_hours_from_the_receipt_and_never_invents_them(self):
        from atipspec.pilot import initialize, record
        project = Project.find(self.root)
        initialize(project, "p")
        metrics = dict(lead_hours=None, human_review_minutes=20, rework_minutes=0, escaped_defects=0,
                       criteria_total=2, criteria_tested=2, observation_days=14)
        with self.assertRaisesRegex(AtipSpecError, "No lead time recorded for bug-1"):
            record(project, "p", "bug-1", "atipspec", metrics, "receipt", "qa")
        with self.assertRaisesRegex(AtipSpecError, "Baseline observations need --lead-hours"):
            record(project, "p", "old", "baseline", metrics, "ticket", "qa")
        reports = project.archive / "bug-1" / "reports"
        reports.mkdir(parents=True)
        (project.archive / "bug-1/spec.md").write_text("---\ntitle: x\ncreated: 2026-10-01T08:00:00Z\n---\n# x\n")
        (reports / "acceptance.json").write_text(json.dumps({"lead_time": {"hours": 5.5, "complete": True}}))
        data = json.loads(record(project, "p", "bug-1", "atipspec", metrics, "receipt", "qa").read_text())
        self.assertEqual((data["lead_hours"], data["lead_hours_origin"]),
                         (5.5, "computed from the delivery receipt: creation to result acceptance"))
        # A delivery archived by 0.2.x: no lead time in its receipt, its records archived with it.
        old = project.archive / "old"
        (old / "approvals").mkdir(parents=True)
        (old / "reports").mkdir()
        (old / "spec.md").write_text("---\ntitle: old\ncreated: 2026-09-12\n---\n# old\n")
        (old / "reports/acceptance.json").write_text(json.dumps({"accepted": True}))
        (old / "approvals/local-result.json").write_text(json.dumps({"accepted_at": "2026-09-12T06:30:00Z"}))
        data = json.loads(record(project, "p", "old", "atipspec", metrics, "receipt", "qa").read_text())
        self.assertEqual((data["lead_hours"], data["lead_hours_origin"]),
                         (6.5, "computed from the records archived with the delivery: creation to result acceptance"))
        data = json.loads(record(project, "p", "old", "baseline", dict(metrics, lead_hours=9.0), "ticket", "qa").read_text())
        self.assertEqual((data["lead_hours"], data["lead_hours_origin"]), (9.0, "recorded"))
        self.assertIn("delivered: bug-1 (5h), old (6h)", self.run_cli("status")[1])
        (project.archive / "weird").mkdir()
        (project.archive / "weird/spec.md").write_bytes(b"caf\xe9\n")
        code, out, err = self.run_cli("status")
        self.assertEqual(code, 0, err)
        self.assertIn("delivered: bug-1 (5h), old (6h), weird", out, "an unreadable archive only loses its lead time")
