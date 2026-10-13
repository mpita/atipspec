"""Specification rigor: the lint of requirements, criteria and scenarios in
English, Spanish and Portuguese, the fit criterion of quality attributes, the
sections a guided spec.md decides, and what `proposal` shows before approval."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from atipspec.check import check_delivery
from atipspec.delivery import parse_spec
from atipspec.lint import has_concrete_value, lint_spec, vague_terms
from atipspec.locale import VAGUE
from atipspec.project import Project
from tests.helpers import ProjectCase

REPOSITORY = Path(__file__).resolve().parent.parent
# What check adds to a decision an approved delivery lacks.
LATER = ", the next time the proposal changes: editing spec.md only for this voids its approval"
PLAN = ("---\nscope: [\"*\", \"src/**\"]\n---\n# Plan\n### T1: Behavior\nCovers: {covers}\nTests: {tests}\n"
        "## Final verification\nVerify:\n- `true`\n")
EXPIRY = """# Auth
### REQ-001: Expired links are rejected
The system must reject a reset link after thirty minutes.
#### AC-001: Expired link
- **GIVEN** a link issued thirty-one minutes ago
- **WHEN** the user opens the link
- **THEN** the page displays "link expired"
"""
# Criteria a careful author writes: no finding, strict or advice.
GOOD = {
    "en": ["When a registered email requests a reset, the system sends a link to that email within 60 seconds.",
           'If a link is older than 30 minutes, then the system returns "link expired" and sends nothing.',
           'While the account is locked, the system shall reject every login with "account locked".',
           "The system shall reject passwords shorter than 12 characters.",
           "Where two-factor is enabled, the system asks for the code before showing the Profile page.",
           "When an order links products many-to-many, the export lists each pair once in `orders.csv`.",
           "When an issue has the label theme:slow-unresponsive, the triage bot assigns it to ops@example.com.",
           'When the user presses "Pay now", the system opens /checkout/express.',
           "When 100 users request a reset within one minute, the p95 response time measured at the API gateway "
           "is below 300 ms.",
           "After 3 failed attempts, the system locks the account for 15 minutes."],
    "es": ["Cuando el usuario envía un correo registrado, el sistema envía el enlace en menos de 60 segundos.",
           "Si la contraseña tiene un mínimo de 12 caracteres, entonces el sistema la acepta y muestra "
           "«Contraseña guardada».",
           "El sistema debe rechazar una contraseña de menos de 12 caracteres.",
           "Mientras la cuenta está bloqueada, el sistema debe mostrar «Cuenta bloqueada» en cada intento.",
           "Dado un pedido de 3 artículos a 10,00, cuando se aplica un cupón del 10 %, entonces el total es 27,00.",
           "Tras 5 intentos fallidos, el sistema bloquea la cuenta durante 15 minutos."],
    "pt": ["Quando o usuário envia um e-mail cadastrado, o sistema envia o link em até 60 segundos.",
           "Se a senha tiver no mínimo 12 caracteres, então o sistema a aceita e mostra «Senha salva».",
           "O sistema deve rejeitar senhas com menos de 12 caracteres.",
           'Enquanto a conta estiver bloqueada, o sistema deve exibir "Conta bloqueada" em cada tentativa.'],
}
# Criteria a test cannot check as written: each one has a strict finding.
BAD = {
    "en": ["When the user saves, the system works correctly.",
           "When the page loads, it responds quickly.",
           "The search returns relevant results.",
           "When a file is uploaded, the system handles it appropriately.",
           "When the report is ready, the system shows it as expected.",
           "The system shall be easy-to-use."],
    "es": ["Cuando el usuario guarda, el sistema funciona correctamente.",
           "Cuando se carga la página, responde adecuadamente y lo antes posible.",
           "El sistema debe reducir los tiempos de espera al mínimo."],
    "pt": ["Quando o usuário salva, o sistema funciona bem.",
           "Quando a página carrega, o sistema responde corretamente.",
           "O sistema deve exibir o resultado conforme esperado."],
}


def spec_of(*criteria: str, section: str = "Requirements") -> str:
    lines = ["# Example", "", f"## {section}", "", "### REQ-001: Example behavior", ""]
    lines += [f"- AC-{number:03d}: {text}" for number, text in enumerate(criteria, 1)]
    return "\n".join(lines) + "\n"


def texts(source: str, language: str = "en", strict: bool | None = None) -> list[str]:
    return [finding.text for finding in lint_spec(parse_spec(source), language, "ears")
            if strict is None or finding.strict == strict]


class LintTablesTests(unittest.TestCase):
    def test_adverbs_and_phrases_missing_in_0_2_0_are_vague(self):
        for language, phrases in {"en": ("correctly", "appropriately", "properly", "as expected", "works well"),
                                  "es": ("correctamente", "adecuadamente", "funciona bien", "como se espera"),
                                  "pt": ("corretamente", "adequadamente", "funciona bem")}.items():
            for phrase in phrases:
                with self.subTest(language=language, phrase=phrase):
                    self.assertEqual(vague_terms(f"the result {phrase} today", language), [phrase])

    def test_literals_identifiers_and_compounds_are_not_vague(self):
        for text, language in (('"Fast checkout"', "en"), ("`theme:slow`", "en"), ("theme:slow-unresponsive", "en"),
                               ("many-to-many", "en"), ("«Rápido»", "es"), ("un mínimo de 12 caracteres", "es"),
                               ("no mínimo 12 caracteres", "pt"), ("Fasten someone's seatbelt", "en")):
            with self.subTest(text=text):
                self.assertEqual(vague_terms(text, language), [])
        self.assertEqual(vague_terms("an easy-to-use and user-friendly form", "en"), ["easy-to-use", "user-friendly"])
        self.assertEqual(vague_terms("un tiempo de espera mínimo posible", "es"), ["mínimo posible"])
        self.assertEqual(vague_terms("o mais rápido possível", "pt"), ["o mais rápido possível"],
                         "a term inside a longer one at the same place is reported once")

    def test_hyphenated_compounds_and_emphasis_are_read(self):
        for text, terms in (("the page is fast-loading", ["fast"]), ("Fast-loading dashboard", ["fast"]),
                            ("an easy-to-read and energy-efficient label", ["easy", "efficient"]),
                            ("the list loads _quickly_", ["quickly"]), ("one-to-many", []), ("1-to-1", []),
                            ("theme:unresponsive-slow", []), ("the slow_query_log flag", []), ("/fast-path", [])):
            with self.subTest(text=text):
                self.assertEqual(vague_terms(text, "en"), terms)

    def test_quoted_vague_text_is_advice_and_no_concrete_value(self):
        criterion = 'When the user presses "Fast checkout", the system opens /checkout/express.'
        self.assertEqual(texts(spec_of(criterion), strict=True), [])
        self.assertEqual(texts(spec_of(criterion), strict=False),
                         ['AC-001 quotes "Fast checkout", which holds vague terms (fast): keep it only if it is the '
                          "interface's literal text, else state the observable value"])
        self.assertFalse(has_concrete_value('the system "works correctly"', "en"))
        self.assertTrue(has_concrete_value('the system shows "Saved"', "en"))

    def test_known_good_criteria_have_no_findings(self):
        for language, criteria in GOOD.items():
            for criterion in criteria:
                with self.subTest(language=language, criterion=criterion):
                    self.assertEqual(texts(spec_of(criterion), language), [])

    def test_known_bad_criteria_are_flagged(self):
        for language, criteria in BAD.items():
            for criterion in criteria:
                with self.subTest(language=language, criterion=criterion):
                    self.assertTrue(texts(spec_of(criterion), language, strict=True))

    def test_the_gate_fixtures_have_no_strict_findings(self):
        from tests.helpers import SPEC
        from tests.test_approval import SCENARIOS
        for name, source in (("helpers.SPEC", SPEC.format(status="draft", impact="[]", base="x", question="None")),
                             ("test_approval.SCENARIOS", SCENARIOS), ("EXPIRY", EXPIRY)):
            with self.subTest(fixture=name):
                self.assertEqual(texts(source, "es", strict=True), [])

    def test_a_statement_continues_on_indented_lines(self):
        spec = parse_spec(spec_of("When 100 users request a reset within one minute, the p95 response")
                          + "  time measured at the API gateway is below 300 ms.\n- AC-002: When saved, the record exists.\n")
        self.assertEqual(spec.criteria[0].text, "When 100 users request a reset within one minute, the p95 response "
                                                "time measured at the API gateway is below 300 ms.")
        self.assertEqual(spec.criteria[1].text, "When saved, the record exists.")
        self.assertEqual(spec.problems, [])


class ScenarioLintTests(unittest.TestCase):
    def test_title_and_every_step_are_linted(self):
        source = """# Portal
