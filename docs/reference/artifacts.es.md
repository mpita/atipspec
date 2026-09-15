# Artefactos

Las specs y los planes usan Markdown con un pequeño frontmatter YAML. La
evidencia, los registros de aprobación y los recibos de informe usan JSON;
las firmas son ficheros SSH separados. El CLI analiza unas pocas formas de
línea e ignora los comentarios HTML y el código en bloques, así que las
plantillas pueden llevar guías que el modelo borra a medida que escribe.

## Identificadores

| Tipo | Formato | Alcance |
| --- | --- | --- |
| Slug de entrega, capacidad, iniciativa, decisión | `[a-z0-9-]`, p. ej. `password-reset` | proyecto |
| Requisito | `REQ-001` | capacidad, estable a través de las entregas |
| Criterio de aceptación | `AC-001` | capacidad, estable a través de las entregas |
| Tarea | `T1` | la entrega |
| Hallazgo | `F1` | la revisión |
| Decisión | `DEC-001` | proyecto, nunca se reutiliza |

## `spec.md`

```markdown
---
title: "Password reset"
status: draft          # draft or ready; `atipspec accept <slug> spec`, run by a person, sets ready
kind: feature          # or fix: a defect repair, one regression criterion, no plan acceptance
capability: auth       # living spec that receives the requirements on deliver
impact: [notifications]  # other living specs or contract sections touched
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...        # commit the delivery started from; diff and rules use it
created: 2026-09-12T15:41:45Z   # `status` shows the age from here
---

# Password reset

## Intent

## Requirements

### REQ-001: Behavior title
Description.

Why: the reason, one line.

Acceptance criteria:
- AC-001: When <trigger>, the system <observable outcome with concrete values>.
- AC-002 [manual]: When <trigger>, a person observes <outcome>.

### REQ-002 [remove]: Behavior being removed
- AC-003: If the removed behavior is requested, then the system responds with <outcome>.

## Quality attributes

## Assumptions
- None

## Out of scope

## Open questions
- None
```

Analizado: encabezados `### REQ-nnn[ [remove]]: title` (niveles 2 a 4),
líneas `- AC-nnn[ [test|manual]]: text` bajo un requisito (`[manual]` marca
un criterio que observa una persona; el plan debe listarlo bajo `Manual:`),
elementos de lista bajo `## Assumptions` y `## Open questions` (`- None`
cuenta como vacío). Las líneas `Why:` y los ejemplos son para las personas y
el revisor. Consulta [escribir criterios](spec-quality.md) para la forma que
espera `check`.

## `plan.md`

```markdown
---
scope: ["shop/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

## Tasks

### T1: Task title
Covers: REQ-001, REQ-002
Tests: AC-001, AC-002
Verify:
- `python -m pytest -q tests/auth`
- `ruff check .`

### T2: Observed only
Covers: REQ-003
Manual: AC-003
Verify: none
```

