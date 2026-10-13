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
    "intent": ("intent", "intención", "intenção"),
    "out_of_scope": ("out of scope", "fuera de alcance", "fora do escopo", "fora de escopo"),
    "quality": ("quality attributes", "atributos de calidad", "atributos de qualidade"),
    "defect": ("defect", "defecto", "defeito"),
    "context": ("context", "contexto"),
    "decision": ("decision", "decisión", "decisão"),
}
# Labels of requirement lines that are not the requirement: its reason and,
# in a fix, the defect observed today. The lint leaves them out.
UNLINTED_LABELS = ("why", "por qué", "motivo", "por quê", "observed", "observado", "observada")
# The labels of a guided fix's `## Defect` section, by meaning.
DEFECT_LABELS = {
    "observed": ("observed", "observado", "observada"),
    "expected": ("expected", "esperado", "esperada"),
    "reproduction": ("reproduction", "reproducción", "reprodução"),
}
# Labels that introduce a requirement's criteria.
CRITERIA_LABELS = ("acceptance criteria", "criterios de aceptación", "critérios de aceitação")
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
# Words with frequent precise uses stay out (correct password, expected value,
# well-formed, significant digits, effective date, a minimum of 12).
VAGUE = {
    "en": ("fast", "quick", "quickly", "slow", "user-friendly", "user friendly", "easy", "easily", "easy-to-use",
           "appropriate", "appropriately", "adequate", "adequately", "efficient", "efficiently", "effectively",
           "robust", "etc.", "and/or", "and so on", "as needed", "if possible", "if necessary", "when necessary",
           "as soon as possible", "reasonable", "reasonably", "sufficient", "sufficiently", "several", "a few",
           "many", "some", "approximately", "seamless", "seamlessly", "intuitive", "intuitively", "optimal",
           "optimally", "flexible", "scalable", "as appropriate", "where possible", "timely", "minimal", "maximize",
           "minimize", "relevant", "typically", "usually", "correctly", "properly", "as expected", "as intended",
           "works well", "work well"),
    "es": ("rápido", "rápida", "rápidos", "rápidas", "rápidamente", "fácil", "fáciles", "fácilmente", "amigable",
           "amigables", "adecuado", "adecuada", "adecuados", "adecuadas", "adecuadamente", "apropiado", "apropiada",
           "apropiados", "apropiadas", "apropiadamente", "eficiente", "eficientes", "eficientemente", "robusto",
           "robusta", "robustos", "robustas", "etc.", "y/o", "y así sucesivamente", "según sea necesario",
           "si es necesario", "cuando sea necesario", "si es posible", "lo antes posible", "razonable", "razonables",
           "razonablemente", "suficiente", "suficientes", "suficientemente", "varios", "varias", "unos pocos",
           "unas pocas", "muchos", "muchas", "algunos", "algunas", "aproximadamente", "intuitivo", "intuitiva",
           "intuitivos", "intuitivas", "intuitivamente", "óptimo", "óptima", "óptimos", "óptimas", "flexible",
           "flexibles", "escalable", "escalables", "cuando sea posible", "oportuno", "oportuna", "lo mínimo",
           "al mínimo", "mínimo posible", "maximizar", "minimizar", "relevante", "relevantes", "normalmente",
           "habitualmente", "correctamente", "como se espera", "como es de esperar", "según lo previsto",
           "funciona bien", "funcione bien", "sin problemas"),
    "pt": ("rápido", "rápida", "rápidos", "rápidas", "rapidamente", "fácil", "fáceis", "facilmente", "amigável",
           "amigáveis", "adequado", "adequada", "adequados", "adequadas", "adequadamente", "apropriado",
           "apropriada", "apropriados", "apropriadas", "apropriadamente", "eficiente", "eficientes",
           "eficientemente", "robusto", "robusta", "robustos", "robustas", "etc.", "e/ou", "e assim por diante",
           "conforme necessário", "se necessário", "quando necessário", "se possível", "o mais rápido possível",
           "o quanto antes", "razoável", "razoáveis", "razoavelmente", "suficiente", "suficientes",
           "suficientemente", "vários", "várias", "alguns poucos", "muitos", "muitas", "alguns", "algumas",
           "aproximadamente", "intuitivo", "intuitiva", "intuitivos", "intuitivas", "intuitivamente", "ótimo",
           "ótima", "ótimos", "ótimas", "flexível", "flexíveis", "escalável", "escaláveis", "quando possível",
           "oportuno", "oportuna", "o mínimo", "ao mínimo", "mínimo possível", "maximizar", "minimizar",
           "relevante", "relevantes", "normalmente", "geralmente", "habitualmente", "corretamente",
           "como esperado", "conforme esperado", "conforme previsto", "funciona bem", "funcione bem",
           "sem problemas"),
}
# Volere's fit criterion: a quality attribute's criterion says how it is measured.
MEASURED = {
    "en": ("measured", "measuring", "measurement"),
    "es": ("medido", "medida", "medidos", "medidas", "se mide", "medición"),
    "pt": ("medido", "medida", "medidos", "medidas", "medição"),
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
        "channel": "channel", "channel_unrecorded": "not recorded", "code": "code", "approval_code": "Approval code",
        "approval_code_hint": "After the human accepts this result, the assistant records it with "
                              "`atipspec accept {slug} result --code {code}`. The code changes when the result changes.",
        "review": "Review", "reviewer": "Reviewer", "session": "session", "no_review": "No review recorded.",
        "session_shared": "The reviewer shared the author's session, so these verdicts are not independent.",
        "review_rounds": "Review {used} of {limit}.",
        "kind": "Kind", "risk": "Risk", "lead_time": "Lead time",
        "lead_time_done": "{hours} h from creation to result acceptance",
        "lead_time_open": "{hours} h since creation; the result is not accepted yet",
        "lead_time_unknown": "unknown, the creation time is unreadable",
        "pointer": "resolves to", "unresolved": "unresolved", "observation": "an observation",
        "not_needed": "risk low: its named test passed in the current evidence, so it needs no reviewer verdict",
        "changes": "Changes from the base commit", "base": "Base", "file": "File", "change": "Change",
        "lines": "Lines", "outside_scope": "Outside the scope", "binary": "binary", "files_count": "{count} file(s)",
        "binary_files": "The diff shows no content for these binary files: {names}. Open them in the repository "
                        "before you accept.",
        "harness_files": "These files configure how the tests run and report, so a change in them can change what "
                         "the evidence says: {names}. Read their diff before you accept.",
        "no_changes": "No file differs from the base commit.",
        "integrated_files": "Brought by {ref} since the base commit and integrated there, so neither listed nor in "
                            "the diff: {names}.",
        "integrated_rest": "{count} file(s) under .atipspec/",
        "added": "added", "modified": "modified", "deleted": "deleted", "type_changed": "type changed",
        "diff_truncated": "Diff truncated: the first {shown} of {total} bytes are shown; the full diff has sha256 "
                          "`{sha}`. Inspect the repository from base `{base}` for the rest.",
        "diff_not_retained": "The archived receipt keeps no diff text: {total} bytes, sha256 `{sha}`; the git "
                             "history holds it.",
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
        "channel": "canal", "channel_unrecorded": "no registrado", "code": "código", "approval_code": "Código de aprobación",
        "approval_code_hint": "Cuando la persona acepte este resultado, el asistente lo registra con "
                              "`atipspec accept {slug} result --code {code}`. El código cambia si cambia el resultado.",
        "review": "Revisión", "reviewer": "Revisor", "session": "sesión", "no_review": "No hay revisión registrada.",
        "session_shared": "El revisor compartió la sesión del autor, así que estos veredictos no son independientes.",
        "review_rounds": "Revisión {used} de {limit}.",
        "kind": "Tipo", "risk": "Riesgo", "lead_time": "Tiempo de entrega",
        "lead_time_done": "{hours} h desde la creación hasta la aceptación del resultado",
        "lead_time_open": "{hours} h desde la creación; el resultado aún no está aceptado",
        "lead_time_unknown": "desconocido, la fecha de creación no se puede leer",
        "pointer": "remite a", "unresolved": "sin resolver", "observation": "una observación",
        "not_needed": "riesgo bajo: su test nombrado pasó en la evidencia actual, así que no necesita veredicto del revisor",
        "changes": "Cambios respecto al commit base", "base": "Base", "file": "Fichero", "change": "Cambio",
        "lines": "Líneas", "outside_scope": "Fuera del alcance", "binary": "binario", "files_count": "{count} fichero(s)",
        "binary_files": "El diff no muestra el contenido de estos ficheros binarios: {names}. Ábralos en el "
                        "repositorio antes de aceptar.",
        "harness_files": "Estos ficheros configuran cómo se ejecutan los tests y cómo informan, así que un cambio en "
                         "ellos puede cambiar lo que dice la evidencia: {names}. Lea su diff antes de aceptar.",
        "no_changes": "Ningún fichero difiere del commit base.",
        "integrated_files": "Traídos por {ref} desde el commit base e integrados allí, así que no se listan ni "
                            "están en el diff: {names}.",
        "integrated_rest": "{count} fichero(s) bajo .atipspec/",
        "added": "añadido", "modified": "modificado", "deleted": "eliminado", "type_changed": "cambio de tipo",
        "diff_truncated": "Diff recortado: se muestran los primeros {shown} de {total} bytes; el diff completo tiene "
                          "sha256 `{sha}`. Revise el resto en el repositorio a partir de la base `{base}`.",
        "diff_not_retained": "El recibo archivado no guarda el texto del diff: {total} bytes, sha256 `{sha}`; lo "
                             "conserva la historia de git.",
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
        "channel": "canal", "channel_unrecorded": "não registrado", "code": "código", "approval_code": "Código de aprovação",
        "approval_code_hint": "Quando a pessoa aceitar este resultado, o assistente o registra com "
                              "`atipspec accept {slug} result --code {code}`. O código muda se o resultado mudar.",
        "review": "Revisão", "reviewer": "Revisor", "session": "sessão", "no_review": "Nenhuma revisão registrada.",
        "session_shared": "O revisor compartilhou a sessão do autor, então estes vereditos não são independentes.",
        "review_rounds": "Revisão {used} de {limit}.",
        "kind": "Tipo", "risk": "Risco", "lead_time": "Tempo de entrega",
        "lead_time_done": "{hours} h da criação à aceitação do resultado",
        "lead_time_open": "{hours} h desde a criação; o resultado ainda não foi aceito",
        "lead_time_unknown": "desconhecido, a data de criação não pode ser lida",
        "pointer": "remete a", "unresolved": "não resolvido", "observation": "uma observação",
        "not_needed": "risco baixo: o teste nomeado passou na evidência atual, então não precisa de veredito do revisor",
        "changes": "Mudanças em relação ao commit base", "base": "Base", "file": "Arquivo", "change": "Mudança",
        "lines": "Linhas", "outside_scope": "Fora do escopo", "binary": "binário", "files_count": "{count} arquivo(s)",
        "binary_files": "O diff não mostra o conteúdo destes arquivos binários: {names}. Abra-os no repositório "
                        "antes de aceitar.",
        "harness_files": "Estes arquivos configuram como os testes rodam e informam, então uma mudança neles pode "
                         "mudar o que a evidência diz: {names}. Leia o diff deles antes de aceitar.",
        "no_changes": "Nenhum arquivo difere do commit base.",
        "integrated_files": "Trazidos por {ref} desde o commit base e integrados lá, então não são listados nem "
                            "estão no diff: {names}.",
        "integrated_rest": "{count} arquivo(s) em .atipspec/",
        "added": "adicionado", "modified": "modificado", "deleted": "excluído", "type_changed": "mudança de tipo",
        "diff_truncated": "Diff cortado: são mostrados os primeiros {shown} de {total} bytes; o diff completo tem "
                          "sha256 `{sha}`. Examine o restante no repositório a partir da base `{base}`.",
        "diff_not_retained": "O recibo arquivado não guarda o texto do diff: {total} bytes, sha256 `{sha}`; o "
                             "histórico do git o conserva.",
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
