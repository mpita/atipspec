# Configuración

`.atipspec/config.yaml`, escrito por `init`:

```yaml
name: shop
language: es
approve_plan: true
review_rounds: 3
context_budget: 800
strict_scope: true
criteria_syntax: ears
strict_criteria: true
max_requirements: 5
max_tasks: 8
max_age_hours: 8
trust: optional
require_proof: false
require_isolated_review: false
exempt_paths: []
```

| Clave | Por defecto | Significado |
| --- | --- | --- |
| `name` | nombre de la carpeta | nombre del proyecto, mostrado por `status` |
| `language` | `en` | idioma en el que el modelo escribe los artefactos; `en`, `es` y `pt` también gobiernan el lint de criterios, los nombres de sección que acepta el parser y el dosier de aceptación. Otro código funciona con las tablas en inglés, y `audit` lo indica |
| `approve_plan` | `true` | solo entregas antiguas: `atipspec build` se niega hasta que se registra la aprobación propia del plan (`accept <slug> plan`). Una entrega guiada aprueba su plan con la propuesta, diga lo que diga esta clave |
| `review_rounds` | `3` | cuántas revisiones tiene una entrega por cada acuerdo aprobado, contando la primera, digan lo que digan las revisiones; las salidas dicen `review N of M`. `atipspec review` y `atipspec run` las cuentan y se detienen cuando se agotan; menos uno, también es el valor por defecto y el máximo que permite `--max-rounds`. La aprobación de una propuesta guiada la cubre; en una entrega antigua, ninguna aprobación lo hace. Consulta [rondas de revisión](../flow/review.md#rondas-de-revision) |
| `context_budget` | `800` | líneas; `atipspec context` avisa por encima |
| `strict_scope` | `true` | un plan debe declarar su `scope`, y unos globs que juntos coinciden con todas las rutas (`**`, `**/*`, `*` con `*/**`) no declaran ninguno; un fichero cambiado fuera de él es un error. Con `false`, un fichero fuera de un scope declarado es un warning y se permite un scope vacío |
| `criteria_syntax` | `ears` | `ears` señala los enunciados de criterio que no empiezan con un trigger ni llevan un shall; `free` desactiva solo esa comprobación |
| `strict_criteria` | `true` | las comprobaciones estrictas de la especificación son errores y bloquean la propuesta: la forma EARS, los términos vagos en requisitos, criterios y pasos de escenario, y el número en el criterio de un atributo de calidad. Con `false` son warnings. El consejo sobre valores concretos y métodos de medición es un warning en ambos casos; consulta [escribir criterios](spec-quality.md) |
| `max_requirements` | `5` | `check` avisa cuando una spec tiene más requisitos: una entrega debería caber en una jornada de trabajo |
| `max_tasks` | `8` | `check` avisa cuando un plan tiene más tareas |
| `max_age_hours` | `8` | `check`, `status` y el dosier avisan cuando el lead time de una entrega supera este valor: horas de reloj desde su creación (`created`, escrito por `new`) hasta la aceptación de su resultado, o hasta ahora mientras tanto. Un warning, nunca un bloqueo |
| `require_proof` | `false` | `true`: todo criterio bajo `Tests:` necesita una entrada en `Proof:` que nombre su test, y la verificación que lo ejecuta, un `Report:`; si falta, es un error que bloquea la propuesta. Una policy de confianza también puede activarlo, y entonces el proyecto no puede desactivarlo. Consulta [build](../flow/build.md) |
| `require_isolated_review` | `false` | `true`: una revisión con `session: shared`, o sin sesión, es un error en vez de un warning, como ya lo es con `risk: high`. Una policy de confianza también puede activarlo |
| `trust` | `optional` | `required`: el proyecto necesita una policy de confianza externa. Sin ella, `check` y `merge-check` están en rojo, `accept` rechaza todas las formas locales salvo `contract`, `deliver` se niega y `run` no arranca; `proposal` no muestra ningún código local. `merge-check` lo aplica cuando lo activa el head, la branch de destino o la base del merge, así que una branch no puede quitarlo para su propio merge, ni siquiera una que se bifurcó antes |
| `exempt_paths` | `[]` | globs de ficheros fuera de `.atipspec/` que una branch puede cambiar sin que los cubra ninguna entrega, como `["docs/**", "*.md"]`: `**` cruza directorios, `*` y `?` no. `merge-check` los lee del `config.yaml` de la branch de destino (la revisión `--base`), nunca de la branch que juzga, así que una branch no puede eximir sus propios cambios, y avisa en una branch que los cambia. Lo decide la persona. Ninguna aprobación lo hashea. Consulta [merge-check](cli.md#atipspec-merge-check) |
| `system` | sin definir | ruta a un checkout del repositorio system. `atipspec new` fija su `contract.md`, y su `glossary.md` cuando lo tiene, en el commit actual del checkout, en el `contracts.json` de la entrega guiada, y el contexto de esa entrega los lee desde ahí; las entregas antiguas leen el checkout tal como está. Consulta [varios repositorios](../teams.md#varios-repositorios) |

Solo `name` y `language` los gestiona `atipspec init`; edita el resto a
mano. `init --language en` en un proyecto existente conserva las demás
claves.

Todos los comandos salvo `init` validan primero las policies y se detienen
con `Invalid .atipspec/config.yaml: <key> must be ...`: los booleanos son
`true` o `false`, los números son enteros positivos (`max_age_hours` admite
decimales, como `7.5`), `criteria_syntax` es `ears` o `free`, `trust` es
`optional` o `required`, y `exempt_paths` es una lista de globs. Una clave
omitida toma su valor por defecto.

Los valores por defecto solo se aplican donde falta una clave. Los proyectos
creados antes de 0.3.0 tienen `strict_scope: false`, `strict_criteria: false`
y `max_age_hours: 48` escritos explícitamente y los conservan; `audit` señala
los dos primeros, e `install --update` lista todas las policies que difieren
de los valores por defecto de esta versión sin editar el fichero.
`config.yaml`, salvo `exempt_paths`, forma parte de lo que hashea la
aprobación de una propuesta guiada: cámbialo cuando ninguna entrega guiada
esté entre su propuesta y su resultado, o vuelve a presentar esas propuestas.

## `.atipspec/teams.json`

Opcional, escrito a mano: las refs que lee el tablero del equipo, los owners
de cada capacidad, los otros repositorios desde los que se fijan contratos, la
branch de integración y la dirección del gestor de tickets. Consulta
[configuración del equipo](../teams.md#configuracion-del-equipo). La
aprobación de una propuesta guiada solo hashea los owners de su capacidad e
`integration`, así que añadir refs, repositorios o `ticket_url` no anula
ninguna aprobación.

## `.atipspec/adapter.json`

Opcional, escrito a mano: el adaptador de proceso al que llama `atipspec run`,
como `{"schema": 1, "name": ..., "command": [...], "isolated_review": false}`.
El comando es un array argv, no código de shell. La aprobación de una
propuesta guiada hashea el fichero. Consulta [el adaptador de
ejecución](execution-adapter.md).

## `.atipspec/.gitignore`

Creado por `init`; ignora `tmp/`, donde se escriben los paquetes de revisión
y donde debe ir el `Report:` JUnit de un plan, como `.atipspec/tmp/junit.xml`.
Todo lo demás bajo `.atipspec/` está pensado para incluirse en commits: el
contrato, las specs vivas, las entregas con su evidencia y sus revisiones, el
archivo.

## `.claude/settings.json`

Escrito o fusionado por `init` e `install` cuando Claude Code es un cliente:
reglas `ask` para `Bash(*atipspec accept *)` y para `Edit` sobre
`.github/workflows/**`, `.gitlab-ci.yml` y `.claude/settings*.json`, y reglas
`deny` para `Edit` sobre los registros de aprobación, de evidencia, de rondas de revisión
(`review-rounds.json`) y del archivo. Todas las demás claves y entradas se
conservan. Consulta [reglas de permisos de
aprobación](../clients.md#reglas-de-permisos-de-aprobacion).

## Entorno

| Variable | Efecto |
| --- | --- |
| `NO_COLOR` | desactiva los colores en la salida de la terminal |
| `TERM=dumb` | lo mismo |
| `ATIPSPEC_TRUST_POLICY` | ruta de la policy de confianza externa; todos los comandos la usan, igual que `--policy` (consulta [confianza de la organización](#confianza-de-la-organizacion)) |
| `ATIPSPEC_POLICY_SHA256` | el SHA-256 que debe tener la policy, como `--policy-sha256` |
| `ATIPSPEC_PR_NUMBER` | el pull request que lee una policy en modo provider, como `--number` |
| `GITHUB_TOKEN`, `GITLAB_TOKEN` | tokens de solo lectura de los adaptadores de proveedor, solo en el worker protegido; `verify` los elimina, junto con el agente SSH y los tokens de los jobs de CI y de OIDC, de los comandos que ejecuta |
| `CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`, `COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT` | los definen los agentes de programación; `accept` nunca registra el canal `terminal` mientras haya uno definido, ni `client-permission` mientras uno nombre a un agente distinto de Claude Code (los valores `0`, `false`, `no` y `off` se ignoran) |
| `CLAUDE_CODE_ENTRYPOINT` | lo define Claude Code; `sdk-ts` y `sdk-py` (el Agent SDK) y `sdk-cli` (`claude -p`) hacen que `accept` registre el canal `assistant` |

## Confianza de la organización

La configuración local del proyecto guía al asistente; no puede relajar la
aceptación de confianza. `approve_plan: false` se salta la aprobación del plan
de una entrega antigua, no el requisito de aprobación de ingeniería de
confianza. La policy TOML externa controla los roles, las claves públicas, las
reglas corporativas y las identidades de proveedor. Debe vivir fuera del
candidato. Sus `require_proof` y `require_isolated_review` se suman a los del
proyecto: la puerta aplica un requisito cuando cualquiera de los dos lo pone a
`true`. Su clave opcional `integration`, un nombre de ref completo como
`refs/remotes/origin/main`, nombra la branch cuyo historial cuenta como
integrado, de modo que lo que una entrega trae desde ella no es cambio de la
entrega en `check`, en el paquete de revisión ni en el dosier; bajo una policy, el `integration` de teams.json no nombra
ninguna branch, aunque las aprobaciones lo sigan hasheando. Consulta [cuando
main avanza](../teams.md#cuando-main-avanza). En modo provider (solo GitHub),
su bloque `[attestation]` nombra el workflow de evidencia de confianza,
`signer_workflow`, en otro repositorio de la misma organización, y fija su
commit, `signer_digest`; una policy sin ellos no se carga. Consulta [dos modos
de confianza](../enterprise.md#dos-modos-de-confianza).

`ATIPSPEC_TRUST_POLICY` selecciona esa policy; `ATIPSPEC_POLICY_SHA256` fija
su contenido. Usa configuración protegida de la organización, no valores
proporcionados por el proyecto. Los adaptadores de GitHub/GitLab usan
`GITHUB_TOKEN` / `GITLAB_TOKEN` de solo lectura en el recolector de confianza.
El runner de verificación elimina esas credenciales de los entornos de los
comandos. Consulta [aceptación empresarial](../enterprise.md).
