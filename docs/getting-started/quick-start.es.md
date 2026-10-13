# Primeros pasos

Un cambio, desde tu lado de la conversación. Tomas tres decisiones: el
contrato, una vez por proyecto; la propuesta de cada cambio, y su resultado
revisado. El asistente ejecuta todos los comandos de abajo y registra cada
decisión con `atipspec accept --code <code>`, el código de la vista que te
mostró; Claude Code, abierto en la raíz del proyecto, te pregunta antes de
que ese comando se ejecute. Los
ejemplos usan Claude Code; la [página de clientes](../clients.md) muestra el
equivalente en los demás. La página de [entrega guiada](../flow/guided.md)
detalla cada paso.

## 1. Define el contrato

Lo primero que hay que hacer en un proyecto es la **fase contract**. Abre una
sesión en el proyecto y di:

```text
/atipspec-contract
```

El skill ejecuta `atipspec contract`, que imprime el workflow y el contrato
actual. El modelo registra lo que ya decidiste (por ejemplo, Django y
PostgreSQL) como decisiones, solo pregunta lo que afecta a las reglas,
rellena `.atipspec/contract.md` y escribe las reglas que el CLI comprobará:

```text
dependencies pyproject.toml django psycopg "pytest*"
forbid-pattern "shop/domain/**" "from shop\.infrastructure"
require-command "python -m pytest -q"
```

El asistente comprueba el repositorio contra él y te lo presenta con las
decisiones que incluye y un código de aprobación. Apruébalo en la
conversación; el asistente registra tu aprobación con ese código:

```bash
atipspec audit
atipspec proposal contract
atipspec accept contract --code 11HN-G0QN
git add .atipspec && git commit -m "chore: architecture contract"
```

Mientras no se registre la aceptación del contrato, `atipspec check` avisa
de ello.

## 2. Pide el cambio

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

El asistente crea la entrega en su propia branch:

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

`new` crea `.atipspec/deliveries/password-reset/` con `spec.md`, `plan.md`,
`deferred.md` y `baseline.json`, registra el commit actual como la base de la
entrega y cambia a la branch `delivery/password-reset`. Luego el skill
ejecuta `atipspec spec password-reset`, que imprime la **fase spec**: su
workflow, las reglas y exactamente el contexto que la entrega necesita.

El modelo te entrevista en rondas de como máximo tres preguntas y luego
escribe los requisitos y sus escenarios en la spec viva,
`.atipspec/specs/auth.md`, con IDs de `atipspec ids auth`:

```markdown
### REQ-AUTH-7KQ2M-001: The user can request a reset link

#### AC-AUTH-7KQ2M-001: Registered email
- **WHEN** a user requests a reset for the registered email "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds
```

En el `spec.md` de la entrega lista esos IDs bajo `requirements` y escribe
la intención, lo que queda fuera de alcance y los límites de calidad. Un
resultado vago, como «funciona correctamente», bloquea la propuesta.

## 3. Aprueba la propuesta

El modelo prepara en `plan.md` el enfoque y cómo se prueba cada escenario, y
lo presenta todo junto:

```bash
atipspec proposal password-reset
```

La vista muestra los escenarios, el alcance, el enfoque, las pruebas, el
nivel de riesgo, el diff de la spec viva y el código de aprobación. Este es
el **punto de parada 1**: léela y luego pide cambios o aprueba en la
conversación. El asistente registra tu aprobación con el código que
presentó:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

Claude Code, abierto en la raíz del proyecto, te pregunta antes de que ese
comando se ejecute. Pone
`status: ready` y registra lo que aprobaste y por qué canal; si alguien
edita después los escenarios, el enfoque o las pruebas, la puerta nombra lo
que cambió y te vuelve a preguntar.

## 4. Construye y revisa

```text
/atipspec-ship password-reset
```

`atipspec ship password-reset` nombra la siguiente fase a la que la entrega
puede entrar, y cada comando de fase se niega mientras falte un paso
obligatorio. El modo ship ejecuta las fases restantes sin pausar hasta el
resultado:

- **build**: código y tests, tarea a tarea, cada una registrada con
  `atipspec task-done password-reset T1 --note "..."`; luego
  `atipspec verify password-reset` ejecuta las comprobaciones finales una
  vez sobre el candidato terminado.
- **review**: `atipspec review password-reset` escribe un paquete; un
  revisor en una sesión aislada escribe `review.md` con un veredicto por
  criterio, cada uno apuntando a un test que pasó, a un `file:line` o a un
  `file::test`.

Obsérvalo desde otra terminal en cualquier momento:

```bash
atipspec status password-reset
```

```text
password-reset  [in_progress]  tasks 1/2
  todo    T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
  todo    FINAL: no evidence; run `atipspec verify password-reset`
  todo    No review.md: run `atipspec review password-reset` and give the packet to a reviewer in an isolated session
  info    lead time 3h: since creation, until the result is accepted
  info    risk normal: every criterion needs a reviewer verdict
  info    Local mode: acceptance records detect drift; identity and evidence provenance are not externally authenticated
Next: T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
```

## 5. Acepta el resultado

Cuando `atipspec check password-reset` está en verde, la entrega está
`checked`. El asistente presenta el resultado:

```bash
atipspec report password-reset
```

El dosier muestra cada criterio con su evidencia y el veredicto del revisor,
cada fichero cambiado desde el commit base con el diff, y el código de
aprobación del resultado. Este es el **punto de parada 2**: revísalo y
acéptalo o pide cambios. El asistente registra tu aceptación y archiva la
entrega:

```bash
atipspec accept password-reset result --code 3C1Q-4VN7
atipspec deliver password-reset
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Result archived. Commit, merge and deployment follow the repository's explicit policy.
```

`deliver` no hace commit, push ni fusión. Antes de la fusión, el asistente
ejecuta `atipspec merge-check --base <target>`, que confirma que la entrega
está aceptada y que el código sigue siendo el que aceptaste; después de
`deliver`, un cambio posterior reabre la entrega (consulta
[deliver](../flow/deliver.md#despues-de-deliver-el-codigo-queda-fijado)).
Las organizaciones que necesitan aprobaciones autenticadas configuran la
[aceptación de confianza](../enterprise.md) en lugar de los registros
locales.

## Qué acabas de conseguir

- Escenarios que aprobaste, conservados en la spec viva de la capacidad
  `auth`.
- Ficheros de evidencia con los comandos exactos, los códigos de salida y el
  hash del árbol de la verificación final.
- Una revisión con un veredicto por criterio, cada uno apuntando a una
  prueba que la puerta resuelve, y la sesión que declara el revisor: `check`
  avisa cuando el revisor vio la conversación del autor, y lo bloquea con
  `risk: high` o con `require_isolated_review`.
- Un registro de cada decisión, atado al contenido que viste, y un contrato
  impuesto sobre cada fichero que tocó la entrega.

Siguiente: [cómo funciona](how-it-works.md), o el [flujo](../flow/index.md)
fase a fase.
