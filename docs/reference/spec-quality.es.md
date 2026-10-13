# Escribir criterios

Una especificación es tan buena como sus criterios, y la industria ha asentado
cómo es un buen criterio: ISO/IEC/IEEE 29148 pide requisitos singulares,
inequívocos y verificables; la INCOSE Guide for Writing Requirements lista
las palabras que hacen que uno no sea verificable; EARS (Easy Approach to
Requirements Syntax) da las formas de la frase; Specification by Example pide
datos concretos; Volere pide a cada atributo de calidad un criterio de ajuste
(fit criterion). El workflow de AtipSpec los sigue, y `check` impone la parte
que una máquina puede comprobar.

## Qué verifica `check`

| Comprobación | Dónde | Nivel |
| --- | --- | --- |
| Estructura del escenario: WHEN y THEN en orden, ningún paso vacío | todos los escenarios | error |
| Forma EARS o de escenario | enunciados de criterio (`- AC-001: ...`) | estricto |
| Ningún término vago | títulos y enunciados de requisitos; enunciados de criterio; títulos de escenario y todos sus pasos | estricto |
| Un número en el resultado | criterios de un atributo de calidad | estricto |
| Cómo se mide | criterios de un atributo de calidad | warning |
| Un valor concreto en el resultado | todos los demás criterios | warning |
| Ningún término vago entre comillas | allí donde lee la comprobación de términos vagos | warning |
| `## Intent`, `## Out of scope` y `## Quality attributes` decididos | el `spec.md` de una entrega guiada | todo hasta que se aprueba la propuesta |

Un hallazgo estricto es un error con `strict_criteria: true`, el valor por
defecto, y un warning con `strict_criteria: false`. Un error o un todo de la
especificación bloquea la propuesta: `atipspec proposal` lo lista bajo «Not
ready for approval» y no muestra ningún código de aprobación, y `atipspec
accept` se niega. Un warning nunca bloquea. `proposal` lista todos los warnings
de la especificación bajo su código de aprobación; el modelo los resuelve o
nombra cada uno que mantiene cuando presenta la propuesta.

