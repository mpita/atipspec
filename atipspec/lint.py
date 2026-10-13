"""Specification lint: the wording checks a machine can make on requirements
and their acceptance criteria, following the INCOSE Guide for Writing
Requirements, EARS, Specification by Example and Volere's fit criterion.

Strict findings follow `strict_criteria` (errors when true, warnings when
false): a criterion statement outside the EARS or scenario form; a vague term
in a requirement's title or statement, or in a criterion, its scenario title
and every step; and a quality attribute's criterion whose outcome states no
number. Advice is always a warning, because it is a heuristic: an outcome that
names no concrete value, quoted text that holds a vague term, and a quality
attribute's criterion that does not say how it is measured. None of them
proves a criterion is good; they catch the ones that cannot be verified as
written.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .locale import CRITERIA_LABELS, MEASURED, SHALL, TRIGGERS, UNLINTED_LABELS, VAGUE
from .locale import code as _language

# Literal text the specification quotes, such as a label shown on screen: the
# strict check never reads inside it, and it counts as a concrete value unless
# it holds a vague term.
LITERAL = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»|`[^`\n]*`')
# Identifiers, not prose: a token with a colon inside (`theme:slow-unresponsive`)
# and a cardinality (`many-to-many`, `one-to-many`).
IDENTIFIER = re.compile(r"\S*\w:\w\S*|\b(?:one|many|\d+)-to-(?:one|many|\d+)\b")
# The underscores of Markdown emphasis (`_quickly_`), not those inside a snake_case name.
EMPHASIS = re.compile(r"(?<!\w)_+|_+(?!\w)")
# A number starts a word: the 95 of `p95` names a percentile, not a value.
NUMBER = re.compile(r"\b\d")
CONCRETE = re.compile(NUMBER.pattern + r"|(?<![\w.])/[\w-]|\S@\S")
WORD = re.compile(r"[^\W\d_][\w'’-]*")
# Words that open a sentence or a step without naming anything, lowercase.
KEYWORDS = {"the", "a", "an", "i", "it", "its", "this", "that", "they", "system", "shall", "must", "when",
            "whenever", "while", "if", "where", "given", "after", "then", "and", "but", "invariant", "el", "la",
            "los", "las", "un", "una", "lo", "sistema", "debe", "deben", "deberá", "cuando", "mientras", "si",
            "donde", "dado", "dada", "dados", "dadas", "tras", "entonces", "y", "pero", "invariante", "o", "os",
            "as", "um", "uma", "deve", "devem", "deverá", "quando", "enquanto", "se", "onde", "então", "e", "mas",
            "após"}
OUTCOME_STEPS = ("THEN", "INVARIANT")
# Spanish and Portuguese step words: a scenario written with them is also read
# with that language's terms, whatever the project's language.
STEP_LANGUAGES = {"es": {"dado", "dada", "dados", "dadas", "cuando", "entonces", "y", "pero", "invariante"},
                  "pt": {"dado", "dada", "dados", "dadas", "quando", "então", "entao", "e", "mas", "invariante"}}
LABEL = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:")


@dataclass
class Finding:
    text: str
    strict: bool = True


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


def vague_terms(text: str, language: str, *more: str) -> list[str]:
    """The vague terms the text contains, in the order they appear, from the
    tables of the language, of the languages in `more` and of English. Quoted
    literals are not read, a term inside a longer one found at the same place
    is left out, and identifiers such as `theme:slow` or `many-to-many` do not
    match; a hyphenated compound such as `fast-loading` does. A language
    without tables gets the English list."""
    lowered = text.lower()
    for pattern in (LITERAL, IDENTIFIER, EMPHASIS):
        lowered = pattern.sub(lambda match: " " * len(match.group(0)), lowered)
    spans: dict[str, tuple[int, int]] = {}
    for code in dict.fromkeys((_language(language) or "en", *more, "en")):
        for term in VAGUE[code]:
            match = re.search(r"(?<![\w/:])" + re.escape(term.lower()) + r"(?![\w/])", lowered)
            if match and term not in spans:
                spans[term] = match.span()
    found = [term for term, (start, end) in spans.items()
             if not any(other[0] <= start and end <= other[1] and other != (start, end) for other in spans.values())]
    return sorted(found, key=lambda term: spans[term][0])


def quoted_vague(text: str, language: str, *more: str) -> dict[str, list[str]]:
    """Each quoted literal that holds vague terms, with those terms: the strict
    check does not read quotes, so quoting an adjective must not hide it."""
    found: dict[str, list[str]] = {}
    for match in LITERAL.finditer(text):
        terms = vague_terms(match.group(0)[1:-1], language, *more)
        if terms:
            found[match.group(0)] = terms
    return found


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


def outcome(criterion) -> str:
    """What the criterion asserts: in a scenario or invariant, the THEN or
    INVARIANT step and the AND/BUT steps after it; in a statement, the text
    after the first comma unless the first clause holds the shall, else all of it."""
    if criterion.form != "statement":
        steps, started = [], False
        for word, value in criterion.steps:
            started = started or word in OUTCOME_STEPS
            if started:
                steps.append(value)
        return "\n".join(steps)
    clause, comma, rest = criterion.text.partition(",")
    if comma and rest.strip() and not any(pattern.search(clause) for pattern in SHALL.values()):
        return rest.strip()
    return criterion.text


def has_concrete_value(text: str, language: str = "en", *more: str) -> bool:
    """Whether the text names something a test or a person can compare: a
    number, quoted text without a vague term, a path, an address, or a
    capitalized name (of a page, a state, a role) that opens neither the line
    nor a sentence and is no keyword."""
    vague = quoted_vague(text, language, *more)
    text = LITERAL.sub(lambda match: " " if match.group(0) in vague else match.group(0), text)
    if LITERAL.search(text) or CONCRETE.search(text):
        return True
    for line in text.splitlines():
        for match in WORD.finditer(line):
            word, before = match.group(0), line[:match.start()].rstrip()
            if word[:1].isupper() and before and before[-1] not in ".!?;" and word.lower() not in KEYWORDS:
                return True
    return False


def requirement_text(requirement) -> str:
    """The requirement as stated: its title and the lines that describe it,
    without its criteria and scenarios, headings, the criteria label, or the
    lines that give its reason or, in a fix, the defect observed today. Those
    run on like a Markdown paragraph, with the list under them, up to a blank
    line, a criterion or another label; a label alone also takes the block
    after the blank lines that follow it."""
    from .delivery import AC_HEADING, AC_LIKE, HEADING, LIST_ITEM
    lines = [requirement.title]
    in_scenario = False
    skipping: str | None = None    # "criterion" or "label" while the lines after one belong to it
    item = opened = False          # whether that label is a list item, and whether its text has started
    for line in requirement.body:
        in_scenario = in_scenario or bool(AC_HEADING.match(line))
        if in_scenario or HEADING.match(line):
            skipping = None
            continue
        if not line.strip():
            skipping = "label" if skipping == "label" and not opened else None
            continue
        # An indented line continues the line before it; a criterion, as the
        # parser reads it, only those that are no list item.
        if skipping and line[:1].isspace() and not (skipping == "criterion" and LIST_ITEM.match(line)):
            continue
        label = LABEL.match(line)
        listed = bool(LIST_ITEM.match(line))
        # Under a label, a list belongs to it unless the label is an item of
        # that list; a line that is no item, unless it opens another label.
        if skipping == "label" and not AC_LIKE.match(line) and (not item if listed else not label):
            opened = True
            continue
        name = label.group(1).strip().lower() if label else None
        skipping = "criterion" if AC_LIKE.match(line) else "label" if name in UNLINTED_LABELS else None
        if skipping == "label":
            item, opened = listed, bool(line[label.end():].strip(" *\t"))
        if not skipping:
            lines.append((line[label.end():] if name in CRITERIA_LABELS else line).strip(" *\t"))
    return "\n".join(line for line in lines if line)


def step_languages(requirement) -> tuple[str, ...]:
    """The languages with tables whose step words the requirement's scenarios use."""
    from .delivery import AC_HEADING, STEP
    words: set[str] = set()
    in_scenario = False
    for line in requirement.body:
        in_scenario = in_scenario or bool(AC_HEADING.match(line))
        step = STEP.match(line) if in_scenario else None
        if step:
            words.add(step.group(1).lower())
    return tuple(code for code, table in STEP_LANGUAGES.items() if words & table)


