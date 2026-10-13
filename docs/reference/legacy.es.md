# Entregas antiguas

Una entrega antigua guarda sus requisitos dentro de su propio `spec.md`, sin
`schema: 2`. `atipspec new` crea entregas guiadas desde 0.2.0, y fixes guiados
desde 0.3.0, así que las entregas antiguas de un proyecto son:

- las entregas creadas con AtipSpec 0.1.x;
- los fixes creados con `new --kind fix` antes de 0.3.0.

AtipSpec las lee tal como están, con la misma puerta para la evidencia, la
revisión y el resultado, hasta que se archivan. Nada las convierte por su
cuenta. Esta página describe lo que cambia; la [entrega
guiada](../flow/guided.md) es el flujo para todo lo nuevo.

## `spec.md` con los requisitos dentro

```markdown
---
title: "Password reset"
status: draft          # draft or ready; `atipspec accept` sets ready when it records the human's approval
kind: feature          # or fix: a fix created before 0.3.0, one regression criterion, no plan acceptance
capability: auth       # living spec that receives the requirements on deliver
impact: [notifications]  # other living specs or contract sections touched
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...        # commit the delivery started from; diff and rules use it
created: 2026-09-12T15:41:45Z   # the lead time counts from here
---

# Password reset

## Intent

Let a user who forgot the password recover access without support.

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

Acceptance criteria:
- AC-001: When a registered email requests a reset, the system sends a link to that email within 60 seconds.
- AC-002 [manual]: When the reset email is opened on a 375 px wide screen, a person sees the "Reset password" button without scrolling sideways.

### REQ-002 [remove]: Security questions
- AC-003: If a user opens "/account/questions", then the system responds with status 404.

## Quality attributes

### REQ-003: Reset requests under load

Acceptance criteria:
- AC-004: When 100 users request a reset within one minute, the p95 response time measured at the API gateway is below 300 ms.

## Assumptions
- The link is single-use.

## Out of scope
- Password policy changes.

## Open questions
- None
```

Se analizan: los encabezados `### REQ-nnn[ [remove]]: title` (niveles 2 a 4),
las líneas `- AC-nnn[ [test|manual]]: text` bajo un requisito, que pueden
continuar en líneas sangradas, los encabezados de escenario como en una spec
viva guiada, y los elementos de lista bajo `## Assumptions` y `## Open
questions` (`- None` cuenta como vacío). `deliver` fusiona los requisitos en
`specs/<capability>.md` por ID y elimina los marcados con `[remove]`.
Consulta [escribir criterios](spec-quality.md) para las comprobaciones; son
las mismas.

## Aprobaciones

| | Entrega antigua | Entrega guiada |
| --- | --- | --- |
| Para empezar `spec` o `fix` | la aceptación del contrato, registrada para su contenido actual | nada; `check` avisa mientras el contrato no esté aceptado |
| Antes de `plan` | `accept <slug> spec --code <code>` | los escenarios completos, sin preguntas abiertas |
| Antes de `build` | con `approve_plan: true` (el valor por defecto), `accept <slug> plan --code <code>`; un fix creado antes de 0.3.0 no tiene aceptación del plan | `accept <slug> proposal --code <code>` |
| El resultado | `accept <slug> result --code <code>` | lo mismo |

`atipspec proposal <slug>` en una entrega antigua presenta la aprobación que
sigue pendiente, con su código y el comando `accept` que la registra, o dice
que no hay ninguna: la spec hasta que se acepta, y después el plan cuando
`approve_plan` lo pide. Una funcionalidad cuya spec y cuyo plan están listos
se presenta como una sola propuesta, y `accept <slug> proposal` con ese
código registra la spec y el plan juntos; un fix solo presenta su
spec. Un código registra solo la fase con la que la vista lo mostró, así que
ejecuta el comando que imprime la vista. La aprobación de la spec hashea
`spec.md` y `contract.md`; la aprobación del plan añade `plan.md` entero, así
que cualquier edición del plan, una tarea nueva incluida, la vuelve a pedir.
`review_rounds` se reinicia con cada nueva aprobación de la spec; ninguna
aprobación cubre `config.yaml`. `accept <slug> spec` y `accept <slug> plan`
se rechazan en las entregas guiadas.

## Finalización de tareas

Una tarea está completa cuando `atipspec task-done <slug> Tn --note "..."` la
registra, o cuando un commit de la branch desde la base lleva el marcador
`[<slug>:Tn]` (varios ids pueden compartir uno, `[password-reset:T1,T2]`).
Las entregas guiadas ignoran los marcadores de commit. Un plan antiguo no
tiene `## Final verification` salvo que alguien la añada: `verify` ejecuta
los comandos de Verify de cada tarea, y todo `require-command` del contrato
debe aparecer en uno de ellos.

## IDs

Los requisitos y criterios antiguos se numeran por capacidad, `REQ-001`,
`AC-001`, por encima del número más alto de la spec viva, las entregas
abiertas y el archivo. `atipspec ids <capability> --legacy` imprime el
siguiente par. Dos personas que numeran a la vez pueden colisionar; el
`atipspec ids <capability>` del flujo guiado elige un prefijo que no usa
ningún ID visible. Los IDs numerados siguen siendo válidos en todos los
flujos y nunca se renumeran.

## Varios repositorios

Con `system:` en `config.yaml`, una entrega antigua lee el contrato y el
glosario del repositorio system desde el checkout tal como está; una guiada
los lee desde el commit que fijó `new` (consulta [varios
repositorios](../teams.md#varios-repositorios)).

## Convertir una funcionalidad antigua

`atipspec migrate <slug>` muestra, como un diff, cómo una funcionalidad
antigua se convierte en una entrega guiada, y no escribe nada: sus requisitos
pasan a `specs/<capability>.md`, `spec.md` lista sus IDs bajo `requirements`
y recibe `schema: 2`, `status: draft`, `risk: normal` y un `baseline.json`
nuevo. `atipspec migrate <slug> --apply` lo escribe después de hacer una
copia de seguridad de los originales y de los registros de aprobación en
`.atipspec/migrations/<digest>/`. No aprueba nada: la entrega vuelve a
borrador y su propuesta se presenta para su aprobación. El plan existente se
conserva; pasa las comprobaciones compartidas a un `## Final verification`
cuando lo revises. Un fix antiguo mantiene su flujo hasta que se
entrega, y `migrate` lo rechaza.
