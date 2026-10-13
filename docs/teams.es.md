# Equipos y escala

AtipSpec está construido para proyectos que duran meses con varias personas y
sus agentes. Dos ideas sostienen todo el peso: la unidad de asignación es la
entrega, y el coste de una petición está acotado por la entrega, no por el
proyecto.

## Entregas, no tareas

| Jira | AtipSpec | Unidad de |
| --- | --- | --- |
| Epic | iniciativa | meses de trabajo, varias personas |
| Story | entrega | asignación a una persona, una branch |
| Sub-task | tarea | una ejecución de agente con un contexto limpio |

Las tareas dentro de una entrega comparten una spec y una branch, y se
ejecutan en secuencia. Una entrega está dimensionada para cerrarse en una
jornada de trabajo: `check` avisa por encima de `max_requirements` y
`max_tasks`, `status` muestra el lead time de cada entrega, desde su creación
hasta la aceptación de su resultado, y `check`, `status` y el dosier avisan por
encima de `max_age_hours` (8 por defecto). El trabajo más grande se convierte
en varias entregas bajo una iniciativa. El trabajo que dos personas deberían
hacer en paralelo se convierte en dos entregas, divididas por propiedad, con
la interfaz entre ellas fijada en la iniciativa:

```bash
atipspec initiative orders --title "Orders"
atipspec new orders-api    --title "Orders API"    --capability orders    --owner ana  --initiative orders --worktree
atipspec new orders-screen --title "Orders screen" --capability orders-ui --owner luis --initiative orders --worktree --impact orders
```

Crear una entrega con `--initiative` la incluye en el roadmap. El roadmap
tiene una sección *Interfaces* para lo que ambas partes acuerdan (la forma de
una API, un evento, un esquema) y el fichero que es su fuente de verdad.

```bash
atipspec status
```

```text
- orders-screen [in_progress] tasks 1/3 @luis SHOP-12 (https://example.atlassian.net/browse/SHOP-12), open 1d 3h: Orders screen
    accepted: proposal accepted by luis@example.com at 2026-10-02T09:12:00Z via client-permission (Claude Code) (current)
    next: T2 is not complete: implement it and record `atipspec task-done orders-screen T2 --note <summary>`
initiatives:
- orders 1/2: orders-api delivered; orders-screen in_progress
```

`atipspec status --format json` da el mismo estado a los scripts, y
`--format markdown` lo da como tablas para un pull request o un resumen de
job; con un slug, la entrada de la entrega y sus comprobaciones.

## Una entrega, una branch, un worktree

```bash
atipspec new orders-api --title "Orders API" --worktree
```

crea la branch `delivery/orders-api` en una carpeta hermana
`../<repo>-orders-api`. Cada persona, y cada agente, trabaja en su propio
árbol; nada se comparte hasta el pull request. `--branch` hace lo mismo en la
carpeta actual. Un equipo con sus propios nombres de branch pasa
`--branch-name feature/SHOP-12-orders-api` con cualquiera de los dos, y
`--reuse-branch` con `--branch-name` para empezar la entrega en una branch
local que ya existe.

Una entrega que necesita otra antes la nombra con `--depends-on`:

```bash
atipspec new orders-screen --title "Orders screen" --capability orders-ui --depends-on orders-api --worktree
```

Hasta que `orders-api` esté archivada con un recibo aceptado en este checkout,
`check orders-screen` mantiene un todo `Waiting for accepted dependency
orders-api`, así que su puerta no está en verde y su resultado no se puede
aceptar.

Integrar main cambia el árbol, lo que deja obsoletas la evidencia y la
revisión. La puerta te obliga a volver a verificar y revisar después de
integrar, así que no existe eso de «en mi branch funcionaba». Integra antes de
la verificación final: después de `deliver`, `merge-check` bloquea cualquier
cambio del código de la branch, integración incluida, hasta que la entrega se
reabre y se acepta de nuevo. Una entrega por branch lo mantiene barato;
entregar otra entrega en la misma branch también deja obsoletas las que
siguen abiertas.

