# Aceptación empresarial

AtipSpec separa **checked** (comprobaciones técnicas/estructurales locales) de
**verified** (evidencia de confianza y aceptación humana). `deliver` exige
verified.

## Aceptación local y aceptación de confianza

Sin una policy, `atipspec accept` registra lo que una persona aceptó (spec,
plan, contrato) y la puerta detecta ediciones posteriores. Eso es detección de
deriva: el registro demuestra el contenido, no la identidad. Con una policy,
la puerta ignora esos registros y exige las aprobaciones firmadas y ligadas a
un rol que se describen abajo.

## Dos modos de confianza

| | `mode = "ssh"` | `mode = "provider"` |
| --- | --- | --- |
| Aprobaciones humanas | firmas SSH separadas de claves inscritas (`approve`), o reviews de proveedor recolectadas y firmadas por una clave de recolector (`sync-approvals`) | se leen en vivo desde el PR o MR por el worker protegido con un token de solo lectura; sin recolector |
| Evidencia de CI | firmada por una clave de recolector de CI inscrita (`attest`) | atestada por el workflow de evidencia con GitHub artifact attestations y verificada con un `gh` fijado |
| Claves a inscribir | una por rol humano, una para CI, una para el recolector | ninguna |
| Excepciones de riesgo | `approve <slug> exception:Fn --expires` | no disponible: arregla el hallazgo o usa el modo ssh |
| Policy | `schema = 1` | `schema = 2`, `[provider.roles]` y `[attestation]` |

El modo provider es la recomendación por defecto: necesita un worker
protegido con `GITHUB_TOKEN`, la policy fijada y un `gh` fijado, y nada más.
La puerta vuelve a leer el proveedor en cada ejecución y falla de forma
cerrada ante cualquier error de la API, review revocada, head cambiado o
discrepancia de digest. `check`, `deliver` y `report` toman el número del PR
o MR con `--number` o `ATIPSPEC_PR_NUMBER`. `enterprise-init` escribe
`policy.provider.example.toml` y `github-evidence.yml`. El modo ssh sigue
siendo la opción estricta para organizaciones que necesitan firmas bajo su
propia custodia de claves, atestaciones de GitLab, o excepciones de riesgo.

La policy ata la atestación a un workflow del propio repositorio de la
policy. Los pull requests de forks no reciben token OIDC por defecto, así
que su evidencia no lleva atestación y la puerta falla de forma cerrada;
activa la opción de GitHub «send write tokens to workflows from pull
requests» solo si la aceptas, y nunca uses `pull_request_target` para el
workflow de evidencia.

## Perímetro de confianza

El repositorio candidato es editable por su autor y por el agente de
programación. Los ficheros que contiene, incluyendo el JSON de evidencia, el
texto de la revisión y los metadatos de aprobación locales, no pueden ser su
propia autoridad. Un worker de aceptación protegido usa un CLI instalado y
fijado, una policy de confianza externa versionada y claves públicas
inscritas. Fija el SHA-256 de la policy en la configuración protegida
(`ATIPSPEC_POLICY_SHA256`).

`enterprise-init` genera ejemplos de configuración y una guía de adopción.
Mueve y configura la policy fuera del checkout; no uses la plantilla
directamente. La plantilla contiene intencionadamente claves de relleno
inválidas. Los roles de firma de CI y de recolector de proveedor no pueden
ostentar también roles de aprobación humana.

Las `contract_rules` corporativas se evalúan en todo el repositorio, además
del contrato del proyecto. Un proyecto no puede eximirse de una regla
corporativa con una decisión de arquitectura local. Actualiza y aprueba la
policy corporativa por separado.

## Roles y approval subjects

| Fase | Rol | Contenido atado |
| --- | --- | --- |
| spec | product | la spec y el contrato de arquitectura |
| plan | engineering | la spec, el plan y el contrato de arquitectura |
| decision:DEC-nnn | engineering | el documento de decisión y el contrato modificado |
| exception:Fn | risk | el árbol, la revisión, los términos del aplazamiento, la caducidad |
| acceptance | qa | el árbol, la revisión, los términos del aplazamiento y los artefactos de evidencia |

El owner declarado de la entrega no puede aprobar su propio trabajo. Los
adaptadores de proveedor también rechazan al autor real del PR/MR. Para las
aprobaciones por SSH, los administradores deben asegurarse de que `owner`
corresponde al propietario real y de que las claves humanas inscritas no son
accesibles para agentes de desarrollo ni cuentas de servicio. Una firma válida
demuestra la posesión de la clave, no la presencia humana ni una revisión
semántica completa.

Obtén el subject con `approval-subject`. Cada aprobador revisa el subject real
y ejecuta `approve` en una máquina de confianza con su clave inscrita. El
comando no crea claves ni fabrica identidad. Las aprobaciones de riesgo exigen
una marca de tiempo ISO futura mediante `--expires`; cambiar los términos
exige una nueva aprobación.

