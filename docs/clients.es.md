# Clientes

AtipSpec se ejecuta dentro del cliente de programación que ya usas. `atipspec init`
instala los mismos skills donde cada cliente los descubre; el CLI es el mismo en
todas partes. Lo que cambia es cómo invocas un skill y cómo el revisor obtiene un
contexto limpio.

## Un skill por fase

Cada fase tiene su propio skill, con el nombre de la fase, más un skill paraguas
para el estado y las preguntas sobre el flujo:

| Skill | Qué hace |
| --- | --- |
| `atipspec-contract` | definir o cambiar el contrato de arquitectura |
| `atipspec-explore` | redactar el brief de una idea que aún no está clara |
| `atipspec-spec` | requisitos y criterios de aceptación; termina en el punto de parada 1 |
| `atipspec-fix` | un defecto: un criterio de regresión y un plan de una tarea, sin entrevista |
| `atipspec-plan` | tareas que la puerta puede demostrar |
| `atipspec-build` | código, evidencia y un commit por tarea |
| `atipspec-review` | la revisión adversarial en un contexto limpio |
| `atipspec-deliver` | fusionar en la spec viva y archivar; termina en el punto de parada 2 |
| `atipspec-curate` | mantener pequeño el contexto del proyecto |
| `atipspec-ship` | ejecutar las fases restantes, deteniéndose solo donde se detiene el CLI |
| `atipspec` | estado, ayuda y qué fase sigue |

El skill de una fase son pocas líneas: ejecuta el comando de la fase, haz lo que
imprime, y detente si se niega. El CLI decide si la fase puede empezar, así que la
fase activa nunca es la interpretación que el modelo hace de tu petición.

| Cliente | `--client` | Skills instalados bajo |
| --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/atipspec*/SKILL.md` |
| Codex | `codex` | `.agents/skills/atipspec*/SKILL.md` |
| Cursor | `cursor` | `.cursor/skills/atipspec*/SKILL.md` |
| GitHub Copilot | `github-copilot` | `.github/skills/atipspec*/SKILL.md` |
| Antigravity | `antigravity` | `.agents/skills/atipspec*/SKILL.md` |
| Gemini CLI | `gemini` | `.gemini/skills/atipspec*/SKILL.md` |

Codex y Antigravity comparten una carpeta. Algunos clientes también descubren las
carpetas de skills de otros clientes; si ves duplicados, instala solo uno.

=== "Claude Code"

    **Invocar**

    ```text
    /atipspec-contract
    /atipspec-spec password-reset: users should be able to reset a forgotten password
    /atipspec-ship password-reset
    ```

    **Revisor en un contexto limpio**: el modelo usa la herramienta Agent con un
    subagente general-purpose y el prompt "Read
    `.atipspec/tmp/password-reset-review-packet.md` and do what it says."
    El subagente nunca ve la conversación.

=== "Codex"

    **Invocar**

    ```text
    $atipspec-spec password-reset: users should be able to reset a forgotten password
    ```

    **Revisor**: un subagente cuando tu versión de Codex ofrezca uno; si no, abre
    una segunda sesión de Codex en el proyecto y pega el prompt del paquete.

=== "Cursor"

    **Invocar**: elige *atipspec-spec* (o la fase que necesites) en el selector de
    skills, o pide al Agent que lo use y describe la entrega.

    **Revisor**: un agente en segundo plano con el prompt del paquete, o un chat
    nuevo que no ha visto el trabajo.

=== "GitHub Copilot"

    **Invocar**: en modo agente, pide a Copilot que use el skill atipspec-spec y
    describe la entrega.

    **Revisor**: una sesión de agente nueva con el prompt del paquete.

=== "Gemini CLI"

    **Invocar**: comprueba `/skills list`, y luego pídele que use atipspec-spec.
    Los skills de proyecto requieren un espacio de trabajo de confianza.

    **Revisor**: una sesión nueva con el prompt del paquete.

=== "Antigravity"

    **Invocar**: pide al agente que use el skill atipspec-spec.

    **Revisor**: un subagente o una sesión nueva con el prompt del paquete.

## Qué carga el modelo

El skill de una fase tiene menos de quince líneas. El comando de la fase imprime
todo lo demás: la cabecera de la fase con el estado derivado, el workflow de la
fase desde `.atipspec/framework/workflows/`, las reglas compartidas de
`.atipspec/framework/rules.md`, y la salida de `atipspec context <slug>`. El
modelo nunca explora `specs/` ni `archive/`, y nunca lee el workflow de una fase a
la que no puede entrar.

## Idioma

El inglés es el idioma principal; el español y el portugués están soportados. Los
ficheros del framework, los skills y la salida del CLI se mantienen en inglés: una
sola fuente, leída por un modelo que sigue instrucciones en inglés y te responde
en el tuyo. Lo que lee una persona sigue `language` en `config.yaml`: el dosier de
aceptación de `atipspec report`, y este sitio, que existe en los tres idiomas con
un selector. Lo que el modelo escribe en tu idioma lo entiende el CLI: nombres de
sección como `Preguntas abiertas` o `Questões em aberto`, marcadores vacíos como
`Ninguna` o `Nenhuma`, y los disparadores y términos vagos del lint de criterios.
Los IDs, los encabezados de plantilla y los estados se mantienen tal como los
definen las plantillas, porque el CLI los analiza.

## Actualizar

Después de actualizar el CLI, ejecuta esto en cada proyecto:

```bash
atipspec install --update
```

Reemplaza los ficheros del framework y de los skills que difieren de la versión
instalada y nunca toca nada más. Una instalación anterior a 0.1.0 tenía un único
skill `atipspec`; la actualización reemplaza su contenido y añade los skills de
fase junto a él.
