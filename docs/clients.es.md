# Clientes

AtipSpec se ejecuta dentro del cliente de programación que ya usas. `atipspec init`
instala los mismos skills donde cada cliente los descubre; el CLI es el mismo en
todas partes. Lo que cambia es cómo invocas un skill y cómo el revisor obtiene una
sesión aislada.

## Un skill por fase

Cada fase tiene su propio skill, con el nombre de la fase, más un skill paraguas
para el estado y las preguntas sobre el flujo:

| Skill | Qué hace |
| --- | --- |
| `atipspec-contract` | definir o cambiar el contrato de arquitectura |
| `atipspec-explore` | redactar el brief de una idea que aún no está clara |
| `atipspec-spec` | la entrevista y los escenarios en la spec viva; con el plan, la propuesta que apruebas en el punto de parada 1 |
| `atipspec-fix` | un defecto: el requisito aceptado que rompe, corregido con un criterio de regresión, y un plan de una tarea, sin entrevista |
| `atipspec-plan` | enfoque, alcance, tareas y pruebas, presentados con la propuesta |
| `atipspec-build` | código y tests, cada tarea registrada con `task-done`, y luego la verificación final |
| `atipspec-review` | la revisión adversarial en una sesión aislada |
| `atipspec-deliver` | el resultado para tu aceptación en el punto de parada 2, y luego el archivado en la spec viva |
| `atipspec-curate` | mantener pequeño el contexto del proyecto |
| `atipspec-ship` | ejecutar las fases restantes, deteniéndose solo donde se detiene el CLI |
| `atipspec` | estado, ayuda y qué fase sigue |

El skill de una fase son pocas líneas: ejecuta el comando de la fase, haz lo que
imprime y detente si se niega. El CLI decide si la fase puede empezar, así que la
fase activa nunca es la interpretación que el modelo hace de tu petición.

