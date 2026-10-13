# Adaptador de ejecución

Los skills guiados trabajan dentro del asistente de programación activo del
usuario. Para una ejecución reanudable, `atipspec run <slug>` usa un adaptador
de proceso configurado explícitamente. Nunca acepta la propuesta ni el
resultado, y nunca hace commit, push, merge ni despliegue. Solo ejecuta
entregas guiadas, y se niega bajo una policy de confianza externa, tanto si
está seleccionada como si es obligatoria.

El runner de procesos necesita un sistema POSIX para su bloqueo del checkout:
Linux, macOS o WSL. En cualquier otro sistema, `run` se niega antes de leer la
entrega o de escribir nada; continúa la entrega en la conversación guiada, que
tiene las mismas fases y la misma puerta. El runner es un proceso en primer
plano con checkpoints, no un servicio instalado en segundo plano. Un
supervisor puede lanzarlo, pero AtipSpec no afirma que persista después de
que se detenga el proceso anfitrión.

## Configuración

Crea `.atipspec/adapter.json` antes de aprobar la propuesta:

```json
{
  "schema": 1,
  "name": "my-agent-wrapper",
  "command": ["/absolute/path/to/wrapper"],
  "isolated_review": false
}
```

El ejecutable se ejecuta en la raíz del proyecto con una petición JSON en
stdin. Debe escribir exactamente una respuesta JSON en stdout; la salida de
diagnóstico va a stderr. El comando es un array argv, no código de shell. Los
cambios en la configuración del adaptador invalidan la aprobación de la
propuesta guiada. El wrapper debe hacer cumplir los permisos solicitados y
usar una conversación nueva del modelo para la revisión antes de declarar
`isolated_review: true`. Un proceso nuevo del sistema operativo no basta por
sí solo para demostrar el aislamiento del contexto del modelo. Este protocolo
no es un sandbox para programas arbitrarios.

El runner obliga a que el `session:` de la revisión coincida con esa
declaración. Una revisión que dice `session: isolated` desde un adaptador sin
`isolated_review: true` hace fallar la ejecución. Cuando la entrega exige una
revisión aislada (`risk: high`, o `require_isolated_review: true` en
`config.yaml`) y el adaptador no la declara, la ejecución se detiene en
`needs_decision` antes de llamar a ningún rol, para que no se haga trabajo que
solo una revisión aislada podría aceptar: ejecuta la entrega en modo guiado y
revísala en una sesión aislada con `atipspec review <slug>`, o configura un
adaptador que aísle al revisor.

Las peticiones incluyen `schema`, `delivery`, `role`, `instruction`,
`agreement`, el `context` versionado, la `task` asignada, los `findings`
anteriores, un contrato de respuesta y los permisos. Las peticiones de
revisión incluyen `review_packet`. El wrapper integra el modelo y las
herramientas de programación que elija; el núcleo de AtipSpec controla la
verificación.

Respuestas:

```json
{"schema": 1, "status": "done", "summary": "Implemented the approved behavior"}
```

`needs_decision`, `blocked` y `failed` también son status válidos y deben
explicar el problema concreto en `summary`. Al completar una revisión se
devuelve además `review_markdown`, que debe corresponder a los IDs de criterio
y al árbol candidato del paquete. El revisor no debe modificar ficheros del
proyecto. El núcleo valida la forma de la respuesta, detecta la deriva del
acuerdo y ejecuta su propia puerta de evidencia y revisión. Un mensaje `done`
no establece la corrección ni la aceptación humana.

## Operación y recuperación

```sh
atipspec adapter
atipspec proposal my-change                       # shows the approval code
atipspec accept my-change proposal --code <code>  # after the human approves
atipspec run my-change --budget 900 --timeout 300   # --max-rounds: at most, and by default, review_rounds less one
atipspec report my-change                         # shows the result's code
atipspec accept my-change result --code <code>    # after the human accepts
atipspec deliver my-change
```

`atipspec run` imprime su estado como JSON y sale con 0 en
`ready_for_acceptance` o `accepted`, y con 2 en cualquier otro estado:
`awaiting_approval`, `needs_decision`, `blocked` o `failed`, con el motivo.
`run.json` registra la fase, el tiempo transcurrido acumulado, las rondas de
corrección y el digest del acuerdo. `progress.json` registra las definiciones
de las tareas completadas. Ambos son metadatos operativos excluidos de la
huella del candidato; la evidencia y las aprobaciones se siguen comprobando de
forma independiente. Los bloqueos del sistema operativo permiten un solo
runner por checkout.

Volver a ejecutar un candidato completado reutiliza la evidencia final y la
revisión vigentes. Después de resolver un fallo informado, usa `--resume`. Las
mutaciones de un agente interrumpidas o que agotaron su tiempo exigen
inspeccionar el trabajo parcial y elegir explícitamente
`--retry-interrupted`; no se repiten a ciegas. La misma versión aprobada
conserva su presupuesto de tiempo transcurrido y de correcciones entre
invocaciones. Los nuevos compromisos aprobados empiezan un presupuesto nuevo.
Aumentar los límites de tiempo es una elección explícita en el CLI.
`--max-rounds` cuenta cada corrección automática, la pida una revisión o una
comprobación; por defecto vale `review_rounds` de `config.yaml` menos uno,
porque cada corrección se vuelve a revisar, y no puede superarlo, porque más
rondas son decisión de la persona. Las revisiones que pide el runner cuentan
en `review-rounds.json`, igual que en `atipspec review`: cada revisión de otro
candidato, contando la primera; cuando se han contado `review_rounds`, el
runner se detiene en `needs_decision`.

Las policies de confianza externas usan su propio workflow protegido de
ejecución y aceptación; este runner inicial no las elude con registros de
aprobación locales. Las métricas de tokens y de coste se informan como no
disponibles, no como cero.

## Límites de la validación

Los tests usan fixtures de subprocesos reales para verificar la ejecución, el
rechazo antes de la aprobación, las comprobaciones compartidas, la revisión,
la reutilización, la interrupción, la deriva, los timeouts, los reintentos y
el bloqueo. Estos fixtures son programas deterministas, no tests con un modelo
real. Todavía hace falta un wrapper nativo para un cliente de programación y
una validación de la integración real antes de afirmar una integración de
extremo a extremo con un modelo sin supervisión.