def fit_criterion(criterion, language: str) -> tuple[bool, bool]:
    """Volere's fit criterion for a quality attribute: (the outcome states a
    number, the criterion says how it is measured)."""
    code = _language(language) or "en"
    text = LITERAL.sub(" ", f"{criterion.title or ''}\n{criterion.text}".lower())
    words = MEASURED[code] + (MEASURED["en"] if code != "en" else ())
    measured = any(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text) for word in words)
    return bool(NUMBER.search(outcome(criterion))), measured


def lint_spec(spec, language: str, syntax: str) -> list[Finding]:
    """Every finding for the requirements the delivery defines or references
    and their criteria, in order. A requirement being removed keeps its title,
    which must match the living spec's, so only its criteria are read."""
    findings: list[Finding] = []
    quality = spec.quality_requirements

    def quoted(ident: str, text: str, *more: str) -> list[Finding]:
        return [Finding(f"{ident} quotes {literal}, which holds vague terms ({', '.join(terms)}): keep it only if "
                        "it is the interface's literal text, else state the observable value", strict=False)
                for literal, terms in quoted_vague(text, language, *more).items()]

    for requirement in spec.requirements:
        more = step_languages(requirement)
        stated = "" if requirement.remove else requirement_text(requirement)
        terms = vague_terms(stated, language)
        if terms:
            findings.append(Finding(f"{requirement.id} uses vague terms ({', '.join(terms)}); "
                                    "state the observable value instead"))
        findings += quoted(requirement.id, stated)
        for criterion in requirement.criteria:
            if criterion.form == "statement":
                findings += [Finding(text) for text in lint_criterion(criterion.id, criterion.text, language, syntax)]
                findings += quoted(criterion.id, criterion.text)
            else:
                read = "\n".join([criterion.title or ""] + [value for _, value in criterion.steps])
                terms = vague_terms(read, language, *more)
                if terms:
                    findings.append(Finding(f"{criterion.id} uses vague terms ({', '.join(terms)}); "
                                            "state the observable value instead"))
                findings += quoted(criterion.id, read, *more)
            if requirement.id in quality:
                number, measured = fit_criterion(criterion, language)
                if not number:
                    findings.append(Finding(f"{criterion.id} is a criterion of quality attribute {requirement.id}: "
                                            "state the number with its unit and how it is measured"))
                elif not measured:
                    findings.append(Finding(f"{criterion.id} is a criterion of quality attribute {requirement.id} "
                                            "but does not say how it is measured: name where and with what, such as "
                                            "\"measured at the API gateway\"", strict=False))
            elif not has_concrete_value(outcome(criterion), language, *more):
                findings.append(Finding(f"{criterion.id} outcome names no concrete value (a number, quoted text, "
                                        "a path or a name); state what a test or a person observes", strict=False))
    return findings