Analizado: `### Tn: title`, una línea `Covers:` con ids de REQ, una línea
`Verify:` seguida de elementos de lista (las comillas invertidas son
opcionales) o la palabra `none`, una línea opcional `Report:` con el XML de
JUnit que escriben los comandos, y una línea opcional `Proof:` seguida de
elementos `- AC-nnn: test id` que `check` verifica contra la evidencia
(consulta [build](../flow/build.md)). `scope` en la frontmatter lista globs
de los ficheros que las tareas pueden cambiar, con la [sintaxis de glob de
las reglas del contrato](contract-rules.md#globs): `check` avisa sobre
ficheros tocados fuera de ellos, incluidas las eliminaciones (un error con
`strict_scope: true`), y el paquete de la revisión los lista. Los ficheros
bajo `.atipspec/` nunca cuentan. Un `scope` vacío o ausente no declara nada.

## `review.md`

Escrito solo por el revisor.

```markdown
---
tree: <fingerprint from the packet>
reviewer: <client or model>
---

## Criteria
- AC-001: PASS. proof pointer
- AC-002: FAIL. precise gap

## Findings
- F1 [blocker]: text
- F2 [major]: text
- F3 [minor]: text

## Notes
```

Todo criterio necesita exactamente un veredicto con un puntero de prueba o
una razón de fallo. Los hallazgos blocker y major bloquean; aplazar
cualquiera de los dos necesita una aprobación de riesgo de confianza con
caducidad. Los hallazgos minor informan.

## `deferred.md`

```markdown
- F2: reason, and where it will be handled
```

Solo se pueden aplazar hallazgos. Una entrada `AC-` o `REQ-` es un error.

## `brief.md`

La salida de la fase explore: Problem, Today, Options, Recommendation,
Questions for the user. No se analiza; se incluye en el contexto.

## `evidence/Tn-<timestamp>.json`

Generado por `atipspec verify`: versión de esquema, entrega, tarea,
resultado, árbol antes/después, head, timestamps, entorno y comandos exactos
con códigos de salida, duración, cola de salida, ruta completa del log y
hash del log; con un `Report:`, el XML de JUnit copiado con su hash y cada
caso de test con su estado. Cuenta el fichero más reciente por tarea. La
atestación de CI de confianza añade firmante, repositorio, digest de policy,
URL de la ejecución y una firma `.json.sig` separada. Los ficheros sin
firmar son solo evidencia local.

## `specs/<capability>.md`

La spec viva conserva las secciones `### REQ-nnn: Title` y los criterios
`AC-nnn`. `deliver` actualiza por ID estable, preservando la identidad al
renombrar. Todo requisito y criterio de aceptación vivo debe tener un ID
desde el principio.

## `decisions/DEC-nnn-<slug>.md`

```markdown
---
id: DEC-003
title: "Use httpx for outbound HTTP"
status: accepted        # proposed, accepted, superseded, rejected
affects: [contract:dependencies, notifications]
supersedes: null
date: 2026-09-12
---

## Context
## Decision
## Alternatives
## Consequences
## Revisit when
```

`context` carga las decisiones aceptadas cuyo `affects` nombra la capacidad
de la entrega, una entrada de impact, `contract` o `*`.

## `initiatives/<slug>/roadmap.md`

```markdown
## Deliveries
- orders-api: Orders API
- orders-screen: Orders screen

## Interfaces
```

Analizado: líneas `- <slug>: title` bajo `## Deliveries`. El status por
entrega se deriva: pending, su status actual, o delivered.

## Status derivado de una entrega

| Status | Significado |
| --- | --- |
| `draft` | la spec no está aceptada para su contenido actual |
| `ready` | spec aceptada, todavía sin plan |
| `planned` | plan con tareas, nada con commit; con `approve_plan`, el plan también necesita aceptación |
| `in_progress` | algunas tareas con commit |
| `implemented` | todas las tareas con commit, la puerta no está en verde |
| `checked` | comprobaciones locales en verde; sin aceptación autenticada |
| `verified` | puerta de confianza en verde con policy aprobada, evidencia de CI firmada y aprobaciones humanas |
| `delivered` | fusionada en la spec viva y archivada |

## Aprobaciones y recibos

`approvals/local-spec.json` y `approvals/local-plan.json` los escribe
`atipspec accept`: kind `local-acceptance`, phase, hash del subject, quién y
cuándo. Son detección de deriva para la puerta local y se ignoran bajo una
policy.

Los `approvals/*.json` firmados registran phase, identity, role, el
timestamp de aprobación, el hash del subject, el repositorio, el digest de
policy y una caducidad opcional. Cada uno tiene una firma SSH `.json.sig`.
Los registros de proveedor también llevan la identidad del PR/MR y la URL de
origen, y se revalidan contra el proveedor en el momento de la aceptación.
`reports/acceptance.json` es el recibo archivado y el índice de artefactos.
Consulta [aceptación empresarial](../enterprise.md).
