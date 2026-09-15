# build

**Del plan al código, la evidencia y los commits.** Tarea a tarea.

| | |
| --- | --- |
| Rol | Quien firma el commit. Cambios pequeños, tests que ejercitan los criterios, las convenciones de esta base de código. Lo dice ahora cuando un criterio no se puede cumplir. |
| Quién decide | El desarrollador, con el modelo. |
| Produce | código y tests, `evidence/*.json`, un commit por tarea |

## Cómo ejecutarla

```text
/atipspec-build password-reset
```

El skill ejecuta `atipspec build password-reset`, que se niega sin un plan
válido y, si no, imprime el workflow, las reglas, el contexto y la siguiente
tarea que no tiene commit. Después de cada commit, `atipspec build
password-reset --no-context` nombra la siguiente.

## El bucle, para cada tarea

1. Lee la tarea, sus requisitos y criterios, las secciones del contrato que
   toca, el código.
2. Haz el cambio más pequeño que satisfaga los criterios dentro del contrato.
   Añade o actualiza tests para que los comandos de Verify ejerciten
   realmente los criterios.
3. Ejecuta la evidencia:

    ```bash
    atipspec verify password-reset --task T1
    ```

    ```text
    [T1] $ python -m pytest -q tests/auth/test_reset.py
        3 passed in 0.21s
    [T1] ok (0.6s)
    T1: pass -> .atipspec/deliveries/password-reset/evidence/T1-20260913T154145Z-3f9a1c2e.json
    ```

4. Cuando el framework de tests escribe JUnit XML, nombra el fichero en el
   `Report:` de la tarea y el test de cada criterio bajo `Proof:`; `verify`
   copia el informe junto a la evidencia y `check` exige que el test nombrado
   se haya ejecutado y haya pasado:

    ```markdown
    ### T1: Request a reset link

    Covers: REQ-001
    Tests: AC-001, AC-002
    Report: .atipspec/tmp/junit.xml
    Proof:
    - AC-001: tests/auth/test_reset.py::test_registered_email_sends_link
    - AC-002: tests/auth/test_reset.py::test_unknown_email_same_response
    Verify:
    - `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
    ```

    Un id de test es el nombre del caso, `Class.name`, `module.Class.name` o
    `path/to/file.py::Class::name`. Sin `Proof:`, un criterio bajo `Tests:`
    lo demuestra el revisor, como antes.

5. Haz commit con el marcador en el mensaje, con la evidencia incluida:

    ```bash
    git add -A
    git commit -m "feat(auth): request password reset link [password-reset:T1]"
    ```

6. `atipspec status password-reset` y a la siguiente tarea.

## Qué hace que una tarea esté terminada

Un commit en la branch actual cuyo mensaje lleva `[<slug>:Tn]`. Nada más. No
un checkbox, no una frase del modelo. Varios ids en un solo marcador está
bien: `[password-reset:T1,T2]`.

## Qué contiene la evidencia

```json
{
  "delivery": "password-reset",
  "task": "T1",
  "result": "pass",
  "tree": "cd03ae507b3605b12a497fcbcf590894a0073076",
  "head": "9f2c1e4...",
  "started": "2026-09-12T15:41:45Z",
  "finished": "2026-09-12T15:41:46Z",
  "commands": [
    {"command": "python -m pytest -q tests/auth/test_reset.py", "exit_code": 0,
     "duration_s": 0.58, "output_tail": "3 passed in 0.21s"}
  ]
}
```

`tree` es la huella del árbol de trabajo contra el que se ejecutaron los
comandos. La puerta acepta la evidencia solo mientras el árbol siga
coincidiendo. Con un `Report:`, el fichero también lleva `reports` (la copia
bajo `evidence/logs/` con su hash) y `tests` (cada caso con su estado), y
alterar la copia se detecta igual que alterar un log de comando. Si un
comando modifica el árbol (un formateador, un fichero generado), `verify` lo
dice y la evidencia ya queda obsoleta: haz commit o descarta y vuelve a
ejecutarla.

## Reglas

- Nunca toques `evidence/` a mano.
- El trabajo imprevisto se convierte en una tarea nueva con `Covers` y
  `Verify`, nunca escondido dentro de otra; un fichero fuera del `scope` del
  plan se añade a `scope` en la misma edición que añade la tarea que lo
  necesita.
- Ningún refactor más allá de la tarea.
- Una violación del contrato reportada por `check` se arregla en el código o
  se escala como una decisión, nunca se silencia.
- Si un criterio no se puede cumplir, detente y díselo al usuario antes de
  cambiar la spec.
- Solo salida real. Si un comando no pudo ejecutarse en este entorno, dilo.
