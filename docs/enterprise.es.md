# Aceptación empresarial

AtipSpec separa **checked** (comprobaciones estructurales y técnicas locales)
de **verified** (evidencia de confianza y aceptación humana). Bajo una policy
de confianza, `deliver` exige verified; `trust: required` hace obligatoria la
policy.

## Aceptación local y aceptación de confianza

Sin una policy, `atipspec accept --code <code>` registra lo que una persona
aprobó en la conversación (la propuesta, el resultado, el contrato; la spec y
el plan de las entregas antiguas) y la puerta detecta las ediciones
posteriores. El registro indica su canal: `terminal` (el código se tecleó en
el prompt del CLI), `client-permission` (Claude Code estaba configurado para
preguntar a la persona antes del comando) o `assistant` (no se preguntó
nada). Incluso el canal local más fuerte dice cómo estaba configurado el
cliente, no quién confirmó: es detección de deriva más un relato honesto del
camino, no identidad. Con una policy, la puerta ignora esos registros y exige
las aprobaciones firmadas y ligadas a un rol que se describen abajo, que
autentican a cada aprobador con una clave inscrita o con la propia revisión
del proveedor.

## Exigir la policy de confianza

La policy se queda fuera del repositorio; el repositorio solo puede declarar
que es obligatoria. Pon `trust: required` en `.atipspec/config.yaml` y
protege ese fichero con CODEOWNERS. Sin una policy (`--policy` o
`ATIPSPEC_TRUST_POLICY`), `check` está en rojo, el `accept` local está
desactivado salvo para el contrato del proyecto, `deliver` se niega y `run`
no arranca. `verify` sigue ejecutándose para la iteración local; la
comprobación de confianza exige evidencia atestada de todos modos.
`merge-check` aplica el requisito cuando lo activa el head, la branch de
destino o la base del merge, así que una branch no puede quitarlo para su
propio merge, ni saltárselo bifurcándose desde un commit anterior. Entonces
bloquea un recibo aceptado localmente, y un recibo de confianza que la policy
no autentica (consulta [CI antes del merge](#ci-antes-del-merge)).

## Dos modos de confianza

| | `mode = "ssh"` | `mode = "provider"` |
| --- | --- | --- |
| Aprobaciones humanas | firmas SSH separadas de claves inscritas (`approve`), o revisiones del proveedor recolectadas y firmadas por una clave de recolector (`sync-approvals`) | el worker protegido las lee en vivo desde el pull request con un token de solo lectura; sin recolector |
| Evidencia de CI | firmada por una clave de recolector de CI inscrita (`attest`) | atestada con GitHub artifact attestations por el workflow de evidencia de confianza, en un repositorio aparte y fijado a un commit, y verificada con un `gh` fijado |
| Claves que inscribir | una por rol humano, una para CI, una para el recolector | ninguna |
| Excepciones de riesgo | `approve <slug> exception:Fn --expires` | no disponible: arregla el hallazgo o usa el modo ssh |
| Policy | `schema = 1` | `schema = 2`, `[provider.roles]` y `[attestation]` |

El modo provider es la recomendación por defecto: necesita un worker
protegido con `GITHUB_TOKEN`, la policy fijada y el `gh` fijado, y un
repositorio de confianza de la organización que contenga el workflow de
evidencia, y nada más. El modo provider es solo para GitHub. La puerta vuelve
a leer el proveedor en cada ejecución y falla de forma cerrada ante cualquier
error de la API, revisión revocada, head cambiado o discrepancia de digest.
`check`, `deliver`, `report` y `merge-check` toman el número del PR con
`--number` o `ATIPSPEC_PR_NUMBER`. `enterprise-init` escribe
`policy.provider.example.toml`, `github-evidence-trusted.yml` y
`github-evidence-caller.yml`. El modo ssh sigue siendo la opción estricta
para las organizaciones que necesitan firmas bajo su propia custodia de
claves, GitLab o excepciones de riesgo.

En un pull request, GitHub ejecuta los workflows que trae el pull request,
así que el cambio que un workflow del repositorio candidato atestigua puede
reescribirlo. Por eso la policy ata cada atestación de evidencia a cuatro
cosas: el repositorio candidato (`repository`, verificado con `--repo`), el
pull request (`refs/pull/<number>/merge`, la ref que GitHub registra para una
ejecución de `pull_request`), el workflow de confianza en un repositorio
aparte de la misma organización (`[attestation] signer_workflow`) en un
commit concreto (`signer_digest`), y los runners alojados por GitHub
(`allow_self_hosted_runners = true` levanta esta condición). Una policy cuyo
workflow vive en el repositorio candidato, o cuyo commit no está fijado, no
se carga. La puerta exige también que el `head` de cada registro sea el
commit que obtuvo el worker. Los pull requests desde forks no reciben token
OIDC por defecto, así que su evidencia no lleva atestación y la puerta falla
de forma cerrada; activa la opción de GitHub «send write tokens to workflows
from pull requests» solo si la aceptas, y nunca uses `pull_request_target`
para el workflow de evidencia.

## Perímetro de confianza

El repositorio candidato es editable por su autor y por el agente de
programación. Los ficheros que contiene, incluidos el JSON de evidencia, el
texto de la revisión y los metadatos de aprobación locales, no pueden ser su
propia autoridad. Un worker de aceptación protegido usa un CLI instalado y
fijado, una policy de confianza externa versionada y claves públicas
inscritas. Fija el SHA-256 de la policy en la configuración protegida
(`ATIPSPEC_POLICY_SHA256`).

`enterprise-init` genera ejemplos de configuración y una guía de adopción.
Mueve y configura la policy fuera del checkout; no uses la plantilla
directamente. La plantilla contiene a propósito claves de relleno no válidas.
Los roles de firma de CI y de recolector del proveedor no pueden tener
también roles de aprobación humana.

Las `contract_rules` corporativas se evalúan en todo el repositorio, además
del contrato del proyecto. Un proyecto no puede eximirse de una regla
corporativa con una decisión de arquitectura local. Actualiza y aprueba la
policy corporativa por separado.

La policy también puede imponer dos mínimos a la puerta, booleanos de primer
nivel junto a `contract_rules`: `require_proof = true` (todo criterio bajo
`Tests:` nombra su test JUnit en `Proof:`, y la verificación tiene un
`Report:`) y `require_isolated_review = true` (una revisión cuyo `session:`
no es `isolated` es un error). Cualquier otro valor impide cargarla. La
puerta aplica un requisito cuando lo activa la policy o el `config.yaml` del
proyecto, así que un proyecto puede añadirlo pero no levantarlo.

## Roles y approval subjects

| Fase | Rol | Contenido atado |
| --- | --- | --- |
| spec | product | la especificación y el contrato de arquitectura |
| plan | engineering | la especificación, el plan y el contrato de arquitectura |
| decision:DEC-nnn | engineering | el documento de decisión y el contrato modificado |
| exception:Fn | risk | el árbol, la revisión, los términos del aplazamiento, la caducidad |
| acceptance | qa | el árbol, la revisión, los términos del aplazamiento y los artefactos de evidencia |

En una entrega guiada, spec y plan atan uno a uno los requisitos que lista la
entrega, no el resto de la spec viva de su capacidad, cuyos demás requisitos
`check` y `merge-check` mantienen como estaban (versión 2 del subject;
consulta [cuando main avanza](teams.md#cuando-main-avanza)). Lo que trajo la
branch de integración no es cambio de la entrega; bajo una policy, solo su
clave `integration` nombra esa branch, como `integration =
"refs/remotes/origin/main"`: `teams.json` forma parte del candidato. Sin la
clave no se atribuye nada, y lo que trae traer la branch de destino cuenta
como cambio de la entrega en `check`. Las aprobaciones
firmadas antes de 0.3.0, y las revisiones del proveedor que llevan su
marcador, se comparan con el subject de versión 1 para el que se hicieron.
Un subject lee los finales de línea CRLF como LF, y lo mismo hacen las
comprobaciones de firma de las aprobaciones y de los registros de evidencia y
los digests de los logs de salida de los comandos y de las copias de los
informes de tests: un checkout con `core.autocrlf` (el valor por defecto de
Git for Windows) y otro sin él dan el mismo subject y verifican las mismas
firmas.

El owner declarado de la entrega no puede aprobar su propio trabajo, esté
escrito con las mayúsculas que esté: un owner `Engineering` es la identidad o
la cuenta `engineering`. El owner se escribe como las identidades, con letras
ASCII, dígitos, `_`, `.`, `@` y `-`: `check` y `approve` rechazan uno que
solo parece una identidad, con una letra cirílica o un carácter invisible.
Los adaptadores del proveedor rechazan también al autor real del PR/MR. En
modo ssh, `spec.md` es la palabra del autor, así que el aprobador de producto
confirma el owner: `approve <slug> spec --owner <identity>` falla salvo que
sea el `owner` que declara `spec.md`, y lo firma con la aprobación. Una
aprobación de spec que no confirma ningún owner (firmada antes de 0.3.0) o
que confirma otro no cuenta: fírmala de nuevo con `--owner`. Cambiar el owner
cambia el subject de la spec, así que producto aprueba de nuevo, y el nuevo
owner no puede firmar las fases posteriores. Los administradores deben seguir
asegurándose de que las claves humanas inscritas no sean accesibles para los
agentes de desarrollo ni para las cuentas de servicio. Una firma válida
demuestra la posesión de la clave, no la presencia humana ni una revisión
semántica completa.

Obtén el subject con `approval-subject`. Cada aprobador revisa el subject
real y ejecuta `approve` en una máquina de confianza con su clave inscrita.
El comando no crea claves ni fabrica identidades. Las aprobaciones de riesgo
exigen una marca de tiempo ISO futura mediante `--expires`; cambiar los
términos exige una nueva aprobación.

La aprobación del plan y de la spec debe preceder a la ejecución de la
evidencia. Un digest de policy nuevo, un subject cambiado, un firmante
desconocido, una firma alterada o una aprobación caducada fallan de forma
cerrada. Para revocar un firmante SSH, elimina su clave de la policy externa y
despliega la nueva policy fijada. Esto invalida los artefactos de la policy
anterior; recolecta nuevas aprobaciones y evidencia bajo la policy nueva.

## GitHub y GitLab

Los adaptadores son de solo lectura. Configura el tipo de proveedor, la URL
HTTPS de la API, el repositorio y las listas de rol a cuenta en la policy
externa. Proporciona GITHUB_TOKEN o GITLAB_TOKEN únicamente al worker
protegido de recolección y comprobación.

Para GitHub, una persona inscrita envía una revisión APPROVED que contiene el
marcador exacto de `approval-subject` en una línea aparte. La revisión debe
apuntar al head actual. Para GitLab, la persona publica ese marcador en una
nota que no sea de sistema y aprueba el MR; deben existir ambas cosas y la
cuenta debe estar activa y no ser un bot.

```sh
atipspec sync-approvals reset acceptance --number 42 \
  --identity approval-collector --key /secure/collector-key \
  --policy /secure/company.toml
```

El recolector firma el registro normalizado, y cada puerta de confianza
vuelve a leer el proveedor. Las revisiones revocadas o cambiadas fallan. Un
head desactualizado, un error de la API, un endpoint de aprobación no
soportado o un acceso insuficiente del token fallan de forma cerrada. El
acceso a la API de aprobaciones de GitLab depende del despliegue y del tier.
El administrador de la policy debe configurar explícitamente los orígenes de
API autoalojados.

Las integraciones están cubiertas por tests de contrato de API simulados. La
conexión en vivo y la protección de branches deben configurarse y probarse en
tu organización real.

Referencias de API: [revisiones de GitHub](https://docs.github.com/en/rest/pulls/reviews),
[aprobaciones de GitLab](https://docs.gitlab.com/api/merge_request_approvals/).

## CI antes del merge

`github-local.yml` y `gitlab-local.yml`, de `enterprise-init`, ejecutan
`atipspec merge-check` como comprobación del pull request: haz obligatorio
ese job en la branch de destino. Falla mientras una entrega que toca la
branch sea un borrador o no esté aceptada, cuando el código del head difiere
del código que aceptó un recibo, cuando la branch reescribe un archivo
anterior, cambia una spec viva fuera de `deliver`, cambia el contrato
aceptado sin su nueva aceptación o cambia código fuera de `.atipspec/` que
ninguna entrega de la branch cambió después de su commit base, como el
código commiteado antes de `atipspec new`, salvo que `exempt_paths`, en el
`config.yaml` de la branch de destino, exima esos ficheros (consulta la
[referencia del CLI](reference/cli.md#atipspec-merge-check)). También falla
mientras `.atipspec/framework/` no sea lo que instala la versión fijada, porque
cada fase imprime al agente esas reglas y esos workflows: ejecuta
`atipspec install --update` con esa versión. Avisa, sin bloquear, cuando la
branch relaja una política de `config.yaml` respecto a la branch de destino, o
cambia `overview.md`, `glossary.md`, una decisión (y nombra cada decisión con
su estado), `adapter.json` o `teams.json`; y cuando la branch cambia el contrato o una decisión que lo afecta,
el resultado muestra la aceptación del contrato y su canal. El job obtiene el head de la
branch, no el commit de merge sintético del proveedor, con el historial
completo, y nada puede escribir en el checkout antes de `merge-check`, que
juzga el head con commit. Instala el verificador fijado desde fuera del
checkout con `python -I`, así que nunca se carga un paquete `pip/` ni un
wheel que el candidato incluya en un commit, no ejecuta ningún comando del
candidato y no necesita credenciales; los tests del proyecto se ejecutan en su
propio job. El job de GitLab obtiene la branch de destino, así que se aplica
su `trust: required`. El job de GitHub escribe el resultado en el resumen del
job (`--format markdown`): una tabla de las entregas que toca la branch con su
estado y su ticket, y después las comprobaciones. Cuando el agente abre el
pull request a petición del usuario, su descripción lleva el ticket y
`atipspec report <slug> --format markdown`. En modo local, un recibo no está
autenticado: la comprobación muestra que la branch coincide con lo que se
aceptó, no quién lo aceptó, y cómo se registró cada aprobación (su canal), no
quién la dio.

Un límite que se cierra con el proveedor, no con AtipSpec: el proveedor
ejecuta el workflow que trae la branch, así que una branch puede reescribir o
quitar la comprobación. Exígela desde fuera del candidato: en GitHub, con un
ruleset que exija el workflow de un repositorio protegido, o con CODEOWNERS
en `.github/workflows/` y la revisión de code owners obligatoria; en GitLab,
con una pipeline execution policy o un compliance pipeline. En local, Claude
Code pregunta antes de que sus herramientas de edición cambien
`.github/workflows/**`, `.gitlab-ci.yml` o sus propios ajustes (consulta las
[reglas de permisos de aprobación](clients.md#reglas-de-permisos-de-aprobacion));
eso no es un control sobre la branch.

`exempt_paths` en la branch de destino deja que una branch cambie los
ficheros que encajan sin ninguna entrega ni aceptación, también bajo una
policy. Limítalo a ficheros que no la necesitan, como la documentación, y
revisa un cambio en él como un cambio en la CI: no exime nada hasta que se
integra en la branch de destino, y `merge-check` avisa en la branch que lo
cambia. Qué ficheros no necesitan entrega lo decide la persona: las reglas
instaladas le dicen al agente que solo cambie `exempt_paths` cuando ella lo
pida. Ninguna aprobación lo hashea, así que definirlo en main no devuelve a
borrador la propuesta de ninguna entrega abierta; una branch que lo integra
vuelve a verificar y revisar, como tras cualquier cambio del árbol.

Una lista de partida, que la persona adapta. Cada entrada es código que ningún
humano aprueba en una entrega: una branch cambia los ficheros que encajan sin
ninguna entrega.

```yaml
exempt_paths:
  - "docs/**"
  - "README.md"
  - "CHANGELOG.md"
  - "LICENSE"
  - "package-lock.json"
  - "uv.lock"
```

La documentación y los lockfiles son los candidatos habituales. Un lockfile
fija las versiones de las dependencias con las que se ejecuta el código:
exímelo solo donde otra cosa revise las actualizaciones de dependencias, como
una revisión obligatoria de los pull requests del bot de actualizaciones. No
incluyas nunca código, tests, `.github/**`, `.claude/**` ni ficheros que el
agente lee como instrucciones, como `AGENTS.md` o `CLAUDE.md`; un glob amplio
como `**/*.md` también los incluye.

El fichero que añade el job también es código fuera de `.atipspec/`, y no lo
cubre ninguna entrega: la pull request que lo añade falla su propio
`merge-check`, mientras la branch de destino aún no tiene `exempt_paths`, así
que intégrala antes de hacer obligatorio el job. Un cambio posterior en ese
fichero, como un nuevo pin de `ATIPSPEC_PACKAGE`, falla igual: hazlo en una
entrega o, si la persona decide que no la necesita, añade solo ese fichero a
`exempt_paths` en la branch de destino antes, bajo los owners que revisan la
CI; `.github/**` dejaría que una branch cambiara cualquier workflow sin
entrega.

Con `trust: required`, estos jobs fallan de forma cerrada: ejecuta
`merge-check --base <ref> --policy /secure/company.toml` en el worker
protegido y exige ese resultado en su lugar. Con una policy, `merge-check`
exige la aceptación de confianza aunque no esté definido `trust: required`,
así que un recibo aceptado localmente bloquea. Un recibo es un fichero de la
branch, así que con la policy `merge-check` no lo lee como prueba: vuelve a
comprobar cada entrega que la branch archiva tal como la encontró `deliver`.
En un clon temporal con las refs del repositorio obtiene el commit anterior
al commit de archivo, restaura la evidencia, la revisión, los términos del
aplazamiento y las aprobaciones archivadas con la entrega, y exige que su
comprobación de confianza ahí sea `verified` (las aprobaciones de producto,
ingeniería y QA y la evidencia atestada que exige `deliver`; las revisiones
del proveedor recolectadas con `sync-approvals` se vuelven a leer), que ese
commit contenga el código del head y que la spec viva del head sea lo que
`deliver` escribe a partir de ese commit, también cada requisito que lista la
entrega. Haz el commit del archivo por separado justo
después de `deliver`. En modo provider lee las revisiones del pull request
sobre ese commit, o sobre el nuevo head cuando llevan las mismas líneas de
marcador: si el push del archivo descarta las revisiones obsoletas, los
revisores vuelven a aprobar el nuevo head con las mismas líneas. Bajo una
policy, el contrato y las decisiones que lo afectan solo cambian en una
entrega comprobada de esta forma, `contract.md` con una nueva decisión que lo
afecta, aceptada y aprobada por ingeniería; un contrato en borrador se acepta
primero con una entrega así, cuya aprobación del plan lo nombra. Una branch
que los cambie de otra forma bloquea, diga lo que diga el registro local del
contrato.

## Ejecución y recolección en CI

Los jobs de evidencia ejecutan los comandos del candidato sin claves de
firma. Usa el historial completo. Protege el pin del paquete verificador y
los workflows. Un orquestador protegido debe autenticar el workflow
productor, el repositorio, el head de origen, la ejecución exitosa y la
descarga del artefacto antes de atestiguar.

En modo provider, `github-evidence-trusted.yml` es ese orquestador. Cópialo
en el repositorio de confianza; cada repositorio candidato lo llama en el
commit fijado con `github-evidence-caller.yml`, solo en `pull_request`. Su
job `produce` obtiene el head del pull request, borra la evidencia incluida
en commits de la branch, ejecuta los comandos de Verify con acceso de solo
lectura y sube los registros que escribió. Su job `attest` no ejecuta ningún
comando del candidato: toma esos registros por el ID del artefacto, así que un
artefacto que otro job de la ejecución reemplazó hace fallar la descarga;
exige exactamente un registro superado por cada tarea verificada de cada
entrega activa, escrito sobre ese head y ese árbol, y atestigua solo esos. El
worker protegido también borra la evidencia incluida en commits, descarga de
la última ejecución exitosa sobre el head el artefacto del intento de esa
ejecución, `atipspec-evidence-<attempt>`, copia solo sus carpetas `evidence/`
y ejecuta `check` o `deliver` con `--number`, que fallan ante un registro que
`attest` no atestiguó; `ADOPTION.md` lista los comandos. La verificación va
después de las aprobaciones de spec y plan: vuelve a ejecutar el workflow
sobre el head una vez dadas, y QA aprueba después. La atestación demuestra
dónde, cuándo y sobre qué head se produjo la evidencia, no que el código
bajo prueba sea honesto: ese código se ejecuta en `produce` y podría falsear
ahí sus propios resultados, algo que cubren la revisión y las aprobaciones
sobre el head.

Ejecuta los comandos del candidato en un worker efímero sin claves de firma.
Recolecta y firma en un worker protegido separado, usando un checkout nuevo y
saneado y `python -I -m atipspec` desde un paquete instalado y fijado.
`attest` firma, para cada tarea, el registro de `evidence/` que terminó el
último: borra la evidencia que la branch incluyó en commits
(`atipspec.verify.clear_evidence`) antes de que el productor verifique y
antes de que el recolector restaure sus registros. No instales ni importes la
implementación de AtipSpec del candidato. Nunca ejecutes comandos del
candidato en el recolector. Aislar las credenciales en otro paso, en un
worker persistente comprometido, no es suficiente.

Cada comando tiene un log de salida completo cuyo hash se comprueba contra el
registro de evidencia firmado, y lo mismo ocurre con el informe JUnit copiado
cuando una tarea nombra uno. Conserva esos logs e informes junto con la
evidencia.

`attest` valida y firma registros en nombre de ese recolector de confianza.
No consulta ni autentica de forma independiente la URL de ejecución de CI
declarada. Firmar un JSON arbitrario proporcionado por el autor anularía el
perímetro de confianza. La atestación de artefactos nativa del proveedor y la
integración con el orquestador dependen de cada despliegue y deben
configurarse antes de usar el script de aceptación protegido en producción.

Exige el resultado de la aceptación protegida mediante la protección de
branches o las reglas de MR. Las comprobaciones locales siguen siendo de
diagnóstico y pueden informar de un blocker a la espera de una excepción de
riesgo de confianza. El CLI no puede impedir que un administrador se salte
las reglas del repositorio.

## Dosier y piloto

`report --format json|markdown|html` exporta una matriz de trazabilidad, los
punteros de prueba con aquello a lo que se resolvió cada uno, el revisor y la
sesión de la revisión, las referencias a ejecuciones de CI, las aprobaciones
verificadas, los hallazgos, la información de policy y versión, y los cambios
que QA firma: cada fichero cambiado desde el commit base con su status, sus
líneas y si queda fuera del scope del plan, y el diff (hasta 200 KB, 50 KB en
markdown, con el tamaño y el sha256 del diff completo). El HTML escapa el
texto no confiable. Los artefactos firmados son la evidencia; los propios
hashes de un informe son un índice, no una certificación aparte. Conserva
ambos.

`pilot init <name>` crea un protocolo sin mediciones. El equipo completa las
cohortes, la elegibilidad, la ventana de observación, los umbrales y los
responsables humanos. `pilot record` exige mediciones reales con fuente y
recolector; `pilot report` da comparaciones descriptivas y señala las
ventanas incompatibles. Las afirmaciones reales de rendimiento exigen un
piloto completado; los ejemplos generados no son mediciones. Usa una línea
base equiparada y la misma ventana de observación de defectos.
