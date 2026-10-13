# Entrega guiada, de principio a fin

Esta página sigue un cambio desde la petición hasta el archivo: quién hace
qué, qué comando ejecuta el asistente, qué comprueba el CLI y qué ficheros
escribe cada paso. Los [primeros pasos](../getting-started/quick-start.md)
son la versión corta, desde tu lado de la conversación.

## Qué es una entrega guiada

`atipspec new` crea una entrega guiada (`schema: 2` en su `spec.md`), para
una funcionalidad y, con `--kind fix`, para un [fix](fix.md). Sus requisitos
viven en la spec viva de la capacidad, `.atipspec/specs/<capability>.md`; el
`spec.md` de la entrega contiene para qué es el cambio y lo que decide en
torno a ellos:

- la intención, lo que queda fuera de alcance, las suposiciones y las
  preguntas abiertas;
- `requirements`, los IDs de los requisitos que este cambio añade, cambia o
  elimina en la spec viva;
- `owner`, `ticket`, `initiative` y `depends_on`;
- `base`, el commit desde el que partió `new`; `change_id`; `created`, donde
  empieza el lead time; y `risk`, cuánto exige la puerta.

`new` no empieza mientras la spec viva de la capacidad tenga cambios sin
commitear, así que el commit base la tiene tal como el cambio parte de ella:
la propuesta muestra el cambio como un diff contra él, y `check` distingue las
ediciones de esta entrega de lo que trajo la branch de integración.
`baseline.json` registra ese commit; una entrega creada antes de 0.3.0 se
sigue comparando con la spec viva que guardó ahí.
Las entregas creadas antes de 0.2.0, y los fixes creados antes de 0.3.0,
conservan sus requisitos dentro de `spec.md`; consulta [entregas
antiguas](../reference/legacy.md).

## Tres decisiones humanas

| Decisión | Cuándo | Se presenta con | Se registra con |
| --- | --- | --- | --- |
| El contrato y las decisiones que incluye | una vez por proyecto, y cuando cambia el contrato | `atipspec proposal contract` | `atipspec accept contract --code <code>` |
| La propuesta: escenarios, enfoque, pruebas y riesgo | **punto de parada 1**, antes de cualquier código | `atipspec proposal <slug>` | `atipspec accept <slug> proposal --code <code>` |
| El resultado revisado | **punto de parada 2**, antes del archivado | `atipspec report <slug>` | `atipspec accept <slug> result --code <code>` |