Empieza una entrega desde un main actualizado, y trae main con un merge solo
cuando la branch lo necesite. Lo que trae main no anula la propuesta aprobada,
ni cuenta como cambio de la entrega en `check`, en el paquete de revisión ni
en el dosier, una vez que AtipSpec sabe qué branch es main: consulta [cuando
main avanza](#cuando-main-avanza). Un rebase sobre main
reescribe la branch: cuando `new` se ejecutó después de commits propios de la
branch, reescribe el commit desde el que empezó la entrega, y entonces `check`
se detiene hasta que restauras el historial de antes del rebase (`git reflog`
lo muestra) y haces un merge en su lugar.

## Cuando main avanza

Es habitual que varias entregas cambien la misma capacidad, cada una en su
branch. Cuando una se integra en main y otra branch trae main, la spec viva de
la segunda entrega contiene ahora también los requisitos de la primera.
AtipSpec los atribuye a la **branch de integración**:

- `integration` en `teams.json`, como `"refs/remotes/origin/main"`;
- sin ella, la primera de `refs/remotes/origin/HEAD`, que define `git clone`,
  `refs/remotes/origin/main` y `refs/remotes/origin/master` que resuelva, así
  que un checkout de CI sin `origin/HEAD` encuentra la misma rama; declara
  `integration` cuando main tiene otro nombre, porque un checkout de CI no
  tiene `origin/HEAD`; `status` y `audit` avisan cuando `origin/HEAD` nombra
  una rama así e `integration` no está definida;
- bajo una policy de confianza, solo el `integration` de la policy:
  `teams.json` forma parte del candidato y ahí no nombra nada.

Lo que trajo main es lo que cambió entre el commit donde la base de la entrega
se encuentra con main y la base del merge de `HEAD` con main, como en el diff
de una pull request: cada fichero que la entrega no ha cambiado desde
entonces, y cada requisito tal como lo contiene esa base del merge. Da igual
que main integrara las otras entregas con merge, con squash o con rebase.
Entonces:

- La aprobación de la propuesta sigue vigente, y también los registros de
  `task-done`: hashea los requisitos que lista la entrega, no el resto de la
  spec viva. El texto fuera de los requisitos, antes del primero o bajo un
  encabezado entre ellos, el frontmatter, y un comentario HTML o un bloque
  de código cercado en un requisito que la entrega no lista no están en
  ninguna aprobación: `check` avisa cuando cambian, frente a lo que contiene
  main donde main los cambió, y solo los cubre la aceptación del resultado,
  que liga el árbol entero.
- `check` y el diff de la propuesta comparan la spec viva con lo que contiene
  main, así que un requisito que trajo main no es cambio de la entrega.
  Editarlo, eliminarlo o devolverlo a como estaba sí lo es: un requisito que
  la entrega cambia sin listarlo es un error, en todos los niveles de riesgo,
  y `merge-check` también lo bloquea.
- Los ficheros que trajo main no quedan fuera del `scope` del plan, y el
  paquete de revisión y el dosier los listan aparte en vez de en el diff. Un
  fichero que la entrega también cambia sigue siendo suyo, esté en el índice o
  no, y también uno que devuelve a como lo tenía la base, como un fichero que
  borró main: el paquete de revisión y el dosier lo muestran frente a la base
  del merge, como el diff de una pull request, y `check` avisa cuando la
  entrega deshace en él, del todo o en parte, lo que cambió main: una línea
  que añadió main y que la entrega quita o reescribe, o una que quitó main y
  que la entrega vuelve a poner donde estaba, o en cualquier sitio si main no
  dejó ninguna igual en el fichero.
- La evidencia y la revisión quedan obsoletas, como después de cualquier
  cambio del árbol: verifica y revisa de nuevo.

Sin una ref que se resuelva no se atribuye nada, ni cuando main contiene la
carpeta de la propia entrega, como cuando se registró en un commit en la
misma main. `merge-check` cubre lo que muestra el dosier, así que sin ref, o
cuando la pull request va a una branch que no es la de integración, como una
branch de release, un cambio de esa branch que la rama devuelve a como lo
tenía la base es código fuera de toda entrega. Cuenta el dosier que aceptó
la persona. Cuando una entrega abierta devuelve lo que cambió la branch de
integración, la aceptación de su resultado nombra la base del merge frente a
la que su dosier muestra esos ficheros, así que volver a integrar esa branch
después la anula, aunque se conserve el árbol, como lo conserva
`git merge -s ours`. Una entrega archivada cubre los ficheros que mostraba su
dosier cuando se entregó, tal como los lista su recibo (bajo una policy de
confianza, tal como los muestra su dosier en el commit desde el que se
entregó), no lo que mostraría un dosier en el head, ni un fichero que la
branch de destino cambió después del commit que la archivó: al conservar el
código entregado, la rama deshace ese cambio. El riesgo aceptado: un cambio
que main hizo fuera de una entrega,
como un hotfix, también cuenta como traído, igual que en el diff de una pull
request: se juzga donde entró en main, en su propia pull request, cuyo
`merge-check` bloquea el código fuera de toda entrega salvo que lo exima
`exempt_paths` en main. Un fichero que cambió
una entrega archivada antes en la misma rama, y que main también cambió, deja
de coincidir con lo que contiene main cuando la rama integra main, así que
cuenta como cambio de la entrega abierta, también fuera de su scope: una
entrega por rama lo evita. En modo local, la ref y los recibos de las entregas
archivadas en la rama son ficheros locales que se podrían mover o escribir, y
un recibo escrito a mano y con commit avala los requisitos que lista su spec,
y cubre los ficheros que lista, igual que uno escrito por `deliver`: esto
detecta la deriva. Una policy de
confianza autentica en `merge-check`, cuya ref obtiene el worker protegido:
vuelve a comprobar cada entrega archivada en la rama donde se entregó y solo
toma los requisitos de las que autentica; `check` lee los recibos tal como
están en el commit.

Un merge con conflictos que todavía no tiene commit cuenta como cambio de la
entrega hasta el commit del merge: la atribución lee `HEAD`. Dos entregas que
añaden requisitos a la misma capacidad entran en conflicto en git donde ambas
añaden al final; conserva los dos bloques al resolverlo.

## Configuración del equipo

`.atipspec/teams.json` es opcional y se escribe a mano:

```json
{
  "schema": 1,
  "refs": ["refs/remotes/origin/delivery/*", "refs/heads/release"],
  "owners": {"orders": ["ana"], "orders-ui": ["luis", "marta"]},
  "repositories": {"api": "../shop-api"},
  "integration": "refs/remotes/origin/main",
  "ticket_url": "https://example.atlassian.net/browse/{ticket}"
}
```

| Clave | Significado |
| --- | --- |
| `refs` | nombres de ref completos que leen el tablero y `check`; un `*` al final toma todas las refs que coinciden en ese último segmento |
| `owners` | capacidad a sus owners humanos: una entrega guiada de una capacidad con owners necesita un `owner` en `spec.md` |
| `repositories` | nombre a un checkout local, para `contract-pin`; `system` toma por defecto el `system` de `config.yaml` |
| `integration` | la branch de integración, como nombre de ref completo; consulta [cuando main avanza](#cuando-main-avanza) |
| `ticket_url` | una dirección https con `{ticket}` donde va la clave de un ticket o el número de una issue |

La aprobación de una propuesta guiada hashea solo los owners de su capacidad
e `integration`, también bajo una policy de confianza; editar las demás claves
no anula ninguna aprobación.

## El tablero: `atipspec team`

```bash
atipspec team [--fetch] [--json]
```

lista todas las entregas abiertas del checkout de trabajo y de cada ref de
`refs`: su status, owner, ticket, ref, capacidad, requisitos y dependencias.
Ejecútalo antes de tocar una capacidad que otros puedan estar cambiando.
`check` informa de un requisito que dos entregas declaran de forma distinta.
Solo lee refs locales y nunca hace fetch; la primera línea dice cuándo hizo
fetch el repositorio por última vez. `--fetch` primero hace fetch, sin pedir
credenciales, de cada remoto que nombra una entrada `refs/remotes/<remote>/...`:
git y ssh se ejecutan sin terminal ni programa askpass, así que falla un
remoto que necesite una contraseña o una frase de paso que no tengan el
credential helper ni el ssh-agent. Un remoto que falla recibe un warning y el
tablero muestra lo último que se obtuvo. Es el único comando que usa la red.

## Tickets

`atipspec new --ticket` acepta una clave como `SHOP-12` (Jira, Linear), un
número de issue como `#42` o una URL https; cualquier otra cosa se rechaza.
Con `ticket_url` en `teams.json`, una clave o un número se convierte en un
enlace en `status`, `team`, la propuesta, el dosier (`ticket_url` en su JSON,
un enlace en Markdown y HTML) y `merge-check`. El ticket no forma parte de lo
que hashea la aprobación de la propuesta: añádelo o corrígelo en `spec.md` en
cualquier momento. AtipSpec enlaza el ticket; nunca escribe en el gestor de
tickets. Un ticket de texto libre escrito antes de 0.3.0 se muestra tal cual,
sin enlace.

## Pull requests

`github-local.yml` y `gitlab-local.yml`, de `atipspec enterprise-init`,
ejecutan `merge-check` como comprobación del pull request; el resumen de su
job lista cada entrega que toca la branch con su estado y su ticket. Cuando el
usuario pide al agente que abra un pull request, el agente pone en su
descripción el ticket de la entrega y la salida de `atipspec report <slug>
--format markdown`. En modo local, un recibo aceptado no está autenticado: la
comprobación confirma que la branch coincide con lo que se aceptó, no quién lo
aceptó.

## Solapes

`status` y `audit` avisan cuando dos entregas abiertas declaran la misma spec
viva en su `impact`:

```text
  warning: orders-api and orders-screen both touch orders
```

Ese es el conflicto que merece la pena detectar antes de que exista código.
Los conflictos de git siguen siendo asunto de git.

## Varios repositorios

Cada repositorio tiene su propio `.atipspec/`, porque las aprobaciones y la
evidencia están atadas al árbol de su repositorio. Para las partes
compartidas, un pequeño repositorio **system** contiene el contrato del
sistema, el glosario compartido, los contratos de API y los esquemas, y las
iniciativas que abarcan varios repositorios. Apunta cada proyecto a un
checkout de él:

```yaml
# .atipspec/config.yaml
system: ../shop-system
```

Entonces `atipspec new` fija el `contract.md` del system, y su `glossary.md`
cuando lo tiene, en el commit actual del checkout, en el `contracts.json` de
la entrega:

```text
Pinned system contract.md at 3f2a9c41d0e7 as system-contract (contracts.json)
```

El contexto de la entrega los lee desde ese commit, así que el avance del
system no cambia ni lo que lee el agente ni la propuesta aprobada. Cuando el
checkout no está disponible, `new` avisa y la propuesta no se puede aprobar
hasta que exista la fijación:

```bash
atipspec contract-pin <slug> system-contract --repository system --ref HEAD --path contract.md
```

Cualquier otro contrato, como un esquema de API en otro repositorio, se fija
de la misma forma después de nombrar su checkout en `repositories` de
`teams.json`:

```bash
atipspec contract-pin orders-screen orders-api --repository api --ref main --path openapi.yaml
```

`--ref` se resuelve una vez a un id de commit completo; `check` rechaza una
fijación que nombra una branch o un tag, o cuyo contenido ya no tiene el
digest registrado. Volver a fijar cambia `contracts.json`, lo que anula la
aprobación de la propuesta: un contrato compartido cambió, y la persona
aprueba la entrega contra el nuevo. Las entregas antiguas siguen leyendo el
checkout tal como está.

## Mantener el contexto pequeño

Cada comando de fase imprime la salida de `atipspec context <slug>`, que
carga el contrato, el overview, el glosario, las specs vivas de la lista de
impact, las decisiones aceptadas que las afectan y los propios ficheros de la
entrega. Imprime el tamaño:

```text
Context for orders-api: 184 lines (budget 800)
     43  contract (.atipspec/contract.md)
     22  overview (.atipspec/overview.md)
     10  glossary (.atipspec/glossary.md)
     37  decision DEC-001
     48  spec (.atipspec/deliveries/orders-api/spec.md)
     24  plan (.atipspec/deliveries/orders-api/plan.md)
```

Dos cosas lo mantienen acotado con el tiempo: la fase
[curate](flow/curate.md) con sus topes, y la lista de impact, que es la razón
por la que una spec declara lo que toca en vez de que el modelo lo adivine.

## Policies por proyecto

La ceremonia es un dial en `config.yaml`, y en el
[`risk`](flow/spec.md#riesgo) de cada entrega, no una propiedad de la
herramienta:

```yaml
approve_plan: true      # legacy deliveries: build waits for the plan's own approval
review_rounds: 3        # reviews per approved proposal, the first included, before `review` refuses and you decide
context_budget: 800     # lines; context warns above it
max_requirements: 5     # check warns above it: split the delivery
max_tasks: 8            # same, for the plan
max_age_hours: 8        # check and status warn when a delivery has been open longer
```

Los dos puntos de parada, la propuesta y el resultado, se mantienen en todos
los proyectos: los diales cambian lo que la puerta pide entre ellos. Un
proyecto regulado añade `require_proof: true`, `require_isolated_review:
true`, un presupuesto bajo y, para tener aprobaciones autenticadas,
`trust: required` con una policy externa.
