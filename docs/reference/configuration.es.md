# Configuración

`.atipspec/config.yaml`, escrito por `init`:

```yaml
name: shop
language: es
approve_plan: true
review_rounds: 2
context_budget: 800
strict_scope: false
criteria_syntax: ears
strict_criteria: false
max_requirements: 5
max_tasks: 8
max_age_hours: 48
```

| Clave | Por defecto | Significado |
| --- | --- | --- |
| `name` | nombre de la carpeta | nombre del proyecto, mostrado por `status` |
| `language` | `en` | idioma en el que el modelo escribe los artefactos; `en`, `es` y `pt` también gobiernan el lint de criterios, los nombres de sección que acepta el parser y el dosier de aceptación. Otro código funciona con las tablas en inglés, y `audit` lo indica |
| `approve_plan` | `true` | `atipspec build` se niega hasta que se registra la aprobación humana del plan (incluida en la propuesta guiada) |
| `review_rounds` | `2` | rondas de revisión sin una comprobación en verde antes de que el modelo se detenga e informe |
| `context_budget` | `800` | líneas; `atipspec context` avisa por encima |
| `strict_scope` | `false` | cuando es true, un fichero cambiado fuera del `scope` del plan es un error en vez de un warning |
| `criteria_syntax` | `ears` | `ears` avisa sobre criterios que no empiezan con un trigger o no llevan un shall; `free` desactiva esa comprobación |
| `strict_criteria` | `false` | cuando es true, las comprobaciones de forma y de términos vagos en los criterios son errores y bloquean la aceptación |
| `max_requirements` | `5` | `check` avisa cuando una spec tiene más requisitos: una entrega debería caber en una jornada de trabajo |
| `max_tasks` | `8` | `check` avisa cuando un plan tiene más tareas |
| `max_age_hours` | `48` | `status` avisa cuando una entrega lleva abierta más de esto, en horas de reloj |
| `system` | sin definir | ruta a un checkout del repositorio system; su `contract.md` y `glossary.md` se unen a cada contexto |

Solo `name` y `language` los gestiona `atipspec init`; edita el resto a
mano. `init --language en` en un proyecto existente conserva las demás
claves.

## `.atipspec/.gitignore`

Creado por `init`; ignora `tmp/`, donde se escriben los paquetes de
revisión. Todo lo demás bajo `.atipspec/` está pensado para tener commit: el
contrato, las specs vivas, las entregas con su evidencia y sus revisiones,
el archive.

## Entorno

| Variable | Efecto |
| --- | --- |
| `NO_COLOR` | desactiva los colores en la salida de la terminal |
| `TERM=dumb` | lo mismo |

## Confianza de la organización

La configuración local del proyecto guía al asistente; no puede relajar la
aceptación de confianza. `approve_plan: false` se salta la ceremonia
conversacional, no el requisito de aprobación de ingeniería de confianza. La
policy TOML externa controla roles, claves públicas, reglas corporativas e
identidades de proveedor. Debe vivir fuera del candidato.

`ATIPSPEC_TRUST_POLICY` selecciona esa policy; `ATIPSPEC_POLICY_SHA256` fija
su contenido. Usa configuración protegida de la organización, no valores
proporcionados por el proyecto. Los adaptadores de GitHub/GitLab usan
`GITHUB_TOKEN` / `GITLAB_TOKEN` de solo lectura en el recolector de
confianza. El runner de verificación elimina esas credenciales de los
entornos de los comandos. Consulta [aceptación empresarial](../enterprise.md).
