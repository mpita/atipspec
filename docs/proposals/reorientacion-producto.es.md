# Propuesta de reorientación de ATIPSpec

Fecha: 22 de septiembre de 2026. Estado: implementación autorizada por el usuario,
en curso. Consultar [evidencia y pendientes](implementation-status.md); el diseño
completo todavía no está implementado ni validado.

## 1. Decisión de producto

ATIPSpec debería ayudar a un equipo a convertir una necesidad en un acuerdo revisable y ejecutar ese acuerdo hasta presentar un resultado probado. El usuario trabaja con un interlocutor; los roles especializados, las tareas y las comprobaciones se coordinan detrás de esa conversación.

Propuesta de valor: **«Define y aprueba lo que necesitas; ATIPSpec coordina la implementación, las pruebas y la revisión, y te devuelve un resultado listo para aceptar».**

El mercado inicial son desarrolladores y factorías con varios proyectos y equipos, distintos asistentes de programación y procesos Git existentes. La aceptación local debe funcionar por defecto. Las firmas, las políticas externas y las aprobaciones del proveedor son integraciones opcionales.

La autonomía comienza después de aprobar una versión concreta de la propuesta. No permite reinterpretar requisitos, debilitar pruebas para conseguir verde ni declarar que un humano aceptó un resultado que todavía no ha visto.

## 2. Evidencia que motiva el cambio

### Ensayo local

En `/Users/mpita/Sandbox/atipspec-test-project/my-site` se observaron tres entregas, seis tareas y nueve registros de verificación. Estos registros contienen 43 ejecuciones de comandos, nueve builds y 61,74 segundos acumulados de ejecución. No incluyen todas las ejecuciones realizadas durante las revisiones ni otras operaciones fuera del recolector.

Entre el primer commit de inicialización y el último de revisión transcurren aproximadamente dos horas y dos minutos. Ese intervalo incluye preparación, interacción y posibles pausas; no mide por sí solo el tiempo de trabajo ni el coste atribuible al framework.

Hay doce documentos Markdown de entrega con 808 líneas, incluidos comentarios de plantilla, y tres especificaciones vivas con 21 líneas y ningún requisito. El commit `3702d64` actualiza evidencias de T1 y T2 después de T3: incorpora 314 líneas en catorce archivos sin funcionalidad nueva.

La arquitectura actual explica esos síntomas: la evidencia por tarea está ligada a la huella global del repositorio; las tareas posteriores la invalidan. La fase de contrato crea especificaciones de capacidad vacías, que solo reciben requisitos al cerrar. El cierre requiere una política externa aunque el trabajo se haya aceptado y comprobado localmente.

### Señales de comunidades

La investigación es cualitativa: issues y conversaciones autoseleccionadas, con versiones y situaciones diferentes. No constituye una encuesta representativa ni una medición comparativa de productividad. Los reportes antiguos se usan como problemas de diseño que conviene evitar, no como prueba de que persisten en las versiones actuales.

