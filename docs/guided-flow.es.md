# Recorrido guiado en desarrollo

ATIPSpec prepara un acuerdo de comportamiento, solución y pruebas; el humano lo
aprueba, se implementa y se revisa, y el humano acepta el resultado. El recorrido
local no necesita firmas, un servicio central ni commits por tarea.

Esta versión introduce el núcleo del nuevo recorrido. Conserva las entregas
antiguas con requisitos embebidos; no las transforma ni reinterpreta sus
aceptaciones automáticamente.

## Preparar un cambio

```sh
atipspec new saludo --title "Saludo en español" --capability portal --owner ana
atipspec ids portal
```

La segunda orden genera IDs independientes para trabajo concurrente. Hay que
copiarlos una vez y conservarlos. Los IDs numéricos existentes siguen siendo
válidos. `ids --legacy` consulta el contador local; no coordina otros clones.

Escribir requisitos completos en `.atipspec/specs/portal.md`, sin crear archivos
vacíos para capacidades futuras. La entrega los referencia:

```yaml
schema: 2
capability: portal
requirements: [REQ-PORTAL-001]
```

Los IDs cortos de este ejemplo son ilustrativos; usar los generados para trabajo
concurrente. También se puede preparar un documento externo y ejecutar
`atipspec spec-bind saludo --file <documento.md>` para instalarlo y referenciarlo.
La orden valida el formato y mantiene los requisitos ajenos al cambio.

```markdown
# Portal

### REQ-PORTAL-001: Saludo
El portal DEBE saludar al empleado en español.

#### AC-PORTAL-001: Abrir el portal
- **GIVEN** un empleado autorizado
- **WHEN** abre la página de inicio
- **THEN** ve el texto «Hola»
```

Se admiten DADO/CUANDO/ENTONCES y marcadores en portugués. GIVEN es opcional si
no hace falta contexto. Un escenario necesita acción y resultado. `[manual]`
identifica observaciones humanas; `[invariant]` admite una afirmación INVARIANT.
Markdown no ejecuta pruebas por sí solo.

El plan describe solución, alcance, tareas y pruebas. Ejemplo para un proyecto
Python que ya usa pytest:

```markdown
---
scope: ["portal/**", "tests/**"]
---
# Plan: saludo

## Approach
Actualizar el saludo usando la estructura existente.

## Tasks
### T1: Saludo y regresión
Covers: REQ-PORTAL-001
Tests: AC-PORTAL-001

## Final verification
Report: .atipspec/tmp/junit.xml
Proof:
- AC-PORTAL-001: tests.test_portal.test_saludo
Verify:
- `python -m pytest --junitxml=.atipspec/tmp/junit.xml`
```

Las órdenes y nombres de tests deben existir en el proyecto. La selección de
pruebas depende del riesgo: navegación necesita comprobar destino y contenido;
layout necesita observación o medición con viewport; permisos requieren casos
negativos; migraciones requieren datos previos y recuperación.

## Aprobar y ejecutar

```sh
atipspec proposal saludo
atipspec accept saludo proposal --by ana
```

La propuesta muestra el acuerdo y su diff contra la baseline de creación. La
aceptación local registra contenido e identidad declarada; no autentica a quien
ejecuta la orden. El asistente solo puede registrarla cuando el humano ha dado
una instrucción explícita sobre la propuesta presentada.

Un cambio en requisitos, alcance, enfoque o verificación final invalida esa
aprobación. En planes guiados con verificación final, reorganizar tareas internas
no requiere otra aprobación; el núcleo sigue comprobando cobertura y alcance.

Durante el desarrollo, ejecutar comprobaciones focalizadas y registrar avance:

```sh
atipspec task-done saludo T1 --note "Saludo y prueba de regresión implementados"
atipspec verify saludo
atipspec review saludo
```

`task-done` declara avance, no calidad. `verify` ejecuta la sección final una vez
por candidato y conserva evidencia compartida. Si cambia el código, esa
evidencia queda obsoleta. Si un comando sale con cero pero JUnit contiene tests
fallidos, la verificación falla. Un test nombrado debe aparecer y pasar.

El revisor contrasta código, escenarios y evidencia; produce `review.md` con
veredictos y pruebas concretas. Puede terminar sin hallazgos. Se informa si su
contexto está aislado del implementador; no se presupone independencia.

Un [adaptador de proceso](execution-adapter.md) permite ejecutar estos pasos con
`atipspec run saludo`, checkpoints, bloqueo de escritor y presupuestos. Las
pruebas actuales usan procesos deterministas; la integración nativa con un
cliente/modelo sigue pendiente de validación.

## Aceptar el resultado

```sh
atipspec check saludo
atipspec report saludo
atipspec accept saludo result --by ana
atipspec deliver saludo
```

Primero se muestra el resultado observable y sus límites al humano. Un check
verde no sustituye su aceptación. `deliver` archiva el recibo y conserva las
specs aceptadas. No crea commits ni hace push, merge o despliegue.

Las organizaciones que seleccionen una política de confianza mantienen sus
controles autenticados. Una aceptación local no se convierte en una aceptación
empresarial por cambiar la configuración.
