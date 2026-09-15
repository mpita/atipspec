# Diseño de AtipSpec

AtipSpec separa la asistencia de planificación, las comprobaciones técnicas
locales y la aceptación de confianza. Cada una tiene una autoridad distinta y
un modo de fallo distinto.

## Tres tiempos de vida

El contrato de arquitectura define reglas estructurales locales. Las specs
vivas conservan los IDs de requisito y criterio con alcance de capacidad a
través de los cambios. Las entregas contienen la spec propuesta, las tareas,
los mapeos de tests, la evidencia, la revisión técnica, las excepciones de
riesgo y las aprobaciones. El archivado conserva un recibo de aceptación.

El CLI calcula el estado a partir de estos artefactos y de Git. Un marcador de
commit registra la autoría del trabajo, no su corrección semántica. Un código
de salida de un comando registra un resultado de ejecución, no una cobertura
de tests completa. Un puntero de prueba de la revisión es una afirmación que
el revisor técnico y el QA humano deben evaluar.

## Aceptación local

`atipspec accept`, por orden de una persona, escribe el hash de lo que aceptó:
la spec y el contrato, o la spec, el plan y el contrato. La puerta lo compara
con los ficheros en cada ejecución, así que un cambio hecho después de la
aceptación, por un modelo o por cualquiera, es visible y devuelve la entrega a
la persona. Los registros viven bajo `approvals/`, fuera de la huella del
árbol, y no llevan firma: atan contenido, no identidad. Existen para que los
dos puntos de parada sean hechos que el CLI puede comprobar, en vez de frases
en una conversación.

## Dos puertas

Sin confianza externa, `check` valida la gramática, la cobertura, los
registros de aceptación de la persona, el scope declarado, la forma de los
criterios, los comandos/resultados exactos de la evidencia, los tests
nombrados por criterio, la frescura y las reglas locales del contrato. El
éxito es **checked**.
Como los ficheros candidatos son editables por su autor, no afirma ejecución
autenticada ni aceptación humana. `deliver` rechaza una comprobación solo
local.

Con una policy externa versionada, el éxito es **verified**. La puerta exige
además evidencia de CI firmada, aprobaciones de producto e ingeniería previas
a la verificación, aceptación de QA, mapeos de criterio a tarea, contenido
candidato registrado en un commit y reglas corporativas. Los aplazamientos de
blocker/major exigen aprobación de riesgo firmada con caducidad. Los cambios
de contrato exigen nuevas decisiones relacionadas aceptadas, con aprobación de
ingeniería de confianza. Los contratos borrados y el historial faltante
fallan.

## Modos de confianza

Dos modos sostienen la misma puerta. En el modo `ssh`, la autoridad es una
clave inscrita: los humanos firman las aprobaciones, un recolector firma la
evidencia de CI, y una clave comprometida se revoca haciendo rodar la
policy. En el modo `provider`, la autoridad es la cuenta del proveedor y la
identidad de la plataforma de CI: el worker protegido lee las aprobaciones
del PR en vivo con un token de solo lectura, y la evidencia lleva una
atestación de artefacto que ata su digest al workflow que la produjo,
verificada con la propia herramienta de la plataforma. El modo provider se
eligió como recomendación por defecto porque elimina la custodia de claves,
el coste que impedía a la mayoría de las organizaciones ejecutar la puerta
de confianza, manteniendo a la vez las propiedades que importan:
aprobaciones atadas al contenido, revocación detectada en cada ejecución,
evidencia que no se puede sustituir después del hecho. Lo que no puede
llevar es una caducidad, así que las excepciones de riesgo se quedan en el
modo ssh.

## Autoridad y criptografía

Las firmas SSH separadas (detached) atan los bytes exactos del artefacto a una
identidad inscrita en una policy controlada por la organización, fuera del
repositorio candidato. Cada artefacto también ata el repositorio y el digest
de la policy. El digest de la policy está fijado en el CI protegido. Un
fichero allowed-signers local al candidato no sería un ancla de confianza, así
que la puerta rechaza las policies locales al candidato.

Una clave humana es tan independiente como su custodia. Un agente con esa
clave puede firmar; ningún CLI puede inferir la presencia humana a partir de
una firma. La inscripción de la identidad humana, el aislamiento de claves, la
integridad del verificador instalado y la configuración de las branches
protegidas pertenecen al perímetro de confianza de la organización.

Para GitHub/GitLab, un recolector lee las aprobaciones humanas existentes,
comprueba el rol, la separación de autor y el marcador de head/contenido, y
luego firma el registro normalizado. La puerta vuelve a consultar el estado
del proveedor en cada comprobación, así que una respuesta firmada en caché no
puede invalidar una revocación. Los fallos del proveedor fallan de forma
cerrada.

La recolección de CI tiene un perímetro separado: el orquestador autentica el
workflow productor, el SHA de origen, el resultado de la ejecución y la
procedencia del artefacto antes de que el recolector use `attest`. Ese comando
no autentica una URL de CI arbitraria. El código candidato nunca debe
ejecutarse con claves de firma. Usa ejecución efímera y un recolector
protegido separado; un segundo paso en un worker comprometido no es
aislamiento suficiente.

## Frescura sin hashes circulares

La huella de origen/spec excluye los ficheros de evidencia de la entrega, la
revisión, el aplazamiento, la aprobación y el informe. Esos ficheros describen
al candidato y no deben invalidarse a sí mismos de forma recursiva. Los
approval subjects resuelven el problema de dependencia restante: la aprobación
de riesgo ata la revisión y los términos del aplazamiento; la aceptación de QA
ata eso más el conjunto de evidencia firmada. Cambiar los ficheros excluidos,
por tanto, invalida la aceptación correspondiente incluso cuando el hash de
origen se mantiene constante.

## Identidades duraderas

Las specs vivas se fusionan por ID de requisito, conservando los IDs de
criterio. Los títulos pueden cambiar sin cambiar la identidad. Los IDs nuevos
se asignan por encima del máximo encontrado en los artefactos vivos, activos y
archivados. La comparación de tres vías detecta ediciones concurrentes sobre
el mismo requisito o colisiones de propiedad de un criterio. Todo requisito y
criterio de aceptación recibe un ID estable desde el principio.

## Límites operativos

Las reglas del contrato comprueban rutas, patrones, dependencias y comandos
obligatorios; no demuestran corrección arquitectónica. Los mapeos de tests y
los punteros de prueba necesitan revisión semántica. Git excluye los ficheros
ignorados de las huellas de origen, así que mantén versionados los inputs de
build y los lockfiles, y reproduce el entorno de ejecución. Los informes son
índices y resúmenes de evidencia firmada, no certificaciones. Los informes
archivados describen una aceptación histórica. Los pilotos informan
observaciones reales con fuente, con tamaños de muestra y limitaciones; no
inventan ROI.
