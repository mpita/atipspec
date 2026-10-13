# build

**Del plan aprobado al código, los registros de tareas y la evidencia.**
Tarea a tarea, y luego una verificación final.

| | |
| --- | --- |
| Rol | El implementador. Cambios pequeños, tests que ejercitan los criterios, las convenciones de esta base de código. Lo dice en el momento cuando un criterio no se puede cumplir. |
| Quién decide | El desarrollador, con el modelo, dentro del acuerdo aprobado. |
| Produce | código y tests, `progress.json` con las tareas registradas como implementadas, `evidence/*.json` |

## Cómo ejecutarla

```text
/atipspec-build password-reset
```

El skill ejecuta `atipspec build password-reset`, que se niega hasta que la
propuesta está aceptada para su contenido actual y, si no, imprime el
workflow, las reglas, el contexto y la siguiente tarea todavía sin registrar.
Después de cada tarea, `atipspec build password-reset --no-context` nombra la
siguiente.

## El bucle, para cada tarea

1. Lee la tarea, sus requisitos y escenarios, las secciones del contrato que
   toca, el código.
2. Haz el cambio más pequeño que satisfaga los escenarios dentro del contrato
   y del `scope` del plan. Añade o actualiza tests para que ejerciten los
   criterios; mientras trabajas, ejecuta tests focalizados o el `Verify:`
   propio de la tarea con `atipspec verify password-reset --task T1`.
3. Registra la tarea:

    ```bash
    atipspec task-done password-reset T1 --note "request() sends the link to registered emails only"
    ```

    ```text
    AtipSpec: T1 of password-reset recorded as implemented (progress, not verification) in .atipspec/deliveries/password-reset/progress.json
    Next: T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
    ```

4. A la siguiente tarea. Los commits siguen la política de tu repositorio;
   AtipSpec no exige ninguno.

## Qué hace que una tarea esté terminada

Un registro que `atipspec task-done` escribe en `progress.json`: la nota, la
hora, el hash del acuerdo aprobado y el de la tarea sin su título. Es la
declaración de avance del asistente, nunca una prueba: la verificación final
y la revisión comprueban el trabajo. Se niega antes de que la propuesta esté
aprobada, y un registro sigue siendo válido mientras el acuerdo aprobado y la
tarea no cambien; renombrar la tarea lo conserva. Una [entrega
antigua](../reference/legacy.md#finalizacion-de-tareas) también cuenta un marcador
de commit `[<slug>:Tn]`.

## La verificación final

Cuando todas las tareas están registradas, el candidato está terminado:

```bash
atipspec verify password-reset
```

```text
[FINAL] $ python -m pytest -q --junitxml .atipspec/tmp/junit.xml
    4 passed in 0.31s
[FINAL] ok (0.9s)
[FINAL] report .atipspec/tmp/junit.xml: 4 test(s), 0 failed
FINAL: pass -> .atipspec/deliveries/password-reset/evidence/FINAL-20260913T154145.218304Z-3f9a1c2e.json
```

Ejecuta una vez los comandos de `## Final verification` del plan y escribe la
evidencia. Cuando el framework de tests escribe JUnit XML, el plan nombra el
fichero en `Report:` y el test de cada criterio bajo `Proof:`; `verify` copia
el informe junto a la evidencia y `check` exige que cada test nombrado se
haya ejecutado y haya pasado. El propio comando Verify escribe el informe, en
una ruta que git ignora:

```markdown
## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
- AC-AUTH-7KQ2M-002: tests/auth/test_reset.py::test_unknown_email_same_answer
Verify:
- `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
```

Un id de test es el nombre del caso, `Class.name`, `module.Class.name` o
`path/to/file.py::Class::name`. Cuando nombra varios casos (un test
parametrizado, o el mismo nombre en varias clases), todos deben pasar. Sin
`Proof:`, un criterio bajo `Tests:` lo demuestra el revisor, salvo que el
proyecto fije `require_proof: true` (o lo haga la policy de confianza) o la
entrega fije `risk: high`: entonces todo criterio bajo `Tests:` necesita su
entrada `Proof:` y la verificación necesita un `Report:`, un error que
bloquea la propuesta hasta que el plan los nombre.

Solo cuenta un informe que escribe esta ejecución. Antes de que se ejecuten
los comandos, `verify` borra el fichero nombrado en `Report:`; después, el
fichero debe existir y haberse modificado después de ese borrado (con dos
segundos de tolerancia), o la evidencia falla con `test report not found` o
`predates this verification`. Por eso la ruta debe ser una que git ignore,
como `.atipspec/tmp/junit.xml`: un informe con commit o escrito a mano es el
que podría hacerse pasar por una ejecución, y `check` informa de un `Report:`
en una ruta que git no ignora como un error de plan. Nunca apuntes `Report:`
a un fichero que quieras conservar: `verify` lo borra.

Si el código cambia después de la verificación final, vuelve a ejecutarla
sobre el candidato terminado. Luego, `atipspec review password-reset`.

## Qué contiene la evidencia

```json
{
  "delivery": "password-reset",
  "task": "FINAL",
  "result": "pass",
  "tree": "cd03ae507b3605b12a497fcbcf590894a0073076",
  "head": "9f2c1e4...",
  "started": "2026-09-12T15:41:45Z",
  "finished": "2026-09-12T15:41:46Z",
  "commands": [
    {"command": "python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml", "exit_code": 0,
     "duration_s": 0.58, "output_tail": "4 passed in 0.31s",
     "output_path": "logs/FINAL-5d0c...-1.log", "output_sha256": "8a1f..."}
  ]
}
```

`tree` es la huella del árbol de trabajo contra el que se ejecutaron los
comandos. La puerta acepta la evidencia solo mientras el árbol siga
coincidiendo. Renombrar una tarea en `plan.md` (el texto después de
`### T1:`) es el único cambio que tolera: la evidencia y la revisión siguen
siendo válidas y, en un plan guiado con verificación final, cuya aprobación
deja fuera las tareas, la tarea también sigue completa: la huella lee cada
encabezado de tarea reducido a su id, así que esto se cumple también en un
clon nuevo, como el de la CI. Con un `Report:`, el fichero
también lleva `reports` (la copia bajo `evidence/logs/` con su hash, la ruta
desde la que se leyó y `fresh: true`) y `tests` (cada caso con su estado), y
alterar la copia se detecta igual que alterar un log de comando. La evidencia
con un informe escrito por AtipSpec 0.2.x no tiene la marca `fresh`: `check`
pide volver a verificar. Si un comando modifica el árbol (un formateador, un
fichero generado), `verify` lo dice, termina con código 1 y la evidencia ya
queda obsoleta: conserva o descarta el cambio y vuelve a ejecutarlo.

## Reglas

- Nunca toques `evidence/` a mano.
- `check` nunca ejecuta los tests: `verify` es el único comando que los
  ejecuta, y la puerta juzga la evidencia que escribió.
- El trabajo imprevisto se convierte en una tarea nueva con `Covers` y
  `Tests` o `Manual`, nunca escondido dentro de otra; un fichero fuera del
  `scope` del plan se añade a `scope` en la misma edición que añade la tarea
  que lo necesita, y un alcance más amplio vuelve a ti como una propuesta
  cambiada.
- Ningún refactor más allá de la tarea.
- Una violación del contrato reportada por `check` se arregla en el código o
  se escala como una decisión, nunca se silencia.
- Si un criterio no se puede cumplir, detente y díselo al usuario antes de
  cambiar la spec.
- Solo salida real. Si un comando no pudo ejecutarse en este entorno, dilo.
