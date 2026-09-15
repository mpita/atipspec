# review

**Un revisor que no escribió el código escribe `review.md`.** Un pase
adversarial, en un contexto limpio, atado al árbol.

| | |
| --- | --- |
| Rol, lado del autor | El autor que entrega el trabajo. No discute dentro del contexto del revisor, nunca edita `review.md`. Arregla, verifica, hace commit, vuelve a preguntar. |
| Rol, lado del revisor | Adversarial. Juzga contra la spec y el contrato, un veredicto por criterio, con un puntero a la prueba. |
| Quién decide | `atipspec check`. |
| Produce | `review.md` |

## Cómo ejecutarla

```text
/atipspec-review password-reset
```

## Qué ocurre

1. El modelo ejecuta `atipspec review password-reset`. El CLI se niega
   mientras una tarea no tenga commit, la evidencia esté obsoleta o el
   contrato esté violado, y no escribe ningún paquete. Si no, escribe un
   paquete en `.atipspec/tmp/password-reset-review-packet.md` con: la
   rúbrica, el contrato de arquitectura, las specs vivas que la entrega
   declara en su lista de impact, las decisiones aceptadas que las afectan,
   la spec, el plan, los elementos aplazados, un resumen de evidencia, los
   ficheros cambiados fuera del `scope` del plan, y el diff contra el commit
   base de la entrega más los ficheros sin seguimiento. Un diff de más de
   200 KB se sustituye por su `--stat` y un extracto truncado, con una nota
   que le dice al revisor que inspeccione el repositorio. Luego el comando
   imprime el workflow.
2. El modelo lanza al revisor **en un contexto que no ha visto la
   conversación**, dándole solo la ruta del paquete. En Claude Code esto es
   un subagente; consulta [clientes](../clients.md) para los demás.
3. El revisor lee el paquete, inspecciona el repositorio, ejecuta comandos si
   con leer no basta, y escribe:

```markdown
---
tree: cd03ae507b3605b12a497fcbcf590894a0073076
reviewer: claude-code subagent
---

# Review: Password reset

## Criteria

- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. tests/auth/test_reset.py::test_unknown_email_same_response
- AC-003: FAIL. consume() checks the age but the boundary of exactly 30 minutes is accepted.

## Findings

- F1 [blocker]: shop/domain/reset.py imports shop.infrastructure.mail, forbidden by the contract.
- F2 [minor]: request() lacks a docstring.

## Notes

The spec does not say whether a used link may be reused; assumed no.
```

4. El modelo ejecuta `atipspec check password-reset`:
    - Un `FAIL` o un `blocker`: arregla el código, verifica, haz commit.
      Cualquier cambio en el árbol deja la revisión obsoleta, así que vuelve
      a ejecutar `review` y al revisor.
    - Un hallazgo que decides no arreglar ahora va a `deferred.md` con una
      razón: `- F2: cosmetic, handled in the docs cleanup delivery`. Los
      criterios nunca se pueden aplazar.
5. Después de `review_rounds` rondas (2 por defecto) sin una comprobación en
   verde, el modelo se detiene e informa de lo que queda. Tú decides.

## Por qué un contexto separado

El contexto que escribió el código lo confirmará. Los veredictos del revisor
son los únicos que la puerta acepta, y la puerta los rechaza en cuanto el
código cambia. Una violación del contrato siempre es un blocker.

Los hallazgos blocker y major exigen resolución o una excepción de riesgo de
confianza. El verde local es `checked`; [la aceptación de
confianza](../enterprise.md) se exige para `verified` y `deliver`. La
aprobación de QA ata la revisión, las excepciones y la evidencia firmada.
