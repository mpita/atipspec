# Reglas del contrato

`contract.md` es prosa para el modelo más un bloque delimitado que el CLI
evalúa:

````markdown
```rules
dependencies pyproject.toml django psycopg "pytest*"
forbid-pattern "shop/domain/**" "from shop\.infrastructure"   # DEC-002 layering
forbid-path "web/src/**/*.js"                                 # TypeScript only
require-command "python -m pytest -q"
```
````

Una regla por línea, con comillas al estilo shell; `#` empieza un comentario
que se muestra como la razón en los informes.

## Reglas

### `forbid-path <glob>`

Ningún fichero puede coincidir con el glob. `check` mira los ficheros que la
entrega tocó; `audit` mira todos los ficheros con y sin seguimiento fuera de
`.atipspec/`.

### `forbid-pattern <glob> <regex>`

Ningún fichero que coincida con el glob puede contener una línea que
coincida con la expresión regular (sintaxis Python). La primera línea que
coincide se reporta con su número. Úsala para las capas
(`"from shop\.infrastructure|^from django"` en el domain), para librerías
prohibidas, o para patrones que tus convenciones prohíben.

### `dependencies <manifest> <name-or-glob>...`

El manifiesto solo puede declarar las dependencias listadas. Los nombres se
comparan en minúsculas; se permiten globs como `"@types/*"` o `"pytest*"`.
En `check` la regla se ejecuta cuando el manifiesto está entre los ficheros
que la entrega tocó; en `audit` siempre se ejecuta. Manifiestos soportados:

| Fichero | Se lee de |
| --- | --- |
| `pyproject.toml` | `project.dependencies`, `project.optional-dependencies`, `dependency-groups`, las dependencies y groups de Poetry |
| `requirements*.txt` | un requirement por línea, se omiten las líneas `-r`/`-e` |
| `package.json` | dependencies, devDependencies, peerDependencies, optionalDependencies |
| `Cargo.toml` | dependencies, dev-dependencies, build-dependencies |
| `go.mod` | líneas y bloques `require` |

### `require-command <command>`

El plan de toda entrega debe incluir el comando, literal salvo por los
espacios en blanco, en el `Verify:` de al menos una tarea. Así es como los
quality gates del contrato se convierten en evidencia en cada entrega.

## Globs

`**` cruza directorios, `*` y `?` no. Los patrones se anclan a la ruta
completa relativa a la raíz del proyecto: `src/**/*.js` coincide con
`src/c.js` y con `src/a/b/c.js`; `src/*.js` coincide solo con el primero.

## Dónde se aplican las reglas

| | `atipspec check <slug>` | `atipspec audit` |
| --- | --- | --- |
| Ficheros | cambiados desde la base de la entrega, más los sin seguimiento | todos, con y sin seguimiento, fuera de `.atipspec/` |
| `dependencies` | cuando el manifiesto cambió | siempre |
| `require-command` | el plan de la entrega | no aplica |
| Resultado | errores en la puerta de la entrega | errores, exit 1 |

## Cambiar el contrato

Una entrega cuyo diff toca `.atipspec/contract.md` está en rojo a menos que
un fichero nuevo bajo `.atipspec/decisions/` sea parte del mismo diff.
Créalo con `atipspec decision <slug> --title ... --affects
contract:<section>`, y pon su status en `accepted` cuando estés de acuerdo.