### REQ-001: Carga del portal
#### AC-001: Carga rápida
- **DADO** un empleado en Inicio
- **CUANDO** abre el portal
- **ENTONCES** el sistema funciona correctamente
"""
        self.assertEqual(texts(source, "es", strict=True),
                         ["AC-001 uses vague terms (rápida, correctamente); state the observable value instead"])

    def test_spanish_and_portuguese_steps_are_read_with_their_tables(self):
        scenario = "# Links\n### REQ-001: Expired links\n#### AC-001: Expired link\n- GIVEN a link issued 31 minutes ago\n" \
                   "- WHEN the user opens the link\n- {outcome}\n"
        for outcome, term in (("ENTONCES el sistema funciona correctamente", "correctamente"),
                              ("ENTÃO o sistema funciona bem", "funciona bem")):
            with self.subTest(outcome=outcome):
                self.assertEqual(texts(scenario.format(outcome=outcome), "en", strict=True),
                                 [f"AC-001 uses vague terms ({term}); state the observable value instead"])

    def test_quoting_a_vague_outcome_does_not_hide_it(self):
        scenario = "# Links\n### REQ-001: Expired links\n#### AC-001: Expired link\n- DADO un enlace de hace 31 minutos\n" \
                   "- CUANDO el usuario abre el enlace\n- ENTONCES el sistema {outcome}\n"
        for language in ("es", "en"):
            with self.subTest(language=language):
                self.assertEqual(texts(scenario.format(outcome="«funciona correctamente»"), language), [
                    "AC-001 quotes «funciona correctamente», which holds vague terms (correctamente): keep it only "
                    "if it is the interface's literal text, else state the observable value",
                    "AC-001 outcome names no concrete value (a number, quoted text, a path or a name); state what a "
                    "test or a person observes"])
        self.assertEqual(texts(scenario.format(outcome="muestra «Enlace caducado»"), "es"), [])

    def test_an_outcome_without_a_concrete_value_is_advice(self):
        scenario = "# Pricing\n### REQ-001: Coupons\n#### AC-001: Coupon\n- GIVEN an order of 3 items at 10.00\n" \
                   "- WHEN a 10% coupon is applied\n- THEN {outcome}\n"
        advice = texts(scenario.format(outcome="the discount is applied"), strict=False)
        self.assertEqual(advice, ["AC-001 outcome names no concrete value (a number, quoted text, a path or a name); "
                                  "state what a test or a person observes"], "the GIVEN numbers do not count")
        self.assertEqual(texts(scenario.format(outcome="the discount is applied"), strict=True), [])
        for outcome in ("the total is 27.00", 'the page shows "Coupon applied"', "the user lands on `/herramientas`",
                        "the user sees the Sign-in page", "the receipt goes to billing@example.com",
                        "the order moves to /orders/paid"):
            with self.subTest(outcome=outcome):
                self.assertEqual(texts(scenario.format(outcome=outcome)), [])
        self.assertTrue(texts(spec_of("When a registered email requests a reset, the system sends a link to that email."),
                              strict=False), "a statement's outcome is what follows its trigger")
        self.assertTrue(texts(spec_of("When the user opens /tools, the system shows the page."), strict=False))


class RequirementLintTests(unittest.TestCase):
    def test_title_and_statement_are_linted_but_rationale_observation_and_removal_are_not(self):
        source = """# Search
