# fix

**De un reporte de defecto al requisito aceptado que rompe, corregido, un plan
de una tarea y la misma puerta.** Sin entrevista y sin un contrato que aceptar
primero; una sola aprobación de la propuesta, y sin atajos en la evidencia ni
en la revisión.

| | |
| --- | --- |
| Rol | Quien arregla sin ampliar. Reproduce primero, corrige el requisito para que un test falle hoy y pase mañana, no cambia nada que el defecto no exija. |
| Quién decide | Apruebas la propuesta en la conversación: el defecto, el requisito corregido y el plan; el asistente lo registra con `atipspec accept <slug> proposal --code <code>`, con el código que mostró `atipspec proposal <slug>`. **Punto de parada 1.** Después aceptas el resultado, como en cualquier entrega. |
| Produce | el requisito de `specs/<capability>.md` corregido, `spec.md` con el defecto, `plan.md` con una tarea, código, evidencia |

## Cómo ejecutarla

```bash
atipspec new bug-123 --title "Reset link never expires" --capability auth --ticket SHOP-9 --kind fix
```

```text
/atipspec-fix bug-123: a reset link created yesterday still works
```

El skill ejecuta `atipspec fix bug-123`, que se niega en una entrega que no es
un fix y, si no, imprime el workflow, las reglas y el contexto. Un fix, como
una entrega de funcionalidad, no necesita la aceptación del contrato para
empezar; mientras el contrato no esté aceptado, `check` muestra un warning.

## Qué crea `new --kind fix`

Una entrega guiada (`schema: 2`), como una funcionalidad, con `kind: fix`,
`requirements: []`, `risk: normal` y `baseline.json`, que registra el commit
del que parte; `new` se niega mientras la spec viva de la capacidad tenga
cambios sin commitear. Su `spec.md` contiene el defecto, no
un requisito:

```markdown
---
title: "Reset link never expires"
status: draft
kind: fix
capability: auth
ticket: SHOP-9
schema: 2
requirements: [REQ-002]
risk: normal
---

# Reset link never expires

## Defect

Observed: a link created 26 hours ago still opens the reset form.

Expected: the page shows "link expired", as REQ-002 states.

Reproduction: `python -m pytest tests/auth/test_reset.py -k expired`
```

El plan tiene una tarea, `T1: Regression test and fix`, y una
`## Final verification` cuyo `Verify:` lista todos los `require-command` del
contrato y un marcador de posición para el comando que ejecuta el test de
regresión.

## Qué hace el modelo

1. Reproduce el defecto y rellena `## Defect`: `Observed:` y `Expected:` son
   obligatorios, `Reproduction:` es recomendable.
2. Encuentra en `.atipspec/specs/auth.md` el requisito que rompe el defecto,
   lista su ID bajo `requirements` y lo corrige ahí, conservando su ID:
   añade bajo él un criterio de regresión, o reescribe el criterio que dejó
   pasar el defecto.

    ```markdown
    ### REQ-002: The link expires

    #### AC-003: Link older than 30 minutes
    - **WHEN** a link issued 31 minutes ago is opened
    - **THEN** the page shows "link expired"

    #### AC-007: Link issued the day before
    - **GIVEN** a link issued 26 hours ago
    - **WHEN** the user opens it
    - **THEN** the page shows "link expired" and sends nothing
    ```

3. Rellena el plan: `scope`, el enfoque, `Covers: REQ-002`, los criterios del
   requisito bajo `Tests:`, incluido el de regresión, y el comando de test
   bajo `Verify:` en lugar del marcador de posición.
