# Referencia del CLI

Todos los comandos se ejecutan desde cualquier lugar dentro del proyecto;
AtipSpec encuentra la raíz buscando `.atipspec/config.yaml`. Los errores
imprimen `AtipSpec: error: ...` y salen con 1. Nada se almacena entre
comandos: `status` y `check` calculan todo a partir de los ficheros y de
git.

## Proyecto

### `atipspec init`

```text
atipspec init [--name NAME] [--language LANG] [--client ID]...
```

Crea `.atipspec/` con `config.yaml`, `contract.md`, `overview.md`,
`glossary.md`, las carpetas `specs/`, `deliveries/`, `archive/`,
`decisions/`, `initiatives/`, la copia del framework y los skills de los
clientes seleccionados. Pregunta lo que los flags no proporcionan cuando se
ejecuta en una terminal; si no, usa el nombre de la carpeta, `en` y ningún
cliente.

En un proyecto ya inicializado: muestra el estado y, en una terminal, un
menú para añadir o quitar clientes, actualizar el framework, o cambiar el
nombre y el idioma. Con flags los aplica directamente.

### `atipspec install`

```text
atipspec install [--client ID]... [--update]
```

Instala el framework y los skills de los clientes dados sin sobrescribir
nada que difiera. `--update` reemplaza los ficheros del framework y de los
skills que difieren de la versión instalada del CLI. Sin `--client` pregunta
en una terminal, o se dirige a los clientes ya instalados con `--update`.

### `atipspec status`

```text
atipspec status [SLUG]
```

Sin slug: nombre del proyecto, branch, si el contrato existe, specs vivas,
cada entrega abierta con su status derivado, owner y siguiente acción,
avisos de solape, iniciativas con progreso, slugs delivered. Con slug: el
mismo informe que `check`.

### `atipspec audit`

Comprueba todo el repositorio contra las reglas del contrato (dependencies
siempre), la validez de cada spec viva y decisión, el tamaño de los
documentos contra sus topes, los solapes entre entregas abiertas, y los
roadmaps de las iniciativas. Sale con 1 si hay errores.

### `atipspec curate`

Regenera el bloque de índice de `overview.md`, informa de los tamaños de los
documentos contra sus topes e imprime el workflow de curate, que reescribe
la prosa.

## Fases

