"""Criterion lint: the wording checks a machine can make on an acceptance
criterion, following the INCOSE Guide for Writing Requirements and EARS.

Two checks, both by the project's language: the criterion follows a structured
form (an EARS trigger, a scenario, or a "shall" statement), and it contains no
vague term. Neither proves a criterion is good; both catch the criteria that
cannot be verified as written.
"""
from __future__ import annotations

import re

from .locale import SHALL, TRIGGERS, VAGUE
from .locale import code as _language


def follows_form(text: str, language: str) -> bool:
    """True when the criterion starts with a trigger or opens with a subject
    and a shall (the ubiquitous form), or when the language has no tables."""
    code = _language(language)
    if code is None:
        return True
    lowered = text.strip().lower()
    # The templates are in English, so English triggers count in every language.
    codes = (code, "en") if code != "en" else ("en",)
    if any(lowered.startswith(trigger) for c in codes for trigger in TRIGGERS[c]):
        return True
    # Ubiquitous form: the shall belongs to the main clause, before any comma.
    clause = re.split(r"[,;:]", lowered, maxsplit=1)[0]
    return any(SHALL[c].search(clause) for c in codes)


def vague_terms(text: str, language: str) -> list[str]:
    """The vague terms the criterion contains, in the order they appear. A
    language without tables gets the English list."""
    code = _language(language) or "en"
    lowered = text.lower()
    found: dict[str, int] = {}
    for term in VAGUE[code] + (VAGUE["en"] if code != "en" else ()):
        match = re.search(r"(?<![\w/])" + re.escape(term.lower()) + r"(?![\w/])", lowered)
        if match and term not in found:
            found[term] = match.start()
    return sorted(found, key=found.get)


def lint_criterion(ident: str, text: str, language: str, syntax: str) -> list[str]:
    """Problems with one criterion, as messages without a level."""
    problems = []
    if syntax != "free" and _language(language) is not None and not follows_form(text, language):
        problems.append(f"{ident} does not follow the EARS or scenario form (when/while/if/given ..., "
                        "or a shall statement); set criteria_syntax: free to disable")
    terms = vague_terms(text, language)
    if terms:
        problems.append(f"{ident} uses vague terms ({', '.join(terms)}); state the observable value instead")
    return problems
