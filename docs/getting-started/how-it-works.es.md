# Cómo funciona

## Tres verdades con tiempos de vida distintos

| Verdad | Dónde | Vive | Cambia mediante |
| --- | --- | --- | --- |
| El **contrato** | `.atipspec/contract.md` | todo el proyecto | una decisión aceptada |
| Las **specs vivas** | `.atipspec/specs/<capability>.md` | el producto | `atipspec deliver` |
| Una **entrega** | `.atipspec/deliveries/<slug>/` | días o semanas | las fases |

El contrato dice cómo está construido el sistema: stack, estructura, policy
de dependencias, convenciones, quality gates, y un bloque de reglas que el
CLI evalúa. Las specs vivas dicen qué hace el producto, un fichero por
capacidad. Una entrega es la unidad de cambio: su propia spec, plan,
evidencia, revisión y hallazgos aplazados, creada, verificada y archivada
como un todo.

Alrededor de ellos están el libro de decisiones, las iniciativas que agrupan
entregas a lo largo de meses, y dos documentos curados, `overview.md` y
`glossary.md`, que mantienen el proyecto explicable en una página.

## Quién decide qué

| Pregunta | La responde |
| --- | --- |
| ¿Qué construimos? | Tú, aprobando el acuerdo presentado en la conversación |
| ¿Bajo qué reglas? | El contrato que aceptaste con `atipspec accept contract`, impuesto por `check` y `audit` |
| ¿Está una tarea terminada? | git: un commit que lleva `[slug:Tn]` |
| ¿Pasa sus comprobaciones? | `atipspec verify`, que registra los códigos de salida y el hash del árbol |
| ¿Cumple la spec? | Un revisor en un contexto limpio, un veredicto por criterio |
| ¿Está verified? | `check --policy` con evidencia de CI de confianza y aprobaciones de product/engineering/QA |
| ¿Se entrega? | Tú, fusionando |

El agente presenta el acuerdo y ofrece **Aprobar y continuar**, **Pedir cambios**
o **Cancelar**, mediante el selector del cliente o una respuesta escrita. Tras tu
aprobación explícita, ejecuta `atipspec accept` y continúa. No tienes que ejecutar
comandos ni editar estados. El verificador registra evidencias y el revisor emite
veredictos; ninguno sustituye tu decisión. Si cambia el acuerdo, requiere una nueva
aprobación. Las políticas externas conservan su procedimiento autenticado.

## Una aceptación que puedes comprobar

`atipspec accept <slug> spec` es cómo apruebas una spec: pone `status: ready`
y registra un hash de la spec y del contrato en
`approvals/local-spec.json`. `check` compara ese hash con los ficheros en
disco en cada ejecución; un solo byte editado después de tu aceptación
devuelve la entrega a `draft` con un `todo` que te nombra. Lo mismo vale para
`atipspec accept <slug> plan` cuando `approve_plan` está activado, y
`atipspec accept contract` pone `status: accepted` en el contrato.

Esto es detección de deriva, no autenticación: el registro demuestra lo que
se aceptó, no quién ejecutó el comando. Las aprobaciones firmadas bajo una
policy externa son la forma autenticada, y cuando hay una policy configurada,
la puerta ignora los registros locales. Consulta [aceptación
empresarial](../enterprise.md).

## Las fases que abre el CLI

Una fase empieza con su comando: `atipspec spec <slug>`, `atipspec plan
<slug>`, y así sucesivamente. El comando comprueba qué exige la fase y se
niega con una línea cuando falta algo: el contrato no aceptado, la spec no
ready, una tarea sin commit. Si no, imprime el workflow, las reglas y el
contexto, para que el modelo trabaje a partir de lo que abrió el CLI y no de
su propia lectura de la petición. `atipspec ship <slug>` nombra la siguiente
fase a la que una entrega puede entrar. Consulta [el
flujo](../flow/index.md#que-requiere-cada-fase).

## La puerta

`atipspec check <slug>` comprueba la consistencia local. La aceptación de
confianza exige además `--policy`. Lee los ficheros y git, e informa de tres
tipos de cosas:

- **error**: algo está mal o falló. La puerta está en rojo.
- **todo**: algo todavía no ha pasado. La puerta todavía no está en verde.
- **warning** e **info**: merecen atención, no bloquean.

```text
password-reset  [implemented]  tasks 2/2
  error   AC-003 FAIL: the link never expires
  error   F1 [blocker] contract: shop/domain/order.py:3 contains forbidden pattern 'from shop\.infrastructure'
  todo    review.md is stale (the working tree changed since the review); run `atipspec review password-reset` and review again
  info    F2 [minor] Missing docstring
Next: Fix: AC-003 FAIL: the link never expires
```

El código de salida 0 significa que las comprobaciones seleccionadas
pasaron, 1 significa errores, 2 significa incompleto. Sin una policy, el
verde es solo `checked`. `deliver` exige una puerta de confianza en verde y
la [policy externa](../enterprise.md).

## Evidencia atada al árbol

`atipspec verify` ejecuta los comandos que declara una tarea y escribe un
fichero JSON con los comandos, los códigos de salida, las colas de salida, la
duración y la **huella del árbol de trabajo**: un hash de contenido calculado
a través de un índice de git temporal, idéntico antes y después de confirmar
el mismo contenido con un commit. La revisión registra la misma huella.
Cuando el árbol cambia, ambas quedan obsoletas y la puerta las vuelve a
pedir. Hacer rebase sobre main también cambia el árbol, que es justo el
objetivo: no existe eso de «funcionaba en mi branch».

## Estado derivado

Nada se almacena. `status` y `check` calculan en qué punto está una entrega:

`draft` → `ready` → `planned` → `in_progress` → `implemented` → `checked` (local) / `verified` (de confianza) → `delivered`

Ningún status se escribe a mano: `atipspec accept` mueve una spec a `ready` y
un contrato a `accepted`, y la puerta trata un `ready` escrito a mano sin un
registro de aceptación correspondiente como un draft.

## Un contexto que no crece con el proyecto

`atipspec context <slug>` reúne exactamente lo que una fase necesita: el
contrato, el overview, el glosario, las specs vivas que nombra la lista
`impact` de la entrega, las decisiones aceptadas que las afectan, y los
propios ficheros de la entrega. Nunca el archive. Imprime el tamaño contra
`context_budget`, y `audit` avisa cuando un documento supera su tope para que
la fase **curate** pueda reducirlo.

Siguiente: [el flujo](../flow/index.md).
