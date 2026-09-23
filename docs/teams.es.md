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
`max_tasks`, y `status` muestra cuánto tiempo lleva abierta cada entrega y
avisa por encima de `max_age_hours`. El trabajo más grande se convierte en
varias entregas bajo una iniciativa. El trabajo que dos personas deberían
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
- orders-screen [in_progress]  tasks 1/3 @luis, open 1d 3h: Orders screen
    next: T2 is not committed: build it, run `atipspec verify orders-screen --task T2` and commit with [orders-screen:T2]
initiatives:
- orders 1/2: orders-api delivered; orders-screen in_progress
```

Tickets: `--ticket SHOP-12` registra el id externo en la spec; los marcadores
de commit `[orders-api:T1]` son tuyos para combinarlos con cualquier
convención.

## Una entrega, una branch, un worktree

```bash
atipspec new orders-api --title "Orders API" --worktree
```

crea la branch `delivery/orders-api` en una carpeta hermana
`../<repo>-orders-api`. Cada persona, y cada agente, trabaja en su propio
árbol; nada se comparte hasta el pull request. `--branch` hace lo mismo en la
carpeta actual.

Hacer rebase sobre main cambia el árbol, lo que hace que la evidencia y la
revisión queden obsoletas. La puerta te obliga a volver a verificar y revisar
después de integrar, así que no existe eso de «funcionaba en mi branch».

## Solapes

`status` y `audit` avisan cuando dos entregas abiertas declaran la misma spec
viva en su `impact`:

```text
  warning: orders-api and orders-screen both touch orders
```

Ese es el conflicto que merece la pena detectar antes de que exista código.
Los conflictos de git siguen siendo asunto de git.

## Varios repositorios

Cada repositorio tiene su propio `.atipspec/`, porque git es la máquina de
estados y la evidencia es por árbol. Para las partes compartidas, un pequeño
repositorio **system** contiene el contrato del sistema, el glosario
compartido, los contratos de API y los esquemas, y las iniciativas que
abarcan varios repositorios. Apunta cada proyecto a un checkout de él:

```yaml
# .atipspec/config.yaml
system: ../shop-system
```

`atipspec context` incluye entonces el `contract.md` y el `glossary.md` del
system en el material de cada entrega.

## Mantener el contexto pequeño

Cada comando de fase imprime la salida de `atipspec context <slug>`, que
carga el contrato, el overview, el glosario, las specs vivas de la lista de
impact, las decisiones aceptadas que las afectan, y los propios ficheros de
la entrega. Imprime el tamaño:

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
por la que una spec declara qué toca en vez de que el modelo lo adivine.

## Policies por proyecto

La ceremonia es un dial en `config.yaml`, no una propiedad de la herramienta:

```yaml
approve_plan: true      # build refuses until explicit human plan approval is recorded
review_rounds: 2        # rounds before the model stops and reports
context_budget: 800     # lines; context warns above it
max_requirements: 5     # check warns above it: split the delivery
max_tasks: 8            # same, for the plan
max_age_hours: 48       # status warns when a delivery has been open longer
```

Un proyecto pequeño pone `approve_plan: false` y entrega todo de una vez. Uno
regulado mantiene los dos puntos de parada, la aprobación del plan, y un
presupuesto bajo.
