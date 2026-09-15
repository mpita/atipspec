# Escribir criterios

Una spec es tan buena como sus criterios, y la industria ha asentado cómo es
un buen criterio: ISO/IEC/IEEE 29148 exige requisitos singulares,
inequívocos y verificables; la INCOSE Guide for Writing Requirements lista
las palabras que hacen que uno sea no verificable; EARS (Easy Approach to
Requirements Syntax) da las formas de la frase; Specification by Example
exige datos concretos. La plantilla de spec de AtipSpec las sigue, y `check`
impone la parte que una máquina puede comprobar.

## Las formas que acepta `check`

Con `criteria_syntax: ears` (por defecto), un criterio empieza con un
trigger o lleva un `shall`:

| Forma | Estructura | Ejemplo |
| --- | --- | --- |
| Dirigida por evento | When *trigger*, the system *outcome* | When a registered email requests a reset, the system sends a link to that email within 60 seconds. |
| Dirigida por estado | While *state*, the system shall *outcome* | While the account is locked, the system shall reject every login with "account locked". |
| Comportamiento no deseado | If *condition*, then the system *outcome* | If a link is older than 30 minutes, then the system returns "link expired" and sends nothing. |
| Característica opcional | Where *feature*, the system *outcome* | Where two-factor is enabled, the system asks for the code before showing the form. |
| Ubicua | The system shall *outcome* | The system shall reject passwords shorter than 12 characters. |
| Escenario | Given *context*, when *action*, then *outcome* | Given an order of 3 items at 10.00, when a 10% coupon is applied, then the total is 27.00. |

Los triggers que `check` reconoce son *when*, *whenever*, *while*, *if*,
*where*, *given* y *after* al principio del criterio, o *shall* o *must* en
su cláusula principal, antes de cualquier coma. En español: *cuando*,
*mientras*, *si*, *donde*, *dado* (y sus formas), *después de*, *tras*, y
*debe* o *deberá* cerca del principio; los triggers en inglés cuentan en
todos los idiomas, porque las plantillas están en inglés. Un criterio en
otra forma recibe un warning que lo nombra; pon `criteria_syntax: free` para
desactivar esa comprobación. Un idioma sin tablas no tiene comprobación de
forma y usa la lista de términos vagos en inglés. La comprobación de
términos vagos se mantiene activa en todos los modos. Un criterio puede
estar listado bajo `Tests:` en más de una tarea cuando varias tareas lo
ejercitan.

## Términos vagos

La regla de la guía INCOSE: ningún término cuyo significado dependa del
lector. `check` avisa cuando un criterio contiene uno de estos, en inglés o
en español:

`fast`, `quickly`, `user-friendly`, `easy`, `appropriate`, `adequate`,
`efficient`, `robust`, `etc.`, `and/or`, `as needed`, `if possible`,
`reasonable`, `sufficient`, `several`, `many`, `some`, `approximately`,
`seamless`, `intuitive`, `optimal`, `flexible`, `scalable`, `timely`,
`minimal`, `maximize`, `minimize`.

El arreglo es siempre el mismo: reemplaza el adjetivo por el valor
observable. «Responde rápido» se convierte en «responde en menos de 300 ms
en el percentil 95».

Con `strict_criteria: true`, ambas comprobaciones son errores y bloquean la
aceptación; por defecto son warnings que la fase spec debe resolver antes de
presentar la spec.

## Test o manual

Todo criterio se demuestra con un test o lo observa una persona. Marca el
segundo tipo en la spec, en el momento en que se escribe:

```markdown
- AC-005 [manual]: When the label prints, it shows the order code in Code 128.
```

El plan debe respetar la marca: un criterio `[manual]` listado bajo `Tests:`
es un error, y también lo es uno sin marcar bajo `Manual:`. Todo criterio
debe aparecer bajo uno de los dos; hasta que lo haga, `check` reporta un
todo y `atipspec build` se niega. La marca viaja con el criterio hasta la
spec viva.

## Suposiciones

El modelo propone valores por defecto cuando dudas. No son silenciosos: cada
uno es un requisito y una entrada bajo `## Assumptions`, y la puerta te
recuerda que los confirmes en la aceptación. Una suposición que rechazas se
convierte en una pregunta o en un requisito distinto.

## Atributos de calidad

El rendimiento, la capacidad, la disponibilidad y la seguridad usan el mismo
formato `REQ`/`AC` bajo `## Quality attributes`, con un número y una forma
de medirlo, siguiendo el Planguage de Gilb y los quality attribute scenarios
del SEI:

```markdown
### REQ-004: Response time of the reset request

Acceptance criteria:
- AC-006: When 100 users request a reset within one minute, the p95 response
  time measured at the API gateway is below 300 ms.
```

Un atributo de calidad sin número es un adjetivo, y la comprobación de
términos vagos lo trata como tal.

## Why y ejemplos

Una línea `Why:` bajo un requisito registra la razón, como pide ISO 29148;
evita que el requisito lo borre alguien que ya no sabe por qué existe. Un
ejemplo con datos reales, cuando el resultado implica un cálculo, un formato
o una fecha, es lo que Specification by Example llama un key example: tanto
el test como el revisor parten de él.

## Referencias

- ISO/IEC/IEEE 29148:2018, Systems and software engineering, requirements engineering.
- INCOSE, Guide for Writing Requirements.
- Alistair Mavin et al., Easy Approach to Requirements Syntax (EARS), 2009.
- Gojko Adzic, Specification by Example, 2011.
- Karl Wiegers y Joy Beatty, Software Requirements, tercera edición, 2013.
- Tom Gilb, Competitive Engineering (Planguage), 2005.
