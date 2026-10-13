# Diseño de AtipSpec

AtipSpec separa la asistencia de planificación, las comprobaciones técnicas
locales y la aceptación de confianza. Cada una tiene una autoridad distinta y
un modo de fallo distinto.

## Tres tiempos de vida

El contrato de arquitectura define reglas estructurales locales. Las specs
vivas conservan los IDs de requisito y de criterio, con alcance de capacidad,
a través de los cambios. Las entregas contienen la especificación propuesta,
las tareas, los mapeos de tests, la evidencia, la revisión técnica, las
excepciones de riesgo y las aprobaciones. El archivado conserva un recibo de
aceptación.

El CLI calcula el estado a partir de estos artefactos y de Git. Un registro de
`task-done` es la declaración de avance del asistente, no una prueba de
corrección semántica. El código de salida de un comando registra un resultado
de ejecución, no una cobertura de tests completa. Un puntero de prueba de la
revisión es una afirmación que el revisor técnico y el QA humano deben
evaluar.

## Aceptación local

La persona decide en la conversación; el asistente registra la decisión con
`atipspec accept`. Hay tres decisiones: la propuesta (escenarios, enfoque,
tests y riesgo; la spec, en las entregas antiguas), el resultado revisado y
el contrato con las decisiones que lo afectan, una vez por proyecto. El
mecanismo que se describe abajo no añade ninguna; la solicitud de permiso del
cliente confirma la misma decisión.

Cada decisión se presenta con una vista que imprime un **código de
aprobación**: `proposal <slug>`, `report <slug>` o `proposal contract`. El
código son los primeros 40 bits del sha256 del contenido en base32 de
Crockford (`XXXX-XXXX`), fácil de leer y de dictar; al teclearlo se ignoran
las mayúsculas y el guion. No es un secreto. Ata el registro a la versión
presentada: si el contenido cambió entretanto, `accept --code` se niega sin
revelar el código actual. Hace que la solicitud de permiso del cliente muestre
qué se está aprobando, y obliga al asistente a pasar por la vista de
presentación.

El registro guarda el hash del contenido aceptado, el digest de cada fichero,
el código, quién (`--by`, una etiqueta declarada que por defecto es la
identidad de git), cuándo y el **canal**: `terminal` cuando alguien tecleó el
código en el prompt del CLI en una terminal interactiva sin marcador de
agente; `client-permission` cuando Claude Code es el único marcador de
agente, no se ejecuta a través del Agent SDK ni de `claude -p` (que pueden no
cargar la configuración del proyecto, y cuyas solicitudes van a un programa), el
intérprete recibió la línea de comando con la que coincide su regla ask
(`atipspec accept` o `python -m atipspec accept`) y el CLI encontró intactas
sus reglas de permisos de AtipSpec en `.claude/settings.json`; `assistant` en
cualquier otro caso. Claude Code pasa su marcador a todos los procesos que
inicia, así que el marcador de otro agente junto al suyo significa que ese
agente ejecutó el comando, fuera de las reglas de Claude Code. Los marcadores
de agente del entorno (`CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`,
`COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT`) solo pueden bajar el
canal, nunca subirlo. La puerta compara el hash con los ficheros en cada
ejecución, así que un cambio hecho después de la aceptación, por un modelo o
por cualquiera, es visible, nombra el fichero y devuelve la entrega a la
persona. Las entregas guiadas necesitan el registro de la propuesta; un par
de spec y plan no lo sustituye.
El registro del contrato, `.atipspec/approvals/contract.json`, hashea el
contrato y cada decisión que lo afecta sin sus líneas de status: una decisión
añadida, editada o marcada como aceptada a mano después deja la aceptación
desactualizada. Las aprobaciones de entrega hashean `contract.md` entero, como
siempre lo han hecho las aprobaciones firmadas, así que las líneas de status
que escribe `accept contract` las dejan desactualizadas; `proposal contract`
nombra esas aprobaciones antes de que la persona decida.
Los registros viven fuera de la huella del árbol y no llevan firma: atan
contenido e indican el canal, no la identidad.

