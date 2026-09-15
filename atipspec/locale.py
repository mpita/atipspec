"""Language tables. English is the primary language; Spanish and Portuguese
are supported. The framework files and the CLI output stay in English; what a
person reads (the acceptance dossier) and what the model writes in the
configured language (section names, empty markers, criteria) come from here.
"""
from __future__ import annotations

import re

LANGUAGES = ("en", "es", "pt")

# Section headings the parser recognizes, lowercase, per meaning.
SECTIONS = {
    "open_questions": ("open questions", "preguntas abiertas", "perguntas em aberto", "questões em aberto"),
    "assumptions": ("assumptions", "supuestos", "suposições", "premissas"),
}
# List items that mean "nothing here".
EMPTY_ITEMS = ("none", "ninguna", "ninguno", "nenhuma", "nenhum", "n/a", "-")
# `Verify:` values that mean "no command".
NO_COMMANDS = ("none", "ninguno", "ninguna", "nenhum", "nenhuma", "-", "n/a")

# EARS (Mavin, 2009): ubiquitous "shall", event-driven "when", state-driven
# "while", unwanted behavior "if ... then", optional "where"; plus the
# Given/When/Then scenario of Specification by Example.
TRIGGERS = {
    "en": ("when ", "while ", "if ", "where ", "given ", "after ", "whenever "),
    "es": ("cuando ", "mientras ", "si ", "donde ", "dado ", "dada ", "dados ", "dadas ", "después de ", "tras "),
    "pt": ("quando ", "enquanto ", "se ", "onde ", "dado ", "dada ", "dados ", "dadas ", "depois de ", "após "),
}
SHALL = {
    "en": re.compile(r"\b(shall|must)\b", re.I),
    "es": re.compile(r"\b(debe|deben|deberá|deberán)\b", re.I),
    "pt": re.compile(r"\b(deve|devem|deverá|deverão)\b", re.I),
}
# INCOSE Guide for Writing Requirements: terms whose meaning depends on the reader.
VAGUE = {
    "en": ("fast", "quickly", "user-friendly", "easy", "easily", "appropriate", "adequate", "efficient",
           "robust", "etc.", "and/or", "as needed", "if possible", "reasonable", "sufficient", "several",
           "many", "some", "approximately", "seamless", "seamlessly", "intuitive", "optimal", "flexible",
           "scalable", "as appropriate", "where possible", "timely", "minimal", "maximize", "minimize"),
    "es": ("rápido", "rápida", "rápidamente", "fácil", "fácilmente", "amigable", "adecuado", "adecuada",
           "apropiado", "apropiada", "eficiente", "robusto", "robusta", "etc.", "y/o", "según sea necesario",
           "si es posible", "razonable", "suficiente", "varios", "varias", "muchos", "muchas", "algunos",
           "algunas", "aproximadamente", "intuitivo", "intuitiva", "óptimo", "óptima", "flexible", "escalable",
           "cuando sea posible", "oportuno", "mínimo", "maximizar", "minimizar"),
    "pt": ("rápido", "rápida", "rapidamente", "fácil", "facilmente", "amigável", "adequado", "adequada",
           "apropriado", "apropriada", "eficiente", "robusto", "robusta", "etc.", "e/ou", "conforme necessário",
           "se possível", "razoável", "suficiente", "vários", "várias", "muitos", "muitas", "alguns", "algumas",
           "aproximadamente", "intuitivo", "intuitiva", "ótimo", "ótima", "flexível", "escalável",
           "quando possível", "oportuno", "mínimo", "maximizar", "minimizar"),
}

