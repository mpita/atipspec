# plan

**De una spec ready a tareas que la puerta puede demostrar.** La fase donde
se decide el cumplimiento de la arquitectura.

| | |
| --- | --- |
| Rol | Quien tendrá que mantener esto dentro de un año. Prefiere la forma más simple dentro del contrato, reutiliza lo que existe, te cuenta las decisiones con consecuencias antes de tomarlas. |
| Quién decide | Tú, con `atipspec accept <slug> plan`, cuando `approve_plan: true` en `config.yaml` (por defecto). |
| Produce | `plan.md`: enfoque y tareas |

## Cómo ejecutarla

```text
/atipspec-plan password-reset
```

El skill ejecuta `atipspec plan password-reset`, que se niega mientras la
spec no esté ready y, si no, imprime el workflow, las reglas y el contexto.

## Qué hace el modelo

1. Lee el contexto que imprimió el comando, y las áreas de código
   involucradas.
2. Comprueba el contrato. Si la spec necesita algo que el contrato prohíbe,
   se detiene: eso necesita una [decisión](contract.md#cambiar-el-contrato),
   nunca un workaround.
3. Escribe `plan.md`:

```markdown
---
scope: ["shop/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

A `reset` module under `shop/auth/` with `request()` and `consume()`,
following the contract's structure (domain must not import infrastructure,
DEC-002). Tokens stored in the existing `auth_token` table.

## Tasks

### T1: Request a reset link

Covers: REQ-001
Verify:
- `python -m pytest -q tests/auth/test_reset.py`

### T2: Expire links after 30 minutes

Covers: REQ-002
Verify:
- `python -m pytest -q tests/auth/test_reset.py`
- `python -m pytest -q`
```

4. `atipspec check password-reset` hasta que no haya errores de plan.
5. Te muestra el plan si `approve_plan` está activado y te pide que ejecutes
   `atipspec accept password-reset plan`; `atipspec build` se niega hasta
   entonces. Una tarea añadida durante el build cambia el plan, así que lo
   aceptas de nuevo.

## Qué exige `check` de un plan

- Todo requisito activo está cubierto por al menos una tarea (`Covers:`), y
  todo criterio está listado una vez bajo `Tests:` o `Manual:`, siguiendo su
  marca `[manual]` en la spec; hasta entonces `atipspec build` se niega.
- Todo `require-command` del contrato aparece en el `Verify:` de al menos una
  tarea.
- Los comandos son comandos reales del proyecto. `verify` los ejecutará desde
  la raíz del proyecto a través del shell.
- `Verify: none` está permitido cuando la única prueba es la observación, con
  una nota de qué debe observar el revisor.
- `scope` nombra los ficheros que las tareas van a cambiar, con la sintaxis
  de glob de las [reglas del contrato](../reference/contract-rules.md#globs):
  `**` cruza directorios, `*` no. Un fichero tocado fuera de él, incluida una
  eliminación, es un warning en `check` y un error con `strict_scope: true`;
  el paquete de la revisión los lista siempre que se escribe. El trabajo
  imprevisto amplía `scope` en la misma edición que añade su tarea.

## Tareas, no stories

Una tarea es un cambio coherente que se puede confirmar con un commit por sí
solo y deja el proyecto funcionando. Las tareas se ejecutan en secuencia
dentro de una entrega, y por encima de `max_tasks` el plan es demasiado
grande para una jornada de trabajo: `check` avisa y el modelo propone una
iniciativa. El trabajo que quieres ejecutar en paralelo entre varias personas
pertenece a entregas separadas; consulta [equipos y escala](../teams.md).