Lo que esto cubre: un asistente cooperativo pero apresurado que registraría
una aprobación por su cuenta por el camino normal. No puede hacerlo sin el
código, el registro dice cómo se hizo y, con las reglas de Claude Code, el
cliente pregunta primero a la persona y prohíbe a sus herramientas de edición
los registros de aprobación y de evidencia.
Lo que no cubre: un agente que se propone saltarse las protecciones, por
ejemplo escribiendo ficheros desde un script o borrando `review-rounds.json`
con un comando de shell, lo que reinicia la cuenta de rondas a partir del
`review.md` de la carpeta; ejecutando `atipspec accept` dentro de un script o
programa que inicia Claude Code, como un agente que no define ninguno de los
marcadores (el CLI solo ve su propio proceso, así que el registro sigue
diciendo `client-permission`); ejecutando el comando en una terminal sin
marcador de agente y tecleando él mismo el código; iniciando la sesión fuera
de la raíz del proyecto para que la configuración no se cargue; o mediante
configuración gestionada o hooks que responden a las solicitudes de permiso.
`approval-subject` se mantiene, porque el modo provider lo necesita; calcular
un hash nunca fue la barrera. El camino autenticado es una policy de
confianza externa.

## Dos puertas

Sin confianza externa, `check` valida la gramática, la cobertura, los
registros de aceptación de la persona, el scope declarado, la forma de los
criterios, los comandos y resultados exactos de la evidencia, los tests
nombrados por criterio, la frescura y las reglas locales del contrato. El
éxito es **checked**.
Como los ficheros candidatos son editables por su autor, no afirma una
ejecución autenticada ni una aceptación humana. Sin una policy, `deliver`
exige además la aceptación registrada del resultado actual.

Las dos puertas fallan de forma cerrada. El commit base, las reglas del
contrato y la frescura vienen de git, así que sin git `check` da un error en
vez de un warning. Un plan debe declarar un scope más estrecho que el
repositorio (`strict_scope`), y los requisitos y criterios deben superar las
comprobaciones de forma, de términos vagos y de criterio de ajuste
(`strict_criteria`); ambas están activadas en los proyectos nuevos.
`trust: required` en `config.yaml` convierte la falta de una policy en un
error y desactiva la aceptación local, y una branch no puede quitarlo para su
propio merge. Los valores de policy no válidos detienen todos los comandos
antes de que se ejecuten.

Con una policy externa versionada, el éxito es **verified**. La puerta exige
además evidencia de CI firmada, aprobaciones de producto e ingeniería previas
a la verificación, la aceptación de QA, los mapeos de criterio a tarea, el
contenido candidato registrado en un commit y las reglas corporativas. Los
aplazamientos de hallazgos blocker o major exigen una aprobación de riesgo
firmada con caducidad. Los cambios de contrato exigen nuevas decisiones
relacionadas y aceptadas, con aprobación de ingeniería de confianza. Los
contratos borrados y el historial ausente fallan.

## Modos de confianza

Dos modos sostienen la misma puerta. En el modo `ssh`, la autoridad es una
clave inscrita: las personas firman las aprobaciones, un recolector firma la
evidencia de CI, y una clave comprometida se revoca renovando la policy. En el
modo `provider`, la autoridad es la cuenta del proveedor y la identidad de la
plataforma de CI: el worker protegido lee las aprobaciones del PR en vivo con
un token de solo lectura, y la evidencia lleva una atestación de artefacto
que ata su digest al repositorio candidato, al pull request y a un workflow
de confianza situado fuera del repositorio candidato y fijado a un commit,
verificada con la propia herramienta de la plataforma. El workflow vive fuera
porque, en un pull request, la plataforma ejecuta los workflows que trae el
pull request: un workflow del repositorio candidato forma parte del cambio
que atestiguaría. El modo provider se eligió como recomendación por defecto
porque elimina la custodia de claves, el coste que impedía a la mayoría de
las organizaciones ejecutar la puerta de confianza, y conserva a la vez las
propiedades que importan: aprobaciones atadas al contenido, revocación
detectada en cada ejecución y evidencia que no se puede sustituir a
posteriori. Lo que no puede llevar es una caducidad, así que las excepciones
de riesgo se quedan en el modo ssh.

## Autoridad y criptografía

Las firmas SSH separadas (detached) atan los bytes exactos del artefacto a una
identidad inscrita en una policy controlada por la organización, fuera del
repositorio candidato. Cada artefacto ata también el repositorio y el digest
de la policy. El digest de la policy está fijado en el CI protegido. Un
fichero allowed-signers local al candidato no sería un ancla de confianza,
así que la puerta rechaza las policies locales al candidato.

