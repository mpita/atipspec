# spec

**De la intención a escenarios que el revisor puede verificar.** La fase
donde decides qué se construye.

| | |
| --- | --- |
| Rol | El analista. Le importa el resultado observable, no la solución. Hace como máximo tres preguntas por ronda, propone valores por defecto y nunca acepta «funciona bien» como resultado. |
| Quién decide | Apruebas la propuesta en la conversación: estos escenarios junto con el enfoque y las pruebas del [plan](plan.md); el asistente lo registra con `atipspec accept <slug> proposal --code <code>`. **Punto de parada 1.** |
| Produce | requisitos y escenarios en `.atipspec/specs/<capability>.md`; el `spec.md` de la entrega con la intención, lo que queda fuera de alcance, los límites de calidad y los IDs que lista |

## Cómo ejecutarla

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

Si la entrega todavía no existe, el modelo la crea con `atipspec new`. Luego
el skill ejecuta `atipspec spec password-reset`, que imprime el workflow, las
reglas y el contexto. Una entrega guiada no necesita nada más para empezar;
`check` avisa mientras el contrato no esté aceptado. Una entrega de fix usa
[fix](fix.md) en su lugar, y una [entrega
antigua](../reference/legacy.md#aprobaciones) necesita antes la aceptación del
contrato.

## Qué hace el modelo

1. Lee el contexto que imprimió el comando: el contrato, el overview, el
   glosario, las specs vivas de la lista de impact y las decisiones que las
   afectan. Usa las palabras del glosario y pregunta antes de aceptar un
   sinónimo.
2. Pregunta solo lo que el proyecto todavía no responde, en rondas de como
   máximo tres preguntas, primero las de mayor impacto, cada una ligada a la
   decisión que cambia y con un valor por defecto propuesto; hace otra ronda
   mientras quede abierta una decisión con consecuencias. Resuelve, en este
   orden: actor y disparador; camino feliz; caminos de fallo (entrada no
   válida, datos que faltan, permisos, tiempos de espera agotados); datos
   creados, cambiados o borrados; fuera de alcance; atributos de calidad como
   un número con su forma de medirlo, o ninguno; conflictos con el
   comportamiento existente o con el contrato.
3. Toma un prefijo de ID una vez para la entrega con `atipspec ids auth` y
    escribe los requisitos y sus escenarios en la spec viva de la capacidad,
    `.atipspec/specs/auth.md`:

    ```markdown
    ### REQ-AUTH-7KQ2M-001: The user can request a reset link

    From the sign-in screen the user enters an email and receives a link.

    Why: support tickets for forgotten passwords are 40% of the queue.

    #### AC-AUTH-7KQ2M-001: Registered email
    - **GIVEN** a registered user with the email "ana@example.com"
    - **WHEN** the user requests a reset for "ana@example.com"
    - **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

    #### AC-AUTH-7KQ2M-002: Unknown email
    - **WHEN** a reset is requested for "nobody@example.com", which no user has
    - **THEN** the system shows "Check your email" and sends nothing

    ### REQ-AUTH-7KQ2M-002: The link expires

    #### AC-AUTH-7KQ2M-003: Link older than 30 minutes
    - **WHEN** a link issued 31 minutes ago is opened
    - **THEN** the page shows "link expired" and sends nothing

    ### REQ-AUTH-7KQ2M-003: Reset requests under load

    #### AC-AUTH-7KQ2M-004: One hundred requests a minute
    - **WHEN** 100 users request a reset within one minute
    - **THEN** the p95 response time measured at the API gateway is below 300 ms
    ```

4. Rellena el `spec.md` de la entrega: `requirements` lista los IDs que este
    cambio escribe, `## Intent` declara el actor, el disparador, el resultado
    observable y cómo sabrás que funcionó, y `## Out of scope` y
    `## Quality attributes` (una línea `- REQ-...: limit` por cada requisito
    que declara un límite) quedan decididos, `- None` incluido:

    ```markdown
    ---
    title: "Password reset"
    status: draft
    capability: auth
    owner: ana
    requirements: [REQ-AUTH-7KQ2M-001, REQ-AUTH-7KQ2M-002, REQ-AUTH-7KQ2M-003]
    risk: normal
    ---

    # Password reset

    ## Intent

    A user who forgot the password requests a reset link by email and sets a new
    password with it, without contacting support.

    ## Out of scope

    - Password policy changes.

    ## Quality attributes

    - REQ-AUTH-7KQ2M-003: p95 below 300 ms with 100 requests per minute

    ## Assumptions

    - The link is single-use.

    ## Open questions

    - None
    ```

    Cuando aportas un documento o una lista de criterios de aceptación, el
    modelo ejecuta `atipspec spec-bind password-reset --file <path>`, que
    escribe la spec viva y los IDs; con una lista, conserva el original y
    lista bajo `## Import review notes` lo que hay que comprobar.

5. Ejecuta `atipspec check password-reset` y reescribe lo que señala hasta
   que el único todo restante sea tu aprobación. Solo cita palabra por
   palabra el texto que muestra la interfaz, y al presentar nombra cada
   warning que mantiene.
6. Propone el [riesgo](#riesgo) de la entrega, prepara el [plan](plan.md) y
   presenta `atipspec proposal password-reset`, que muestra el código de
   aprobación, el tipo y el riesgo, con qué rigor se comprueban los
   criterios, los warnings de especificación y el diff de la spec viva, y
   pide tu aprobación en la conversación.

## Reglas de la entrevista

- Como máximo tres preguntas por ronda, cada una ligada a la decisión que
  cambia; más rondas mientras quede abierta una decisión con consecuencias.
- Un valor por defecto que propone el modelo se convierte en un requisito y
  una suposición que confirmas en la aceptación, nunca en una elección
  silenciosa.
- Todo escenario con WHEN y THEN y un valor concreto en cada THEN, sin
  términos vagos, y marcado `[manual]` cuando lo observa una persona; si no,
  `check` lo señala. Consulta [escribir criterios](../reference/spec-quality.md).
- Un requisito por cada comportamiento que un usuario valora, independiente
  de otros cambios abiertos, lo bastante pequeño para la entrega y
  comprobable.
- Los atributos de calidad son números con una forma de medirlos, o nada.
- Un `## Intent` vacío bloquea la propuesta, igual que un `## Out of scope`
  o un `## Quality attributes` vacíos: escribe `- None` cuando no aplica
  nada.
- Una entrega cabe en una jornada de trabajo. Por encima de
  `max_requirements`, el modelo propone dividirla en entregas bajo una
  iniciativa antes de pedir la aceptación; `check` avisa en cualquier caso.
- Comportamiento, nunca implementación.
- Una spec con preguntas abiertas no se puede aprobar: la propuesta no
  muestra ningún código.
- `capability` es la spec viva que contiene los requisitos. `impact` lista
  cualquier otra spec viva o sección del contrato que la entrega toque:
  `context` las carga y `status` avisa de solapes con otras entregas
  abiertas.
- `### REQ-AUTH-7KQ2M-003 [remove]: Exact title` en la spec viva, listado en
  `requirements`, borra ese requisito en el deliver. Así es como se retira un
  comportamiento: explícitamente.
- Los requisitos que ya contiene otra entrega abierta o la spec viva
  conservan sus IDs; la entrega lista solo lo que escribe.
- Un requisito que la entrega añade, cambia o elimina en `specs/` sin
  listarlo, en la spec viva de su capacidad o en otra, es un error en todos
  los niveles de riesgo: la aprobación hashea solo los listados, y
  `merge-check` bloquea los demás.

## Riesgo

El `spec.md` de una entrega guiada declara `risk: low`, `normal` (lo que
escribe `new`) o `high`. El modelo propone el nivel; lo apruebas con la
propuesta, que muestra `Kind: ... · Risk: ...` y lo que el nivel exige a la
puerta. `risk` forma parte de lo que cubre el hash de la aprobación de la
propuesta, así que cambiarlo después anula esa aprobación. El nivel no añade
ni quita ninguna aprobación.

| Nivel | Qué exige la puerta |
| --- | --- |
| `low` | un criterio bajo `Tests:` cuyo test nombrado en `Proof:` pasó en la evidencia actual no necesita veredicto del revisor (`check` lo indica con un info, y el dosier muestra `NOT NEEDED` con el motivo); `review.md` sigue siendo obligatorio, todos los demás criterios, manuales incluidos, necesitan su veredicto y un `FAIL` sigue bloqueando. Eliminar un requisito (marcado `[remove]` o borrado de `specs/`), aunque esté listado, o cambiar `contract.md` es un error: `check` compara `specs/` con los requisitos confirmados en la base de la entrega y con lo que han traído desde entonces la branch de integración y las entregas archivadas en la branch |
| `normal` | un veredicto del revisor para cada criterio |
| `high` | `plan.md` declara un `scope`, y un fichero fuera de él es un error, incluso con `strict_scope: false`; cada criterio bajo `Tests:` nombra su test en `Proof:`, con un `Report:` (un error que bloquea la propuesta); la revisión viene de una sesión aislada (`session: isolated`) |

Una entrega sin `risk`, incluidas las antiguas, es `normal`; una entrega
antigua que lo fija a mano obtiene sus efectos, y `check` indica el nivel.
Cualquier otro valor es un error. El paquete de revisión declara el nivel, y
el dosier lo muestra.

## Tu parte

Lee la propuesta como el acuerdo que es. Cambia el texto, añade escenarios,
recorta el alcance. Cuando diga lo que quieres, aprueba en la conversación;
el asistente ejecuta entonces, con el código que presentó:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

Se niega mientras haya una pregunta abierta, un escenario incompleto o un
error en el plan, y cuando el código no coincide con el contenido actual; si
no, pone `status: ready` y registra un hash de los escenarios, del `spec.md`
de la entrega, de los compromisos del plan, del contrato y de la
configuración, junto con el código y el canal. A partir de ahí, cualquier
edición de ellos devuelve la entrega a borrador hasta que vuelvas a aprobar,
y `check` nombra lo que cambió. Claude Code te pregunta antes de que el
comando se ejecute.

!!! note "Cambiar la spec después"
    Si el build revela que un criterio no se puede cumplir, el modelo debe
    detenerse y decírtelo. La spec cambia con tu acuerdo, y la entrega vuelve
    a pasar por la puerta. Los criterios nunca se debilitan en silencio y
    nunca se aplazan.
