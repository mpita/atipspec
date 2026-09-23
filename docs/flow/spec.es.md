# spec

Estos ejemplos muestran la secuencia antigua de spec y plan. En las entregas
guiadas revisas comportamiento, enfoque y pruebas juntos y apruebas una sola vez
en la conversación; el agente registra `accept <slug> proposal`. El agente puede
ejecutar todos los comandos de aprobación local tras tu confirmación explícita.

**De la intención a una spec que el revisor puede verificar.** La fase donde
decides qué se construye.

| | |
| --- | --- |
| Rol | El especificador. Le importa el resultado observable, no la solución. Pregunta en tandas cortas, propone valores por defecto, nunca acepta «funciona bien» como criterio. |
| Quién decide | Tú, ejecutando `atipspec accept <slug> spec`. **Punto de parada 1.** |
| Produce | `spec.md` con requisitos y criterios de aceptación; tu aceptación pone `status: ready` |

## Cómo ejecutarla

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

Si la entrega todavía no existe, el modelo la crea con `atipspec new`. Luego
el skill ejecuta `atipspec spec password-reset`. El comando se niega hasta
que el contrato tiene `status: accepted`; si no, imprime el workflow, las
reglas y el contexto.

## Qué hace el modelo

1. Lee el contexto que imprimió el comando: el contrato, el overview, el
   glosario, las specs vivas de la lista de impact y las decisiones que las
   afectan. Usa las palabras del glosario y pregunta antes de aceptar un
   sinónimo.
2. Cubre, preguntando solo lo que el proyecto todavía no responde: actor y
   disparador, camino feliz, caminos de fallo, datos creados, cambiados,
   borrados o nunca tocados, fuera de alcance, límites no funcionales,
   conflictos con el comportamiento existente o con el contrato.
3. Escribe `spec.md`:

```markdown
---
title: "Password reset"
status: draft
capability: auth
impact: [notifications]
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...
created: 2026-09-12
---

# Password reset

## Intent

Let a user who forgot the password recover access without support.

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

Acceptance criteria:
- AC-001: When a registered email requests a reset, the system sends a link to that email within 60 seconds.
- AC-002: When an unknown email requests a reset, the system responds exactly like a valid one.

### REQ-002: The link expires

Acceptance criteria:
- AC-003: If a link is older than 30 minutes, then the system shows "link expired" and sends nothing.

## Quality attributes

### REQ-003: Reset requests under load

Acceptance criteria:
- AC-004: When 100 users request a reset within one minute, the p95 response time at the API gateway is below 300 ms.

## Assumptions

- The link is single-use.

## Out of scope

- Password policy changes.

## Open questions

- None
```

4. Ejecuta `atipspec check password-reset` hasta que el único todo restante
   sea tu aceptación.
5. Presenta la spec y te pide que ejecutes `atipspec accept password-reset spec`.

## Reglas de la entrevista

- Como máximo cinco preguntas por tanda, cada una ligada al requisito que
  cambia.
- Un valor por defecto que el modelo propone se convierte en un requisito y
  una suposición que confirmas en la aceptación, nunca una elección
  silenciosa.
- Todo criterio en forma EARS o de escenario con valores concretos, sin
  términos vagos, y marcado `[manual]` cuando lo observa una persona; si no,
  `check` avisa. Consulta [escribir criterios](../reference/spec-quality.md).
- Los atributos de calidad son números con una forma de medirlos, o nada.
- Una entrega cabe en una jornada de trabajo. Por encima de
  `max_requirements` el modelo propone dividirla en entregas bajo una
  iniciativa antes de pedir la aceptación; `check` avisa en cualquier caso.
- Comportamiento, nunca implementación.
- Una spec con preguntas abiertas no puede estar ready. `check` la rechaza.
- `capability` es la spec viva que recibe los requisitos en el deliver.
  `impact` lista cualquier otra spec viva o sección del contrato que la
  entrega toque: `context` las carga y `status` avisa de solapes con otras
  entregas abiertas.
- `### REQ-003 [remove]: Exact title` borra esa sección de la spec viva en el
  deliver. Así es como se retira el comportamiento: explícitamente.

## Tu parte

Léela como el contrato que es. Cambia el texto, añade criterios, recorta el
scope. Cuando diga lo que quieres, aprueba en la conversación. Para una spec antigua, el agente ejecuta:

```bash
atipspec accept password-reset spec
```

Se niega mientras haya una pregunta abierta o un requisito sin criterio; si
no, pone `status: ready` y registra un hash de la spec y del contrato. A
partir de ahí, cualquier edición a cualquiera de los dos ficheros devuelve la
entrega a draft hasta que aceptes de nuevo. El agente ejecuta este comando solo tras tu aprobación explícita en la conversación.

!!! note "Cambiar la spec después"
    Si el build revela que un criterio no se puede cumplir, el modelo debe
    detenerse y decírtelo. La spec cambia con tu acuerdo, y la entrega vuelve
    a pasar por la puerta. Los criterios nunca se debilitan en silencio y
    nunca se aplazan.
