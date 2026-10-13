# Referencia del CLI

Todos los comandos se ejecutan desde cualquier lugar dentro del proyecto;
AtipSpec encuentra la raíz buscando `.atipspec/config.yaml`. Todos los
comandos salvo `init` validan primero ese fichero (consulta
[configuración](configuration.md)). Los errores imprimen `AtipSpec: error:
...` y salen con 1 (consulta [códigos de salida](#codigos-de-salida)). El
estado de una entrega es derivado: `status` y `check` lo calculan a partir de
los ficheros y de git en cada ejecución. Lo que el CLI registra lo escribe
como ficheros en el repositorio: los registros de aprobación,
`progress.json`, la evidencia, `review-rounds.json`, el `run.json` del runner
y el recibo del archivo (consulta [artefactos](artifacts.md)).

**Quién ejecuta qué.** En la conversación guiada, el asistente ejecuta los
comandos; tú apruebas en la conversación y el asistente registra tu decisión
con `accept` (consulta [tres decisiones
humanas](../flow/guided.md#tres-decisiones-humanas)). Cada sección indica
cuándo un comando corresponde a la persona, a la CI o a un worker protegido.
`atipspec <command> --help` imprime las opciones.

## Proyecto

### `atipspec init`

```text
atipspec init [--name NAME] [--language LANG] [--client ID]...
```

Crea `.atipspec/` con `config.yaml`, `contract.md`, `overview.md`,
`glossary.md`, las carpetas `specs/`, `deliveries/`, `archive/`,
`decisions/`, `initiatives/`, la copia del framework y los skills de los
clientes seleccionados. Para Claude Code, además, fusiona las reglas de
permisos de AtipSpec en `.claude/settings.json` (consulta [reglas de permisos
de aprobación](../clients.md#reglas-de-permisos-de-aprobacion)). Cuando se
ejecuta en una terminal, pregunta lo que no proporcionan los flags; si no,
usa el nombre de la carpeta, `en` y ningún cliente. `--client` acepta
`claude`, `codex`, `cursor`, `github-copilot`, `antigravity` o `gemini`, y se
puede repetir. `config.yaml` recibe todas las policies escritas
explícitamente, `trust: optional` incluida. Fuera de un repositorio git avisa:
la puerta necesita git y sin él se queda en rojo. También avisa cuando el
repositorio no tiene `.gitignore`.

En un proyecto ya inicializado: muestra el estado y, en una terminal, un menú
para añadir o quitar clientes, actualizar el framework o cambiar el nombre y
el idioma. Con flags, los aplica directamente. Se ejecuta una vez por
proyecto.

### `atipspec install`

```text
atipspec install [--client ID]... [--update]
```

Instala el framework y los skills de los clientes indicados sin sobrescribir
nada que difiera, y fusiona las reglas de permisos de Claude Code.
`--update` reemplaza los ficheros del framework y de los skills que difieren
de la versión instalada del CLI, quita los ficheros de `.atipspec/framework/`
que esa versión no instala (salvo los que git ignora) y repara las reglas de
permisos que falten.
También lista las policies de `config.yaml` que difieren de los valores por
defecto de esta versión o que no están definidas, y nunca las edita. Sin
`--client` pregunta en una terminal, o se dirige a los clientes ya instalados
con `--update`. Ejecútalo después de actualizar AtipSpec.

### `atipspec status`

```text
atipspec status [SLUG] [--format text|json|markdown]
```

Sin slug: el nombre del proyecto, la branch, la aceptación del contrato
(quién, cuándo, canal, código y decisiones, o qué cambió desde entonces), una
línea `approvals:` con el estado de las reglas de permisos del cliente, las
specs vivas, cada entrega abierta con su status derivado, owner, ticket (con
su enlace, consulta [tickets](../teams.md#tickets)), lead time (`open 5h`, o
`accepted after 5h` cuando su resultado ya está aceptado), las aprobaciones
registradas con su canal y la siguiente acción, un warning por encima de
`max_age_hours`, los warnings de solape, las iniciativas con su progreso, los
slugs entregados con su lead time, una línea `trust:` cuando `config.yaml`
define `trust: required` y un aviso cuando `origin/HEAD` nombra una rama de
integración que no es main ni master y `teams.json` no declara ninguna, porque
un checkout de CI no la encontraría: el aviso pide declararla en
`teams.json`, y en la policy de confianza cuando una juzga el merge (consulta
[cuando main avanza](../teams.md#cuando-main-avanza)). Con un slug: el mismo informe que `check` y, a
continuación, el ticket, las aprobaciones registradas con su canal, como las
muestra el status del proyecto, `review N of M` una vez que `atipspec review`
ha escrito un paquete, y la siguiente acción.

`--format json` imprime el mismo estado como datos (`schema: 1`): cada
entrega abierta con su slug, título, tipo, estado, el código de salida que
daría `check`, owner, ticket y `ticket_url`, tareas, lead time, aprobaciones
registradas y siguiente acción, las iniciativas, cada entrega archivada con
su owner, su ticket y si su recibo registra un resultado aceptado, e
`integration_warning` (ese aviso, o `null`); con un slug, la entrada de esa entrega y sus comprobaciones. `--format markdown`
imprime las entregas como tablas (Delivery, Ticket, Owner, State, Next), para
un pull request o un resumen de job. `status` siempre sale con 0; `check` y
`merge-check` son las puertas.

### `atipspec audit`

```text
atipspec audit
```

Comprueba todo el repositorio contra las reglas del contrato (dependencies
siempre), la validez de cada spec viva y de cada decisión, el tamaño de los
documentos contra sus topes, los solapes entre entregas abiertas y los
roadmaps de las iniciativas. Falla mientras `.atipspec/framework/` no sea lo
que instala la versión instalada (un fichero cambiado, que falta, o añadido y
no ignorado por git): cada fase imprime al agente esas reglas y esos
workflows, y ninguna aprobación de una entrega los cubre, así que
`atipspec install --update` los restaura. Avisa cuando la aceptación del contrato no está
registrada o está desactualizada, cuando faltan las reglas de permisos de
Claude Code o están incompletas, nombrando las que faltan, y, como `status`,
cuando `origin/HEAD` nombra
una rama de integración que no es main ni master y `teams.json` no declara
ninguna, y señala un `strict_scope: false` o un
`strict_criteria: false` heredado de un proyecto anterior. Sale con 1 si hay
errores.

### `atipspec curate`

```text
atipspec curate
```

Regenera el bloque de índice de `overview.md`, informa de los tamaños de los
documentos contra sus topes e imprime el workflow de curate, que reescribe la
prosa (consulta [curate](../flow/curate.md)).

## Entrega guiada

Los comandos de una entrega en el orden en que los usa el [flujo
guiado](../flow/guided.md). Los comandos de fase (`spec`, `plan`, `build`, y
`explore` y `fix` más abajo) comprueban lo que exige la fase y salen con 1
con una línea que nombra el paso que falta; si no, imprimen `Phase <name>:
<title> (<slug>)`, el status derivado, el workflow de la fase desde
`.atipspec/framework/workflows/`, las reglas compartidas y la salida de
`atipspec context`. `--no-context` deja fuera el contexto, para volver a
entrar en una fase dentro de la misma sesión. Consulta [qué requiere cada
fase](../flow/index.md#que-requiere-cada-fase).

### `atipspec new`

```text
atipspec new SLUG --title TITLE [--capability NAME] [--impact NAME]...
                  [--owner WHO] [--ticket TICKET] [--initiative SLUG]
                  [--depends-on SLUG]... [--kind feature|fix]
                  [--branch | --worktree] [--branch-name NAME] [--reuse-branch]
```

Crea una entrega guiada en `deliveries/SLUG/`: `spec.md` (`schema: 2`,
`status: draft`, `base` con el id completo del commit actual, `created`,
`change_id`, `requirements: []`, `risk: normal`), `plan.md`, `deferred.md` y
`baseline.json`, que registra ese commit. `check` y la propuesta comparan la
spec viva de la capacidad con la que tiene ese commit, así que
`new` se niega mientras `specs/<capability>.md` tenga cambios sin commitear:
descártalos o, para hacerlos en la entrega, apártalos y vuelve a escribirlos
cuando `new` haya terminado; con un commit propio, fuera de una entrega,
`merge-check` los bloquea. El `spec.md` de una funcionalidad tiene `## Intent`, `## Out of scope` y
`## Quality attributes`, las dos últimas con `- None`; sus requisitos van a
`specs/<capability>.md` (consulta [artefactos](artifacts.md#specmd)).
`--capability` nombra esa spec viva y por defecto es el slug; `--impact`
lista otras specs vivas o secciones del contrato que toca. `--kind fix` crea
un fix guiado, la reparación de un defecto: un `spec.md` con un `## Defect`
que rellenar y un `requirements` que debe apuntar al requisito aceptado que
corrige en la spec viva de `--capability`, un plan de una tarea cuyo
`## Final verification` lista los comandos obligatorios del contrato y un
marcador de posición para el del test de regresión, y `atipspec fix` como su
fase (consulta [fix](../flow/fix.md)).

`--owner` nombra a quién pertenece (obligatorio cuando `teams.json` lista
owners para la capacidad). `--ticket` acepta una clave como `PROJ-123`, un
número de issue como `#42` o una URL https, y rechaza cualquier otra cosa
(consulta [tickets](../teams.md#tickets)). `--initiative` registra la entrega
en ese roadmap. `--depends-on` nombra una entrega cuyo recibo aceptado debe
estar en el archivo antes de que la comprobación de esta se ponga en verde.
`--branch` crea `delivery/SLUG` y cambia a ella; `--worktree` crea esa branch
en `../<repo>-SLUG` y escribe la entrega ahí. `--branch-name` usa otro nombre
de branch con cualquiera de los dos, y `--reuse-branch` cambia a esa branch
local existente en vez de crearla; ambos necesitan `--branch` o
`--worktree`, y `--reuse-branch` necesita `--branch-name`.

Con `system` en `config.yaml`, `new` fija el `contract.md` del repositorio
system, y su `glossary.md` cuando lo tiene, en el `contracts.json` de la
entrega, e imprime cada fijación; cuando ese checkout no está disponible,
avisa y nombra el comando `contract-pin` que la propuesta necesitará
entonces. Rechaza un slug existente y el slug `contract`, reservado para
`proposal contract` y `accept contract`.

### `atipspec spec`

```text
atipspec spec SLUG [--no-context]
```

Abre la fase spec: la entrevista, los requisitos y escenarios en la spec viva
y la intención de la entrega. Se niega en un fix (usa `atipspec fix`), y en
una entrega antigua mientras la aceptación del contrato
no esté registrada para su contenido actual. Una entrega guiada no necesita
nada más; `check` avisa mientras el contrato no esté aceptado. Consulta
[spec](../flow/spec.md).

### `atipspec ids`

```text
atipspec ids CAPABILITY [--legacy]
```

Imprime un prefijo de IDs de requisito y de criterio para una entrega, como
`REQ-PRICING-7KQ2M-001` y `AC-PRICING-7KQ2M-001`: un token aleatorio de cinco
caracteres que no usa ningún ID que este checkout pueda ver (la spec viva,
todas las entregas y el archivo, y la spec viva en cada ref que lista
`teams.json`), y pide numerar con él los demás requisitos y criterios de la
entrega, `-002`, `-003`. El asistente lo ejecuta una vez por entrega. Dos
branches que sacaron el mismo token antes de que ninguna se publicara
obtienen IDs duplicados, de los que informa `check`. Los IDs más largos de
versiones anteriores siguen siendo válidos. `--legacy` imprime los siguientes
IDs numéricos a partir del historial local, lo que no es seguro para trabajo
concurrente (consulta [entregas antiguas](legacy.md#ids)).

### `atipspec spec-bind`

```text
atipspec spec-bind SLUG --file PATH
```

Instala requisitos en la spec viva de la entrega guiada,
`specs/<capability>.md`, conservando los demás que haya ahí, lista sus IDs
bajo `requirements` en `spec.md` y lo devuelve a borrador; no aprueba nada.
Un documento con IDs de requisito se vincula tal cual. Uno sin ellos se
importa cuando tiene una sección `Acceptance Criteria`: su título se
convierte en un requisito y cada elemento numerado o con viñeta en uno de sus
criterios, un escenario cuando el elemento tiene pasos `**When**` y
`**Then**`. Los IDs importados son cortos y se derivan de la capacidad y del
título, así que importar de nuevo el mismo documento da los mismos IDs; se
rechaza uno que ya nombra un requisito con otro título en la spec viva. El
original se guarda en `sources/<sha256>.md` de la entrega, listado bajo
`sources` en `spec.md`, y `## Import review notes` en `spec.md` lista lo que
la persona comprueba antes de aprobar. Un documento con cualquier otra forma
se rechaza, sin escribir nada. Una importación nunca deduce una eliminación.
Rechaza las entregas antiguas.

### `atipspec plan`

```text
atipspec plan SLUG [--no-context]
```

Abre la fase plan: enfoque, scope, tareas y verificación final. Una entrega
guiada puede planificar antes de su aprobación, una vez que sus escenarios
están completos sin ningún hallazgo bloqueante de la especificación, su
intención está enunciada, sus secciones de fuera de alcance y de calidad
están decididas (en un fix, su defecto enunciado y los requisitos que
corrige listados) y no hay ninguna pregunta abierta. Una entrega antigua
necesita su spec aceptada para su contenido actual. Consulta
[plan](../flow/plan.md).

### `atipspec proposal`

```text
atipspec proposal SLUG
atipspec proposal contract
```

Presenta lo que aprueba la persona, con su código de aprobación.
`proposal SLUG` muestra el scope, los escenarios, el enfoque, los tests y el
diff de la especificación de una entrega, con su ticket y su enlace; una línea
`Kind: ... · Risk: ...` que dice lo que el nivel de riesgo pide a la puerta;
en un fix, una línea `Corrects:` que dice si cada requisito que lista
es uno aceptado; una línea `Pinned contracts:` con cada contrato fijado desde
otro repositorio (nombre, repositorio, commit y ruta); una línea
`Capability decisions` con las decisiones aceptadas sobre una capacidad que
cargan `context` y el paquete de revisión (se marcan aceptadas en la
conversación, sin código ni registro); el diff de la especificación deja
fuera los requisitos que trajo la branch de integración (consulta [cuando
main avanza](../teams.md#cuando-main-avanza)). En
una entrega antigua, incluido un fix creado antes de 0.3.0, muestra la
aprobación que sigue pendiente (la spec; la spec y el plan juntos como una
sola propuesta cuando una funcionalidad tiene ambos listos; o el plan), o que
no hay ninguna (el plan de un fix antiguo, un plan con
`approve_plan: false` o uno ya aceptado). `proposal contract` muestra el
contrato, sus reglas, los hallazgos de la auditoría y las decisiones cuyo
`affects` nombra `contract`, `contract:<section>` o `*`, o está vacío (una
cuyo Context o Decision sigue como en la plantilla no está lista para
aprobarse), y nombra las aprobaciones de entrega vigentes que registrarlo dejaría
desactualizadas, porque las líneas de status que escribe forman parte de lo
que ellas hashean. El código y el comando `accept` exacto aparecen solo
cuando `accept` registraría ese contenido; si no, la vista lista lo que falta
bajo «Not ready for approval». Debajo, la vista de una entrega dice con qué
rigor se comprueban los criterios (`Criteria check: strict` o
`warnings only`, señalando cuándo `criteria_syntax: free` desactiva la
comprobación de forma), qué necesitan la evidencia y la revisión
(`Evidence check:` con `require_proof` o `risk: high`, y si la revisión debe
venir de una sesión aislada), una línea `Policy changes since the base
commit` con cada policy que `config.yaml` cambia desde la base de la entrega,
y lista los warnings de la spec, del plan (como su tamaño frente a
`max_tasks`) y del contrato (como una aceptación que no está vigente) que el
modelo resuelve o nombra al presentar. Presentar no concede nada; con
`trust: required` no muestra ningún código local.

### `atipspec accept`

```text
atipspec accept SLUG proposal [--code CODE] [--by WHO]
atipspec accept SLUG result [--code CODE] [--by WHO]
atipspec accept SLUG spec [--code CODE] [--by WHO]     legacy deliveries
atipspec accept SLUG plan [--code CODE] [--by WHO]     legacy deliveries
atipspec accept contract [--code CODE] [--by WHO]
```

La persona aprueba en la conversación; después, el asistente ejecuta este
comando con el código del contenido que presentó. El código es `XXXX-XXXX`:
los primeros 40 bits del sha256 del contenido en base32 de Crockford (dígitos
y letras sin I, L, O ni U). Al teclearlo se ignoran las mayúsculas, los
espacios y el guion, y O, I y L se leen como 0, 1 y 1. Cuando el código no
nombra el contenido actual, el comando no registra nada y dice que el
contenido cambió, sin revelar el código actual. Sin una fase para una entrega,
se niega y nombra las formas.

En una terminal interactiva sin marcador de agente en el entorno, el CLI
siempre pide teclear el código en su prompt; cuando además se da `--code`,
ambos deben coincidir. En cualquier otro caso, `--code` es obligatorio. El
registro indica el canal:

| Canal | Cuándo |
| --- | --- |
| `terminal` | el código se tecleó en el prompt del CLI en una terminal interactiva, sin marcador de agente |
| `client-permission` | Claude Code es el único marcador de agente (`CLAUDECODE`, o `AI_AGENT` nombrando a Claude Code), fuera del Agent SDK y de `claude -p` (`CLAUDE_CODE_ENTRYPOINT` no es `sdk-*`), el intérprete recibió la línea de comando con la que coincide su regla ask (el `atipspec accept` instalado o `python -m atipspec accept`), `.claude/settings.json` contiene intactas las reglas de AtipSpec, y ningún hook de `.claude/settings.json` ni de `.claude/settings.local.json` puede contestar la pregunta para Bash, así que Claude Code, en una sesión abierta en la raíz del proyecto, pregunta primero a la persona |
| `assistant` | cualquier otra cosa: un agente sin esas reglas, reglas alteradas, un cliente sin mecanismo de permisos, el marcador de otro agente junto al de Claude Code (Claude Code pasa su marcador a los agentes que inicia), Claude Code ejecutado a través del Agent SDK o de `claude -p`, `python -m atipspec.cli`, `python -m atipspec.__main__` o `python -c`, la CI. Se registra, con un warning |

El canal es lo que declara el propio proceso del comando, no una prueba de
quién aprobó; el CLI solo ve ese proceso:

- `client-permission` dice que las reglas están en este proyecto, no que la
  sesión las cargara ni que el CLI viera a la persona confirmar. Claude Code
  solo las lee en una sesión abierta en la raíz del proyecto, la carpeta que
  contiene `.claude/settings.json`: una sesión abierta en una carpeta padre o
  en otro repositorio que entra en el proyecto con `cd`, como hacen algunas
  sesiones de workflows y de subagentes, no pregunta y aun así registra
  `client-permission`. Lo mismo ocurre con un script o programa que inicia
  Claude Code y que ejecuta él mismo `atipspec accept`, incluido un agente
  que no define ninguno de los marcadores, aunque la regla de Claude Code
  solo preguntó por el script. Tras registrarlo, `accept` imprime una nota
  con la raíz.
- `terminal` dice que el código se tecleó en un terminal sin marcadores de
  agente. Un agente puede quitar sus marcadores y contestar al prompt desde
  un pseudo-terminal que él crea, así que este canal no es más fuerte que los
  otros.
- Un registro escrito a mano en `approvals/` se lee igual que uno que
  escribió el CLI.

Los marcadores de agente (`CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`,
`COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT`) solo bajan el canal.
Solo una policy de confianza externa (`trust: required`) autentica quién
aprobó.

Qué hace cada forma:

- `proposal` valida escenarios, plan, contrato, base y coordinación, y
  rechaza las preguntas abiertas; pone `status: ready` y escribe
  `approvals/local-proposal.json` (en las entregas antiguas, también
  `local-spec.json` y `local-plan.json`, con el código de una vista que
  presentó la propuesta, no solo la spec o solo el plan).
- `result` exige una comprobación local en verde y ninguna policy de
  confianza, y escribe `approvals/local-result.json`; `deliver` lo exige sin
  una policy.
- `spec` se niega en las entregas guiadas, y mientras un requisito no tenga
  criterio o haya una pregunta abierta; si no, pone `status: ready` y
  registra el hash de `spec.md` y del contrato.
- `plan` se niega en las entregas guiadas; exige una spec aceptada y un plan
  sin errores, y registra el hash de la spec, el plan y el contrato.
- `contract` valida las reglas, pone `status: accepted` en `contract.md` y en
  cada decisión que listó `proposal contract`, y escribe
  `.atipspec/approvals/contract.json` con sus hashes. Las aprobaciones de
  entrega que hashearon las líneas de status anteriores quedan
  desactualizadas; las nombra.

Con `trust: required` en `config.yaml`, todas las formas salvo `contract` se
niegan: la aceptación local está desactivada y los aprobadores firman con
`atipspec approve`.

`--by` es una etiqueta declarada que por defecto es el `user.email` de git;
el asistente solo la pasa con el nombre que dio el usuario. Los registros
guardan el hash y su `subject_version`, el digest de cada parte, el código,
quién, cuándo, el commit y el canal.

`check` compara el hash registrado con los ficheros: después de cualquier
edición, la entrega vuelve a ser un borrador (o el plan queda sin aceptar),
con un todo que nombra los ficheros, o los requisitos de la spec viva, que
cambiaron, hasta que la persona aprueba el contenido cambiado y se registra
de nuevo. Traer la branch de integración no es una edición de ese tipo
(consulta [cuando main avanza](../teams.md#cuando-main-avanza)). Con una
policy de confianza mandan las aprobaciones firmadas y estos registros se
ignoran. `approval-subject` imprime el digest que firman los modos de
confianza; no es un código de aprobación local.

### `atipspec build`

```text
atipspec build SLUG [--no-context]
```

Abre la fase build y nombra la siguiente tarea: la primera que no está
registrada con `task-done` (o, en una entrega antigua, sin marcador de
commit), o indica que todas las tareas están completas. Una entrega guiada
necesita su propuesta aceptada para su contenido actual; una antigua, un plan
con tareas, aceptado cuando `approve_plan` está activado. Se niega mientras
el plan, la spec, la base, la definición del contrato o la coordinación con
otras entregas tengan un error o un paso pendiente; un fichero que incumple
una regla del contrato es lo que arregla el build, así que no se niega por
eso. Consulta [build](../flow/build.md).

### `atipspec task-done`

```text
atipspec task-done SLUG TASK --note TEXT
```

Registra que una tarea del plan está implementada, con la nota: qué cambió.
Escribe `progress.json` en la carpeta de la entrega, con la hora, el hash del
acuerdo aprobado y el de la tarea sin su título, e imprime la siguiente
acción. Se niega antes de la aprobación, o mientras el plan, la spec, la
definición del contrato, la base o la coordinación tengan un error, ante una
tarea desconocida y ante una nota vacía. Un registro es avance, no
verificación: `verify` y la revisión comprueban el trabajo. Sigue siendo
válido mientras el acuerdo aprobado y la tarea, salvo su título, no cambien.
No hace falta ningún commit.

### `atipspec verify`

```text
atipspec verify SLUG [--task Tn]... [--timeout SECONDS]
                [--policy PATH] [--policy-sha256 HASH] [--number N]
```

Ejecuta, desde la raíz del proyecto y a través del shell, los comandos de
`## Final verification` del plan una vez para el candidato terminado o, en un
plan sin esa sección, los comandos de Verify de cada tarea; `--task` ejecuta
solo los comandos propios de las tareas nombradas, una comprobación de
desarrollo. Imprime el final de la salida de cada comando y escribe
`evidence/<task or FINAL>-<time>.json` con los comandos, los códigos de
salida, los logs de salida completos y la huella del árbol de trabajo.
`--timeout` limita cada comando (por defecto, 1800 segundos). Sale con 1
cuando un comando falla o los comandos cambiaron el árbol, lo que deja esa
evidencia obsoleta de inmediato. Requiere git. Sin una policy no necesita
ninguna aprobación; ejecútalo sobre el candidato terminado, después de la
aprobación de la propuesta.

Con un `Report:`, la ruta debe ser una que git ignore, como
`.atipspec/tmp/junit.xml`. `verify` borra ese fichero antes de que se
ejecuten los comandos y lo lee después: un informe ausente
(`test report not found`) o modificado antes del borrado
(`predates this verification`, con dos segundos de tolerancia) hace fallar
la evidencia, igual que un test fallido dentro de él. La evidencia registra
la copia del informe con `fresh: true`.

Con `--policy` (o `ATIPSPEC_TRUST_POLICY`), exige primero la spec lista y sus
aprobaciones de confianza de spec y plan, y lo ejecuta el productor protegido
(consulta [aceptación de confianza](#aceptacion-de-confianza)).

### `atipspec review`

```text
atipspec review SLUG [--out FILE]
```

Se niega, sin escribir nada, mientras una tarea no esté completa, la
evidencia falte o esté obsoleta, o el contrato esté violado. Si no, cuenta la
revisión y escribe el paquete del revisor en
`.atipspec/tmp/SLUG-review-packet.md` (o en `--out`): la rúbrica, el
contrato, las specs vivas de la lista de impact, las decisiones aceptadas que
las afectan, la spec, el plan, deferred, el resumen de la evidencia, los
ficheros fuera del `scope` del plan, el diff contra la base (limitado a
200 KB, con `--stat` cuando se trunca) y los ficheros sin seguimiento; luego
imprime `review N of M` y el workflow de review. Se cuenta una revisión cada
vez que el paquete es para un candidato distinto del del paquete anterior,
contando la primera, diga lo que diga `review.md`: una revisión que pasó
también cuenta, porque el CLI no puede distinguir los veredictos de un revisor
de unos editados después. Cuando se han contado `review_rounds` revisiones para el
acuerdo aprobado actual y el candidato vuelve a cambiar, se niega, sin contar
nada, y pide presentar `atipspec check SLUG` al usuario: cambiar la
propuesta, subir `review_rounds` o parar; hasta entonces, `check` lo informa
como un error. Un paquete que no se puede construir no cuenta nada. `check`
solo toma la revisión del último paquete contado: un `review.md` escrito sin
ejecutar `review` lo espera. La cuenta está en `review-rounds.json`, que
escribe el CLI desde `accept <slug> proposal`; sin él, `review` se niega en
una entrega guiada creada desde 0.3.0, vuelve a contar a partir del
`review.md` de la carpeta, como primera revisión, en una aprobada bajo una
policy de confianza, y empieza en el paquete siguiente en una creada antes de
0.3.0, cuyo `review.md` nombra un árbol de la huella anterior. El diff
muestra el contenido almacenado: sin filtro textconv, y
un fichero de texto que un atributo local marca como binario, o texto UTF-8
con un byte NUL, se muestra como texto, cada NUL como `␀`; un byte que no es
UTF-8 se muestra como `�`. Un revisor en una sesión aislada lee el paquete y
escribe `review.md` (consulta [review](../flow/review.md)).

### `atipspec check`

```text
atipspec check SLUG [--json] [--policy PATH] [--policy-sha256 HASH] [--number N]
```

La puerta. Sale con 0 en verde, 1 con errores, 2 incompleta. Consulta [cómo
funciona](../getting-started/how-it-works.md#la-puerta) para los niveles.
Imprime el status derivado, cada hallazgo y la siguiente acción; `--json`
imprime el mismo informe como datos. Falla de forma cerrada: sin git es un
error (el commit base, las reglas del contrato y la frescura de la evidencia
vienen de git), y con `trust: required` y sin policy también es un error, igual
que un `.atipspec/framework/` que no es lo que instala la versión instalada
(consulta [`audit`](#atipspec-audit)), que bloquea la propuesta, las tareas,
el build y la revisión hasta `atipspec install --update`.
Nunca ejecuta los tests: juzga la evidencia que escribió `verify` y la
revisión que escribió el revisor. Un veredicto PASS necesita un puntero que
pueda resolver, y `review.md` necesita `reviewer:` y declara su `session:`
(consulta [review](../flow/review.md#que-comprueba-la-puerta-en-reviewmd)). El
nivel de `risk` en el `spec.md` de una entrega cambia lo que pide (consulta
[riesgo](../flow/spec.md#riesgo)). Muestra el lead time de la entrega, desde
su creación hasta la aceptación de su resultado, y avisa, sin bloquear,
cuando supera `max_age_hours`. En una entrega guiada en draft lista además
lo que aún le falta a la propuesta en el plan y en el contrato, y sus
warnings; cuando no falta nada, su único todo es presentar la propuesta para
su aprobación. Sin una policy, el verde es `checked`, y
`accepted` una vez registrada la aceptación del resultado actual; con
`--policy`, el verde de la puerta de confianza es `verified`.

### `atipspec report`

```text
atipspec report SLUG [--format json|markdown|html] [--out FILE]
                [--policy PATH] [--policy-sha256 HASH] [--number N]
```

El dosier de aceptación que presenta el asistente para la aceptación del
resultado: el status, el código de aprobación del resultado mientras la
entrega está `checked` y no hay ninguna policy definida, el tipo, el riesgo y
el lead time, la matriz de trazabilidad con cada veredicto y aquello a lo que
se resolvió su puntero, el revisor y la sesión de la revisión (con un warning
cuando es compartida), `Revisión N de M` una vez que `atipspec review` ha
contado una revisión, las aprobaciones, las comprobaciones, la evidencia y
los cambios desde el commit base: cada fichero cambiado salvo la carpeta de
la propia entrega, con su status, las líneas añadidas y eliminadas y si queda
fuera del `scope` del plan, y el diff de esos ficheros, `config.yaml`, el
contrato y las decisiones incluidos, tal como están almacenados, igual que el
del paquete. Compara la base con el árbol candidato al que están atadas la
evidencia, la revisión y la aceptación del resultado, ficheros sin
seguimiento incluidos. Un fichero listado como `binary` no tiene texto en el
diff, y el dosier nombra los ficheros binarios que el candidato añade o
cambia: inspecciónalos en el repositorio antes de aceptar. También nombra,
como el paquete de revisión, los ficheros cambiados que configuran cómo se
ejecutan los tests y cómo informan (`conftest.py`, `pytest.ini`,
`pyproject.toml`, `package.json`, `jest.config.*` y similares), cuyo cambio
puede alterar lo que dice la evidencia. Los formatos JSON
y HTML conservan hasta 200 KB de diff, y markdown (el valor por defecto),
hasta 50 KB; un diff más largo se corta, con su tamaño completo, su sha256 y
la base desde la que inspeccionar el resto. El recibo archivado conserva los
ficheros y el tamaño y el sha256 del diff, no su texto. `--out` escribe fuera
del repositorio, bajo `.atipspec/tmp/` o en `reports/` de la entrega, así que
una exportación no cambia nada de lo que ata la aceptación. El informe de una
entrega archivada lee su recibo. Con `--policy`, muestra las aprobaciones de
confianza que firma QA.

### `atipspec deliver`

```text
atipspec deliver SLUG [--policy PATH] [--policy-sha256 HASH] [--number N]
```

Exige una comprobación en verde y la aceptación por la persona del resultado
actual: sin una policy, el registro que escribe `accept SLUG result`; con
una, una comprobación de confianza en verde con evidencia y aprobaciones
autenticadas. Fusiona los requisitos en la spec viva de la capacidad por ID,
escribe el recibo `reports/acceptance.json` con `code_tree`, el hash de todo
lo que hay fuera de `.atipspec/`, `living_spec`, el digest de la spec viva
que escribió, y `living_requirements`, el texto de cada requisito que lista
tal como lo escribió ahí, pone `status: delivered`, mueve la carpeta a
`archive/` y nombra `merge-check` como el paso previo al merge. No hace
commit, push ni merge.

### `atipspec merge-check`

```text
atipspec merge-check --base REF [--format text|markdown] [--policy PATH] [--policy-sha256 HASH] [--number N]
```

La puerta de una branch antes de su merge en `REF` (una branch o un commit,
como `origin/main`), que ejecutan el asistente antes de pedir el merge y el
job de CI del pull request. Encuentra las entregas que cambia la branch desde
su base de merge con `REF`, en las carpetas de `deliveries/` y `archive/`
cuyo nombre es un slug, lista cada una con su estado y su ticket (una tabla
en Markdown, con el enlace del ticket) y bloquea cuando:

- una entrega abierta no está `accepted` (en local) o `verified` (con una
  policy);
- una entrega archivada en la branch tiene un recibo sin un resultado
  aceptado o sin `code_tree` (entregada antes de 0.3.0), o su `code_tree`
  difiere del código del head: cualquier cambio fuera de `.atipspec/` después
  de `deliver`, incluido tomar la branch de destino (merge o rebase). Nombra
  los ficheros cambiados cuando el árbol aceptado o el commit de archivo están
  disponibles, y dice cómo seguir: reabrir la entrega revirtiendo el commit que
  la archivó, y volver a verificarla, revisarla, aceptarla y entregarla
  (revertir los ficheros solo sirve para un cambio de la propia branch), y
  tomar la branch de destino antes de `deliver` la próxima vez. En local también bloquea un recibo que
  cambió después del commit que lo archivó; uno eliminado y añadido de nuevo,
  salvo que el commit anterior tenga la entrega abierta, como tras revertir
  el commit de archivo para reabrirla, o que un archivo anterior añadiera ese
  mismo recibo; y uno cuyo `code_tree` no tiene ni el commit de archivo ni el
  anterior. Así, reescribir `code_tree` tras un cambio del código se ve, pero
  un recibo no está autenticado: una historia reescrita de forma coherente, o
  una reapertura hecha a mano (su carpeta de `archive/` eliminada y la entrega
  restaurada en un commit, y luego archivada de nuevo con un recibo escrito a
  mano), sigue pasando; solo una policy de confianza vuelve a comprobar la entrega;
- la branch cambia o elimina una entrega archivada antes que ella;
- la branch cambia una spec viva de `specs/` de otra forma que no sea a
  través de `deliver` (el `living_spec` del recibo; con una policy, lo que
  `deliver` escribe a partir del commit desde el que se entregó) o la
  propuesta aprobada de una entrega guiada abierta. También compara cada
  requisito: el head lo contiene tal como lo tenía la base del merge, tal
  como lo escribió la última entrega archivada en la branch que lo lista (el
  texto que registra el `living_requirements` de su recibo, tal como lo
  añadió el commit que la archivó; con una policy, lo que `deliver` escribe a
  partir del commit desde el que se entregó, y solo de una entrega que la
  policy autentica), o tal como lo lista una entrega
  guiada abierta, así que un recibo no respalda un requisito que su entrega
  no listó, ni una edición posterior de uno que sí listó, ni una edición
  posterior del recibo;
- un fix guiado archivado en la branch, o abierto en ella, lista un
  requisito que la spec viva no contenía en la base del merge y que ninguna
  entrega anterior de la branch escribió: un fix corrige un requisito
  aceptado;
- la branch cambia el contrato, o una decisión que lo afecta, y la
  aceptación del contrato no está vigente; con una policy, la branch cambia
  `contract.md` o una decisión así fuera de una entrega comprobada bajo la
  policy (`contract.md` con una nueva decisión que afecta al contrato,
  aprobada por ingeniería), o acepta un contrato en borrador con el que no se
  comprobó ninguna entrega así;
- la branch cambia un fichero fuera de `.atipspec/` que no cubre ninguna
  entrega que archiva o deja abierta y que `exempt_paths` no cubre. Una
  entrega cubre los ficheros que muestra su dosier: los que cambiaron entre su
  commit base y el head, y los que cambió la branch de integración y la branch
  tiene de otra forma, también devueltos a como los tenía la base (consulta
  [cuando main avanza](../teams.md#cuando-main-avanza)), salvo los que la
  branch ya había cambiado antes de esa base. El dosier de una entrega
  abierta es el del head, que liga la aceptación de su resultado: cuando la
  entrega devuelve lo que cambió la branch de integración, esa aceptación
  nombra la base del merge, así que volver a integrar la branch la anula. El
  de una entrega archivada es el que tenía al entregarse, tal como lo lista su
  recibo (con una policy, tal como estaba en el commit desde el que se
  entregó), menos los ficheros que la branch de destino cambió después del
  commit que la archivó, cuyo cambio la branch deshace. El código commiteado
  antes de `atipspec new`, o cambiado en un fichero que la entrega vuelve a
  cambiar,
  queda fuera, igual que un cambio de una branch de destino que no es la de
  integración, o de cualquier branch sin ref de integración, que la branch
  devuelve a como lo tenía la base, y todo código de una branch que no toca
  ninguna entrega o solo elimina alguna. Una entrega archivada en la branch
  cuyo commit base no está en la historia de `HEAD`, como en un clon
  superficial o tras un squash o un rebase de la branch, también bloquea: sin
  él, `merge-check` no puede saber qué ficheros cubre la entrega, y dice que
  no buscó código fuera de las entregas.
  `exempt_paths`, una lista de globs, se lee del `config.yaml` de `REF`,
  nunca de la branch, así que una branch no puede eximir sus propios cambios:
  la persona decide qué ficheros no necesitan entrega y añade los globs antes
  en la branch de destino. No cuentan los ficheros del cliente que solo
  contienen lo que instala AtipSpec, como una skill de esta versión o un
  `.claude/settings.json` al que solo se le añadieron sus reglas;
- el árbol de trabajo difiere de `HEAD`: juzga el head con commit;
- `.atipspec/framework/` no es lo que instala la versión de AtipSpec que
  ejecuta `merge-check` (consulta [`audit`](#atipspec-audit));
- `.atipspec/` no está en la raíz del repositorio git;
- `trust: required` está definido en el head, en `REF` o en la base del
  merge y no se da ninguna policy. Con una policy, con o sin
  `trust: required`, un recibo aceptado localmente bloquea, igual que uno de
  confianza cuya entrega no vuelve a superar su comprobación de confianza: en
  el commit anterior al commit de archivo, obtenido en un clon temporal con
  las refs del repositorio y con la evidencia, la revisión, los términos del
  aplazamiento y las aprobaciones archivadas con ella, la comprobación debe
  ser `verified` (aprobaciones y evidencia atestada; en modo provider, las
  revisiones del pull request sobre ese commit, o sobre el head con las
  mismas líneas de marcador, leídas con `--number`), y ese commit debe
  contener el código del head. Haz el commit del archivo por separado justo
  después de `deliver`.

La línea de cada entrega entregada o aceptada nombra el canal que declaró
`accept` para cada aprobación local: cómo se ejecutó el comando, no quién
aprobó. Una branch que no toca ninguna entrega está lista salvo que cambie una
spec viva, el contrato o un fichero fuera de `.atipspec/` que `exempt_paths`
no cubre; el resultado lista los ficheros que dejó pasar `exempt_paths`, y
avisa cuando la branch cambia `exempt_paths`, que ninguna aprobación hashea.
También avisa, sin bloquear, cuando la branch relaja respecto a `REF` una
política de `config.yaml` entre `strict_scope`, `strict_criteria`,
`criteria_syntax`, `review_rounds`, `max_tasks`, `max_requirements`,
`max_age_hours`, `require_proof`, `require_isolated_review` y `trust`, listada como la propuesta lista sus
cambios de políticas, por ejemplo `review_rounds 3 → 99`, porque toda entrega
que empiece tras el merge las toma y ninguna propuesta las lista; y cuando
añade, cambia o quita `overview.md`, `glossary.md` o una decisión, nombrada
con el estado de cada decisión, porque el agente las lee como contexto en
cada fase y ninguna aprobación de una entrega las cubre; y cuando cambia
`adapter.json`, que nombra el programa que ejecuta `atipspec run` y si sus
revisiones cuentan como aisladas, o `teams.json`. Cuando la branch
cambia el contrato o una decisión que lo afecta, el resultado muestra la
aceptación del contrato con el canal que declaró `accept contract`.
No ejecuta ningún comando del candidato, solo git y
lecturas de ficheros, así que un job de pull request lo ejecuta sin
credenciales. `--format markdown` imprime el resultado para un resumen de job
de CI. Sale con 0 si está lista y con 1 si está bloqueada. Los ejemplos de CI
de `enterprise-init` lo ejecutan (consulta
[aceptación empresarial](../enterprise.md#ci-antes-del-merge)).

### `atipspec ship`

```text
atipspec ship SLUG
```

La guía del modo ship: nombra la siguiente fase en la que puede entrar la
entrega, por qué, el punto de parada que sigue (la aprobación de la
propuesta, o la de la spec en una entrega antigua, antes de construir; la
aceptación del resultado antes de `deliver`) y el comando que hay que
ejecutar. La fase que nombra siempre cumple sus propios prerrequisitos.
Consulta [modo ship](../flow/index.md#modo-ship).

### `atipspec context`

```text
atipspec context SLUG [--out FILE] [--summary]
                 [--role guide|analyst|designer|tester|implementer|reviewer] [--task Tn]
```

Imprime el material de la entrega con un resumen de tamaño contra
`context_budget`: el contrato, el overview, el glosario, las specs vivas de
la lista de impact, las decisiones aceptadas que las afectan y los propios
ficheros de la entrega, nunca el archivo. `--out` lo escribe en un fichero;
`--summary` imprime solo los tamaños. `--role` añade la instrucción de ese
rol, ajustada al `risk` de la entrega, tal como la envía el runner; `--task`
limita el material a esa tarea y a los requisitos que cubre. Los comandos de
fase imprimen su salida.

## Otras entregas

### `atipspec explore`

```text
atipspec explore SLUG [--no-context]
```

Abre la fase explore para una entrega que existe: el modelo escribe un
`brief.md` de una página con el problema, lo que existe, las opciones y una
recomendación, y se detiene. Consulta [explore](../flow/explore.md).

### `atipspec fix`

```text
atipspec fix SLUG [--no-context]
```

Abre la fase fix de una entrega creada con `--kind fix`: reproducir el
defecto, corregir el requisito aceptado que rompe con un criterio de
regresión, planificar una tarea y presentar la propuesta. Se niega en una
entrega que no es un fix, y en un fix creado antes de 0.3.0 mientras la
aceptación del contrato no esté registrada para su contenido actual.
Consulta [fix](../flow/fix.md).

### `atipspec migrate`

```text
atipspec migrate SLUG [--apply]
```

Muestra, como un diff, cómo una entrega antigua se convierte en una guiada, y
no escribe nada: sus requisitos pasan a `specs/<capability>.md`, `spec.md`
los lista bajo `requirements` sin su encabezado vacío `## Requirements`, y
recibe `schema: 2`, `status: draft` y un `baseline.json` nuevo. `--apply` lo
escribe después de hacer una copia de seguridad de los originales y de los
registros de aprobación en `.atipspec/migrations/<digest>/`. No es una
aprobación: la entrega vuelve a borrador y necesita que se apruebe su
propuesta. Un fix antiguo mantiene su flujo hasta que se entrega:
`migrate` lo rechaza. Consulta [entregas antiguas](legacy.md).

## Contrato y decisiones

### `atipspec contract`

```text
atipspec contract
```

Abre la fase contract: imprime el workflow, las reglas y el `contract.md`
actual. Nunca se niega. Después, el asistente presenta `atipspec proposal
contract` y registra tu aprobación con
`atipspec accept contract --code <code>`. Consulta
[contract](../flow/contract.md).

### `atipspec decision`

```text
atipspec decision SLUG --title TITLE [--affects NAME]...
```

Crea `decisions/DEC-nnn-SLUG.md` con status `proposed`. `--affects` acepta
nombres de capacidad, `contract`, `contract:<section>` o `*`; sin él, la
decisión lo afecta todo. Una decisión que afecta al contrato o a todo se
acepta con el contrato: `atipspec accept contract` fija su status; nunca lo
edites a mano.

### `atipspec initiative`

```text
atipspec initiative SLUG --title TITLE
```

Crea `initiatives/SLUG/roadmap.md`; `new --initiative SLUG` lista una entrega
en él.

## Automatización

### `atipspec run`

```text
atipspec run SLUG [--resume] [--retry-interrupted] [--budget SECONDS] [--timeout SECONDS] [--max-rounds N]
```

Ejecuta una entrega guiada aprobada a través del adaptador de proceso
configurado e imprime su estado como JSON; consulta [el adaptador de
ejecución](execution-adapter.md). Necesita la propuesta aceptada para su
contenido actual; si no, registra `awaiting_approval` y se detiene; nunca
acepta nada. `--budget` limita los segundos transcurridos para esta versión
aprobada (por defecto, 900), y `--timeout`, cada llamada al adaptador o cada
comando de verificación (por defecto, 300). `--max-rounds` limita las
correcciones automáticas; por defecto vale `review_rounds` de `config.yaml`
menos uno, porque cada corrección se vuelve a revisar, y no puede superarlo.
Las revisiones que pide el runner cuentan igual que en `atipspec review`, y se detiene en `needs_decision` cuando
se agotan. `--resume` continúa después de que resolvieras una decisión o un
fallo informados; `--retry-interrupted` reintenta después de que
inspeccionaras una mutación interrumpida de un agente. Sale con 0 cuando el
estado es `ready_for_acceptance` o `accepted`, y con 2 en cualquier otro
estado. Rechaza las entregas antiguas, y se niega con una policy de
confianza, tanto seleccionada como obligatoria. El runner necesita un
sistema POSIX (Linux, macOS o WSL) para su bloqueo del checkout; en otros
sistemas se niega antes de leer la entrega o de escribir nada, y la entrega
continúa en la conversación guiada, que tiene las mismas fases y la misma
puerta.

### `atipspec adapter`

```text
atipspec adapter
```

Imprime, como JSON, lo que declara el adaptador de `.atipspec/adapter.json` y
lo que proporciona el runner: si la revisión se ejecuta aislada, los
checkpoints, que no es un servicio en segundo plano y que las métricas de
tokens y de coste no están disponibles. Se niega cuando no hay ningún
adaptador configurado.

## Equipos

### `atipspec team`

```text
atipspec team [--fetch] [--json]
```

El tablero: todas las entregas abiertas del checkout de trabajo y de cada ref
que lista `teams.json` (un `*` al final toma todas las refs que coinciden),
con su status, owner, ticket, ref, capacidad, requisitos y dependencias. Solo
lee refs locales; su primera línea dice cuándo hizo fetch el repositorio por
última vez. `--fetch` primero hace fetch de cada remoto que nombra una
entrada `refs/remotes/<remote>/...`, sin pedir credenciales (git y ssh se
ejecutan sin terminal ni programa askpass); un remoto que falla recibe un
warning y el tablero muestra lo último que se obtuvo de él. `--json` imprime
el tablero como datos, con el `ticket_url` de cada ticket. Consulta [el
tablero](../teams.md#el-tablero-atipspec-team).

### `atipspec contract-pin`

```text
atipspec contract-pin SLUG NAME --repository NAME --ref REV --path PATH
```

Fija el fichero `PATH` del checkout de otro repositorio, nombrado en
`repositories` de `teams.json` (`system` toma por defecto el `system` de
`config.yaml`), en el commit al que se resuelve `REV`, en el `contracts.json`
de la entrega bajo `NAME` con su digest, e imprime ese commit. El contexto de
la entrega lee el fichero desde ese commit; `check` rechaza una fijación que
nombra una branch o un tag, o cuyo contenido difiere de su digest.
`contracts.json` forma parte de lo que hashea la aprobación de la propuesta,
así que volver a fijar la anula. Consulta [varios
repositorios](../teams.md#varios-repositorios).

## Aceptación de confianza

Estos comandos sirven a una policy de confianza externa (consulta [aceptación
empresarial](../enterprise.md)). Los ejecutan personas con claves inscritas,
un worker de CI protegido y un recolector; el asistente nunca firma. `check`,
`verify`, `report`, `deliver` y `merge-check` toman la policy con:

- `--policy PATH`: la policy de confianza TOML de la organización, fuera del
  repositorio candidato (o `ATIPSPEC_TRUST_POLICY`);
- `--policy-sha256 HASH`: el digest que debe tener la policy, fijado en la
  configuración protegida (o `ATIPSPEC_POLICY_SHA256`);
- `--number N`: el pull request, para una policy en modo provider (o
  `ATIPSPEC_PR_NUMBER`).

Con una policy, `check` exige las aprobaciones firmadas y la evidencia
atestada, y su verde es `verified`; `verify` exige las aprobaciones de spec y
plan antes de ejecutarse; `deliver` exige la puerta de confianza en verde; y
los registros locales de `accept` se ignoran. Con `trust: required` en
`config.yaml`, `check`, `accept` (salvo `accept contract`), `deliver` y `run`
se niegan a funcionar sin una. Nunca derives estos valores de documentos
candidatos.

### `atipspec enterprise-init`

```text
atipspec enterprise-init [--out DIRECTORY]
```

Escribe los ejemplos de policy de confianza (`policy.example.toml` para el
modo ssh, `policy.provider.example.toml` para el modo provider), los jobs de
CI que ejecutan `merge-check` (`github-local.yml`, `gitlab-local.yml`), los
workflows de evidencia del modo provider (`github-evidence-trusted.yml`,
`github-evidence-caller.yml`), un script de aceptación protegido y
`ADOPTION.md` en `DIRECTORY` (por defecto, `.atipspec/enterprise`). No activa
nada, y se niega cuando los ficheros ya existen ahí.

### `atipspec approval-subject`

```text
atipspec approval-subject SLUG PHASE
```

Imprime el marcador que un aprobador pone en la revisión de un pull request,
`ATIPSPEC-APPROVE <slug> <phase> <subject> <head>`: el digest del contenido
de la fase y el commit del head. Lee la policy de `ATIPSPEC_TRUST_POLICY`. No
es un código de aprobación local.

### `atipspec approve`

```text
atipspec approve SLUG PHASE --identity ID --key PATH --policy PATH
                 [--policy-sha256 HASH] [--expires TIME] [--owner ID]
```

Firma una aprobación humana desde una identidad inscrita, en la máquina de
confianza de esa persona. `PHASE` es `spec`, `plan`, `acceptance`,
`decision:DEC-nnn` o `exception:Fn`. `--key` es la clave privada, fuera del
repositorio. Las excepciones exigen `--expires` con una marca de tiempo ISO
futura y con zona horaria. La aprobación de la spec confirma el owner de la
entrega: `--owner` debe ser el `owner` que declara `spec.md`, y se firma con
él; es obligatorio para `spec` y se rechaza en todas las demás fases. Ese
owner no puede aprobar las fases posteriores, y una aprobación de spec que no
confirma ningún owner, o que confirma otro, no cuenta; una firmada antes de
0.3.0 se vuelve a firmar con `--owner`. `approve` rechaza un owner que no
esté escrito con letras ASCII, dígitos, `_`, `.`, `@` y `-`, como las
identidades.

### `atipspec sync-approvals`

```text
atipspec sync-approvals SLUG PHASE --number N --identity ID --key PATH --policy PATH
                        [--policy-sha256 HASH] [--expires TIME]
```

Recolecta las aprobaciones humanas del pull request o merge request `N` que
llevan el marcador `approval-subject` de la fase, en modo de solo lectura a
través de la API de GitHub o de GitLab, y firma el registro normalizado con
la identidad de recolector inscrita. Una fase `exception:Fn` necesita
`--expires` con una marca de tiempo futura. La puerta vuelve a leer el
proveedor en cada ejecución, así que una revisión revocada falla.

### `atipspec attest`

```text
atipspec attest SLUG --identity ID --key PATH --run-url URL --policy PATH [--policy-sha256 HASH]
```

El recolector protegido firma la evidencia de cada tarea, el registro de
`evidence/` que terminó el último, con la URL de la ejecución de CI. No
autentica esa ejecución: el orquestador verifica el productor, el head y el
artefacto antes de llamarlo, y primero borra la evidencia que la branch
incluyó en commits (`atipspec.verify.clear_evidence`). Rechaza la evidencia
cuyo informe de tests no tiene la marca `fresh`.

## Pilotos

### `atipspec pilot`

```text
atipspec pilot init NAME
atipspec pilot record NAME --delivery SLUG --cohort baseline|atipspec --source SOURCE --collector WHO
                      [--lead-hours H] --human-review-minutes M --rework-minutes M
                      --escaped-defects N --criteria-total N --criteria-tested N --observation-days N
atipspec pilot report NAME
```

`pilot init` crea un protocolo de evaluación real vacío en
`.atipspec/pilots/NAME/`. `pilot record` añade una observación completa y con
fuente; los valores desconocidos no se introducen como cero. Para la cohorte
`atipspec`, `--lead-hours` puede omitirse: se lee del recibo archivado de la
entrega, o de los registros archivados con ella, y la observación lo indica
en `lead_hours_origin`; nunca se estima. La cohorte `baseline` lo necesita
medido. `pilot report` compara las cohortes registradas, con tamaños de
muestra, medianas y limitaciones, y señala las ventanas de observación
desiguales.

## Códigos de salida

| Código | Significado |
| --- | --- |
| 0 | hecho; para `check`, verde; para `merge-check`, lista; para `run`, `ready_for_acceptance` o `accepted` |
| 1 | error; para `check` y `audit`, rojo; para `merge-check`, bloqueada; para `verify`, un comando falló o cambió el árbol |
| 2 | `check`: incompleta, queda trabajo; `run`: cualquier estado salvo `ready_for_acceptance` y `accepted` |
| 130 | cancelado desde el teclado |

## Entorno

| Variable | Efecto |
| --- | --- |
| `ATIPSPEC_TRUST_POLICY` | selecciona la policy de confianza externa para todos los comandos, igual que `--policy` |
| `ATIPSPEC_POLICY_SHA256` | el digest que debe tener la policy, como `--policy-sha256` |
| `ATIPSPEC_PR_NUMBER` | el pull request en modo provider, como `--number` |
| `GITHUB_TOKEN`, `GITLAB_TOKEN` | tokens de solo lectura para los adaptadores de proveedor en el worker protegido; `verify` los elimina de los comandos que ejecuta, junto con todas las variables `ATIPSPEC_`, `SSH_AUTH_SOCK`, `GIT_ASKPASS`, los tokens de los jobs de CI (`CI_JOB_TOKEN`, `ACTIONS_RUNTIME_TOKEN`) y el token de solicitud OIDC (`ACTIONS_ID_TOKEN_REQUEST_TOKEN`) |
| `NO_COLOR`, `TERM=dumb` | desactivan los colores en la salida de la terminal |
| marcadores de agente y `CLAUDE_CODE_ENTRYPOINT` | deciden el canal que registra `accept`; consulta [entorno](configuration.md#entorno) |

Define las variables de confianza en la configuración protegida de la
organización, nunca a partir de valores que proporcione el repositorio
candidato.