### REQ-001: Fast search
The search must respond quickly.

Why: many users complained.

Observed: the page is slow.

Acceptance criteria:
- AC-001: When a user searches for "lamp", the system lists the 20 newest matches.

### REQ-003 [remove]: Fast export
- AC-002: If a user requests an export, then the system responds with HTTP 404.
"""
        self.assertEqual(texts(source), ["REQ-001 uses vague terms (fast, quickly); state the observable value instead"])
        source = "# Búsqueda\n### REQ-001: Búsqueda\nPor qué: muchos usuarios se quejaron.\nObservado: es lenta.\n" \
                 "- AC-001: Cuando el usuario busca «lámpara», el sistema lista 20 resultados.\n"
        self.assertEqual(texts(source, "es"), [])

    def test_criteria_label_text_and_sub_items_of_a_criterion_are_linted(self):
        source = """# Save
### REQ-001: Save
Acceptance criteria: the system works correctly.
- AC-001: When the user saves, the system shows "Saved".
  - and the system responds quickly
Why: users lose
  some work today.
"""
        self.assertEqual(texts(source), ["REQ-001 uses vague terms (correctly, quickly); state the observable value "
                                         "instead"])


    def test_a_reason_or_observation_runs_on_like_a_paragraph_with_its_list(self):
        source = """# Search