Nada más pide una aprobación registrada; una decisión sobre una capacidad que
surja se aprueba en la conversación, y la siguiente propuesta la lista.
Decides en la conversación: el asistente
presenta la vista, con su código de aprobación, y ofrece **Aprobar y
continuar**, **Pedir cambios** o **Cancelar** con el selector del cliente, o
te pide una respuesta escrita. Tras tu aprobación explícita, ejecuta el
comando `accept` con el código del contenido que te mostró; si ese contenido
cambió entretanto, el comando se niega y el asistente lo vuelve a presentar.
Claude Code, configurado por `init` y abierto en la raíz del proyecto, te
pregunta antes de que ese comando se ejecute: el aviso confirma la misma aprobación, no es una segunda. El
registro indica su canal, `terminal`, `client-permission` o `assistant`
(consulta [accept](../reference/cli.md#atipspec-accept)). El contrato no es
necesario para empezar una entrega guiada: mientras no esté aceptado,
`check` muestra un warning.

## Paso a paso

| Paso | Tú | El asistente ejecuta | Escribe |
| --- | --- | --- | --- |
| 1. Contrato | lo apruebas, una vez | `contract`, `audit`, `proposal contract`, `accept contract` | `contract.md`, `decisions/`, `approvals/contract.json` |
| 2. Crear | pides el cambio | `new` | `deliveries/<slug>/`: `spec.md`, `plan.md`, `deferred.md`, `baseline.json` |
| 3. Especificar | respondes las preguntas | `spec`, `ids`, `check` y, opcionalmente, `spec-bind` | `specs/<capability>.md`, `spec.md` |
| 4. Planificar | | `plan`, `check` | `plan.md` |
| 5. Propuesta | la apruebas: **punto de parada 1** | `proposal`, `accept <slug> proposal` | `approvals/local-proposal.json`, `status: ready` |
| 6. Construir | | `build`, `task-done` | código y tests, `progress.json` |
| 7. Verificar | | `verify` | `evidence/` |
| 8. Revisar | | `review`; un revisor en una sesión aislada | `review-rounds.json`, `review.md` |
| 9. Resultado | lo aceptas: **punto de parada 2** | `check`, `report`, `accept <slug> result` | `approvals/local-result.json` |
| 10. Entregar | decides el commit y la fusión | `deliver`, `merge-check` | la spec viva, `reports/acceptance.json`, `archive/<slug>/` |

### 1. El contrato

Una vez por proyecto, la [fase contract](contract.md) escribe
`.atipspec/contract.md` con las reglas que comprueba el CLI, y una decisión
por cada elección que ya tomaste. El asistente ejecuta `atipspec audit`,
presenta `atipspec proposal contract` y, tras tu aprobación, registra
`atipspec accept contract --code <code>`, que pone el contrato y las
decisiones que lista en `accepted` y escribe
`.atipspec/approvals/contract.json`.

### 2. Crear la entrega

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

`new` escribe `spec.md` con `status: draft`, `base` (el id completo del
commit actual), `requirements: []` y `risk: normal`; un `plan.md` por
rellenar; un `deferred.md` vacío; y `baseline.json`. `--branch` crea la
branch `delivery/password-reset` y cambia a ella, `--worktree` lo hace en una
carpeta hermana; trabaja con una branch por entrega (consulta
[equipos](../teams.md)). `--ticket` enlaza un ticket; `--depends-on` nombra
una entrega cuyo recibo aceptado debe estar en el archivo antes de que el
check de esta se ponga en verde.

### 3. Especificar

`/atipspec-spec password-reset: <what you want>` ejecuta
`atipspec spec password-reset`, que imprime el workflow, las reglas y el
contexto. El asistente lee el código y las specs vivas, pregunta solo lo que
queda abierto, en rondas de como máximo tres preguntas, y escribe los
requisitos y sus escenarios en la spec viva. Toma un prefijo de ID una vez
por entrega:

```bash
atipspec ids auth
```

```text
auth/REQ-AUTH-7KQ2M-001 auth/AC-AUTH-7KQ2M-001
Number further requirements and criteria of this delivery with the same prefix: -002, -003.
```

```markdown
### REQ-AUTH-7KQ2M-001: The user can request a reset link

Why: support tickets for forgotten passwords are 40% of the queue.

#### AC-AUTH-7KQ2M-001: Registered email
- **GIVEN** a registered user with the email "ana@example.com"
- **WHEN** the user requests a reset for "ana@example.com"
- **THEN** the system answers "Check your email" and sends one reset link to "ana@example.com"

#### AC-AUTH-7KQ2M-002 [manual]: The email reads well on a phone
- **WHEN** the reset email is opened on a 375 px wide screen
- **THEN** the "Reset password" button is visible without scrolling sideways
```

Un escenario necesita WHEN y THEN, en el orden GIVEN, WHEN, THEN; AND y BUT
extienden el paso anterior. `[manual]` marca uno que observa una persona;
`[invariant]`, uno que se cumple sin un disparador.
`### REQ-... [remove]: Title` retira un requisito en el deliver. El `spec.md`
de la entrega lista los IDs bajo `requirements` y rellena `## Intent`,
`## Out of scope` y `## Quality attributes` (`- None` cuando no aplica
nada). Un documento redactado aparte, o una lista de criterios de
aceptación, entra con `atipspec spec-bind password-reset --file <path>`, que
escribe la spec viva y los IDs y no aprueba nada.

`atipspec check password-reset` lista lo que falta y lo que señala el lint;
un resultado vago, como «funciona correctamente», bloquea la propuesta.
Consulta [spec](spec.md) y [escribir criterios](../reference/spec-quality.md).

### 4. Planificar

El plan puede empezar antes de la aprobación: `atipspec plan password-reset`
se abre en cuanto los escenarios están completos, la intención está
declarada y no queda ninguna pregunta abierta. El asistente escribe
`plan.md`:

```markdown
---
scope: ["src/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

A `request_reset(email)` function in `src/auth/reset.py` that answers the same
message for every email and sends the link only to registered ones.

## Tasks

### T1: Request a reset link

Covers: REQ-AUTH-7KQ2M-001
Tests: AC-AUTH-7KQ2M-001
Manual: AC-AUTH-7KQ2M-002

## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
Verify:
- `python -m pytest -q --junitxml .atipspec/tmp/junit.xml`
```

Cada requisito listado está cubierto por una tarea, cada criterio está bajo
`Tests:` o `Manual:`, y cada `require-command` del contrato se ejecuta en la
verificación final. Consulta [plan](plan.md).

### 5. La propuesta: punto de parada 1

```bash
atipspec proposal password-reset
```

La vista muestra el tipo y el riesgo con lo que exige el nivel, con qué
rigor se comprueban los criterios, qué necesitan la evidencia y la revisión,
la intención del cambio, los requisitos con sus escenarios, el plan y el diff
de la spec viva contra el commit base, con el código de aprobación. Cuando
algo bloquea, lo lista bajo "Not ready for approval" y no muestra ningún
código. Tras tu aprobación, el asistente registra:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

Pone `status: ready` y escribe `approvals/local-proposal.json` con el hash de
lo que aprobaste: `spec.md` salvo su `status` y su `ticket`, cada requisito
que lista de la spec viva de la capacidad, `baseline.json`, el
alcance, el enfoque y la verificación final del plan, `contract.md`,
`config.yaml` salvo su `exempt_paths`, `adapter.json`, los responsables de
la capacidad y `integration` de `teams.json`, y `contracts.json`. Editar
cualquiera de ellos devuelve la entrega a `draft`, y `check` nombra lo que
cambió. Las tareas
añadidas o divididas dentro del plan no, porque la verificación final las
cubre; tampoco otra entrega integrada desde main (consulta [cuando main
avanza](../teams.md#cuando-main-avanza)).

### 6. Construir

`atipspec build password-reset` se niega hasta que la propuesta está
aceptada para su contenido actual, y luego imprime el workflow y la
siguiente tarea. El asistente implementa cada tarea con sus tests, dentro del
`scope` del plan, y la registra:

```bash
atipspec task-done password-reset T1 --note "request_reset answers the same message and sends only to registered emails"
```

`task-done` escribe `progress.json`: una declaración de avance atada al
acuerdo aprobado, no una prueba. Se niega antes de la aprobación. Los commits
siguen la política de tu repositorio; no se exige ninguno. Consulta
[build](build.md).

### 7. Verificar

```bash
atipspec verify password-reset
```

ejecuta una vez los comandos de `## Final verification` sobre el candidato
terminado y escribe `evidence/FINAL-<time>.json` con los comandos, los
códigos de salida, los logs de salida y la huella del árbol de trabajo. Con
un `Report:`, primero borra ese fichero y exige que los comandos lo vuelvan a
escribir, y `check` exige que cada test nombrado en `Proof:` se haya
ejecutado y haya pasado. Cualquier cambio posterior en el árbol deja la
evidencia obsoleta. `--task T1` ejecuta los comandos Verify propios de una
tarea, una comprobación de desarrollo.

### 8. Revisar

```bash
atipspec review password-reset
```

se niega mientras una tarea no esté registrada, la evidencia esté obsoleta o
el contrato esté violado. Si no, cuenta la revisión, escribe el paquete en
`.atipspec/tmp/password-reset-review-packet.md` e imprime `review N of M`. Un
revisor en una sesión aislada, un
subagente o una sesión nueva a la que solo se le da el paquete, escribe
`review.md`: `tree`, `reviewer`, `session`, un PASS o FAIL por criterio con
un puntero que la puerta resuelve, y los hallazgos. Las correcciones vuelven
a pasar por verify y review; `review_rounds` limita cuántas veces. Consulta
[review](review.md).

### 9. El resultado: punto de parada 2

`atipspec check password-reset` pasa a `checked` cuando todo está en verde.
El asistente presenta:

```bash
atipspec report password-reset
```

el dosier: cada criterio con su evidencia y su veredicto, el revisor y la
sesión, las aprobaciones, cada fichero cambiado desde el commit base con el
diff, y el código de aprobación del resultado. Tras tu aceptación:

```bash
atipspec accept password-reset result --code 3C1Q-4VN7
```

escribe `approvals/local-result.json`, atado al árbol, a la revisión, a los
hallazgos aplazados y a la evidencia. La entrega está `accepted`; el lead
time se detiene.

### 10. Entregar

```bash
atipspec deliver password-reset
```

fusiona los requisitos en `specs/auth.md` por ID, escribe el recibo
`reports/acceptance.json` (con `code_tree`, el hash de todo lo que está fuera
de `.atipspec/`), pone `status: delivered` y mueve la carpeta a
`.atipspec/archive/password-reset/`. No hace commit, push ni fusión. Antes de
la fusión, `atipspec merge-check --base <target>` confirma que cada entrega
que toca la branch está aceptada y que su código sigue siendo el código
aceptado. Consulta [deliver](deliver.md).

## Valores de estado

`status` y `check` derivan en qué punto está una entrega a partir de sus
ficheros y de git:

`draft` → `planned` → `in_progress` → `implemented` → `checked` → `accepted` → `delivered`

| Estado | Significado |
| --- | --- |
| `draft` | la propuesta no está aceptada para su contenido actual |
| `ready` | aceptada, pero el plan no tiene ninguna tarea: en una entrega guiada, solo cuando sus tareas se quitaron después de la aprobación |
| `planned` | propuesta aceptada, ninguna tarea registrada |
| `in_progress` | algunas tareas registradas con `task-done` |
| `implemented` | todas las tareas registradas, la puerta aún no está en verde |
| `checked` | la puerta local está en verde; el resultado no está aceptado |
| `accepted` | la aceptación del resultado actual está registrada; `deliver` puede ejecutarse |
| `delivered` | fusionada en la spec viva y archivada |

Bajo una policy de confianza externa, `verified` sustituye a `checked` y a
`accepted`.

## El modo ship y el runner

`/atipspec-ship <slug>` mantiene una sola conversación: `atipspec ship <slug>`
nombra la siguiente fase a la que la entrega puede entrar, y el asistente
entra en ella, deteniéndose en los dos puntos de parada, ante un cambio
material y ante un bloqueo. `atipspec run <slug>` ejecuta una entrega
aprobada mediante un adaptador de procesos configurado, con checkpoints y
presupuestos; nunca acepta nada. Consulta el [adaptador de
ejecución](../reference/execution-adapter.md).

## Con una policy de confianza externa

Una organización que necesita aprobaciones autenticadas añade una policy de
confianza externa. La puerta ignora entonces los registros locales y exige
aprobaciones firmadas de producto, ingeniería y QA y evidencia de CI
atestada; el éxito es `verified`, y `deliver` lo exige. Con
`trust: required` en `config.yaml`, la aceptación local queda desactivada.
Consulta [aceptación empresarial](../enterprise.md).

## Qué se registra y dónde

| Fichero | Lo escribe | Contiene |
| --- | --- | --- |
| `deliveries/<slug>/spec.md` | `new`, el asistente; `status`, `accept` | la intención y las decisiones del cambio, los IDs que lista |
| `specs/<capability>.md` | el asistente, `spec-bind`; `deliver` al archivar | los requisitos y sus escenarios |
| `deliveries/<slug>/baseline.json` | `new` | la spec viva cuando empezó la entrega |
| `deliveries/<slug>/plan.md` | el asistente | alcance, enfoque, tareas, verificación final |
| `deliveries/<slug>/approvals/local-*.json` | `accept` | lo que aprobaste, su código, cuándo y el canal |
| `deliveries/<slug>/progress.json` | `task-done` | las tareas registradas como implementadas |
| `deliveries/<slug>/evidence/` | `verify` | comandos, códigos de salida, logs, informes de tests |
| `deliveries/<slug>/review-rounds.json` | `review`, `run` | las revisiones contadas |
| `deliveries/<slug>/review.md` | el revisor | veredictos y hallazgos |
| `deliveries/<slug>/run.json` | `run` | el checkpoint del runner |
| `archive/<slug>/reports/acceptance.json` | `deliver` | el recibo que lee `merge-check` |

Nadie escribe a mano los registros de `approvals/`, `evidence/` o
`archive/`, ni `review-rounds.json`; las reglas de permisos de Claude Code
impiden que sus herramientas de edición toquen esos ficheros. Consulta
[artefactos](../reference/artifacts.md).

## Entregas antiguas

Las entregas creadas antes de 0.2.0, y los fixes creados antes de 0.3.0,
conservan sus requisitos en `spec.md`, aprueban la spec (y el plan, con
`approve_plan`) en lugar de una propuesta, y también completan tareas con
marcadores en los commits. Consulta [entregas
antiguas](../reference/legacy.md).
