# plan

**De los escenarios al enfoque, las tareas y las pruebas que la puerta puede
demostrar.** La fase donde se decide el cumplimiento de la arquitectura.

| | |
| --- | --- |
| Rol | El diseñador y el tester: quien tendrá que mantener esto dentro de un año. Prefiere la forma más simple dentro del contrato, reutiliza lo que existe, te cuenta las decisiones con consecuencias antes de tomarlas y elige las pruebas según el riesgo. |
| Quién decide | Tú, como parte de la propuesta: escenarios, enfoque y pruebas se aprueban juntos (**punto de parada 1**). Una [entrega antigua](../reference/legacy.md#aprobaciones) aprueba su plan aparte cuando `approve_plan: true`. |
| Produce | `plan.md`: alcance, enfoque, tareas y la verificación final |

## Cómo ejecutarla

```text
/atipspec-plan password-reset
```

El skill ejecuta `atipspec plan password-reset`. Una entrega guiada puede
planificarse antes de su aprobación, en cuanto sus escenarios están
completos sin un hallazgo bloqueante, su intención está declarada, sus
secciones de fuera de alcance y de calidad están decididas y no queda
ninguna pregunta abierta; el comando se niega con lo primero que falte y, si
no, imprime el workflow, las reglas y el contexto.

## Qué hace el modelo

1. Lee el contexto que imprimió el comando, y las áreas de código
   implicadas.
2. Comprueba el contrato. Si los escenarios necesitan algo que el contrato
   prohíbe, se detiene: eso necesita una
   [decisión](contract.md#cambiar-el-contrato), nunca un rodeo.
3. Escribe `plan.md`:

    ```markdown
    ---
    scope: ["shop/auth/**", "tests/auth/**"]
    ---

    # Plan: Password reset

    ## Approach

    A `reset` module under `shop/auth/` with `request()` and `consume()`,
    following the contract's structure (domain must not import infrastructure,
    DEC-002). Tokens stored in the existing `auth_token` table.

    ## Tasks

    ### T1: Request a reset link

    Covers: REQ-AUTH-7KQ2M-001
    Tests: AC-AUTH-7KQ2M-001, AC-AUTH-7KQ2M-002

    ### T2: Expire links after 30 minutes

    Covers: REQ-AUTH-7KQ2M-002
    Tests: AC-AUTH-7KQ2M-003

    ### T3: Reset requests under load

    Covers: REQ-AUTH-7KQ2M-003
    Tests: AC-AUTH-7KQ2M-004

    ## Final verification

    Report: .atipspec/tmp/junit.xml
    Proof:
    - AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
    - AC-AUTH-7KQ2M-002: tests/auth/test_reset.py::test_unknown_email_same_answer
    - AC-AUTH-7KQ2M-003: tests/auth/test_reset.py::test_link_expires_after_30_minutes
    - AC-AUTH-7KQ2M-004: tests/auth/test_load.py::test_p95_below_300_ms
    Verify:
    - `python -m pytest -q --junitxml .atipspec/tmp/junit.xml`
    ```

4. `atipspec check password-reset` hasta que no haya errores de plan.
5. Presenta el plan con los escenarios en `atipspec proposal password-reset`
   y pide tu aprobación en la conversación; el asistente la registra con
   `atipspec accept password-reset proposal --code <code>`, y
   `atipspec build` se niega hasta entonces. La aprobación ata el alcance, el
   enfoque y la verificación final del plan. Dividir o añadir una tarea
   dentro de ellos no necesita una nueva aprobación, porque la verificación
   final cubre todas las tareas, aunque `check` sigue comprobando la
   cobertura y el alcance; un alcance más amplio, otro enfoque o una
   verificación final cambiada se te presentan de nuevo.

## Qué exige `check` de un plan

- Todo requisito activo está cubierto por al menos una tarea (`Covers:`), y
  todo criterio está listado una vez bajo `Tests:` o `Manual:`, según su
  marca `[manual]` en la spec; hasta entonces `atipspec build` se niega.
- Todo `require-command` del contrato aparece en los comandos de
  `## Final verification` o, en un plan sin esa sección, en el `Verify:` de
  al menos una tarea.
- Los comandos son comandos reales del proyecto. `verify` los ejecuta desde
  la raíz del proyecto a través del shell: la verificación final, una vez
  para el candidato terminado; el `Verify:` propio de una tarea es una
  comprobación de desarrollo.
- Una tarea con solo criterios `Manual:` puede decir `Verify: none`, con una
  nota de lo que el revisor debe observar.
- Un `Report:` nombra una ruta que git ignora, como
  `.atipspec/tmp/junit.xml`, y que escriben los comandos Verify. Con
  `require_proof: true` o `risk: high`, todo criterio bajo `Tests:` tiene una
  entrada `Proof:` que nombra su test, y su verificación tiene un `Report:`;
  `proposal` muestra ese requisito junto a la comprobación de los criterios
  (consulta [build](build.md)). Con `risk: low`, un criterio bajo `Tests:`
  cuyo test nombrado en `Proof:` pasó no necesita veredicto del revisor
  (consulta [riesgo](spec.md#riesgo)).
- `scope` nombra los ficheros que las tareas van a cambiar, con la sintaxis
  de glob de las [reglas del contrato](../reference/contract-rules.md#globs):
  `**` cruza directorios, `*` no. Con `strict_scope: true`, el valor por
  defecto, o con `risk: high`, un plan sin `scope`, o con globs que juntos
  coinciden con cualquier ruta (`**`, `**/*`, `*` con `*/**`), es un error
  que bloquea la aprobación, para que veas el alcance antes de aprobar. Un
  fichero tocado fuera de él, incluida una eliminación, es un error (un
  warning con `strict_scope: false` y un riesgo distinto de `high`); el
  paquete de revisión los lista siempre que se escribe. Los skills y las
  reglas de permisos que instala AtipSpec no cuentan mientras contengan solo
  su contenido; quitar una de esas reglas sí cuenta. El trabajo imprevisto
  amplía `scope` en la misma edición que añade su tarea, y un alcance más
  amplio cambia lo que aprobaste, así que se te presenta de nuevo.

## Tareas, no stories

Una tarea es un cambio coherente que deja el proyecto funcionando, registrado
con `task-done` cuando está implementado. Las tareas se ejecutan en secuencia
dentro de una entrega, y por encima de `max_tasks` el plan es demasiado
grande para una jornada de trabajo: `check` avisa y el modelo propone una
iniciativa. El trabajo que quieres ejecutar en paralelo entre varias personas
pertenece a entregas separadas; consulta [equipos y escala](../teams.md).