### REQ-001: Search lists the first 20 matches
Observed:
- open /search?q=lamp with 20000 products
- the page is slow and many requests time out
Expected: the page loads quickly.

Why: support receives several tickets a week about links reused after
some days.

- AC-001: When a user searches for "lamp", the system lists the 20 newest matches.
"""
        self.assertEqual(texts(source), ["REQ-001 uses vague terms (quickly); state the observable value instead"])
        criterion = '- AC-001: When a user searches for "lamp", the system lists the 20 newest matches.\n'
        source = "# Search\n### REQ-001: Search\nObserved:\n\n- the page is slow\n\nThe search must respond quickly.\n"
        self.assertEqual(texts(source + criterion), ["REQ-001 uses vague terms (quickly); state the observable value "
                                                     "instead"], "a label alone takes one block")
        source = "# Search\n### REQ-001: Search\n- Why: many users complained.\n- Expected: the page loads quickly.\n"
        self.assertEqual(texts(source + criterion), ["REQ-001 uses vague terms (quickly); state the observable value "
                                                     "instead"], "a label in a list ends at the next item")

class QualityAttributeTests(unittest.TestCase):
    def test_legacy_quality_section_needs_a_number_and_says_how_it_is_measured(self):
        low = "When 100 users request a reset within one minute, the response time stays low."
        self.assertEqual(texts(spec_of(low, section="Quality attributes"), strict=True),
                         ["AC-001 is a criterion of quality attribute REQ-001: state the number with its unit and "
                          "how it is measured"])
        unmeasured = "When 100 users request a reset within one minute, the p95 response time is below 300 ms."
        self.assertEqual(texts(spec_of(unmeasured, section="Quality attributes"), strict=True), [])
        self.assertEqual(len(texts(spec_of(unmeasured, section="Quality attributes"), strict=False)), 1,
                         "without its measurement method the criterion is advice, not an error")
        self.assertIn("does not say how it is measured", texts(spec_of(unmeasured, section="Atributos de calidad"),
                                                               "es")[0])
        measured = spec_of("When 100 users request a reset within one minute, the p95 response",
                           section="Quality attributes") + "  time measured at the API gateway is below 300 ms.\n"
        self.assertEqual(texts(measured), [])
        self.assertEqual(texts(spec_of("Cuando 50 usuarios abren el listado, el p95 medido en el balanceador es "
                                       "inferior a 2 s.", section="Atributos de calidad"), "es"), [])
        self.assertEqual(texts(spec_of(low), strict=True), [], "outside the quality attributes no number is required")


class GuidedSpecCase(ProjectCase):
    """A guided delivery whose requirements live in specs/auth.md."""

    def bind(self, source: str, slug: str = "password-reset", covers: str = "REQ-001", tests: str = "AC-001",
             intent: bool = True) -> Project:
        if intent:
            self.new_delivery(slug)
        else:
            code, out, err = self.run_cli("new", slug, "--title", "Password reset", "--capability", "auth")
            self.assertEqual(code, 0, out + err)
        project = Project.find(self.root)
        project.tmp.mkdir(parents=True, exist_ok=True)
        (project.tmp / "auth.md").write_text(source)
        code, out, err = self.run_cli("spec-bind", slug, "--file", str(project.tmp / "auth.md"))
        self.assertEqual(code, 0, out + err)
        (self.delivery(slug) / "plan.md").write_text(PLAN.format(covers=covers, tests=tests))
        return project

    def edit_spec(self, old: str, new: str, slug: str = "password-reset") -> None:
        path = self.delivery(slug) / "spec.md"
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def set_strict(self, value: str) -> None:
        config = self.root / ".atipspec/config.yaml"
        config.write_text(re.sub(r"strict_criteria: \w+", f"strict_criteria: {value}", config.read_text()))


class GuidedDecisionTests(GuidedSpecCase):
    def test_new_creates_intent_scope_and_quality_sections(self):
        code, out, err = self.run_cli("new", "password-reset", "--title", "Password reset", "--capability", "auth")
        self.assertEqual(code, 0, out + err)
        text = (self.delivery() / "spec.md").read_text()
        for heading in ("## Intent\n\n<!--", "## Out of scope\n\n<!--", "## Quality attributes\n\n<!--"):
            self.assertIn(heading, text)
        spec = parse_spec(text)
        self.assertEqual(spec.sections, {"intent": [], "out_of_scope": ["- None"], "quality": ["- None"]})
        self.assertEqual(spec.assumptions + spec.open_questions, [])

    def test_empty_intent_blocks_proposal_and_acceptance(self):
        self.bind(EXPIRY, intent=False)
        code, out, err = self.run_cli("proposal", "password-reset")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Not ready for approval:", out)
        self.assertIn("- spec.md ## Intent is empty: state the actor, the trigger, the observable result", out)
        self.assertNotIn("Approval code:", out)
        report = check_delivery(Project.find(self.root), "password-reset")
        self.assertTrue(report.next_action.startswith("spec.md ## Intent is empty"), report.render())
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)
        self.assertFalse((self.delivery() / "approvals").exists())
        code, out, err = self.run_cli("plan", "password-reset", "--no-context")
        self.assertEqual(code, 1)
        self.assertIn("the spec is not ready: spec.md ## Intent is empty", err)
        self.edit_spec("## Intent\n\n", "## Intent\n\nA user who forgot the password sets a new one from the "
                                        "emailed link.\n\n")
        self.assertEqual(self.accept("password-reset", "proposal")[0], 0)

    def test_section_without_items_is_undecided(self):
        project = self.bind(EXPIRY)
        self.edit_spec("- None\n\n## Quality attributes", "\n## Quality attributes")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertIn("spec.md ## Out of scope is undecided: list the items, or write `- None`", report.todos)
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)

    def remove_decided_sections(self) -> None:
        path = self.delivery() / "spec.md"
        text = path.read_text()
        path.write_text(text[:text.index("## Out of scope")] + "## Assumptions\n\n- None\n\n## Open questions\n\n- None\n")

    def test_0_2_0_delivery_without_new_sections_only_warns(self):
        project = self.bind(EXPIRY)
        baseline = self.delivery() / "baseline.json"
        data = json.loads(baseline.read_text())
        self.assertEqual(data.pop("sections"), ["intent", "out_of_scope", "quality"])
        baseline.write_text(json.dumps(data))
        self.remove_decided_sections()
        report = check_delivery(project, "password-reset", preapproval=True)
        for heading in ("Out of scope", "Quality attributes"):
            self.assertIn(f"spec.md has no ## {heading} section: add it with its items, or `- None`", report.of("warning"))
        code, out, err = self.accept("password-reset", "proposal")
        self.assertEqual(code, 0, out + err)
        report = check_delivery(project, "password-reset")
        for heading in ("Out of scope", "Quality attributes"):
            self.assertIn(f"spec.md has no ## {heading} section: add it with its items, or `- None`{LATER}",
                          report.of("warning"), "adding it now would void the approval")

    def test_deleting_a_section_the_delivery_was_created_with_leaves_it_undecided(self):
        project = self.bind(EXPIRY)
        self.remove_decided_sections()
        report = check_delivery(project, "password-reset", preapproval=True)
        for heading in ("Out of scope", "Quality attributes"):
            self.assertIn(f"spec.md has no ## {heading} section: add it with its items, or `- None`", report.todos)
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)

    def test_a_placeholder_decides_nothing(self):
        project = self.bind(EXPIRY, intent=False)
        self.edit_spec("## Intent\n\n", "## Intent\n\nTBD\n\n")
        self.edit_spec("- None\n\n## Quality attributes", "- ...\n\n## Quality attributes")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertTrue(any(text.startswith("spec.md ## Intent is empty") for text in report.todos), report.render())
        self.assertIn("spec.md ## Out of scope is undecided: list the items, or write `- None`", report.todos)

    def test_a_status_written_by_hand_does_not_lift_the_decisions(self):
        project = self.bind(EXPIRY, intent=False)
        self.edit_spec("status: draft", "status: ready")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertTrue(any(text.startswith("spec.md ## Intent is empty") for text in report.todos), report.render())
        out = self.run_cli("proposal", "password-reset")[1]
        self.assertIn("Not ready for approval:", out)
        self.assertNotIn("Approval code:", out)
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)
        self.assertFalse((self.delivery() / "approvals").exists())

    def test_a_selected_policy_does_not_lift_the_decisions_before_a_local_record(self):
        project = self.bind(EXPIRY, intent=False)
        self.edit_spec("status: draft", "status: ready")
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        policy = Path(outside.name) / "policy.toml"
        policy.write_text('schema = 1\nversion = "1"\nrepository = "example/demo"\n[[signers]]\nidentity = "po"\n'
                          'roles = ["product"]\npublic_key = "ssh-ed25519 AAAA"\n')
        with patch.dict(os.environ, {"ATIPSPEC_TRUST_POLICY": str(policy)}):
            out = self.run_cli("proposal", "password-reset")[1]
            self.assertIn("- spec.md ## Intent is empty", out[:out.index("Criteria check:")])
            self.assertNotIn("Approval code:", out)
            self.assertEqual(self.accept("password-reset", "proposal")[0], 1)
            report = check_delivery(project, "password-reset")
            self.assertTrue(any(text.startswith("spec.md ## Intent is empty") for text in report.of("warning")),
                            "the gate under a policy counts the status people set; the signatures are the approval")
        self.assertFalse((self.delivery() / "approvals").exists())
        report = check_delivery(project, "password-reset")
        self.assertEqual(report.status, "draft", report.render())

    def test_delivery_approved_with_empty_intent_warns(self):
        from atipspec.accept import _write
        project = self.bind(EXPIRY, intent=False)
        self.edit_spec("status: draft", "status: ready")
        _write(project, "password-reset", "proposal", "tester", "0000-0000", "terminal", None)   # as 0.2.0 recorded it
        report = check_delivery(project, "password-reset")
        intent = [item for item in report.items if item.text.startswith("spec.md ## Intent is empty")]
        self.assertEqual([item.level for item in intent], ["warning"], "a delivery past its proposal keeps going")
        self.assertTrue(intent[0].text.endswith(LATER), intent[0].text)
        self.edit_spec("## Out of scope", "## Out of scope\n\n- Changes to the email template")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertTrue(any(text.startswith("spec.md ## Intent is empty") for text in report.todos),
                        "a new approval needs the intent")

    def test_vague_scenario_blocks_the_proposal_in_a_new_project(self):
        self.bind(EXPIRY.replace('the page displays "link expired"', "el sistema funciona correctamente"))
        code, out, err = self.run_cli("proposal", "password-reset")
        self.assertIn("Criteria check: strict; vague or unstructured criteria block approval", out)
        self.assertIn("- AC-001 uses vague terms (correctamente); state the observable value instead", out)
        self.assertNotIn("Approval code:", out)
        code, out, err = self.accept("password-reset", "proposal")
        self.assertEqual(code, 1)
        self.assertIn("correctamente", err)


class QualityReferenceTests(GuidedSpecCase):
    def test_guided_quality_item_must_name_a_requirement_of_the_change(self):
        source = EXPIRY + """### REQ-002: Listing under load