| Señal | Fuente primaria de la experiencia | Implicación para ATIPSpec |
|---|---|---|
| Se aprecia el contexto de planificación, pero también se denuncia exceso de documentos. | [Comparación comunitaria, diciembre de 2025](https://www.reddit.com/r/ClaudeCode/comments/1pba1ud/spec_driven_development_sdd_speckit_openspec_bmad/) | Documentación progresiva, con resumen y detalle bajo demanda. |
| Usuarios de un equipo describen Spec Kit como excesivo para parte de su trabajo; otros prefieren la sencillez de OpenSpec. | [Conversación de septiembre de 2026](https://www.reddit.com/r/SpecDrivenDevelopment/comments/1w4u5r5/speckit/) | Poder empezar con un cambio pequeño y ampliar el proceso según el riesgo. |
| Un reporte de BMAD alpha describe recarga de contexto y demasiados pasos sin aplicar las correcciones. | [BMAD #1188, diciembre de 2025, cerrado](https://github.com/bmad-code-org/BMAD-METHOD/issues/1188) | Reanudar y corregir dentro del recorrido autorizado; evitar obligar al usuario a transportar contexto. |
| Las convenciones de ramas pueden bloquear la adopción en un equipo. | [Spec Kit #1110, noviembre de 2025, cerrado](https://github.com/github/spec-kit/issues/1110) | Respetar ramas y tickets existentes; separar identidad del cambio y nombre de rama. |
| Usuarios preguntan cómo encajar SDD en equipos que ya planifican en Jira o Linear. | [Conversación sobre trabajo en equipo, junio de 2026](https://www.reddit.com/r/SpecDrivenDevelopment/comments/1txjtg7/how_do_you_use_specdriven_development_in_a_team/) | Aceptar documentación y tickets existentes y evitar una segunda planificación equivalente. |
| Un autor de una extensión señala la dificultad de comentar requisitos concretos desde un chat. Es una experiencia interesada, no una evaluación independiente. | [Experiencia con OpenSpec, agosto de 2026](https://www.reddit.com/r/SpecDrivenDevelopment/comments/1vysadk/i_implemented_openspec_support_in_my_intellij/) | Permitir comentarios por requisito y mostrar diferencias desde la última aprobación. |
| Un reporte de OpenSpec describe exploración redundante por cargar tarde el contexto. | [OpenSpec #1651, agosto de 2026](https://github.com/Fission-AI/OpenSpec/issues/1651) | Cargar primero decisiones y contexto relevante, comprobando que siguen vigentes. |

Las alternativas ya están evolucionando. [BMAD documenta distintos recorridos](https://blog.bmadcode.com/bmad-method-has-three-flows-now-heres-what-actually-changes-between-them/) y [BMad Loop](https://github.com/bmad-code-org/bmad-loop) ofrece orquestación determinista, reanudación y límites de ejecución, todavía en beta. [Spec Kit admite extensiones, presets y bundles](https://github.github.io/spec-kit/guides/customization.html), y su [guía para funcionalidades complejas](https://github.github.io/spec-kit/concepts/complex-features.html) reconoce el coste de contexto y de descomponer en exceso. ATIPSpec deberá demostrar una experiencia mejor; la mera lista de capacidades no basta.

## 3. Principios del recorrido

1. Un interlocutor visible y roles activados por necesidad.
2. Especificaciones comprensibles para negocio, con escenarios verificables.
3. Una aprobación conjunta de alcance, plan y estrategia de pruebas en el caso habitual.
4. Ejecución autónoma dentro de lo aprobado, con recuperación de interrupciones.
5. Una presentación final del resultado y aceptación humana explícita.
6. Control proporcional al riesgo, no al número de archivos o líneas.
7. Git y archivos abiertos como soporte inicial; ningún servicio central obligatorio.
8. Calidad evaluada por comportamiento y evidencia, no por cantidad de documentos o revisores.

## 4. Roles y contratos de responsabilidad

Un rol define entradas, decisiones permitidas, salida mínima y límites. No implica siempre un proceso o un modelo adicional.

| Rol | Responsabilidad y salida mínima | Límites |
|---|---|---|
| Guía/coordinador | Entiende la solicitud, consulta contexto, selecciona profundidad, presenta decisiones y resume progreso. | No aprueba por el humano ni determina por opinión si pasó un comando. |
| Analista de producto | Define actor, resultado, alcance, escenarios y preguntas pendientes. Actualiza las specs correspondientes. | No inventa decisiones de negocio ni añade funcionalidad fuera de la intención. |
| Diseñador técnico | Propone solución, componentes afectados, contratos compartidos, tareas y recuperación cuando aplica. | No impone arquitectura nueva para un cambio que cabe en la existente. |
| Especialista de pruebas | Examina escenarios antes de implementar, identifica casos negativos y estrategia de comprobación. Después evalúa la suficiencia de los tests. | No confunde número de tests o cobertura de líneas con cobertura de comportamiento. |
| Implementador | Modifica código y tests dentro del acuerdo; devuelve cambios y resultados de ejecución. | No cambia expectativas para ocultar un fallo. |
| Revisor independiente | Contrasta intención aprobada, diff y evidencia; devuelve hallazgos concretos con localización y justificación. | No exige un mínimo artificial de defectos ni introduce preferencias como bloqueos. |

El coordinador conversacional usa el modelo; las transiciones de estado, la validación de artefactos, la ejecución de comandos y los límites de reintentos pertenecen al núcleo determinista.

### Activación por riesgo

- **Cambio pequeño y reversible:** guía/analista, implementador y revisión breve. Diseño y estrategia de prueba caben en la propuesta. No requiere seis sesiones.
- **Funcionalidad habitual:** producto y diseño preparan la propuesta; pruebas comprueba los escenarios antes de aprobar; implementación y revisión se ejecutan después.
- **Cambio de riesgo alto:** activar revisión especializada para permisos, aislamiento de datos, dinero, migraciones, contratos públicos o infraestructura. La profundidad y responsables aparecen en la propuesta.

Una revisión con contexto limpio reduce el anclaje al razonamiento del autor, pero no demuestra independencia humana ni elimina errores correlacionados del modelo. Si el cliente no puede crear sesiones independientes, ATIPSpec debe mostrar esa limitación. La portabilidad se expresa mediante capacidades del adaptador, no mediante garantías idénticas ficticias.

## 5. Cómo guía al usuario

El recorrido admite una idea, un ticket, un documento existente o una spec. Antes de preguntar, inspecciona las decisiones aplicables, el código y las pruebas relevantes. Distingue lo decidido por el usuario, lo observado en el repositorio y lo propuesto como suposición.

Agrupa dos o tres preguntas de alto impacto por ronda como orientación de experiencia, no como máximo rígido que oculte incertidumbres importantes. Las preguntas deben indicar qué decisión cambian. Los detalles internos reversibles pueden quedar delegados; las decisiones de negocio no se sustituyen por supuestos silenciosos.

Antes de presentar la propuesta, producto, diseño y pruebas resuelven sus contradicciones dentro del alcance conocido. Si hay una alternativa con consecuencias de coste, datos, permisos o experiencia, el guía la presenta al usuario. Se evita que cada rol repita una entrevista.

## 6. La aprobación es un acuerdo de ejecución

La vista de aprobación tiene dos niveles:

- **Resumen:** problema, resultado observable, alcance, exclusiones relevantes, riesgo, decisiones pendientes y qué hará el agente.
- **Detalle:** escenarios, diseño pertinente, tareas, pruebas previstas y diferencias respecto de la versión anterior.

En el flujo habitual, «Aprobar y ejecutar» aprueba una versión de ese conjunto. Se conserva un identificador de versión y un digest del contenido aprobado. No se exige al usuario conocer comandos de hash, claves o archivos de aprobación.

Una aprobación desde conversación debe responder a una presentación inequívoca de esa versión. Una edición posterior invalida la referencia anterior cuando afecta al acuerdo. El adaptador registra una instrucción humana explícita o deriva a una aceptación local; jamás deduce aprobación de un texto producido por el agente. Sin autenticación externa, el registro declara honestamente que es aceptación local.

### Qué puede resolver el agente después

Puede corregir errores, añadir pruebas, reorganizar pasos internos, ajustar nombres privados o refactorizar dentro de lo necesario para cumplir el acuerdo. Esas decisiones se registran sin imponer otra aprobación.

Requieren revisión del acuerdo los cambios en resultado observable, alcance funcional, contratos públicos, permisos, tratamiento de datos, dependencias de terceros relevantes, coste operativo o restricciones aprobadas. Si la clasificación es ambigua, se presenta la diferencia y se solicita decisión. Ningún clasificador semántico se considera una demostración infalible.

El plan separa **compromisos aprobados** y **descomposición operativa**. Los primeros se versionan e invalidan al cambiar; la segunda puede evolucionar dentro de esos límites. Así, añadir una subtarea de prueba no obliga a aprobar otra vez toda la especificación.

Las organizaciones pueden separar aprobación de producto e ingeniería. El equipo pequeño conserva un único punto previo a la ejecución.

## 7. Autonomía y estados

Estados propuestos: `draft → awaiting_approval → approved → running → ready_for_acceptance → accepted`.

Durante `running`, el motor ejecuta implementación, verificaciones y revisión; conserva checkpoints para continuar. Las situaciones `needs_decision`, `blocked` y `failed` se distinguen y explican. Integración y publicación son estados posteriores independientes: una aprobación de plan no autoriza implícitamente desplegar.

El agente prepara todo lo necesario para la aceptación: código, pruebas, revisión, actualización documental, diff y demostración cuando aplica. Los commits y la preparación de PR siguen la configuración y autorización del repositorio. El merge y despliegue siguen su política explícita.

Límites iniciales sugeridos y configurables:

- Dos ciclos automáticos de corrección de un mismo hallazgo antes de escalar.
- Presupuesto de tiempo y, donde el cliente lo informe, de tokens/coste.
- Sin progreso material entre ciclos: detener y explicar el bloqueo.
- Escalar una ambigüedad con alternativas concretas, no con un informe genérico de cientos de líneas.

Corregir un hallazgo requiere comprobar el arreglo y su posible regresión. Un nuevo hallazgo real no se oculta porque se agotó el presupuesto: queda pendiente y bloquea cuando corresponde.

## 8. Especificaciones y artefactos

### Fuente funcional

`specs/` conserva requisitos y escenarios por capacidad. No contiene shells vacíos para funcionalidades aún no definidas. Un overview opcional recoge posibilidades futuras sin presentarlas como requisitos.

Las specs se editan junto con el código en la rama del cambio. El contenido en esa rama es propuesto mientras la entrega está abierta; la rama principal conserva la baseline aceptada. En modo local sin ramas, el estado y la baseline registrada deben distinguir claramente cambios pendientes de la versión aceptada.

La entrega referencia los requisitos modificados y contiene intención del cambio, tareas y estrategia de verificación. No copia íntegra la definición funcional. El diff respecto de una baseline inmutable forma parte de la propuesta y de su aprobación.

### Formato recomendado

```markdown
# Navegación del portal

## Propósito
Permitir que los empleados accedan a las secciones del portal.

### REQ-NAV-001: Acceso a las secciones
El portal DEBE ofrecer enlaces a Inicio, Preguntas frecuentes y Herramientas.

#### AC-NAV-001: Acceder a la guía de herramientas
- **GIVEN** un empleado está en la página de inicio
- **WHEN** selecciona «Herramientas» en el menú
- **THEN** accede a `/herramientas`
- **AND** ve «Herramientas de IA disponibles»
```

Es una convención Markdown inspirada en escenarios BDD, no una afirmación de ejecución automática de Gherkin ni de certificación normativa. [Gherkin](https://cucumber.io/docs/gherkin/reference/) define el significado de contexto, acción y resultado. Se admiten marcadores traducidos y se mantiene consistente el idioma del texto.

El esquema se normaliza internamente y valida IDs, contexto necesario, acción y resultado; admite invariantes y requisitos no funcionales cuando forzarlos a una acción ficticia empeora la claridad. Detectar palabras vagas es una ayuda, no una validación semántica completa.

Los IDs del ejemplo son ilustrativos. Los existentes se preservan. Para nuevas entidades creadas concurrentemente se necesitan IDs con unicidad independiente de un contador local: namespace de repositorio/capacidad y un componente generado por cambio, con alias legible opcional. Nunca renumerar silenciosamente requisitos al integrar.

### Tamaño documental

- Cambio pequeño: spec modificada si cambia el comportamiento y un documento breve de cambio. Un arreglo que restaura un requisito existente lo referencia sin reescribirlo.
- Cambio habitual: lo anterior y plan ampliado solo cuando mejora la revisión.
- Cambio de alto riesgo: diseño y decisiones adicionales según necesidad.
- Estado y evidencia: generados por el motor. Un recibo compacto versionable; logs extensos como artefactos con retención configurada. La vista HTML es una proyección, no otra fuente de verdad.

Como guía, una propuesta pequeña debería poder entenderse en una pantalla o en menos de dos minutos. No se corta información decisiva para cumplir una cuota de líneas.

## 9. Estrategia de pruebas

El especialista de pruebas interviene antes de implementar: pregunta qué podría fallar aunque el camino feliz funcione y qué comprobación observaría el resultado real.

| Riesgo o comportamiento | Comprobación apropiada |
|---|---|
| Texto fijo y estructura semántica | Prueba de render pertinente; evitar expectativas accidentales sobre todo el HTML. |
| Navegación | Destino y contenido de llegada; smoke en navegador si el resultado depende de routing/hidratación. |
| Espaciado o layout | Medición o inspección en navegador con viewport registrado. |
| Regla de negocio | Ejemplos, bordes, entradas inválidas e invariantes. |
| Permisos y multitenencia | Casos negativos de acceso y aislamiento entre identidades/empresas. |
| Migración | Datos previos, aplicación y recuperación sin pérdida según el plan. |
| Contrato entre servicios | Pruebas de contrato y compatibilidad proveedor/consumidor. |

No se exigen tests nuevos para todo cambio trivial si no aportan una comprobación útil. Una comprobación manual declarada no se convierte automáticamente en un test pasado.

### Dos momentos de ejecución

1. **Desarrollo:** pruebas focalizadas, y reproducción roja previa para defectos cuando sea viable. Sirven para iterar; no necesitan convertirse en evidencia final por tarea.
2. **Verificación final:** ejecutar la selección aprobada y los controles del proyecto sobre el candidato terminado. Un mismo resultado puede respaldar varios escenarios.

La deduplicación se limita a una ejecución compartida con igual comando, directorio, configuración, entorno y estado. No se deduplican pasos que deliberadamente deben repetirse o producen efectos dependientes del orden. En la primera versión no se necesita un sofisticado caché de impacto: basta con ejecutar la verificación global una vez por candidato.

Si cambia el código después, la evidencia afectada queda obsoleta. Si no puede demostrarse qué parte afecta, se repite la comprobación completa. Debe incluirse la identidad de inputs, configuración y dependencias relevantes; el hash del código aislado no describe todo entorno de ejecución.

### Cobertura y revisión

Cada escenario se muestra como probado automáticamente, observado manualmente, pendiente o no satisfecho. Cuando hay un resultado de test estructurado, se vincula al test real; cuando solo hay un comando, el informe no finge granularidad que no tiene. JUnit es una entrada inicial útil; no se obliga a rellenar manualmente el mismo vínculo en cuatro lugares.

La revisión exige hallazgos reproducibles o bien justificados, con severidad vinculada al efecto. Debe aceptar «sin hallazgos». Puede reutilizar resultados vigentes y ejecutar comprobaciones adicionales motivadas. Para riesgos altos puede exigirse reproducción independiente. Mutation testing y pruebas por propiedades se activan donde aporten valor y exista soporte, no por defecto en una landing.

## 10. Varios equipos

### Dentro de un repositorio

La unidad de asignación es un cambio con un responsable humano, no cada acción interna del agente. Cada cambio tiene identidad estable, ticket opcional, capacidades afectadas, baseline y dependencias. El equipo conserva sus nombres de rama.

Cambios simultáneos usan ramas/worktrees independientes. Los roles que trabajan sobre un mismo checkout tienen un único escritor activo; los revisores no escriben código mientras otro rol modifica ese árbol. La concurrencia se habilita por independencia real, no por número de agentes disponibles.

Se declaran propietarios de capacidades y contratos. Antes de ejecutar e integrar se comparan cambios publicados por otros equipos. Coincidir en un requisito o contrato genera una advertencia y, si cambian incompatiblemente sus expectativas, exige reconciliación. Un merge textual limpio no demuestra compatibilidad de requisitos.

Un CLI local solo ve refs y metadatos disponibles. No puede detectar una rama no publicada en el equipo de otra persona. La integración Git/PR o un servicio opcional debe publicar esos datos; los bloqueos son avisos salvo que el proveedor los haga cumplir.

### Entre repositorios

Una iniciativa puede enlazar varios cambios: API, interfaz y despliegue. Los contratos compartidos se fijan por versión o commit inmutable, no mediante una ruta local mutable. Cada consumidor registra qué revisión utiliza.

Ejemplo: el equipo de API define `customers-api@<revision>`; frontend construye contra esa versión; integración ejecuta pruebas de compatibilidad antes de la entrega conjunta. Una ruptura de contrato solicita decisión del responsable y actualiza las dependencias. Terminar ambos repositorios por separado no implica terminar la iniciativa.

Jira/Linear conservan la responsabilidad del backlog cuando ya existen. ATIPSpec enlaza el ticket y deriva tareas internas; no crea un segundo gestor obligatorio. Las sincronizaciones externas son explícitas y preservan una autoridad clara por campo para evitar edición divergente.

### Vista compartida

La vista útil indica responsable, estado, capacidad afectada, versión de interfaz, dependencias y decisión pendiente. Al principio puede ser una consulta CLI/HTML derivada de repositorios y PRs. Una plataforma web central no es requisito del primer lanzamiento.

## 11. Arquitectura del producto

### Núcleo determinista

- Modelo versionado de requisitos, escenarios, cambios, aprobaciones y ejecuciones.
- Parsers y validaciones estructurales.
- Máquina de estados y checkpoints recuperables.
- Runner de comprobaciones y normalización de resultados.
- Comparación entre propuesta aprobada, estado candidato y baseline.
- Construcción de contexto relevante y vista de diferencias.
- Coordinación Git y detección de conflictos declarados.

### Roles y adaptadores

Las instrucciones de rol producen salidas estructuradas; el núcleo comprueba su forma y las evidencias observables. Los adaptadores declaran si soportan sesiones separadas, ejecución en segundo plano, interrupción, reanudación, lectura de costes y decisiones humanas.

Un skill por sí solo puede conducir al modelo mientras la sesión está activa, pero no garantiza que continúe después de cerrarse. La ejecución desatendida requiere un runner soportado. El primer alcance debería elegir un adaptador completo y probarlo, manteniendo los demás en modo guiado con capacidades explícitas.

El contexto se carga por tarea y por rol, con referencias y versiones. Los resúmenes son índices revisables; no sustituyen la lectura del código actual cuando una decisión depende de él. Si no hay datos de tokens o coste, se informa «no disponible», nunca cero.

### Extensiones

Firmas, políticas corporativas, sincronización de tickets, verificadores adicionales y panel central quedan fuera del recorrido básico. Las configuraciones organizativas se versionan y actualizan explícitamente; un proyecto ve qué hereda y qué puede modificar.

## 12. Qué conservar y qué cambiar del código actual

| Área | Tratamiento propuesto |
|---|---|
| Git, IDs estables, trazabilidad, reportes y adaptación a clientes | Conservar y evolucionar con esquemas versionados. |
| `deliver.py`, `check.py`, `assurance.py` | Desacoplar aceptación local y confianza externa; permitir cierre normal sin credenciales. |
| `verify.py`, comprobación de evidencias | Introducir ejecución final compartida y separar resultados de desarrollo. |
| `delivery.py`, `lint.py`, plantillas | Añadir escenarios estructurados, mensajes claros y compatibilidad con el formato existente. |
| `phases.py`, skills de fase y `ship` | Evolucionar hacia coordinador, estado reanudable y una entrada principal. |
| `context.py` | Selección por rol/tarea y referencias vigentes, con presupuesto y explicación del contexto cargado. |
| `traceability.py`, creación de IDs y worktrees | Resolver unicidad concurrente, baseline y cambios sobre contratos. |
| Módulos de confianza | Mantener compatibilidad para quienes ya la usan; activación explícita y garantías diferenciadas. |

La migración debe ser optativa, mostrar un diff y preservar los documentos originales y aprobaciones históricas. No convertir una aceptación local antigua en aceptación empresarial ni recalificar evidencia histórica como recién ejecutada.

## 13. Secuencia de implementación propuesta

### Hito A: completar una entrega pequeña

Cerrar localmente; verificar una vez por candidato; dejar specs completas; emitir una propuesta y un resultado breves. Repetir `my-site` y una corrección visual existente. No empezar por una nueva plataforma web.

### Hito B: aprobación y ejecución autónoma

Propuesta conjunta, roles selectivos, revisión separada, ejecución reanudable y límites. Probar interrupción durante tests, fallo de herramienta, cambio de requisito y agotamiento del presupuesto.

### Hito C: dos equipos sin interferencias

Ramas existentes, ownership, contratos fijados, dependencias y reconciliación. Probar dos cambios concurrentes sobre requisitos distintos y dos incompatibles sobre el mismo requisito, además de un cambio API/frontend entre repositorios.

### Hito D: facilidad de adopción y ecosistema

Importación revisable de especificaciones externas, comentarios por escenario, plantillas por stack y configuración organizativa. Publicar ejemplos, migraciones y matriz real de capacidades de clientes. Incorporar más adaptadores después de demostrar el primero.

## 14. Criterios para situar ATIPSpec entre las mejores opciones

El diseño no justifica subir hoy su nota. Se necesitan pruebas del producto, pilotos y mantenimiento. Los siguientes son objetivos propuestos, no resultados obtenidos:

| Dimensión | Evidencia requerida |
|---|---|
| Adopción | Un desarrollador nuevo completa un cambio pequeño sin asistencia del autor ni configuración de firmas. Medir tiempo y abandonos. |
| Fluidez | Dos momentos humanos en el caso ordinario: aprobar propuesta y aceptar resultado. Contar por separado aclaraciones, cambios de alcance e incidencias. |
| Autonomía | Completa el recorrido aprobado y se recupera tras interrupciones sin repetir pasos válidos ni atribuirse permisos nuevos. |
| Pruebas | Cada escenario aceptado tiene evidencia apropiada, sin confundir lint/build con prueba funcional; los tests detectan defectos relevantes introducidos de forma controlada. |
| Equipos | Detecta conflictos sobre requisitos/contratos publicados y permite trabajar sobre cambios independientes sin un archivo central continuamente disputado. |
| Claridad | Revisores comprenden qué aprueban y detectan contradicciones deliberadas en las propuestas; medir comprensión además de longitud. |
| Eficiencia | Comparación de tiempo humano, duración total, ejecuciones duplicadas y coste disponible contra el proceso previo y alternativas. |
| Madurez | Instalación, actualizaciones y migraciones probadas; CI real, mantenimiento documentado y uso sostenido por equipos externos. |

Piloto inicial: al menos dos equipos y un conjunto de cambios comparable que incluya interfaz pequeña, regla de negocio, arreglo, integración y migración. Mantener constantes modelo, herramientas y entorno cuando sea posible; registrar versiones y experiencia previa. Alternar el orden para reducir el efecto de aprendizaje. Comparar también con el flujo nativo del agente, no solo con frameworks.

Acordar antes de empezar las tolerancias de calidad y el coste aceptable. Una hipótesis útil es reducir al menos un 30 % el tiempo humano de coordinación respecto al ATIPSpec actual sin empeorar los resultados de calidad en los casos evaluados. Ese porcentaje es una meta de diseño a negociar, no una promesa. Los defectos poco frecuentes exigen ventanas mayores; un piloto pequeño solo permite conclusiones exploratorias.

La oportunidad es especialmente clara si ATIPSpec combina especificaciones fáciles de revisar, ejecución recuperable y coordinación entre equipos con un coste diario bajo. Esa combinación deberá demostrarse en proyectos reales para justificar una posición superior a herramientas con ecosistemas ya establecidos.
