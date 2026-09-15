# Instalación

## Requisitos

- Python 3.11 o más nuevo.
- git. AtipSpec lee la finalización de tareas y la frescura de la evidencia
  desde git.
- Un cliente de programación con acceso a ficheros: Claude Code, Codex,
  Cursor, GitHub Copilot en modo agente, Gemini CLI o Antigravity.

AtipSpec no tiene dependencias de terceros y nunca llama a una API de
modelo. El modelo que hace el trabajo es el que hay dentro de tu cliente.

## Instalar el CLI

=== "uv (recomendado)"

    ```bash
    uv tool install atipspec
    ```

    Actualiza más tarde con `uv tool upgrade atipspec`.

=== "pip"

    ```bash
    python -m pip install --user atipspec
    ```

=== "Desde un clon"

    ```bash
    git clone https://github.com/mpita/atipspec.git
    cd atipspec
    uv tool install .            # or: python -m pip install .
    ```

    Para trabajar en el propio AtipSpec, instálalo en modo editable para que
    el comando siga al checkout: `uv tool install --reinstall -e .`

Compruébalo:

```bash
atipspec --version
```

## Configurar un proyecto

Desde la raíz de un repositorio git:

```bash
atipspec init
```

`init` pregunta el nombre del proyecto, el idioma de salida de los
artefactos, y los clientes que usas, con un selector (flechas o
++j++/++k++ para moverte, ++space++ para seleccionar, ++a++ para todos,
++enter++ para confirmar). Luego crea `.atipspec/` e instala un skill por
fase donde cada cliente los descubre.

```text
  ▄▀█ ▀█▀ █ █▀█ █▀ █▀█ █▀▀ █▀▀
  █▀█  █  █ █▀▀ ▄█ █▀▀ ██▄ █▄▄
  spec-driven delivery with a deterministic gate · v0.1.0

┌  New project
│
◇  Project name
│  shop
│
◇  Output language
│  es
│
◇  Which clients do you use?
│  Claude Code, Cursor
│
◇  Project shop, output language es
◇  Created .atipspec/ with specs/, deliveries/, archive/, decisions/, initiatives/
◇  Contract, overview and glossary skeletons ready for the contract phase
◇  Framework in .atipspec/framework/ (23 files)
◇  Claude Code: .claude/skills/atipspec*/ (11 skills) (installed)
◇  Cursor: .cursor/skills/atipspec*/ (11 skills) (installed)
│
└  AtipSpec is ready.

Next steps
  1. Open a new Claude Code session in this project and run /atipspec-contract to define the contract, then /atipspec-spec <slug>: what you want.
  2. Open a new Cursor session in this project and pick atipspec-contract in the skill picker, then atipspec-spec for each delivery.
  3. `atipspec status` shows the state and the next action at any time.
```

Los flags se saltan las preguntas, que es lo que necesitan los scripts:

```bash
atipspec init --name shop --language es --client claude --client cursor
```

!!! tip "¿Ya está inicializado?"
    Ejecutar `atipspec init` de nuevo muestra el estado del proyecto y
    ofrece un menú: añadir o quitar clientes, actualizar el framework y los
    skills a la versión instalada del CLI, cambiar el nombre o el idioma.
    Después de actualizar AtipSpec, ejecuta `atipspec install --update` en
    cada proyecto.

`init` avisa cuando el repositorio no tiene `.gitignore`: las cachés de
build como `__pycache__/` o `node_modules/` cambian el árbol de trabajo y
dejan la evidencia obsoleta, así que añade uno antes del primer `atipspec
verify`.

## Haz commit de lo que creó init

`.atipspec/` es parte de tu repositorio: el contrato, las specs vivas, las
entregas y su evidencia se comparten con el equipo a través de git. Solo
`.atipspec/tmp/` está ignorado.

```bash
git add .atipspec .claude .cursor
git commit -m "chore: initialize AtipSpec"
```

Siguiente: los [primeros pasos](quick-start.md).
