# contract

**Define y protege la arquitectura.** La primera fase de un proyecto, y la
que mantiene la cuadragésima entrega sobre los mismos raíles que la primera.

| | |
| --- | --- |
| Rol | El guardián del contrato. Describe la realidad antes que las reglas, escribe reglas que el CLI puede comprobar, nunca cambia el contrato dentro de una entrega de funcionalidad. |
| Quién decide | Apruebas el contrato y las decisiones listadas en la conversación; el asistente registra tu decisión con `atipspec accept contract --code <code>`. |
| Produce | `contract.md`, `decisions/DEC-nnn-*.md`, `approvals/contract.json`; las specs vivas llegan después, con sus primeros requisitos |

## Cómo ejecutarla

```text
/atipspec-contract
```

El skill ejecuta `atipspec contract`, que imprime el workflow, las reglas y
el `contract.md` actual. Presenta `atipspec proposal contract` (el contrato,
sus reglas, el resultado del audit, las decisiones que incluye y un código de
aprobación), pide la aprobación en la conversación y ejecuta
`atipspec accept contract --code <code>` tras tu aprobación explícita. El CLI
pone entonces el contrato y las decisiones listadas en `accepted` y registra
sus hashes en `.atipspec/approvals/contract.json`. Las entregas antiguas,
incluidos los fixes creados antes de 0.3.0, exigen esa aceptación registrada
antes de entrar en `fix` o en `spec`; en las entregas guiadas, fixes
incluidos, `check` avisa hasta que exista.

## Un proyecto nuevo

Di lo que ya decidiste: «una app web Django con PostgreSQL y un front React».
El modelo registra eso como decisiones con sus razones, para que nunca se
reabran por accidente:

```bash
atipspec decision stack --title "Django, PostgreSQL and React" --affects contract
```

Luego solo pregunta lo que afecta a las reglas: cómo hablan el front y el
back, dónde viven los contratos de API, la autenticación, los comandos de
calidad, qué está prohibido. Rellena `contract.md`:

````markdown
## Stack
Python 3.12, Django 5, PostgreSQL 16; React 18 with TypeScript in web/.

## Structure
shop/domain/ has no imports from shop/infrastructure/ or Django. Views are
thin; use cases live in shop/application/.

## Dependencies
New libraries need a decision. Pin exact versions.

## Quality gates
python -m pytest -q, ruff check ., npm test in web/.

## Rules

```rules
dependencies pyproject.toml django psycopg "pytest*" ruff
dependencies web/package.json react react-dom "@types/*" typescript vite
forbid-pattern "shop/domain/**" "from shop\.infrastructure|^from django"   # DEC-001 layering
forbid-path "web/src/**/*.js"                                             # TypeScript only
require-command "python -m pytest -q"
require-command "ruff check ."
```
````

Las specs vivas se crean cuando se definen sus requisitos. El asistente
ejecuta el audit y presenta el contrato y las decisiones incluidas. Elige
**Aprobar y continuar**, **Pedir cambios** o **Cancelar** en el selector del
cliente, si está disponible, o responde en la conversación. Estos comandos
los ejecuta el asistente; `accept`, solo después de tu aprobación explícita,
con el código que presentó:

```bash
atipspec audit
atipspec proposal contract
atipspec accept contract --code 11HN-G0QN
```

## Un proyecto existente

El modelo lee manifiestos, carpetas, CI y tests, y propone un contrato que
**describe lo que existe**; las reglas que cree que deberías añadir se marcan
como propuestas. Luego `atipspec audit`: cada violación se arregla ahora, tú
la aceptas como excepción (la regla se estrecha) o se descarta. Nunca se deja
atrás un audit en rojo.

## Cambiar el contrato

El contrato solo cambia con una decisión, y la puerta lo impone: una entrega
cuyo diff toca `contract.md` sin un fichero nuevo en `.atipspec/decisions/`
está en rojo.

```bash
atipspec decision allow-httpx --title "Use httpx for outbound HTTP" --affects contract:dependencies
```

El asistente prepara la decisión y el cambio de contrato en la misma entrega,
ejecuta `atipspec audit` y presenta ambos con `atipspec proposal contract`.
Tras tu aprobación explícita, ejecuta `atipspec accept contract --code <code>`,
que pone la decisión en `accepted`. Una decisión cuyo estado se fijó a mano
no forma parte del contrato aceptado: la aceptación del contrato queda
desactualizada, la puerta mantiene la entrega en rojo, las entregas antiguas
no pueden entrar en `spec`, y `atipspec context` deja fuera la decisión hasta
que el contrato se vuelva a aceptar.

!!! info "Qué pueden y no pueden comprobar las reglas"
    Las reglas son estructurales a propósito: rutas prohibidas, patrones
    prohibidos, dependencias declaradas por manifiesto, comandos
    obligatorios. Capturan la deriva que realmente ocurre en proyectos
    largos: una librería nueva, un cruce de capas, un comando de test que se
    salta. El juicio de diseño se queda con el revisor, que recibe el
    contrato completo en el paquete. Consulta la
    [referencia de reglas](../reference/contract-rules.md).