`check` lee los requisitos que la entrega define o referencia, nunca el resto
de la spec viva. En una entrega guiada, un requisito de la capacidad que
difiere del que contenía la spec viva en el commit base de la entrega
(añadido, editado, borrado o marcado con `[remove]`) pero que no figura en
`requirements` es un error en todos los niveles de riesgo, porque la
aprobación hashea solo los listados y `merge-check` bloquea un requisito
cambiado fuera de las entregas que lo listan: lístalo si este cambio lo
escribe, para que `check` lo lea, o deshaz el cambio. `new` no empieza
mientras esa spec viva tenga cambios sin commitear, así que el commit base la
tiene tal como la entrega parte de ella; una funcionalidad creada antes de
0.3.0 se compara en su lugar con su `baseline.json`. Un
requisito cambiado en la spec viva de otra capacidad también es un error: la
entrega no lo entrega, y `merge-check` lo bloquea. Lo que trajo la branch de
integración (consulta [cuando main avanza](../teams.md#cuando-main-avanza)) o
escribió una entrega archivada en la branch después de la base, tal como lo
registra su recibo, y lo que lista otra entrega abierta de la capacidad, no
es cambio de la entrega; lo que trae un merge de cualquier otra branch sí lo
es. Un recibo avala solo los requisitos que lista su entrega, tal como los
añadió el commit que la archivó, o, si aún no tiene commit, mientras `HEAD`
contenga esa entrega abierta. El texto de la spec viva fuera de sus
requisitos, antes del primero o bajo un encabezado que cierra uno, su
frontmatter, y un comentario HTML o un bloque de código cercado en un
requisito que la entrega no lista no están en ninguna aprobación: un cambio
en ellos es un warning, frente a la base del merge donde la rama de
integración los cambió, y solo los cubre la aceptación del resultado, que
liga el árbol entero.

## Las formas que acepta `check`

Con `criteria_syntax: ears` (el valor por defecto), un enunciado de criterio
empieza con un trigger o lleva un `shall`:

| Forma | Estructura | Ejemplo |
| --- | --- | --- |
| Dirigida por evento | When *trigger*, the system *outcome* | When a registered email requests a reset, the system sends a link to that email within 60 seconds. |
| Dirigida por estado | While *state*, the system shall *outcome* | While the account is locked, the system shall reject every login with "account locked". |
| Comportamiento no deseado | If *condition*, then the system *outcome* | If a link is older than 30 minutes, then the system returns "link expired" and sends nothing. |
| Característica opcional | Where *feature*, the system *outcome* | Where two-factor is enabled, the system asks for the code before showing the form. |
| Ubicua | The system shall *outcome* | The system shall reject passwords shorter than 12 characters. |
| Escenario | Given *context*, when *action*, then *outcome* | Given an order of 3 items at 10.00, when a 10% coupon is applied, then the total is 27.00. |

Los triggers que reconoce `check` son *when*, *whenever*, *while*, *if*,
*where*, *given* y *after* al principio del criterio, o *shall* o *must* en
su cláusula principal, antes de cualquier coma. En español: *cuando*,
*mientras*, *si*, *donde*, *dado* (y sus formas), *después de*, *tras*, y
*debe* o *deberá* en la cláusula principal. En portugués: *quando*,
*enquanto*, *se*, *onde*, *dado* (y sus formas), *depois de*, *após*, y
*deve* o *deverá*. Los triggers en inglés cuentan en todos los idiomas,
porque las plantillas están en inglés. Pon `criteria_syntax: free` para
desactivar la comprobación de forma; las demás comprobaciones siguen
activas. Un idioma sin tablas no tiene comprobación de forma y usa la lista
de términos vagos en inglés. Un enunciado de criterio puede continuar en
líneas sangradas.

## Escenarios

Un escenario es un encabezado de criterio bajo su requisito, con un paso por
línea:

```markdown
### REQ-001: The user can request a reset link

#### AC-001: Registered email
- **GIVEN** a registered user on the "Sign in" page
- **WHEN** the user requests a reset for that email
- **THEN** the system sends a link to that email within 60 seconds
```

El parser comprueba la estructura, diga lo que diga `strict_criteria`: WHEN y
THEN son obligatorios, los pasos siguen el orden GIVEN, WHEN, THEN, AND y BUT
amplían el paso anterior, y ningún paso está vacío. Un criterio
`[invariant]` afirma con INVARIANT o THEN y no necesita trigger. Después, el
lint lee el título del escenario y todos sus pasos en busca de términos
vagos. Las palabras de paso en español y en portugués (*DADO*, *CUANDO*,
*ENTONCES*, *QUANDO*, *ENTÃO*, ...) también funcionan, y un escenario escrito
con ellas se lee además con los términos vagos de ese idioma, sea cual sea el
idioma del proyecto.

## Términos vagos

La regla de la guía INCOSE: ningún término cuyo significado dependa del
lector. `check` informa de un requisito o un criterio que contenga uno. En
inglés:

`fast`, `quick`, `quickly`, `slow`, `user-friendly`, `user friendly`, `easy`,
`easily`, `easy-to-use`, `appropriate`, `appropriately`, `adequate`,
`adequately`, `efficient`, `efficiently`, `effectively`, `robust`, `etc.`,
`and/or`, `and so on`, `as needed`, `if possible`, `if necessary`,
`when necessary`, `as soon as possible`, `reasonable`, `reasonably`,
`sufficient`, `sufficiently`, `several`, `a few`, `many`, `some`,
`approximately`, `seamless`, `seamlessly`, `intuitive`, `intuitively`,
`optimal`, `optimally`, `flexible`, `scalable`, `as appropriate`,
`where possible`, `timely`, `minimal`, `maximize`, `minimize`, `relevant`,
`typically`, `usually`, `correctly`, `properly`, `as expected`, `as intended`,
`works well`, `work well`.

En español, además de la lista en inglés:

`rápido`, `rápida`, `rápidos`, `rápidas`, `rápidamente`, `fácil`, `fáciles`,
`fácilmente`, `amigable`, `amigables`, `adecuado`, `adecuada`, `adecuados`,
`adecuadas`, `adecuadamente`, `apropiado`, `apropiada`, `apropiados`,
`apropiadas`, `apropiadamente`, `eficiente`, `eficientes`, `eficientemente`,
`robusto`, `robusta`, `robustos`, `robustas`, `etc.`, `y/o`,
`y así sucesivamente`, `según sea necesario`, `si es necesario`,
`cuando sea necesario`, `si es posible`, `lo antes posible`, `razonable`,
`razonables`, `razonablemente`, `suficiente`, `suficientes`, `suficientemente`,
`varios`, `varias`, `unos pocos`, `unas pocas`, `muchos`, `muchas`, `algunos`,
`algunas`, `aproximadamente`, `intuitivo`, `intuitiva`, `intuitivos`,
`intuitivas`, `intuitivamente`, `óptimo`, `óptima`, `óptimos`, `óptimas`,
`flexible`, `flexibles`, `escalable`, `escalables`, `cuando sea posible`,
`oportuno`, `oportuna`, `lo mínimo`, `al mínimo`, `mínimo posible`,
`maximizar`, `minimizar`, `relevante`, `relevantes`, `normalmente`,
`habitualmente`, `correctamente`, `como se espera`, `como es de esperar`,
`según lo previsto`, `funciona bien`, `funcione bien`, `sin problemas`.

En portugués, además de la lista en inglés:

`rápido`, `rápida`, `rápidos`, `rápidas`, `rapidamente`, `fácil`, `fáceis`,
`facilmente`, `amigável`, `amigáveis`, `adequado`, `adequada`, `adequados`,
`adequadas`, `adequadamente`, `apropriado`, `apropriada`, `apropriados`,
`apropriadas`, `apropriadamente`, `eficiente`, `eficientes`, `eficientemente`,
`robusto`, `robusta`, `robustos`, `robustas`, `etc.`, `e/ou`,
`e assim por diante`, `conforme necessário`, `se necessário`,
`quando necessário`, `se possível`, `o mais rápido possível`, `o quanto antes`,
`razoável`, `razoáveis`, `razoavelmente`, `suficiente`, `suficientes`,
`suficientemente`, `vários`, `várias`, `alguns poucos`, `muitos`, `muitas`,
`alguns`, `algumas`, `aproximadamente`, `intuitivo`, `intuitiva`, `intuitivos`,
`intuitivas`, `intuitivamente`, `ótimo`, `ótima`, `ótimos`, `ótimas`,
`flexível`, `flexíveis`, `escalável`, `escaláveis`, `quando possível`,
`oportuno`, `oportuna`, `o mínimo`, `ao mínimo`, `mínimo possível`,
`maximizar`, `minimizar`, `relevante`, `relevantes`, `normalmente`,
`geralmente`, `habitualmente`, `corretamente`, `como esperado`,
`conforme esperado`, `conforme previsto`, `funciona bem`, `funcione bem`,
`sem problemas`.

Un término coincide con palabras completas, también dentro de un compuesto
con guion o de un énfasis de Markdown: `fast-loading` y `_quickly_`
coinciden. Un token con dos puntos dentro, como `theme:slow-unresponsive`, y
una cardinalidad, como `many-to-many`, son identificadores y pasan. El texto
entre comillas (`"..."`, `“...”`, `«...»`) o entre comillas invertidas no lo
lee la comprobación estricta: cita el texto literal de la interfaz, como el
botón `"Fast checkout"`, en vez de reformularlo. Una cita que contiene un
término vago recibe en su lugar un warning, para que la persona lo vea en la
propuesta, y no cuenta como valor concreto. Las palabras con usos precisos
frecuentes quedan fuera de las listas: *correct* (the correct password),
*expected* (`Expected:`), *well* (well-formed), *significant* (significant
digits), *effective* (effective date) y *a minimum of 12*.

El arreglo es siempre el mismo: sustituye el adjetivo por el valor
observable. «Responde rápido» se convierte en «responde en menos de 300 ms en
el percentil 95».

## Valores concretos

Specification by Example pide a cada resultado los datos que compara un test.
El resultado es el paso THEN o INVARIANT y los pasos AND y BUT que lo siguen
o, en un enunciado de criterio, lo que sigue a la primera coma cuando el
trigger va primero, y el enunciado entero en otro caso. `check` avisa cuando
el resultado no nombra ningún valor concreto:

- un número, como `27.00`, `60 seconds` o `HTTP 404` (el 95 de `p95` nombra
  un percentil, no un valor);
- texto entre comillas sin términos vagos, como `"link expired"`;
- una ruta, como `/orders/paid`, o una dirección, como `billing@example.com`;
- un nombre con mayúscula que no abre la frase, como la página `Sign-in`.

Un número en GIVEN no hace concreto el THEN: «Given an order of 3 items at
10.00 ... then the discount is applied» recibe el warning; «then the total is
27.00» no. Esta comprobación es una heurística, así que se queda en warning en
todos los modos.

## Requisitos

Escribe un requisito por cada comportamiento que un usuario valora,
independiente de otros cambios abiertos, lo bastante pequeño para la entrega
y comprobable: los criterios INVEST de una historia. `check` lee el título de
un requisito y las líneas que lo enuncian en busca de términos vagos. Deja
fuera sus criterios, la etiqueta `Acceptance criteria:` (el texto que la
sigue sí se lee), un párrafo `Why:` (*Por qué:*, *Motivo:*, *Por quê:*), que
da la razón, y un párrafo `Observed:` (*Observado:*), que describe un
defecto, no el requisito. Cada uno abarca, con la lista que lo sigue, hasta
una línea en blanco, un criterio u otra etiqueta como `Expected:`; una
etiqueta sola en su línea toma también el bloque que la sigue. Un elemento de
lista sangrado bajo un enunciado de criterio no forma parte del criterio, así
que se lee como texto del requisito. Un requisito marcado con `[remove]`
mantiene el título de la spec viva, así que solo se leen sus criterios. Un
fix guarda la historia del defecto bajo `## Defect` en su `spec.md`,
fuera de cualquier requisito, y corrige un requisito aceptado en `specs/`,
que se lee como cualquier otro.

## Atributos de calidad y criterios de ajuste

El rendimiento, la capacidad, la disponibilidad y la seguridad son requisitos
con criterios, como cualquier otro comportamiento, siguiendo el fit criterion
de Volere y el Planguage de Gilb: el resultado del criterio enuncia el número
con su unidad, y el criterio dice cómo se mide.

En una entrega guiada, el requisito vive en `specs/<capability>.md`, y el
`spec.md` de la entrega lo nombra bajo `## Quality attributes`, una línea por
requisito:

```markdown
## Quality attributes

- REQ-004: p95 below 300 ms with 100 requests per minute
```

Una línea que no nombra ningún requisito de este cambio es un todo mientras
la propuesta está en borrador y un error después: el límite debe ser un
requisito con un criterio, para que una tarea lo pruebe, la revisión le dé un
veredicto y la evidencia lo demuestre. `- None` dice que el cambio no tiene
ningún atributo de calidad. En una entrega antigua, el requisito se escribe
bajo `## Quality attributes` en su `spec.md`:

```markdown
### REQ-004: Response time of the reset request

Acceptance criteria:
- AC-006: When 100 users request a reset within one minute, the p95 response
  time measured at the API gateway is below 300 ms.
```

Un criterio de un atributo de calidad sin un número en su resultado es un
hallazgo estricto. Sin una palabra que diga cómo se mide (*measured*,
*medido*, *medida*, *medição*), es un warning: nombra dónde y con qué.

## Intención y alcance de una entrega guiada

`atipspec new` escribe un `spec.md` guiado con `## Intent`, `## Out of scope`
y `## Quality attributes`, y los lista bajo `sections` en el `baseline.json`
de la entrega. Hasta que se aprueba la propuesta, un Intent vacío, o uno que
solo dice `TBD`, `TODO` o `...`, es un todo que bloquea la propuesta: enuncia
el actor, el desencadenante, el resultado observable y cómo sabrá el usuario
que funcionó. Una sección Out of scope o Quality attributes sin ningún
elemento está sin decidir, y también es un todo: lista los elementos, o
escribe `- None`. Borrar uno de esos encabezados también es un todo. Aprobada
significa un registro de aprobación local del contenido actual; editar la
línea de `status` no cambia nada. Bajo una policy de confianza, cuyas firmas
son la aprobación, `check` cuenta en su lugar el `status` que pusieron las
personas; `proposal` y `accept proposal` siguen contando solo el registro
local. Una entrega creada antes de 0.3.0 sin esas dos secciones solo recibe
un warning, igual que una entrega cuya propuesta está aprobada para su
contenido actual. Esos warnings sobre una entrega aprobada esperan al siguiente
cambio de su propuesta: editar `spec.md` solo por ellos anula la aprobación.

## Rigor

Los proyectos nuevos tienen `strict_criteria: true`: un hallazgo estricto es
un error que bloquea la propuesta. Los proyectos inicializados antes de 0.3.0
conservan el `strict_criteria: false` que escribió `init`, donde los
hallazgos estrictos son warnings que la fase spec resuelve antes de presentar.
`proposal` muestra el modo antes de la aprobación: «Criteria check: strict» o
«warnings only», y dice cuándo `criteria_syntax: free` deja la forma sin
comprobar. `config.yaml` forma parte de lo que hashea la aprobación de una
propuesta guiada, así que bajar el modo después de la aprobación deja esa
aprobación desactualizada.

## Test o manual

Todo criterio se demuestra con un test o lo observa una persona. Marca el
segundo tipo en la spec, en el momento en que se escribe:

```markdown
#### AC-SHIP-4TQ8N-005 [manual]: Printed label
- **WHEN** the label prints
- **THEN** it shows the order code in Code 128
```

Un enunciado de criterio de una entrega antigua lleva la marca de la misma
forma:
`- AC-005 [manual]: When the label prints, it shows the order code in Code 128.`

El plan debe respetar la marca: un criterio `[manual]` listado bajo `Tests:`
es un error, y también lo es uno sin marcar bajo `Manual:`. Todo criterio
debe aparecer bajo uno de los dos; hasta que lo haga, `check` informa de un
todo y `atipspec build` se niega. La marca viaja con el criterio hasta la
spec viva. Un criterio puede figurar bajo `Tests:` en más de una tarea cuando
varias tareas lo ejercitan.

## Suposiciones

El modelo propone valores por defecto cuando dudas. No son silenciosos: cada
uno es un requisito y una entrada bajo `## Assumptions`, y la puerta te
recuerda que los confirmes en la aceptación. Una suposición que rechazas se
convierte en una pregunta o en un requisito distinto.

## Why y ejemplos

Una línea `Why:` bajo un requisito registra la razón, como pide ISO 29148;
evita que borre el requisito alguien que ya no sabe por qué existe. Un
ejemplo con datos reales, cuando el resultado implica un cálculo, un formato
o una fecha, es lo que Specification by Example llama un key example: tanto
el test como el revisor parten de él.

## Referencias

- ISO/IEC/IEEE 29148:2018, Systems and software engineering, requirements engineering.
- INCOSE, Guide for Writing Requirements.
- Alistair Mavin et al., Easy Approach to Requirements Syntax (EARS), 2009.
- Gojko Adzic, Specification by Example, 2011.
- Suzanne Robertson y James Robertson, Mastering the Requirements Process (Volere), tercera edición, 2012.
- Bill Wake, INVEST in Good Stories, and SMART Tasks, 2003.
- Karl Wiegers y Joy Beatty, Software Requirements, tercera edición, 2013.
- Tom Gilb, Competitive Engineering (Planguage), 2005.