# The acceptance dossier is read by product, QA and risk owners: its labels
# follow the project's language. Identifiers, statuses and commands do not.
STRINGS = {
    "en": {
        "title": "Delivery acceptance", "dossier": "DELIVERY ACCEPTANCE DOSSIER", "status": "Status",
        "accepted": "Accepted", "yes": "yes", "no": "no", "scope": "Scope", "owner": "Owner", "ticket": "Ticket",
        "candidate": "Candidate", "content": "Content", "policy": "Policy",
        "criteria": "Acceptance criteria", "requirement": "Requirement", "criterion": "Criterion",
        "outcome": "Outcome", "tasks": "Tasks", "verdict": "Verdict", "proof": "Proof", "tests": "tests",
        "approvals": "Human approvals", "no_approvals": "No authenticated approvals.", "expires": "expires",
        "checks": "Checks and unresolved work", "all_passed": "All checks passed.",
        "evidence": "Verification evidence", "evidence_file": "evidence", "ci": "CI", "commands": "commands",
        "not_run": "not run", "generated": "Generated",
        "footer": "The dossier describes this candidate at the time shown. Its JSON contains artifact hashes; "
                  "retain the signed evidence and approvals alongside it.",
        "footer_html": "Retain the signed evidence and approvals with this report. Artifact hashes are available "
                       "in the JSON dossier.",
        "scope_trusted": "trusted acceptance", "scope_local": "local checks; not authenticated acceptance",
        "scope_archived": "historical acceptance receipt; approvals are not revalidated after archival",
    },
    "es": {
        "title": "Aceptación de la entrega", "dossier": "EXPEDIENTE DE ACEPTACIÓN DE LA ENTREGA", "status": "Estado",
        "accepted": "Aceptada", "yes": "sí", "no": "no", "scope": "Alcance", "owner": "Responsable", "ticket": "Ticket",
        "candidate": "Candidato", "content": "Contenido", "policy": "Política",
        "criteria": "Criterios de aceptación", "requirement": "Requisito", "criterion": "Criterio",
        "outcome": "Resultado", "tasks": "Tareas", "verdict": "Veredicto", "proof": "Prueba", "tests": "tests",
        "approvals": "Aprobaciones humanas", "no_approvals": "Sin aprobaciones autenticadas.", "expires": "caduca",
        "checks": "Comprobaciones y trabajo pendiente", "all_passed": "Todas las comprobaciones pasaron.",
        "evidence": "Evidencia de verificación", "evidence_file": "evidencia", "ci": "CI", "commands": "comandos",
        "not_run": "no ejecutado", "generated": "Generado",
        "footer": "El expediente describe este candidato en el momento indicado. Su JSON contiene los hashes de los "
                  "artefactos; conserve la evidencia firmada y las aprobaciones junto a él.",
        "footer_html": "Conserve la evidencia firmada y las aprobaciones con este informe. Los hashes de los "
                       "artefactos están en el expediente JSON.",
        "scope_trusted": "aceptación de confianza", "scope_local": "comprobaciones locales; no es una aceptación autenticada",
        "scope_archived": "recibo histórico de aceptación; las aprobaciones no se revalidan tras el archivado",
    },
    "pt": {
        "title": "Aceitação da entrega", "dossier": "DOSSIÊ DE ACEITAÇÃO DA ENTREGA", "status": "Estado",
        "accepted": "Aceita", "yes": "sim", "no": "não", "scope": "Escopo", "owner": "Responsável", "ticket": "Ticket",
        "candidate": "Candidato", "content": "Conteúdo", "policy": "Política",
        "criteria": "Critérios de aceitação", "requirement": "Requisito", "criterion": "Critério",
        "outcome": "Resultado", "tasks": "Tarefas", "verdict": "Veredito", "proof": "Prova", "tests": "testes",
        "approvals": "Aprovações humanas", "no_approvals": "Sem aprovações autenticadas.", "expires": "expira",
        "checks": "Verificações e trabalho pendente", "all_passed": "Todas as verificações passaram.",
        "evidence": "Evidência de verificação", "evidence_file": "evidência", "ci": "CI", "commands": "comandos",
        "not_run": "não executado", "generated": "Gerado",
        "footer": "O dossiê descreve este candidato no momento indicado. Seu JSON contém os hashes dos artefatos; "
                  "guarde a evidência assinada e as aprovações junto a ele.",
        "footer_html": "Guarde a evidência assinada e as aprovações com este relatório. Os hashes dos artefatos "
                       "estão no dossiê JSON.",
        "scope_trusted": "aceitação confiável", "scope_local": "verificações locais; não é uma aceitação autenticada",
        "scope_archived": "recibo histórico de aceitação; as aprovações não são revalidadas após o arquivamento",
    },
}


def code(language: str | None) -> str | None:
    """The language table to use, or None when there is none for it."""
    value = (language or "en").lower().split("-")[0].split("_")[0]
    return value if value in LANGUAGES else None


def strings(language: str | None) -> dict:
    return STRINGS[code(language) or "en"]


def section_pattern(meaning: str) -> re.Pattern:
    return re.compile("^(" + "|".join(re.escape(name) for name in SECTIONS[meaning]) + ")$", re.I)


def empty_pattern() -> re.Pattern:
    return re.compile("^(" + "|".join(re.escape(item) for item in EMPTY_ITEMS) + r")\.?$", re.I)