Una clave humana es tan independiente como su custodia. Un agente con esa
clave puede firmar; ningún CLI puede inferir la presencia humana a partir de
una firma. La inscripción de la identidad humana, el aislamiento de las
claves, la integridad del verificador instalado y la configuración de las
branches protegidas pertenecen al perímetro de confianza de la organización.

Para GitHub/GitLab, un recolector lee las aprobaciones humanas existentes,
comprueba el rol, la separación respecto al autor y el marcador de
head/contenido, y luego firma el registro normalizado. La puerta vuelve a
consultar el estado del proveedor en cada comprobación, así que una respuesta
firmada en caché no puede anular una revocación. Los fallos del proveedor
fallan de forma cerrada.

La recolección de CI tiene un perímetro separado: el orquestador autentica el
workflow productor, el SHA de origen, el resultado de la ejecución y la
procedencia del artefacto antes de que el recolector use `attest`. Ese
comando no autentica una URL de CI arbitraria. El código candidato nunca debe
ejecutarse con claves de firma. Usa ejecución efímera y un recolector
protegido separado; un segundo paso en un worker comprometido no es
aislamiento suficiente.

## Frescura sin hashes circulares

La huella del código fuente y de la especificación excluye los ficheros de
evidencia, revisión, aplazamiento, aprobación e informe de la entrega. Esos
ficheros describen al candidato y no deben invalidarse a sí mismos de forma
recursiva. Los approval subjects resuelven el problema de dependencia
restante: la aprobación de riesgo ata la revisión y los términos del
aplazamiento; la aceptación de QA ata eso más el conjunto de evidencia
firmada. Por tanto, cambiar los ficheros excluidos invalida la aceptación
correspondiente aunque el hash del código fuente se mantenga constante.

`deliver` cambia la propia huella de la entrega (la carpeta se mueve y la spec
viva la absorbe), así que el recibo guarda también `code_tree`: el hash de
todo lo que hay fuera de `.atipspec/`. Nada de lo que AtipSpec escribe después
lo cambia, y cualquier cambio de código sí. `merge-check` lo compara con el
head de la branch antes del merge, y comprueba que toda entrega abierta que la
branch toca esté aceptada: el hueco entre la aceptación y el merge lo cierra
el mismo hash, no la confianza en la branch.

## Identidades duraderas

Las specs vivas se fusionan por ID de requisito, conservando los IDs de
criterio. Los títulos pueden cambiar sin cambiar la identidad. `atipspec ids`
da a cada entrega un prefijo aleatorio corto que no usa ningún ID visible en
el checkout ni en las refs del equipo, así que las branches paralelas no
colisionan; los IDs numerados de las entregas antiguas, asignados por encima
del máximo encontrado en los artefactos vivos, activos y archivados, siguen
siendo válidos. La comparación de tres vías detecta ediciones concurrentes
del mismo requisito o colisiones en la propiedad de un criterio, y `check`
informa de los IDs duplicados. Todo requisito y criterio de aceptación recibe
un ID estable desde el principio.

## Límites operativos

Las reglas del contrato comprueban rutas, patrones, dependencias y comandos
obligatorios; no demuestran la corrección arquitectónica. Los mapeos de tests
y los punteros de prueba necesitan revisión semántica. Git excluye los
ficheros ignorados de las huellas del código fuente, así que mantén
versionados los inputs de build y los lockfiles, y reproduce el entorno de
ejecución. Los informes son índices y resúmenes de evidencia firmada, no
certificaciones. Los informes archivados describen una aceptación histórica.
`merge-check` compara todo el árbol de código, así que traer la branch de
destino a una branch ya entregada, o cualquier arreglo posterior, reabre la
entrega: revierte el commit de archivo y vuelve a verificar, revisar, aceptar
y entregar. Trae la branch de destino con un merge antes de la verificación
final; una entrega por branch lo mantiene barato. En modo local, el recibo es
una declaración dentro de la branch: una edición de su `code_tree` se ve en
el diff del pull request. Con una policy de confianza, `merge-check` no se fía
de la palabra del recibo: vuelve a comprobar la entrega en el commit anterior
al commit de archivo, con los ficheros archivados con ella, como hizo
`deliver` (en modo provider, con las revisiones del pull request sobre ese
commit), exige que ese commit contenga el código del head y compara la spec
viva, también cada requisito que lista la entrega, con lo que `deliver`
escribe a partir de ese commit. Los pilotos informan de
observaciones reales con fuente, con tamaños de muestra y limitaciones; no
inventan ROI.