| Cliente | `--client` | Skills instalados bajo |
| --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/atipspec*/SKILL.md` |
| Codex | `codex` | `.agents/skills/atipspec*/SKILL.md` |
| Cursor | `cursor` | `.cursor/skills/atipspec*/SKILL.md` |
| GitHub Copilot | `github-copilot` | `.github/skills/atipspec*/SKILL.md` |
| Antigravity | `antigravity` | `.agents/skills/atipspec*/SKILL.md` |
| Gemini CLI | `gemini` | `.gemini/skills/atipspec*/SKILL.md` |

Codex y Antigravity comparten una carpeta. Algunos clientes también descubren las
carpetas de skills de otros clientes; si ves duplicados, instala solo uno.

=== "Claude Code"

    **Invocar**

    ```text
    /atipspec-contract
    /atipspec-spec password-reset: users should be able to reset a forgotten password
    /atipspec-ship password-reset
    ```

    **Revisor en una sesión aislada**: el modelo usa la herramienta Agent con un
    subagente general-purpose y el prompt "Read
    `.atipspec/tmp/password-reset-review-packet.md` and do what it says."
    El subagente nunca ve la conversación, así que escribe `session: isolated`.

=== "Codex"

    **Invocar**

    ```text
    $atipspec-spec password-reset: users should be able to reset a forgotten password
    ```

    **Revisor**: un subagente cuando tu versión de Codex ofrezca uno; si no, abre
    una segunda sesión de Codex en el proyecto y pega el prompt del paquete.
    Cualquiera de los dos escribe `session: isolated`; una revisión escrita en la
    misma sesión escribe `session: shared`.

=== "Cursor"

    **Invocar**: elige *atipspec-spec* (o la fase que necesites) en el selector de
    skills, o pide al Agent que lo use y describe la entrega.

    **Revisor**: un agente en segundo plano con el prompt del paquete, o un chat
    nuevo que no haya visto el trabajo: `session: isolated`. En el mismo chat:
    `session: shared`.

=== "GitHub Copilot"

    **Invocar**: en modo agente, pide a Copilot que use el skill atipspec-spec y
    describe la entrega.

    **Revisor**: una sesión de agente nueva con el prompt del paquete:
    `session: isolated`. En la misma sesión: `session: shared`.

=== "Gemini CLI"

    **Invocar**: comprueba `/skills list` y luego pídele que use atipspec-spec.
    Los skills de proyecto requieren un espacio de trabajo de confianza.

    **Revisor**: una sesión nueva con el prompt del paquete: `session: isolated`.
    En la misma sesión: `session: shared`.

=== "Antigravity"

    **Invocar**: pide al agente que use el skill atipspec-spec.

    **Revisor**: un subagente o una sesión nueva con el prompt del paquete:
    `session: isolated`. En la misma sesión: `session: shared`.

El revisor declara `session:` en `review.md`; nada en el cliente lo demuestra. Una
revisión compartida es un warning, y un error con `risk: high` o
`require_isolated_review` (consulta [review](flow/review.md)): en ese caso, pide
una sesión nueva para el revisor.

## Qué carga el modelo

El skill de una fase son pocas líneas. El comando de la fase imprime todo lo
demás: la cabecera de la fase con el estado derivado, el workflow de la fase desde
`.atipspec/framework/workflows/`, las reglas compartidas de
`.atipspec/framework/rules.md` y la salida de `atipspec context <slug>`. El modelo
lee `specs/` solo en la medida en que el contexto lo selecciona y escribe la spec
viva que cambia, nunca lee `archive/` entero y nunca lee el workflow de una fase a
la que no puede entrar.

## Reglas de permisos de aprobación

Apruebas en la conversación y el asistente lo registra con
`atipspec accept ... --code <code>`. Donde el cliente se puede configurar para
preguntarte antes de que ese comando se ejecute, `init` e `install` lo configuran,
y el registro lo indica en su `channel`:

| Cliente | Qué instala AtipSpec | Canal de un `accept` del asistente |
| --- | --- | --- |
| Claude Code | `.claude/settings.json`: `ask` para `Bash(*atipspec accept *)`, y para `Edit` sobre `.github/workflows/**`, `.gitlab-ci.yml` y `.claude/settings*.json`; `deny` de `Edit` sobre `.atipspec/deliveries/*/approvals/**`, `.atipspec/deliveries/*/evidence/**`, `.atipspec/deliveries/*/review-rounds.json`, `.atipspec/approvals/**` y `.atipspec/archive/**` | `client-permission` mientras esas reglas estén intactas y ningún hook del proyecto conteste la pregunta, `assistant` en caso contrario |
| Codex | nada todavía: las reglas de proyecto en `.codex/rules/*.rules` pueden preguntar antes de un prefijo de comando, pero solo se cargan en una capa de proyecto de confianza y su comportamiento con `approval_policy = never` no está verificado | `assistant` |
| Cursor | nada: `.cursor/cli.json` tiene listas de permitidos y denegados, sin preguntar, y solo para su CLI | `assistant` |
| GitHub Copilot | nada: el ajuste de aprobación automática de la terminal de VS Code es de mejor esfuerzo, no una barrera de seguridad | `assistant` |
| Gemini CLI | nada: su motor de políticas puede preguntar, pero hoy no carga las políticas del espacio de trabajo | `assistant` |
| Antigravity | nada: sus reglas de permisos son globales o se fijan en el IDE | `assistant` |

Cómo se comportan las reglas de Claude Code:

- Claude Code evalúa `deny`, luego `ask` y luego `allow`; una regla `allow` nunca
  las anula, y las reglas `ask` preguntan en todos los modos de permisos. En los
  modos que no pueden preguntar, el comando se deniega, así que no se registra
  nada.
- El aviso te pide permitir el comando exacto, con el código del contenido que
  aprobaste; confirma esa misma aprobación, no es una segunda.
- Las reglas `deny` cubren las herramientas de edición de Claude Code, los
  comandos de ficheros que reconoce y las redirecciones; las versiones anteriores
  a 2.1.210 tratan de otra forma las reglas `Edit` y las redirecciones. No cubren
  programas arbitrarios, como un script que escribe un fichero.
- Las reglas `ask` para `Edit` sobre `.github/workflows/**`, `.gitlab-ci.yml` y
  `.claude/settings*.json` hacen que las herramientas de edición de Claude Code
  te pregunten antes de cambiar la CI que ejecuta `merge-check`, o los ajustes
  que contienen estas reglas. A diferencia de las reglas `deny`, no frenan una
  redirección: con Claude Code 2.1.296 en modo `acceptEdits`, un comando Bash
  que los ajustes permiten, como `echo`, `printf` o `python3 -c`, escribió en
  `.github/workflows/` con una redirección sin preguntar, y cualquier programa
  que la sesión pueda ejecutar puede escribir ahí. La protección que se
  mantiene es `merge-check`: bloquea una branch que cambia la CI, los ajustes
  del cliente o los skills fuera de una entrega, y la CI en sí se protege en el
  proveedor (consulta [CI antes del merge](enterprise.md#ci-antes-del-merge)).
- Las reglas se cargan desde el `.claude/settings.json` del proyecto: abre la
  sesión en la raíz del proyecto. Una sesión abierta en un subdirectorio, o en
  una carpeta padre u otro repositorio que entra en el proyecto con `cd` (lo
  hacen algunas sesiones de workflows y de subagentes), `--setting-sources` sin
  `project`, la configuración de usuario o gestionada, y los hooks de ahí que
  responden a las solicitudes de permiso las eluden sin que el CLI pueda
  saberlo. Un hook `PreToolUse` o `PermissionRequest` para Bash en el
  `.claude/settings.json` o el `.claude/settings.local.json` del proyecto sí se
  ve: `status` y `audit` lo nombran y el canal es `assistant`. Las sesiones
  ejecutadas con el Agent SDK, que no carga la configuración del proyecto salvo
  que su programa lo pida y entrega los avisos a ese programa, y `claude -p`
  registran `assistant`.
- La fusión conserva todas las demás claves y entradas, añade solo las reglas que
  faltan y no escribe nada cuando ya están todas. Un fichero que no es JSON puro
  (con comentarios, por ejemplo) o un enlace simbólico se deja intacto, y se
  imprimen las reglas para añadirlas a mano. Quitar Claude Code desde el menú de
  `init` quita solo estas reglas.
- `audit` avisa cuando las reglas faltan o están incompletas, nombrando las que
  faltan, y `status` imprime una línea `approvals:` con su estado. Hasta que
  estén todas, las aceptaciones se registran con el canal `assistant`.
  `atipspec install --update` las repara.

`client-permission` significa que las reglas que hacen que Claude Code te
pregunte están en este proyecto, no que la sesión las cargara ni que el CLI te
viera confirmar. En una terminal sin marcadores de agente, `accept` te pide que
escribas el código (canal `terminal`); un agente puede quitar sus marcadores y
contestar a esa solicitud desde una terminal que él crea, así que ningún canal
identifica a quién aprobó: describen cómo se ejecutó el comando. Para
aprobaciones autenticadas, usa una [policy de confianza externa](enterprise.md).

## Idioma

El inglés es el idioma principal; el español y el portugués están soportados. Los
ficheros del framework, los skills y la salida del CLI se mantienen en inglés: una
sola fuente, leída por un modelo que sigue instrucciones en inglés y te responde en
el tuyo. Lo que lee una persona sigue `language` en `config.yaml`: el dosier de
aceptación de `atipspec report`, y este sitio, que existe en los tres idiomas con
un selector. Lo que el modelo escribe en tu idioma lo entiende el CLI: nombres de
sección como `Intención` o `Intenção`, `Fuera de alcance` o `Fora do escopo`,
`Atributos de calidad` o `Atributos de qualidade`, `Preguntas abiertas` o
`Questões em aberto`; marcadores vacíos como `Ninguna` o `Nenhuma`; etiquetas como
`Por qué:` u `Observado:`; y los disparadores, los términos vagos y las palabras de
medida del lint. Los IDs, los encabezados de plantilla y los estados se mantienen
tal como los definen las plantillas, porque el CLI los analiza.

## Actualizar

Después de actualizar el CLI, ejecuta esto en cada proyecto:

```bash
atipspec install --update
```

Reemplaza los ficheros del framework y de los skills que difieren de la versión
instalada, quita los ficheros de `.atipspec/framework/` que esa versión no
instala, fusiona en `.claude/settings.json` las reglas de permisos de Claude Code
que faltan sin quitar nada, y nunca toca nada más. Hasta que se ejecuta,
`audit`, `check` y `merge-check` fallan: cada fase imprime al agente las reglas
y los workflows del framework, así que tienen que ser los que trae la versión
instalada, igual que los skills. Fija la misma versión en la CI que ejecuta
`merge-check`. Una instalación anterior a 0.1.0
tenía un único skill `atipspec`; la actualización reemplaza su contenido y añade
los skills de fase junto a él.
