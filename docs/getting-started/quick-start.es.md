# Primeros pasos

Estos ejemplos muestran la secuencia antigua de spec y plan. En las entregas
guiadas revisas comportamiento, enfoque y pruebas juntos y apruebas una sola vez
en la conversación; el agente registra `accept <slug> proposal`. El agente puede
ejecutar todos los comandos de aprobación local tras tu confirmación explícita.

Empieza con la spec y la verificación locales, luego configura la
aceptación de confianza. Los ejemplos usan Claude Code; la [página de
clientes](../clients.md) muestra el equivalente en los demás.

## 1. Define el contrato

Lo primero que hay que hacer en un proyecto es la **fase contract**. Abre una
sesión en el proyecto y di:

```text
/atipspec-contract
```

El skill ejecuta `atipspec contract`, que imprime el workflow y el contrato
actual. El modelo registra lo que ya decidiste (por ejemplo, Django y
PostgreSQL) como decisiones, solo pregunta lo que afecta a las reglas,
rellena `.atipspec/contract.md` y escribe las reglas que el CLI comprobará:

```text
dependencies pyproject.toml django psycopg "pytest*"
forbid-pattern "shop/domain/**" "from shop\.infrastructure"
require-command "python -m pytest -q"
```

Comprueba el repositorio contra él, acéptalo cuando estés de acuerdo, y haz
commit:

```bash
atipspec audit
atipspec accept contract
git add .atipspec && git commit -m "chore: architecture contract"
```

Hasta que el contrato esté aceptado, `atipspec spec` se niega a empezar una
entrega.

## 2. Empieza una entrega

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

Esto crea `.atipspec/deliveries/password-reset/` con `spec.md`, `plan.md` y
`deferred.md`, registra el commit actual como la base de la entrega, y
cambia a la branch `delivery/password-reset`.

## 3. Haz la spec, y apruébala

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

El skill ejecuta `atipspec spec password-reset`, que imprime la **fase
spec**: su workflow, las reglas y exactamente el contexto que la entrega
necesita. El modelo te entrevista en tandas cortas y escribe requisitos con
criterios de aceptación:

```markdown
### REQ-001: The user can request a reset link

Acceptance criteria:
- AC-001: A request with a registered email sends a link to that email.
- AC-002: A request with an unknown email responds like a valid one.
```

Cuando la puerta dice que la spec está completa, el modelo la presenta y
espera. Este es el **punto de parada 1**: léela, pide cambios o aprueba en la
conversación. El agente registra tu confirmación:

```bash
atipspec accept password-reset spec
```

Eso pone `status: ready` y registra lo que aceptaste; si alguien edita la
spec después, la puerta te vuelve a preguntar. El agente registra tu aprobación explícita en la conversación con este comando.

## 4. Plan, build, review

```text
/atipspec-ship password-reset
```

`atipspec ship password-reset` nombra la siguiente fase a la que la entrega
puede entrar, y cada comando de fase se niega mientras falte un paso
obligatorio. El modo ship ejecuta las fases restantes sin pausar, salvo
donde le pediste que lo hiciera:

- **plan**: enfoque y tareas, cada una con los requisitos que cubre y los
  comandos que lo demuestran. Si `approve_plan` está activado, te muestra el
  plan y espera `atipspec accept password-reset plan`.
- **build**: tarea a tarea. Código, tests, `atipspec verify`, un commit por
  tarea que lleva `[password-reset:T1]`.
- **review**: `atipspec review` escribe un paquete; un revisor en un
  contexto limpio escribe `review.md` con un veredicto por criterio.

Obsérvalo desde otra terminal en cualquier momento:

```bash
atipspec status password-reset
```

```text
AtipSpec: shop (en)
git: branch delivery/password-reset
contract: accepted
living specs: none
- password-reset [in_progress] tasks 1/2 @ana, open 3h: Password reset
    accepted: spec accepted by ana@example.com at 2026-09-13T12:39:09Z (current)
    accepted: plan accepted by ana@example.com at 2026-09-13T13:02:41Z (current)
    next: T2 is not committed: build it, run `atipspec verify password-reset --task T2` and commit with [password-reset:T2]
```

## 5. Deliver

Una comprobación local en verde significa `checked`. Configura la
[aceptación de confianza](../enterprise.md), recolecta las aprobaciones de
product/engineering antes de la verificación de CI, obtén la atestación de
CI y la aprobación de QA, y luego ejecuta:

```bash
atipspec check password-reset --policy /secure/company.toml
atipspec deliver password-reset --policy /secure/company.toml
```

Los requisitos se fusionan en `.atipspec/specs/auth.md`, la carpeta se mueve
a `.atipspec/archive/`, y el modelo te pide que fusiones la branch. Este es
el **punto de parada 2**.

## Qué acabas de conseguir

- Una spec que aprobaste, conservada para siempre en la spec viva de la
  capacidad `auth`.
- Ficheros de evidencia con los comandos exactos, los códigos de salida y el
  hash del árbol de cada tarea.
- Una revisión hecha por un contexto que nunca vio el razonamiento del
  autor.
- Un commit por tarea, y un contrato que se impuso sobre cada fichero que la
  entrega tocó.

Siguiente: [cómo funciona](how-it-works.md), o el [flujo](../flow/index.md)
fase a fase.
