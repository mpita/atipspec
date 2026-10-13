# review

**Un revisor que no escribió el código escribe `review.md`.** Un pase
adversarial, en una sesión aislada, atado al árbol.

| | |
| --- | --- |
| Rol, lado del autor | El autor que entrega el trabajo. No discute dentro del contexto del revisor, nunca edita `review.md`. Arregla, verifica, vuelve a preguntar. |
| Rol, lado del revisor | Adversarial. Juzga contra la spec y el contrato, un veredicto por criterio, con un puntero a la prueba. |
| Quién decide | `atipspec check`. |
| Produce | `review.md` |

## Cómo ejecutarla

```text
/atipspec-review password-reset
```

## Qué ocurre

1. El modelo ejecuta `atipspec review password-reset`. El CLI se niega
   mientras una tarea no esté completa, la evidencia esté obsoleta o el
   contrato esté violado, y no escribe ningún paquete. Si no, cuenta la
   revisión (consulta [rondas de revisión](#rondas-de-revision)) y
   escribe un paquete en `.atipspec/tmp/password-reset-review-packet.md` con:
   la rúbrica, el riesgo de la entrega y lo que exige, el contrato de
   arquitectura, las specs vivas que la entrega declara en su lista de
   impact, las decisiones aceptadas que las afectan, la spec, el plan, los
   elementos aplazados, un resumen de evidencia, los ficheros cambiados fuera
   del `scope` del plan, y el diff contra el commit base de la entrega más
   los ficheros sin seguimiento. Un diff de más de 200 KB se sustituye por su
   `--stat` y un extracto truncado, con una nota que le dice al revisor que
   inspeccione el repositorio. Luego el comando imprime `review N of M` y el
   workflow.
2. El modelo da el paquete a un revisor **en una sesión aislada**: una
   sesión que no ha visto la conversación y a la que solo se le da la ruta
   del paquete. En Claude Code esto es un subagente; consulta
   [clientes](../clients.md) para los demás. Cuando el cliente no puede
   ofrecer una, el revisor escribe igualmente la revisión y declara
   `session: shared`. Con `risk: high` o `require_isolated_review`, el modelo
   te pide en cambio que abras una sesión nueva para el revisor.
3. El revisor lee el paquete, inspecciona el repositorio, ejecuta comandos si
   con leer no basta, y escribe:

```markdown
---
tree: cd03ae507b3605b12a497fcbcf590894a0073076
reviewer: claude-code subagent
session: isolated
---

# Review: Password reset

## Criteria

- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. tests.auth.test_reset.test_unknown_email_same_response
- AC-003: FAIL. consume() checks the age but the boundary of exactly 30 minutes is accepted.

## Findings

- F1 [blocker]: shop/domain/reset.py imports shop.infrastructure.mail, forbidden by the contract.
- F2 [minor]: request() lacks a docstring.

## Notes

The spec does not say whether a used link may be reused; assumed no.
```

4. El modelo ejecuta `atipspec check password-reset`:
    - Un `FAIL` o un `blocker`: arregla el código y vuelve a verificar.
      Cualquier cambio en el árbol deja la revisión obsoleta, así que vuelve
      a ejecutar `review` y al revisor.
    - Un hallazgo minor que decides no arreglar ahora va a `deferred.md`
      con una razón: `- F2: cosmetic, handled in the docs cleanup delivery`.
      Un hallazgo blocker o major se arregla: solo lo aplaza una excepción
      de riesgo bajo una policy de confianza. Los criterios nunca se pueden
      aplazar.
5. Cuando `atipspec review` se niega porque se agotaron las rondas de
   revisión, el modelo se detiene y presenta `atipspec check password-reset`
   con los hallazgos que quedan. Tú decides.

## Qué comprueba la puerta en `review.md`

- `tree:` es el del paquete: el candidato que contó el último
  `atipspec review`. Una revisión de otro candidato está obsoleta, salvo que
  solo hayan cambiado títulos de tareas, y una escrita sin ejecutar `review`
  queda a la espera de que se ejecute (consulta [rondas de
  revisión](#rondas-de-revision)).
- `reviewer:` nombra el cliente o el modelo que escribió la revisión; sin él,
  `check` informa de un error.
- `session:` es `isolated` (el revisor nunca vio la conversación del autor)
  o `shared`. Una revisión que lo omite cuenta como `shared`. Una revisión
  compartida es un warning, y un error cuando la spec dice `risk: high` o
  cuando `require_isolated_review` está activado en `config.yaml` o en la
  policy de confianza. Cualquier otro valor es un error. En el flujo guiado,
  el revisor declara la sesión; la declaración se registra, se muestra en el
  dosier y la puerta actúa según ella, pero nada la mide. El [ejecutor de
  procesos](../reference/execution-adapter.md) la contrasta con el
  `isolated_review` que declara el adaptador.
- Cada criterio tiene un veredicto, salvo, con `risk: low`, uno cuyo test
  nombrado en `Proof:` pasó en la evidencia actual: `check` lo indica con un
  info. Un `FAIL` bloquea en todos los niveles. Consulta
  [riesgo](spec.md#riesgo).
- Cada `PASS` necesita un puntero que la puerta resuelve, uno de estos:
    - un test que pasó en el informe JUnit de la evidencia actual, nombrado
      como lo nombra el informe (`tests.auth.test_reset.test_link`) o como en
      una entrada de Proof; un nombre con espacios va entre comillas
      invertidas;
    - `path:line` o `path:line-line`, una línea que existe en un fichero del
      candidato: fuera de `.atipspec/` y de `.git` y no ignorado por git. Los
      logs de evidencia de la entrega cuentan, aunque git ignore `*.log`,
      como `evidence/logs/FINAL-<run>-1.log:12` desde la carpeta de la
      entrega;
    - `path::test`, un fichero de ese tipo que contiene ese nombre como
      palabra (un sufijo `[param]` se ignora); el dosier lo muestra como un
      nombre encontrado en el fichero, ya que la puerta no lo ejecuta.

    Para un criterio marcado `[manual]`, también vale una descripción de lo
    que se hizo y se observó, de tres palabras o más. Un `FAIL` necesita su
    motivo. `PASS. ok` es un error. Mientras la revisión está obsoleta, sus
    punteros no se juzgan, y mientras la evidencia no está al día, un puntero
    sin resolver es un todo: el test que nombra puede estar en la siguiente
    ejecución. Un puntero que se resuelve demuestra que nombra algo real, no
    que pruebe el criterio: el dosier muestra a qué se resolvió cada uno para
    que lo juzgues tú, y las entradas de [Proof](build.md), obligatorias con
    `require_proof`, atan un criterio a su test: un `PASS` de un criterio así
    que no nombra ese test es un warning.

## Rondas de revisión

`review_rounds` en `config.yaml` (3 por defecto) es cuántas revisiones tiene
una entrega por acuerdo aprobado, contando la primera: una primera revisión y
dos de candidatos corregidos. `atipspec review` cuenta una revisión cada vez que
escribe un paquete para un candidato distinto del último paquete, diga lo que
diga `review.md`: una revisión que pasó también cuenta, porque el revisor
escribe ese fichero y el CLI no puede distinguir sus veredictos de otros
editados después. Volver a escribir el paquete para el mismo candidato no
cuenta nada, y tampoco un paquete que no se puede construir. Una vez usadas
las revisiones, si el candidato vuelve a cambiar, `review` se niega, sin contar
nada, y nombra la decisión: cambiar la propuesta, subir `review_rounds` o
parar. Hasta entonces, `check` informa de las revisiones agotadas como un error,
diga lo que diga `review.md`, y el dosier muestra la cuenta. `check` solo
toma la revisión del último paquete que contó `atipspec review`: un
`review.md` escrito para un candidato sin ejecutar el comando es un todo que
lo pide, así que saltárselo no ahorra ninguna revisión. La cuenta vive en
`review-rounds.json`, en la carpeta de la entrega, que escribe el CLI, y
vuelve a empezar cuando cambia el acuerdo aprobado: la propuesta de una
entrega guiada, la spec de una antigua. Las reglas de Claude Code mantienen
las herramientas de edición del cliente lejos de ese fichero, no un comando
de shell. `atipspec accept <slug> proposal` crea el fichero, así que en una
entrega guiada creada desde 0.3.0 un fichero que falta se borró: `review` se
niega y `check` falla hasta que decidas, restaurándolo desde git o aprobando
otra vez la propuesta, lo que empieza una cuenta nueva. Cuando falta el
fichero en una entrega aprobada bajo una policy de confianza, `atipspec
review` vuelve a contar a partir del `review.md` de la carpeta, como primera
revisión; en una creada antes de 0.3.0 cuenta a partir del paquete
siguiente, porque un `review.md` escrito antes nombra un árbol de la huella
anterior.
Subir `review_rounds` en una entrega guiada cambia `config.yaml`, que entra
en el hash de la aprobación de la propuesta, así que la propuesta se vuelve a
presentar. En una entrega antigua (incluido un fix creado antes de 0.3.0),
cuya aprobación es la de la spec, ninguna aprobación cubre `config.yaml`: un
límite subido se aplica de inmediato, así que el modelo solo lo sube cuando
tú lo dices, y el dosier muestra `Revisión N de M`. `atipspec status
password-reset` muestra `review N of M`. `atipspec run` cuenta de la misma
forma las revisiones que pide y se detiene en `needs_decision` cuando se
agotan. También lleva su propia cuenta: `--max-rounds`, que por defecto es
`review_rounds` menos uno, porque cada corrección se vuelve a revisar, y no
puede superarlo, limita cada corrección automática, la pida una revisión o un
check.

## Por qué una sesión aislada

El contexto que escribió el código lo confirmará. Los veredictos del revisor
son los únicos que la puerta acepta, y la puerta los rechaza en cuanto el
código cambia, salvo que solo hayan cambiado títulos de tareas en un plan.
Una violación del contrato siempre es un blocker.

Los hallazgos blocker y major exigen resolución o una excepción de riesgo de
confianza. El verde local es `checked`: el asistente presenta entonces
`atipspec report <slug>` para que aceptes el resultado, y `deliver` lo exige.
Bajo la [aceptación de confianza](../enterprise.md), el verde es `verified`,
y la aprobación firmada de QA ata la revisión, las excepciones y la
evidencia.
