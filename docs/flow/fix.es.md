# fix

**De un reporte de defecto a un criterio de regresión, un plan de una tarea y
la misma puerta.** Sin entrevista, sin aceptación de plan, sin atajos en la
evidencia ni en la revisión.

| | |
| --- | --- |
| Rol | Quien arregla sin ampliar. Reproduce primero, escribe el criterio que falla hoy y pasa mañana, no cambia nada que el defecto no exija. |
| Quién decide | Tú aceptas la spec con `atipspec accept <slug> spec`. **Punto de parada 1.** |
| Produce | `spec.md` con un requisito y un criterio de regresión, `plan.md` con una tarea, código, evidencia, un commit |

## Cómo ejecutarla

```bash
atipspec new bug-123 --title "Reset link never expires" --capability auth --ticket SHOP-9 --kind fix
```

```text
/atipspec-fix bug-123: a reset link created yesterday still works
```

El skill ejecuta `atipspec fix bug-123`, que se niega en una entrega que no
es un fix o mientras el contrato no esté aceptado, y si no, imprime el
workflow, las reglas y el contexto.

## Qué crea `new --kind fix`

Una spec con `kind: fix`, `## Intent` nombrando el defecto, un `REQ-001` con
Observed, Expected y Why, y un `AC-001` para rellenar en forma EARS:

```markdown
### REQ-001: Reset link never expires

Observed: a link created 26 hours ago still resets the password.

Expected: a link older than 30 minutes is refused.

Why: auth/REQ-002 in the living spec.

Acceptance criteria:
- AC-001: When a reset link is 31 minutes old, the system returns "link expired" and sends nothing.
```

Y un plan con una tarea, `T1: Fix and regression test`, que cubre `REQ-001`,
testea `AC-001`, cuyo `Verify:` ya lista todos los `require-command` del
contrato.

## Qué es distinto de una entrega

- Sin entrevista: el criterio viene del reporte. El modelo hace una sola
  pregunta cuando el comportamiento esperado no está claro a partir del
  reporte o de las specs vivas.
- Sin aceptación de plan, diga lo que diga `approve_plan`: el plan es una
  tarea.
- `max_requirements` es 2. Una reparación que necesita más no es un fix.
- Si la reparación cambia un comportamiento que declara una spec viva, es una
  entrega: el modelo se detiene y lo dice.

Todo lo demás es igual: tu aceptación de la spec, la evidencia atada al
árbol, un commit con `[bug-123:T1]`, la revisión en un contexto limpio, la
puerta de confianza y `deliver`.
