# Cómo funciona

## Tres verdades con tiempos de vida distintos

| Verdad | Dónde | Vive | Cambia mediante |
| --- | --- | --- | --- |
| El **contrato** | `.atipspec/contract.md` | todo el proyecto | una decisión aceptada |
| Las **specs vivas** | `.atipspec/specs/<capability>.md` | el producto | `atipspec deliver` |
| Una **entrega** | `.atipspec/deliveries/<slug>/` | días o semanas | las fases |

El contrato dice cómo está construido el sistema: stack, estructura, policy
de dependencias, convenciones, quality gates y un bloque de reglas que el
CLI evalúa. Las specs vivas dicen qué hace el producto, un fichero por
capacidad. Una entrega es la unidad de cambio: su propia spec, plan,
evidencia, revisión y hallazgos aplazados, creada, verificada y archivada
como un todo.

Alrededor de ellas están el registro de **decisiones**, las **iniciativas**
que agrupan entregas a lo largo de meses, y dos documentos curados,
`overview.md` y `glossary.md`, que mantienen el proyecto explicable en una
página.

## Quién decide qué

| Pregunta | La responde |
| --- | --- |
| ¿Qué construimos? | Tú, aprobando la propuesta (escenarios, enfoque y pruebas) en la conversación |
| ¿Bajo qué reglas? | El contrato que aprobaste, registrado con `atipspec accept contract --code <code>` e impuesto por `check` y `audit` |
| ¿Está terminada una tarea? | El asistente lo declara con `atipspec task-done`, atado al acuerdo aprobado; una declaración de avance, no una prueba |
| ¿Pasa sus comprobaciones? | `atipspec verify`, que ejecuta la verificación final y registra los códigos de salida y el hash del árbol |
| ¿Cumple la spec? | Un revisor en una sesión aislada, declarada en `review.md`, con un veredicto por criterio y un puntero que la puerta resuelve |
| ¿Se acepta el resultado? | Tú, aceptando el resultado revisado que muestra `atipspec report`; o, bajo una policy de confianza, `check --policy` con evidencia de CI de confianza y aprobaciones de producto, ingeniería y QA (`verified`) |
| ¿Cuándo se fusiona? | La política de tu repositorio; antes, `atipspec merge-check` confirma la branch |

El asistente presenta el acuerdo con su código de aprobación y ofrece
**Aprobar y continuar**, **Pedir cambios** o **Cancelar**, con el selector del
cliente o una respuesta escrita. Tras tu aprobación explícita, ejecuta
`atipspec accept ... --code <code>` y continúa. Claude Code, configurado por
`init` y abierto en la raíz del proyecto, te pregunta antes de que ese comando
se ejecute; ese aviso confirma la misma aprobación. No tienes que ejecutar comandos ni editar estados. El
verificador registra la evidencia y el revisor registra los veredictos;
ninguno puede sustituir tu decisión. Un acuerdo que cambia necesita una nueva
aprobación. Las policies de confianza externas conservan su procedimiento
autenticado.

## Una aceptación que puedes comprobar

Hay tres decisiones humanas, cada una presentada por una vista que imprime un
código de aprobación (`XXXX-XXXX`, los primeros 40 bits del sha256 del
contenido en base32 de Crockford):

| Decisión | Se presenta con | Se registra con |
| --- | --- | --- |
| La propuesta: escenarios, enfoque y pruebas | `atipspec proposal <slug>` | `atipspec accept <slug> proposal --code <code>` |
| El resultado revisado | `atipspec report <slug>` | `atipspec accept <slug> result --code <code>` |
| El contrato y sus decisiones, una vez por proyecto | `atipspec proposal contract` | `atipspec accept contract --code <code>` |

`accept` se niega cuando el código no corresponde al contenido actual, así que
el registro ata la versión que viste. Escribe un hash de ese contenido, los
digests por fichero, el código y el canal en `approvals/local-<phase>.json`
(el del contrato, en `.atipspec/approvals/contract.json`). `check` compara el
hash con los ficheros en disco en cada ejecución; un solo byte editado después
de tu aceptación devuelve la entrega a `draft` con un `todo` que nombra el
fichero que cambió. Las entregas guiadas, fixes incluidos, necesitan el
registro de la propuesta; un par de spec y plan no lo sustituye. Las entregas
antiguas aprueban su spec, y su plan cuando `approve_plan` está activado, con
`accept <slug> spec|plan --code <code>`; un fix creado antes de 0.3.0 aprueba
solo su spec.

El canal dice cómo te llegó el comando:

| Canal | Significado |
| --- | --- |
| `terminal` | El código se tecleó en la solicitud del CLI, en una terminal sin marcadores de agente |
| `client-permission` | Claude Code ejecutó `atipspec accept` por sí mismo, y las reglas de este proyecto, intactas, hacen que te pregunte antes en una sesión abierta en la raíz del proyecto |
| `assistant` | Nada te preguntó: un cliente sin reglas de permisos, reglas alteradas, el marcador de otro agente junto al de Claude Code, Claude Code ejecutado con el Agent SDK o con `claude -p`, o una línea de comandos que la regla no reconoce, como `python -m atipspec.cli` |