4. Propone el [riesgo](#riesgo) en `spec.md`.
5. Presenta `atipspec proposal bug-123`, que muestra `Kind: fix · Risk: ...`,
   `Corrects: REQ-002 (accepted requirement)` y el diff de la spec viva
   contra los requisitos aceptados en el commit base de la entrega, y pide tu
   aprobación.
6. Tras la aprobación, escribe el test de regresión, comprueba que falla,
   hace el cambio más pequeño, registra `task-done`, ejecuta `verify` y da
   el paquete de revisión a un revisor.
7. Presenta `atipspec report bug-123` para que aceptes el resultado, y luego
   `deliver` escribe el requisito corregido en la spec viva. La historia del
   defecto queda en la entrega archivada.

Unos diez comandos: `new`, `fix`, `proposal`, `accept proposal`,
`task-done`, `verify`, `review`, `report`, `accept result`, `deliver`.

## Qué exige `check` de un fix

- `base` en `spec.md` es el id completo del commit que registró
  `atipspec new`: un commit de la historia de `HEAD`, y el head que registra
  `baseline.json`. Un nombre como `HEAD` o una branch, u otro commit, es un
  error: uno posterior dejaría los commits entre el registrado y él fuera de
  la comparación, de la comprobación del alcance y del diff del dosier, y uno
  anterior compararía con requisitos que todavía no estaban aceptados. Una
  entrega migrada desde una antigua conserva su base anterior, que no puede
  ser posterior a ese head.
- `requirements` lista al menos un requisito, y cada uno está entre los
  requisitos que contenía `specs/<capability>.md` en el commit base de la
  entrega, o que llegaron a ella después a través de la branch de
  integración (consulta [equipos](../teams.md#cuando-main-avanza)) o de una
  entrega archivada en la branch tras la base, tal como su recibo registra que
  esa entrega lo escribió: un fix corrige un requisito que la capacidad ya
  aceptó. El fichero de trabajo y `baseline.json` no
  cambian esa lista, y `capability` es la que nombra `spec.md`, aunque a
  `new` se le diera otra. Un requisito que no está ahí es un error, porque un
  comportamiento que ningún requisito cubre es una entrega de funcionalidad.
  Solo en un proyecto cuyas specs vivas no contenían ningún requisito en la
  base (un proyecto existente sin specs) puede el fix escribir el primero,
  con un info; un fix cuya capacidad no tiene ninguno mientras otras sí es un
  error que pide la `capability` correcta.
- Un fix cambia solo los requisitos que lista, y no elimina ninguno: un
  requisito añadido, cambiado, borrado o marcado `[remove]` en la spec viva
  de su capacidad sin estar listado es un error, igual que uno listado
  marcado `[remove]` o cualquier requisito cambiado en la spec viva de otra
  capacidad, que la propuesta también muestra como diff. Lo que trajo la
  branch de integración o una entrega archivada desde la base no es cambio
  del fix; lo que trae una fusión de cualquier otra branch sí lo es. Cuando
  el cambio tiene commit en la branch, el mensaje dice que puede haberlo
  hecho otro cambio, que entonces necesita su propia entrega.
- `merge-check` comprueba lo mismo contra la branch de destino: un fix
  archivado en la branch cuyo requisito no estaba en la spec viva en la base
  de la fusión, ni lo escribió una entrega anterior de la branch, bloquea la
  fusión, y lo mismo hace un requisito cambiado fuera de las entregas que lo
  listan.
- Al menos un criterio de los requisitos corregidos está bajo `Tests:`: el
  test de regresión automatizado.
- `## Defect` declara `Observed:` y `Expected:`.
- Más de 2 requisitos es un warning (`max_requirements` cuando es menor):
  una reparación que necesita más no es un fix.

Todo lo demás es lo de una entrega guiada: una aprobación de la propuesta, la
evidencia atada al árbol, la revisión en una sesión aislada (declarada en
`session:`), tu aceptación del resultado, `deliver` y `merge-check`.

## Riesgo

`risk` en `spec.md` fija cuánta ceremonia exige la puerta, en un fix como en
cualquier entrega: `low` para una reparación local cuyo test de regresión el
plan nombra en `Proof:`, que entonces no necesita veredicto del revisor;
`high` para seguridad, dinero, datos o permisos. Lo apruebas con la
propuesta; cambiarlo anula esa aprobación. Consulta [riesgo](spec.md#riesgo).

## Fixes creados antes de 0.3.0

Un fix sin `schema: 2` en su `spec.md` mantiene su propio flujo hasta que se
archiva: necesita la aceptación del contrato para empezar, su requisito
embebido y `accept <slug> spec`, y ninguna aceptación del plan. `deliver`
fusiona su requisito en la spec viva como antes.