La aprobación del plan y de la spec debe preceder a la ejecución de la
evidencia. Un digest de policy nuevo, un subject cambiado, un firmante
desconocido, una firma alterada o una aprobación caducada fallan de forma
cerrada. Para revocar un firmante SSH, elimina su clave de la policy externa y
despliega la nueva policy fijada. Esto invalida los artefactos de la policy
anterior; recolecta nuevas aprobaciones/evidencia bajo la policy nueva.

## GitHub y GitLab

Los adaptadores son de solo lectura. Configura el tipo de proveedor, la URL de
la API HTTPS, el repositorio y las listas de rol a cuenta en la policy
externa. Suministra GITHUB_TOKEN o GITLAB_TOKEN únicamente al worker protegido
de recolección/comprobación.

Para GitHub, un humano inscrito envía una review APPROVED que contiene el
marcador exacto de `approval-subject` en una línea aparte. La review debe
apuntar al head actual. Para GitLab, el humano publica ese marcador en una
nota que no sea de sistema y aprueba el MR; ambas cosas deben existir y la
cuenta debe estar activa y no ser un bot.

```sh
atipspec sync-approvals reset acceptance --number 42 \
  --identity approval-collector --key /secure/collector-key \
  --policy /secure/company.toml
```

El recolector firma el registro normalizado, y cada puerta de confianza
vuelve a consultar al proveedor. Las reviews revocadas o cambiadas fallan. Un
head desactualizado, un error de la API, un endpoint de aprobación no
soportado o un acceso de token insuficiente fallan de forma cerrada. El acceso
a la API de aprobaciones de GitLab depende del despliegue/tier. Los orígenes
de API autoalojados deben configurarse explícitamente por el administrador de
la policy.

Las integraciones están cubiertas por tests de contrato de API simulados. La
conexión en vivo y la protección de branches deben configurarse y probarse en
tu organización real.

Referencias de API: [reviews de GitHub](https://docs.github.com/en/rest/pulls/reviews),
[aprobaciones de GitLab](https://docs.gitlab.com/api/merge_request_approvals/).

## Ejecución y recolección de CI

Los jobs generados para GitHub y GitLab ejecutan la verificación local sin
claves de firma. Usa el historial completo. Protege el pin del paquete
verificador y los workflows. Un orquestador protegido debe autenticar el
workflow productor, el repositorio, el head de origen, la ejecución exitosa y
la descarga del artefacto antes de atestiguar.

Ejecuta los comandos candidatos en un worker efímero sin claves de firma.
Recolecta y firma en un worker protegido separado, usando un checkout nuevo y
saneado y `python -I -m atipspec` desde un paquete instalado y fijado. No
instales ni importes la implementación candidata de AtipSpec. Nunca ejecutes
comandos candidatos en el recolector. Aislar las credenciales en otro paso,
sobre un worker persistente comprometido, no es suficiente.

Cada comando tiene un log de salida completo cuyo hash se comprueba contra el
registro de evidencia firmado, y lo mismo ocurre con el informe JUnit copiado
cuando una tarea nombra uno. Conserva esos logs e informes junto con la
evidencia.

`attest` valida y firma registros en nombre de ese recolector de confianza. No
consulta ni autentica de forma independiente la URL de ejecución de CI
declarada. Firmar un JSON arbitrario proporcionado por el autor anularía el
perímetro de confianza. La atestación de artefactos nativa del proveedor o la
integración con el orquestador es específica de cada despliegue y debe
configurarse antes de usar el script de aceptación protegido en producción.

Exige el resultado de la aceptación protegida mediante protección de branches
o reglas de MR. Las comprobaciones locales siguen siendo diagnósticas y
pueden reportar un blocker a la espera de una excepción de riesgo de
confianza. El CLI no puede impedir que un administrador se salte las reglas
del repositorio.

## Dosier y piloto

`report --format json|markdown|html` exporta una matriz de trazabilidad,
punteros de prueba, referencias a la ejecución de CI, aprobaciones
verificadas, hallazgos e información de policy/versión. El HTML escapa el
texto no confiable. Los artefactos firmados son la evidencia; los propios
hashes de un informe son un índice, no una certificación aparte. Conserva
ambos.

`pilot init <name>` crea un protocolo sin mediciones. El equipo completa las
cohortes, la elegibilidad, la ventana de observación, los umbrales y los
humanos responsables. `pilot record` exige mediciones reales con fuente y
recolector; `pilot report` da comparaciones descriptivas y marca ventanas
incompatibles. Las afirmaciones reales de rendimiento exigen un piloto
completado; los ejemplos generados no son mediciones. Usa una línea base
equiparada y la misma ventana de observación de defectos.