The reset page must stay responsive under load.
#### AC-002: Fifty users at once
- **WHEN** 50 users open the reset page within one second
- **THEN** the p95 load time measured at the load balancer is below 2 s
"""
        project = self.bind(source, covers="REQ-001, REQ-002", tests="AC-001, AC-002")
        self.assertEqual(parse_spec((self.delivery() / "spec.md").read_text()).meta["requirements"],
                         ["REQ-001", "REQ-002"])
        self.edit_spec("## Quality attributes\n\n<!--", "## Quality attributes\n\n- p95 below 2 s\n\n<!--")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertTrue(any(text.startswith("quality attribute `p95 below 2 s` names no requirement of this change: ")
                            for text in report.todos), report.render())
        self.assertEqual(self.accept("password-reset", "proposal")[0], 1)
        self.edit_spec("- p95 below 2 s", "- REQ-009: p95 below 2 s")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertTrue(any("`REQ-009: p95 below 2 s` names REQ-009, not a requirement of this change" in text
                            for text in report.todos), report.render())
        self.edit_spec("- REQ-009: p95 below 2 s", "- REQ-002: p95 below 2 s")
        self.edit_spec("\n- None\n\n## Assumptions", "\n## Assumptions")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertFalse(report.blocking(("spec",)), report.render())
        canonical = project.specs / "auth.md"
        canonical.write_text(canonical.read_text().replace("is below 2 s", "stays low"))
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertIn("AC-002 is a criterion of quality attribute REQ-002: state the number with its unit and how it "
                      "is measured", report.errors, "p95 names a percentile, not the limit")
        canonical.write_text(canonical.read_text().replace("stays low", "is below 2 s"))
        code, out, err = self.accept("password-reset", "proposal")
        self.assertEqual(code, 0, out + err)


class ProposalTests(GuidedSpecCase):
    def test_proposal_shows_check_mode_and_specification_warnings(self):
        self.bind(EXPIRY.replace('the page displays "link expired"', "the link is refused"))
        out = self.run_cli("proposal", "password-reset")[1]
        self.assertIn("Approval code:", out)
        self.assertIn("Criteria check: strict; vague or unstructured criteria block approval", out)
        warnings = out[out.index("Warnings; resolve them, or name each one when presenting:"):]
        self.assertIn("- AC-001 outcome names no concrete value", warnings[:warnings.index("## Change intent")])
        self.assertLess(out.index("Approval code:"), out.index("Criteria check:"))
        self.assertLess(out.index("Criteria check:"), out.index("## Change intent"))
        self.set_strict("false")
        out = self.run_cli("proposal", "password-reset")[1]
        self.assertIn("Criteria check: warnings only (strict_criteria: false in config.yaml)", out)
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text().replace("criteria_syntax: ears", "criteria_syntax: free"))
        self.set_strict("true")
        out = self.run_cli("proposal", "password-reset")[1]
        self.assertIn("Criteria check: strict; vague criteria block approval; criteria_syntax: free, so their form is "
                      "not checked", out)

    def test_a_delivery_compares_with_the_living_spec_its_base_commit_holds(self):
        project = self.bind(EXPIRY)
        canonical = project.specs / "auth.md"
        canonical.write_text(canonical.read_text() + "\n### REQ-002: Login lockout\nThe account locks after five "
                             "failed logins.\n- AC-002: When the user fails a fifth time, the system shall lock the "
                             "account.\n")
        baseline = self.delivery() / "baseline.json"
        data = json.loads(baseline.read_text())
        baseline.write_text(json.dumps({**data, "content": canonical.read_text()}))
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertTrue(any(text.startswith("REQ-002 differs in .atipspec/specs/auth.md from the requirements "
                                            "accepted before this delivery") for text in report.errors),
                        "the content baseline.json holds is not what it compares with")
        # A delivery created before 0.3.0, without sections, still compares with its baseline.json.
        baseline.write_text(json.dumps({**{key: value for key, value in data.items() if key != "sections"},
                                        "content": canonical.read_text()}))
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertFalse([text for text in report.errors if "REQ-002" in text], report.render())

    def test_requirement_changed_in_specs_but_not_listed_is_an_error(self):
        project = self.bind(EXPIRY)
        canonical = project.specs / "auth.md"
        canonical.write_text(canonical.read_text() + "\n### REQ-002: Fast and user-friendly login\n"
                             "The login works correctly.\n- AC-002: The login is fast.\n")
        report = check_delivery(project, "password-reset", preapproval=True)
        self.assertEqual([text for text in report.errors if "accepted before this delivery" in text],
                         ["REQ-002 differs in .atipspec/specs/auth.md from the requirements accepted before this "
                          "delivery but is not listed in `requirements`: list it if this change writes it, so check "
                          "reads it, or remove it"])
        out = self.run_cli("proposal", "password-reset")[1]
        self.assertIn("- REQ-002 differs in .atipspec/specs/auth.md", out.split("Not ready for approval:")[1])
        self.assertNotIn("Approval code", out)


class DocumentationExampleTests(unittest.TestCase):
    """The specifications the documentation shows pass the lint they teach."""

    def test_documented_examples_pass_the_lint(self):
        docs = REPOSITORY / "docs"
        if not docs.is_dir():
            self.skipTest("the documentation is not part of this distribution")
        pages = [path for path in sorted(docs.rglob("*.md")) if not re.search(r"\.(es|pt)\.md$", path.name)]
        checked = 0
        for path in pages + [REPOSITORY / "README.md"]:
            for block in re.findall(r"^```[a-z]*\n(.*?)^```", path.read_text(encoding="utf-8"), re.S | re.M):
                if not re.search(r"^#{2,4} REQ-", block, re.M):
                    continue
                spec = parse_spec(block)
                for requirement in spec.requirements:
                    requirement.criteria = [ac for ac in requirement.criteria if "<" not in ac.text]
                checked += len(spec.criteria)
                findings = [finding.text for finding in lint_spec(spec, "en", "ears")]
                with self.subTest(page=str(path.relative_to(REPOSITORY))):
                    self.assertEqual(findings, [])
        self.assertGreater(checked, 5)

    def test_documented_vague_terms_are_the_tables(self):
        page = REPOSITORY / "docs" / "reference" / "spec-quality.md"
        if not page.is_file():
            self.skipTest("the documentation is not part of this distribution")
        listed = set(re.findall(r"`([^`\n]+)`", page.read_text(encoding="utf-8")))
        for language, terms in VAGUE.items():
            with self.subTest(language=language):
                self.assertEqual([term for term in terms if term not in listed], [])


if __name__ == "__main__":
    unittest.main()
