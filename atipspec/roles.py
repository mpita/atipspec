"""Role responsibilities and risk-based activation for guided delivery."""
from __future__ import annotations

ROLES = {
    "guide": "Read the request and relevant repository facts. Separate facts, user decisions and assumptions. Ask only consequential unresolved questions. Present the agreement and offer approval, changes or cancellation in the conversation. Record explicit human confirmation with the local accept command and continue; do not require the user to run it. Never invent approval or replace an external policy's authenticated procedure.",
    "analyst": "Define actors, observable outcomes, scope and verifiable scenarios in canonical specs. Include relevant failures and boundaries. Do not invent business decisions or copy the same definition into the delivery.",
    "designer": "Choose the simplest compatible implementation within approved constraints. Identify affected interfaces, dependencies and recovery needs. Keep routine decomposition separate from approved commitments.",
    "tester": "Check scenario sufficiency before implementation. Select tests by risk, including negative permissions and isolation cases when applicable. During execution link actual results to behaviors. A successful build does not prove a business outcome.",
    "implementer": "Implement the assigned approved behavior and regression tests. Use focused development checks. Do not change requirements, approvals or review to conceal failure. Return a summary and real limitations. Do not commit, push, merge or deploy.",
    "reviewer": "Read the approved requirements, diff, current code and evidence. Return precise PASS/FAIL verdicts and justified findings. No findings is valid. Do not edit code or approve the result. Disclose context independence and observations not performed.",
}


def active_roles(risk):
    if risk == "low":
        return ["guide", "implementer", "reviewer"]
    return ["guide", "analyst", "designer", "tester", "implementer", "reviewer"]


def role_instruction(role, risk="normal"):
    if role not in ROLES:
        from .errors import AtipSpecError
        raise AtipSpecError(f"Unknown role: {role}")
    text = ROLES[role]
    if risk == "high":
        text += " High risk: explicitly examine data loss, authorization, tenant isolation, compatibility and recovery where applicable; unresolved material decisions block execution."
    return text
