# Artefactos

Las especificaciones y los planes usan Markdown con un pequeño frontmatter
YAML. La evidencia, los registros de aprobación y los recibos de informe usan
JSON; las firmas son ficheros SSH separados. El CLI analiza unas pocas formas
de línea e ignora los comentarios HTML y el código en bloques, así que las
plantillas pueden llevar indicaciones que el modelo borra a medida que
escribe.

## Identificadores

| Tipo | Formato | Alcance |
| --- | --- | --- |
| Slug de entrega, capacidad, iniciativa, decisión | `[a-z0-9-]`, p. ej. `password-reset` | proyecto |
| Requisito | `REQ-PRICING-7KQ2M-001`, de `atipspec ids`; `REQ-001` en las entregas antiguas | capacidad, estable a través de las entregas |
| Criterio de aceptación | `AC-PRICING-7KQ2M-001`; `AC-001` en las entregas antiguas | capacidad, estable a través de las entregas |
| Tarea | `T1` | la entrega |
| Hallazgo | `F1` | la revisión |
| Decisión | `DEC-001` | proyecto, nunca se reutiliza |

Los equipos que trabajan en paralelo sobre una misma capacidad toman los IDs
de `atipspec ids <capability>`: la capacidad en mayúsculas, un token de cinco
caracteres en base32 de Crockford (sin I, L, O ni U) que no usa ningún ID
visible, y un número; cada entrega numera sus demás requisitos y criterios
con su token, `-002`, `-003`. Los IDs más largos de versiones anteriores, con
32 caracteres hexadecimales, y los IDs numerados de las [entregas
antiguas](legacy.md#ids) siguen siendo válidos y nunca se renumeran. Los IDs
importados se derivan del título de la misma forma.

## `spec.md`

El `spec.md` de una entrega guiada (`schema: 2`, lo que crea `atipspec new`)
contiene para qué es el cambio y qué decide. Sus requisitos viven en
`specs/<capability>.md`, y `requirements` lista sus IDs:

```markdown
---
title: "Password reset"
status: draft          # `atipspec accept <slug> proposal` sets ready when it records the human's approval
capability: auth
impact: []
owner: ana
ticket: SHOP-12        # a key, an issue number such as "#42" or an https URL; not part of the approval
initiative: null
base: 9f2c1e...        # the full id of the commit `new` recorded; check compares with it, so it never changes
created: 2026-09-12T15:41:45Z
schema: 2
change_id: 0c5e7a...
requirements: [REQ-001, REQ-002, REQ-004]
risk: normal
---

# Password reset

## Intent

A user who forgot the password requests a reset link by email and sets a new
password with it, without contacting support.

## Out of scope

- Password policy changes.

## Quality attributes

- REQ-004: p95 below 300 ms with 100 requests per minute

## Assumptions

- The link is single-use.

## Open questions

- None
```

| Sección | Qué pide `check` |
| --- | --- |
| `## Intent` | el actor, el desencadenante, el resultado observable y cómo sabrá el usuario que funcionó; vacía, o solo con `TBD`, `TODO` o `...`, es un todo que bloquea la propuesta hasta que esta se aprueba, y un warning después |
| `## Out of scope` | al menos un elemento, `- None` incluido; sin ninguno está sin decidir, un todo hasta que se aprueba la propuesta |
| `## Quality attributes` | una línea `- REQ-...: limit` por cada requisito de este cambio que enuncia un límite, o `- None`; una línea que no nombra ninguno es un todo hasta que se aprueba la propuesta y un error después. Los criterios del requisito necesitan un criterio de ajuste (consulta [escribir criterios](spec-quality.md#atributos-de-calidad-y-criterios-de-ajuste)) |
| `## Assumptions` | cada elemento es un valor por defecto que la persona confirma al aprobar |
| `## Open questions` | cualquier elemento bloquea la propuesta |

`risk` es `low`, `normal` o `high`: lo que la puerta pide al plan, a la
evidencia y a la revisión (consulta [riesgo](../flow/spec.md#riesgo)). Forma
parte de lo que hashea la aprobación de la propuesta. Un `risk` ausente cuenta
como `normal`; cualquier otro valor es un error.

Un fix guiado (`kind: fix`, lo que crea `new --kind fix`) tiene el mismo
frontmatter. Su `requirements` nombra los requisitos aceptados de la
capacidad que corrige, y su cuerpo enuncia el defecto en vez de la intención:

```markdown
## Defect

Observed: a link created 26 hours ago still opens the reset form.

Expected: the page shows "link expired", as REQ-002 states.

Reproduction: `python -m pytest tests/auth/test_reset.py -k expired`

## Assumptions

- None

## Open questions

- None
```

`Observed:` y `Expected:` son obligatorios (un todo hasta que se aprueba la
propuesta, un warning después); `Reproduction:` se recomienda. Las etiquetas
también se leen en español (`Observado`, `Esperado`, `Reproducción`) y en
portugués (`Observado`, `Esperado`, `Reprodução`), y el encabezado como
`Defecto` o `Defeito`. Un fix no tiene `## Intent`, `## Out of scope` ni
`## Quality attributes`. Consulta [fix](../flow/fix.md#que-exige-check-de-un-fix)
para lo que `check` pide a sus requisitos y a su plan.

Aprobada significa que el registro de aprobación local coincide con el
contenido actual; la línea de `status` no cuenta. Bajo una policy de
confianza, cuyas firmas son la aprobación, `check` cuenta en su lugar el
`status` que ponen las personas, mientras que `proposal` y `accept proposal`
siguen contando solo el registro local. Una entrega creada con estas
secciones, que `baseline.json` lista bajo `sections`, las conserva: borrar
una es un todo, igual que una sin decidir. Una entrega creada antes de 0.3.0
sin `## Out of scope` o `## Quality attributes` recibe un warning. En una
entrega aprobada, estos warnings esperan al siguiente cambio de su propuesta:
editar `spec.md` solo por ellos anula la aprobación. Los nombres de sección
también se leen en español (`Intención`, `Fuera de alcance`, `Atributos de
calidad`) y en portugués (`Intenção`, `Fora do escopo`, `Atributos de
qualidade`).

El `spec.md` de una [entrega antigua](legacy.md) contiene él mismo sus
requisitos, en el formato que muestra esa página.

## `plan.md`

```markdown
---
scope: ["shop/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

## Tasks

### T1: Task title
Covers: REQ-AUTH-7KQ2M-001, REQ-AUTH-7KQ2M-002
Tests: AC-AUTH-7KQ2M-001, AC-AUTH-7KQ2M-002

### T2: Observed only
Covers: REQ-AUTH-7KQ2M-003
Manual: AC-AUTH-7KQ2M-004
Verify: none

## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
Verify:
- `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
- `ruff check .`
```

Se analizan: `### Tn: title`; una línea `Covers:` con ids de REQ; las líneas
`Tests:` y `Manual:` con los criterios que la tarea demuestra con un test o
con la observación de una persona, según la marca `[manual]` de cada
criterio; y una sección opcional `## Final verification` (también
`Verificación final` o `Verificação final`) con su lista `Verify:`, que
`verify` ejecuta una vez para el candidato terminado. Una tarea puede llevar
su propio `Verify:`, una comprobación de desarrollo, o `Verify: none` cuando
solo una observación la demuestra. `Verify:` va seguido de elementos de lista
(las comillas invertidas son opcionales) o de la palabra `none`. Una línea
opcional `Report:` nombra el XML de JUnit que escriben los comandos, en una
ruta relativa dentro del proyecto que git ignora (`check` informa de
cualquier otra ruta como error, y de una ruta que Windows lee como absoluta o
fuera del proyecto, como `/x`, `C:\x` o `..\x`, en todas las plataformas), y
una línea opcional `Proof:` seguida de elementos `- AC-...: test id` que
`check` verifica contra la evidencia (consulta [build](../flow/build.md));
con `require_proof: true` o `risk: high`, todo criterio bajo `Tests:`
necesita uno, y su verificación, un `Report:`. En un plan con verificación
final, `Report:` y `Proof:` van en esa sección. `scope` en el frontmatter
lista globs de los ficheros que las tareas pueden cambiar, con la [sintaxis
de glob de las reglas del contrato](contract-rules.md#globs). Con
`strict_scope: true`, el valor por defecto, un `scope` vacío o ausente, o uno
cuyos globs juntos coinciden con todas las rutas, es un error; los ficheros
tocados fuera de él, eliminaciones incluidas, también son errores (warnings con
`strict_scope: false`, donde un `scope` vacío no declara nada), y el paquete
de revisión los lista. Los ficheros bajo `.atipspec/` nunca cuentan, ni
tampoco los skills de cliente y las reglas de permisos que instala AtipSpec
mientras solo contengan su contenido; eliminar una de esas reglas sí cuenta.

La aprobación de una propuesta guiada ata el frontmatter del plan, su enfoque
y su verificación final, no su sección `## Tasks`: las tareas que se dividen
o se añaden bajo ellos no necesitan una nueva aprobación. Un plan sin
verificación final se ata entero.

## `review.md`

Lo escribe solo el revisor.

```markdown
---
tree: <fingerprint from the packet>
reviewer: <client or model>
session: isolated        # or shared; a review without it counts as shared
---

## Criteria
- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. src/auth/reset.py:42-48
- AC-003: FAIL. precise gap

## Findings
- F1 [blocker]: text
- F2 [major]: text
- F3 [minor]: text

## Notes
```

Todo criterio necesita exactamente un veredicto. Un `PASS` necesita un
puntero que `check` resuelva: un test que pasó en el informe JUnit de la
evidencia actual, un `path:line` o `path:line-line` que existe en un fichero
del candidato, fuera de `.atipspec/` y no ignorado por git (los logs de
evidencia de la entrega cuentan, como `evidence/logs/<file>.log:<line>`), o un
`path::test` cuyo fichero contiene ese nombre como palabra; para un criterio
`[manual]`, también vale una descripción de tres palabras o más. Un `FAIL`
necesita su razón. `reviewer:` es obligatorio. `session:` es `isolated` o
`shared`: una revisión compartida es un warning, y un error con `risk: high` o
`require_isolated_review`. Con `risk: low`, un criterio cuyo test nombrado en
`Proof:` pasó en la evidencia actual puede no tener veredicto. Los hallazgos
blocker y major bloquean; aplazar cualquiera de los dos necesita una
aprobación de riesgo de confianza con caducidad. Los hallazgos minor
informan. Consulta [review](../flow/review.md#que-comprueba-la-puerta-en-reviewmd).

## `deferred.md`

```markdown
- F2: reason, and where it will be handled
```

Solo se pueden aplazar hallazgos. Una entrada `AC-` o `REQ-` es un error.

## `brief.md`

La salida de la fase explore: Problem, Today, Options, Recommendation,
Questions for the user. No se analiza; se incluye en el contexto.

## `evidence/<task>-<timestamp>.json`

Lo genera `atipspec verify`, un fichero por ejecución: `FINAL-...` para la
verificación final, `T1-...` para los comandos propios de una tarea. Versión
del esquema, entrega, tarea, resultado, árbol antes y después (huellas que
dejan fuera los títulos de las tareas, así que la evidencia de una tarea
renombrada sigue vigente), head, marcas de tiempo, entorno y comandos
exactos con sus códigos de salida, duración, final de la salida, ruta del log
completo y hash del log; con un `Report:`, el XML de JUnit copiado con su
hash, la ruta desde la que se leyó y `fresh: true` (los comandos lo
escribieron después de que `verify` lo borrara), y cada caso de test con su
estado. Cuenta el fichero más reciente de cada tarea. La evidencia con
informe pero sin la marca `fresh`, escrita por 0.2.x, es un todo hasta que
`verify` vuelva a ejecutarse. La atestación de CI de confianza añade el
firmante, el repositorio, el digest de la policy, la URL de la ejecución y
una firma `.json.sig` separada. Los ficheros sin firmar son solo evidencia
local. En modo provider el fichero no cambia: una atestación de artefacto de
GitHub del workflow de evidencia de confianza cubre su hash, y su `head` debe
ser el commit que obtuvo el worker protegido. Las rutas de logs e informes se
escriben con `/` en todas las plataformas.

## `review-rounds.json`

Lo escriben `atipspec accept <slug> proposal`, que lo crea, y `atipspec
review` y `atipspec run`: el acuerdo aprobado para el
que cuenta, cuántas revisiones se contaron (paquetes para otro candidato,
contando el primero) y el árbol del último paquete. `check` solo toma la
revisión de ese paquete. Queda fuera de
la huella, y las reglas de permisos de Claude Code prohíben editarlo con las
herramientas de edición del cliente; no impiden que un comando de shell lo
borre. En una entrega guiada creada desde 0.3.0 un fichero que falta se
borró, así que `review` se niega y `check` falla hasta que decida la persona;
en una aprobada bajo una policy de confianza, `atipspec review` vuelve a
contar a partir del `review.md` de la carpeta, como primera revisión, y en una
creada antes de 0.3.0, cuyo `review.md` nombra un árbol de la huella
anterior, a partir del paquete siguiente. Consulta [rondas de revisión](../flow/review.md#rondas-de-revision).

## `specs/<capability>.md`

La spec viva de una capacidad: la verdad actual sobre su comportamiento, una
sección por requisito con sus escenarios.

```markdown
# auth

## Requirements

### REQ-AUTH-7KQ2M-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

#### AC-AUTH-7KQ2M-001: Registered email
- **GIVEN** a registered user with the email "ana@example.com"
- **WHEN** the user requests a reset for "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

#### AC-AUTH-7KQ2M-002 [manual]: The email reads well on a phone
- **WHEN** the reset email is opened on a 375 px wide screen
- **THEN** the "Reset password" button is visible without scrolling sideways

### REQ-AUTH-7KQ2M-004 [remove]: Security questions

#### AC-AUTH-7KQ2M-009: Questions page removed
- **WHEN** a user opens "/account/questions"
- **THEN** the system responds with status 404
```

Se analizan: los encabezados `### REQ-...[ [remove]]: title` (niveles 2 a 4);
bajo cada uno, los encabezados de escenario
`#### AC-...[ [manual|invariant]]: title` con un paso por línea, `GIVEN`,
`WHEN`, `THEN`, `AND`, `BUT` (o `INVARIANT` en un invariante, y las palabras
de paso en español y en portugués), en negrita o no; y los enunciados de criterio `- AC-...: text`,
la forma antigua. Las líneas `Why:` y los ejemplos son para las personas y
el revisor. `deliver` actualiza el fichero por ID estable, conservando la
identidad al renombrar, y elimina un requisito marcado con `[remove]`. Todo
requisito y criterio de aceptación vivo tiene un ID desde el principio. El
`requirements` de una entrega guiada lista los que escribe; consulta
[escribir criterios](spec-quality.md) para lo que `check` espera de ellos.

## `baseline.json`, `progress.json` y `run.json`

`baseline.json`, escrito por `new`: la spec viva de la capacidad cuando
empezó la entrega (`content`), el commit (`head`) y las secciones decididas
del nuevo `spec.md` (`sections`). El `base` de la entrega tiene que ser ese
commit, y el diff de la propuesta y la comparación de `specs/` leen la spec
viva tal como la tiene ese commit; solo una entrega creada antes de 0.3.0, sin
`sections`, compara con `content`. La aprobación de la propuesta lo hashea.

`progress.json`, escrito por `task-done`: para cada tarea, la nota, la hora,
el hash del acuerdo aprobado con su `subject_version` y el hash de la tarea
sin su título. Una tarea cuenta como completa mientras coincidan ambos.

`run.json`, escrito por `atipspec run`: el checkpoint del runner, con su
estado, fase, tiempo transcurrido, rondas de corrección y el acuerdo para el
que se ejecuta. `progress.json` y `run.json` quedan fuera de la huella del
árbol.

## `contracts.json` y `sources/`

El `contracts.json` de una entrega guiada (`schema: 1`) lista los contratos
que fijó desde otros repositorios, con `contract-pin` o, para el repositorio
system, en `new`: cada uno con `name`, `repository`, `revision` (un id de
commit completo), `path` y el `sha256` de su contenido. La aprobación de la
propuesta lo hashea.

`sources/<sha256>.md` guarda cada documento que importó `spec-bind`, tal como
era; `sources` en `spec.md` los lista y `## Import review notes` dice qué hay
que comprobar antes de aprobar.

## `decisions/DEC-nnn-<slug>.md`

```markdown
---
id: DEC-003
title: "Use httpx for outbound HTTP"
status: accepted        # proposed, accepted, superseded, rejected; set by `accept contract` when it affects the contract
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
de la entrega, una entrada de impact, `contract` o `*`, o está vacío (todo).
Una decisión cuyo `affects` nombra `contract`, `contract:<section>` o `*`, o
está vacío, se acepta con el contrato:
`atipspec accept contract --code <code>` fija su status. Una decisión así solo cuenta con el contenido que
nombra la aceptación registrada del contrato, así que una marcada como
`accepted` a mano no forma parte del contrato ni la carga `context`. Sin un
registro, `context` las carga por su status solo cuando el propio contrato se
aceptó antes de 0.3.0.

## `initiatives/<slug>/roadmap.md`

```markdown
## Deliveries
- orders-api: Orders API
- orders-screen: Orders screen

## Interfaces
```

Se analizan las líneas `- <slug>: title` bajo `## Deliveries`. El status de
cada entrega se deriva: pending, su status actual o delivered.

## Status derivado de una entrega

| Status | Significado |
| --- | --- |
| `draft` | la propuesta (en una entrega antigua, la spec) no está aceptada para su contenido actual |
| `ready` | aceptada, pero el plan no tiene ninguna tarea |
| `planned` | plan con tareas, ninguna registrada; un plan antiguo con `approve_plan` necesita además su aceptación |
| `in_progress` | algunas tareas registradas con `task-done` (o, en una entrega antigua, con un marcador de commit) |
| `implemented` | todas las tareas registradas, la puerta no está en verde |
| `checked` | comprobaciones locales en verde; el resultado no está aceptado |
| `accepted` | comprobaciones locales en verde y la aceptación del resultado actual registrada; se puede ejecutar `deliver` |
| `verified` | puerta de confianza en verde con policy aprobada, evidencia de CI firmada y aprobaciones humanas |
| `delivered` | fusionada en la spec viva y archivada |

## Aprobaciones y recibos

`approvals/local-<phase>.json` lo escribe `atipspec accept`:
`local-proposal.json` y `local-result.json` en las entregas guiadas, más
`local-spec.json` y `local-plan.json` en las antiguas, incluidos los
fixes creados antes de 0.3.0. Campos (schema 2):

| Campo | Significado |
| --- | --- |
| `kind`, `delivery`, `phase` | `local-acceptance`, el slug y la fase |
| `subject` | sha256 del contenido aceptado; `check` lo compara en cada ejecución |
| `subject_version` | cómo se hasheó el subject: 2 desde 0.3.0; un registro sin él es de la versión 1 |
| `code` | el código de aprobación que se presentó y se pasó con `--code` |
| `files` | el digest de cada parte del subject, para que la deriva nombre el fichero, o el requisito, que cambió |
| `accepted_at`, `by`, `head` | cuándo, la etiqueta declarada de `--by` (la identidad de git por defecto), el commit |
| `channel`, `client` | `terminal`, `client-permission` o `assistant`, y el cliente que lo ejecutó |

La versión 2 hashea de la spec viva de la capacidad de una propuesta guiada
solo cada requisito que lista la entrega, como
`specs/<capability>.md#REQ-...`: `check` y `merge-check` bloquean un cambio
de cualquier otro, así que traer main no anula ninguna aprobación (consulta
[cuando main avanza](../teams.md#cuando-main-avanza)). De
`teams.json` hashea solo los owners de la capacidad e `integration`, también
bajo una policy de confianza, y de `spec.md`, todo salvo `status` y `ticket`.
La aceptación de un resultado también hashea, como `integrated`, la base del
merge con la branch de integración (la de la policy bajo una policy) cuando
la entrega devuelve lo que cambió esa branch: su dosier muestra esos ficheros
frente a ese commit, así que volver a integrar la branch después anula la
aceptación, aunque se conserve el árbol. La versión 1 hasheaba ambos ficheros enteros; `check` compara cada registro
con la versión con la que se escribió. Los registros escritos por 0.2.x
(schema 1, sin código, ficheros, canal ni `subject_version`) siguen siendo
válidos mientras su contenido no cambie; `status` los muestra como
`channel not recorded`. Son detección de deriva para la puerta local y se ignoran
bajo una policy. Los registros de `task-done` de `progress.json` y las
aprobaciones firmadas llevan `subject_version` de la misma forma.

`.atipspec/approvals/contract.json` lo escribe `atipspec accept contract`:
kind `contract-acceptance`, el hash del subject, el código, `content` (el
digest de `contract.md` y de cada decisión que afecta al contrato, sin sus
líneas de status), los IDs de las decisiones, quién, cuándo, el commit y el
canal. Una decisión añadida, editada, retirada o marcada como aceptada a mano
después deja la aceptación desactualizada hasta que el contrato se presenta
y se acepta de nuevo.

Los `approvals/*.json` firmados registran la fase, la identidad, el rol, la
marca de tiempo de la aprobación, el hash del subject, el repositorio, el
digest de la policy y una caducidad opcional. Cada uno tiene una firma SSH
`.json.sig`. Los registros del proveedor llevan además la identidad del PR/MR
y la URL de origen, y se revalidan contra el proveedor en el momento de la
aceptación y en `merge-check`. `reports/acceptance.json` es el recibo
archivado y el índice de artefactos: `accepted`, `acceptance_mode` (`local` o
`trusted`), las comprobaciones de la puerta, la matriz de trazabilidad, las
aprobaciones, los digests de los artefactos, `kind`, `risk`, `lead_time`
(`created`, `proposal_accepted_at`, `result_accepted_at`, `hours` y
`complete`: las horas de reloj desde la creación de la entrega hasta la
aceptación de su resultado; bajo una policy, hasta la última aceptación
firmada), `tree` (la huella de la entrega), `review` (revisor, sesión y
árbol), `changes` (el commit base, cada fichero cambiado con su status, sus
líneas y su object id, `outside_scope`, `diff_bytes` y `diff_sha256` del
diff, cuyo texto queda en el historial de git, e `integrated`, la ref de
integración y los ficheros que trajo, excluidos del resto), `ticket` y
`ticket_url`, `code_tree`, el hash de todo lo que había fuera de `.atipspec/`
cuando se entregó, `living_spec`, el digest de la spec viva que escribió
`deliver`, y `living_requirements`, el texto de cada requisito que lista la
entrega tal como `deliver` lo escribió ahí (`null` para uno que eliminó).
Cada fila de la matriz lleva `pointer`, aquello a lo que se resolvió su
veredicto PASS. Los recibos escritos antes de 0.3.0 no tienen `review`,
`changes`, `pointer`, `kind`, `risk` ni `lead_time`, y se siguen mostrando.
`merge-check` compara `code_tree` con el head de la branch y `living_spec`
con la spec viva que hay ahí, y exige que cada requisito listado tenga el
texto que registra `living_requirements`, tal como lo añadió el commit que
archivó la entrega, incluso cuando el texto que escribió `deliver` nunca llegó
entero a un commit; `check` también compara con esos textos la spec viva de
una entrega abierta, para los requisitos que lista el `spec.md` archivado. Los
recibos escritos antes de 0.3.0 no tienen `code_tree` y bloquean una branch
que los añade. Con una policy de confianza, `merge-check` no se fía de la
palabra del recibo para una aceptación de confianza: vuelve a comprobar la
entrega en el commit anterior al commit de archivo, con los ficheros
archivados con ella, y compara la spec viva, y cada requisito que lista la
entrega, con lo que `deliver` escribe a partir de ese commit. Del código,
`merge-check` toma como de la entrega los ficheros que lista `changes` y los
que nombra como `integrated`, tal como estaban al entregarse (con una policy,
los que muestra su dosier en ese commit). Consulta
[aceptación empresarial](../enterprise.md).