El CLI solo ve su propio proceso, así que cada canal es lo que declara ese
proceso. No puede ver si la sesión cargó las reglas: una sesión abierta en
otra carpeta que entra en el proyecto con `cd` no pregunta y registra
`client-permission`. Un script, o un agente que no fija ninguno de los
marcadores listados en [entorno](../reference/configuration.md#entorno), que
Claude Code ejecuta y que llama dentro a `atipspec accept` también registra
`client-permission`, aunque Claude Code solo te preguntó por el script o por
el agente. Y un agente puede quitar sus marcadores y contestar a la
solicitud del CLI desde una terminal que él crea, lo que registra
`terminal`.

Esto es detección de deriva, no autenticación: el registro demuestra qué se
aceptó y cómo se ejecutó el comando, no quién eres. Las aprobaciones firmadas
bajo una policy externa son la forma autenticada, y cuando hay una policy
configurada, la puerta ignora los registros locales. Consulta [aceptación
empresarial](../enterprise.md).

## Las fases que abre el CLI

Una fase empieza con su comando: `atipspec spec <slug>`,
`atipspec plan <slug>`, y así sucesivamente. El comando comprueba qué exige
la fase y se niega con una línea cuando falta algo: los escenarios
incompletos, la propuesta sin aprobar, una tarea sin registrar. Si no,
imprime el workflow, las reglas y el contexto, para que el modelo trabaje a
partir de lo que abrió el CLI y no de su propia lectura de la petición.
`atipspec ship <slug>` nombra la siguiente fase a la que una entrega puede
entrar. Consulta [el flujo](../flow/index.md#que-requiere-cada-fase).

## La puerta

`atipspec check <slug>` comprueba la consistencia local. La aceptación de
confianza exige además `--policy`. Lee los ficheros y git, e informa de tres
tipos de cosas:

- **error**: algo está mal o falló. La puerta está en rojo.
- **todo**: algo todavía no ha pasado. La puerta todavía no está en verde.
- **warning** e **info**: merecen atención, no bloquean.

```text
password-reset  [implemented]  tasks 2/2
  error   AC-003 FAIL: the link never expires
  error   F1 [blocker] contract: shop/domain/order.py:3 contains forbidden pattern 'from shop\.infrastructure'
  todo    review.md is stale (the working tree changed since the review); run `atipspec review password-reset` and review again
  info    F2 [minor] Missing docstring
Next: Fix: AC-003 FAIL: the link never expires
```

El código de salida 0 significa que las comprobaciones seleccionadas
pasaron, 1 significa errores y 2 significa incompleto. La puerta falla de
forma cerrada: sin git está en rojo, porque el commit base, las reglas del
contrato y la frescura de la evidencia vienen de git. Sin una policy, el
verde es solo `checked`, y `deliver` exige además tu aceptación registrada
del resultado; con la [policy externa](../enterprise.md), exige una puerta de
confianza en verde. Antes de la fusión, `atipspec merge-check --base <target>`
comprueba la branch entera: cada entrega que toca está aceptada, y el código
sigue siendo el que aceptó cada recibo.

## Evidencia atada al árbol

`atipspec verify` ejecuta los comandos que declara una tarea y escribe un
fichero JSON con los comandos, los códigos de salida, las colas de salida, la
duración y la **huella del árbol de trabajo**: un hash de contenido calculado
a través de un índice de git temporal, idéntico antes y después de hacer
commit del mismo contenido. La revisión registra la misma huella. Cuando el
árbol cambia, ambas quedan obsoletas y la puerta las vuelve a pedir;
renombrar una tarea en el plan es el único cambio que sobreviven. Integrar
main también cambia el árbol, que es justo el objetivo: no existe eso de
«funcionaba en mi branch». Un informe JUnit solo cuenta cuando lo escribió
esa ejecución: `verify` lo borra primero, y `check` nunca ejecuta los tests
por sí mismo.

## Estado derivado

El estado nunca se almacena: `status` y `check` calculan en qué punto está
una entrega a partir de sus ficheros y de git en cada ejecución. Lo que leen
son registros en el repositorio: las aprobaciones, `progress.json`, la
evidencia, `review.md` y el recibo.

`draft` → `planned` → `in_progress` → `implemented` → `checked` → `accepted` → `delivered`

`checked` es la puerta local en verde; `accepted` añade tu aceptación
registrada de ese resultado; bajo una policy de confianza, `verified` es la
puerta de confianza en verde. Una entrega antigua pasa también por `ready`,
su spec aceptada antes de que exista un plan. `atipspec accept` mueve una
spec a `ready`, y el contrato y sus decisiones a `accepted`. La puerta trata
un `ready` escrito a mano sin un registro de aceptación correspondiente como
un borrador, y un contrato, o una decisión que lo afecta, marcados
`accepted` a mano sin un registro correspondiente como no aceptados. Una
decisión sobre una capacidad es el único estado que escribe el asistente: la
marca `accepted` después de que la apruebes en la conversación, sin código ni
registro, y la siguiente `atipspec proposal` la lista para que veas lo que
seguirán la implementación y la revisión.

## Un contexto que no crece con el proyecto

`atipspec context <slug>` reúne exactamente lo que una fase necesita: el
contrato, el overview, el glosario, las specs vivas que nombra la lista
`impact` de la entrega, las decisiones aceptadas que las afectan y los
propios ficheros de la entrega. Nunca `archive/`. Imprime el tamaño contra
`context_budget`, y `audit` avisa cuando un documento supera su tope para que
la fase **curate** pueda reducirlo.

Siguiente: [el flujo](../flow/index.md).