Un comando por fase. Cada uno comprueba qué exige la fase y sale con 1 con
una línea que nombra el paso que falta; si no, imprime `Phase <name>:
<title>`, el status derivado, el workflow de la fase desde
`.atipspec/framework/workflows/`, las reglas compartidas y, para `explore`,
`spec`, `plan` y `build`, la salida de `atipspec context`.
Consulta [el flujo](../flow/index.md#que-requiere-cada-fase) para los
prerrequisitos.

```text
atipspec explore SLUG [--no-context]
atipspec spec SLUG [--no-context]
atipspec fix SLUG [--no-context]        only for a delivery created with --kind fix
atipspec plan SLUG [--no-context]
atipspec build SLUG [--no-context]      also names the next task without a commit
atipspec review SLUG [--out FILE]       writes the reviewer packet when the prerequisites hold
atipspec deliver SLUG --policy PATH     see below
atipspec contract                       prints the workflow and the current contract.md
atipspec curate                         regenerates the overview index, reports sizes, prints the workflow
atipspec ship SLUG                      prints the next phase the delivery can enter
```

`--no-context` imprime el workflow sin el material de contexto, para volver
a entrar en una fase dentro de la misma sesión.

## Aceptación

### `atipspec accept`

```text
atipspec accept SLUG proposal [--by WHO]
atipspec accept SLUG result [--by WHO]
atipspec accept SLUG spec [--by WHO]
atipspec accept SLUG plan [--by WHO]
atipspec accept contract
```

La persona aprueba en la conversación y el agente ejecuta el comando. También puedes usarlo manualmente. `spec` se niega mientras un
requisito no tenga criterio o haya una pregunta abierta; si no, pone
`status: ready` y escribe `approvals/local-spec.json` con un hash de
`spec.md` y el contrato. `plan` exige una spec aceptada y un plan sin
errores, y registra el hash de la spec, el plan y el contrato. `contract`
pone `status: accepted` en `contract.md`. `--by` usa por defecto el
`user.email` de git.

`check` compara el hash registrado con los ficheros: después de cualquier
edición la entrega vuelve a ser draft (o el plan queda sin aceptar) hasta que la persona aprueba el contenido cambiado y se registra de nuevo su aceptación. Con `--policy`, mandan las
aprobaciones firmadas y estos registros se ignoran.

## Entregas

### `atipspec new`

```text
atipspec new SLUG --title TITLE [--capability NAME] [--impact NAME]...
                  [--owner WHO] [--ticket ID] [--initiative SLUG]
                  [--branch | --worktree] [--kind feature|fix]
```

Crea `deliveries/SLUG/` con `spec.md` (status draft, base = commit actual),
`plan.md` y `deferred.md`. `--kind fix` crea una reparación de defecto: una
spec con un criterio de regresión para rellenar, un plan de una tarea cuyo
`Verify:` lista los comandos obligatorios del contrato, sin aceptación de
plan, y `atipspec fix` como su fase (consulta [fix](../flow/fix.md)).
`--branch` crea y cambia a `delivery/SLUG`; `--worktree` crea esa branch en
`../<repo>-SLUG` y escribe la entrega ahí. `--initiative` registra la
entrega en el roadmap.

### `atipspec check`

```text
atipspec check SLUG
```

La puerta. Sale con 0 en verde, 1 con errores, 2 incompleto. Consulta [cómo
funciona](../getting-started/how-it-works.md#la-puerta) para los niveles.

### `atipspec context`

```text
atipspec context SLUG [--out FILE] [--summary]
```

Imprime el material de la entrega con un resumen de tamaño contra
`context_budget`. `--out` lo escribe en un fichero; `--summary` imprime
solo los tamaños.

### `atipspec verify`

```text
atipspec verify SLUG [--task Tn]... [--timeout SECONDS]
```

Ejecuta los comandos de Verify de cada tarea desde la raíz del proyecto a
través del shell, imprime su cola de salida, y escribe
`evidence/Tn-<timestamp>.json`. Sale con 1 si algún comando falla. Requiere
git.

### `atipspec review`

```text
atipspec review SLUG [--out FILE]
```

Se niega, sin escribir nada, mientras una tarea no tenga commit, la
evidencia falte o esté obsoleta, o el contrato esté violado. Si no, escribe
el paquete del revisor en `.atipspec/tmp/SLUG-review-packet.md`: rúbrica,
contrato, las specs vivas de la lista de impact, las decisiones aceptadas
que las afectan, spec, plan, deferred, resumen de evidencia, ficheros fuera
del `scope` del plan, el diff contra la base (limitado a 200 KB, con
`--stat` cuando se trunca) y los ficheros sin seguimiento; luego imprime el
workflow de review.

### `atipspec deliver`

```text
atipspec deliver SLUG --policy /secure/company.toml
```

Exige una comprobación de confianza en verde, evidencia autenticada y
aprobaciones humanas. Fusiona los requisitos en la spec viva de la
capacidad, pone `status: delivered`, mueve la carpeta a `archive/`.

## Decisiones e iniciativas

### `atipspec decision`

```text
atipspec decision SLUG --title TITLE [--affects NAME]...
```

Crea `decisions/DEC-nnn-SLUG.md` con status `proposed`. `--affects` toma
nombres de capacidad, `contract`, `contract:<section>` o `*`.

### `atipspec initiative`

```text
atipspec initiative SLUG --title TITLE
```

Crea `initiatives/SLUG/roadmap.md`.

## Códigos de salida

| Código | Significado |
| --- | --- |
| 0 | hecho; para `check`, verde |
| 1 | error, o para `check` y `audit`, rojo |
| 2 | `check`: incompleto, queda trabajo |
| 130 | cancelado desde el teclado |

## Aceptación de confianza

| Comando | Propósito |
| --- | --- |
| `enterprise-init [--out directory]` | Escribe ejemplos de policy, CI y adopción sin activarlos |
| `approval-subject <slug> <phase>` | Imprime el marcador de aprobación atado al contenido/head |
| `approve <slug> <phase> --identity id --key path --policy path` | Firma desde una identidad humana inscrita |
| `sync-approvals <slug> <phase> --number n --identity id --key path --policy path` | Recolecta una aprobación humana existente de GitHub/GitLab, de solo lectura |
| `attest <slug> --identity id --key path --run-url url --policy path` | El recolector protegido firma la evidencia de CI |
| `check <slug> --policy path [--policy-sha256 hash] [--number n] [--json]` | Puerta de confianza; por defecto, sin policy, es solo una comprobación local; `--number` nombra el PR o MR en el modo provider |
| `report <slug> --format json\|markdown\|html [--out path] [--policy path]` | Dosier y matriz de trazabilidad |
| `ids <capability>` | Muestra los siguientes IDs de requisito/criterio |
| `pilot init <name>` | Crea un protocolo de evaluación real vacío |
| `pilot record <name> ...` | Registra una observación completa con fuente; consulta `--help` |
| `pilot report <name>` | Compara las cohortes registradas, con tamaños de muestra y limitaciones |

Phases: `spec`, `plan`, `acceptance`, `decision:DEC-nnn`, `exception:Fn`. Las
exceptions exigen `--expires` con una marca de tiempo ISO futura y con zona
horaria. `verify` acepta `--policy` y exige la aprobación de spec/plan antes
de ejecutar. `deliver` exige una policy y la aceptación de confianza
completa. `ATIPSPEC_TRUST_POLICY`, `ATIPSPEC_POLICY_SHA256` y `ATIPSPEC_PR_NUMBER` son
alternativas de entorno protegidas a los flags del comando. Nunca las
derives de documentos candidatos.

Consulta [adopción empresarial](../enterprise.md) para el perímetro de
confianza, el aislamiento de CI, la custodia de claves y la integración de
solo lectura con el proveedor.
