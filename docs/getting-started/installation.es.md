# Instalación

## Requisitos

- Python 3.11 o posterior.
- git. AtipSpec lee de git el commit base, las reglas del contrato, la
  frescura de la evidencia y el diff; sin git, la puerta está en rojo.
- Un cliente de programación con acceso a ficheros: Claude Code, Codex,
  Cursor, GitHub Copilot en modo agente, Gemini CLI o Antigravity.

AtipSpec no tiene dependencias de terceros y nunca llama a una API de
modelo. El modelo que hace el trabajo es el que hay dentro de tu cliente.

## Plataformas

Linux, macOS y Windows; la CI ejecuta la batería de tests en Linux y en
Windows, cuya página de códigos no es UTF-8. En Windows:

- `atipspec run`, el ejecutor de procesos opcional, necesita un sistema
  POSIX (Linux, macOS o WSL) para detener los procesos de un adaptador. La conversación
  guiada en tu cliente funciona en todas partes, con las mismas fases y la
  misma puerta.
- Los comandos Verify del plan se ejecutan en el shell de la plataforma,
  `cmd.exe` en Windows. Escribe comandos que acepten ambos shells, como
  `python -m pytest`, o llama a un script.
- Las aprobaciones y la evidencia no dependen de los finales de línea:
  AtipSpec lee CRLF como LF siempre que calcula el hash de un fichero o
  comprueba una firma, así que lo que se aprueba, se acepta o se verifica en
  un checkout con `core.autocrlf` (el valor por defecto de Git for Windows)
  sigue valiendo en Linux y macOS, y al revés. AtipSpec escribe sus ficheros
  en UTF-8 con LF.

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
artefactos y los clientes que usas, con un selector (flechas o
++j++/++k++ para moverte, ++space++ para seleccionar, ++a++ para todos,
++enter++ para confirmar). Luego crea `.atipspec/` e instala un skill por
fase donde cada cliente los descubre.

```text
  ▄▀█ ▀█▀ █ █▀█ █▀ █▀█ █▀▀ █▀▀
  █▀█  █  █ █▀▀ ▄█ █▀▀ ██▄ █▄▄
  spec-driven delivery with a deterministic gate · v0.3.1

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
◇  Claude Code: .claude/settings.json asks before `atipspec accept` and before edits to CI workflows or its settings, and denies edits to approval, evidence and review round records (created)
│
└  AtipSpec is ready.

Next steps
  1. Open a new Claude Code session in this project and run /atipspec-contract to define the contract, then /atipspec-spec <slug>: what you want.
  2. Open a new Cursor session in this project and pick atipspec-contract in the skill picker, then atipspec-spec for each delivery.
  3. `atipspec status` shows the state and the next action at any time.
```

Para Claude Code, `init` también fusiona dos tipos de reglas de permisos en
el `.claude/settings.json` compartido: Claude Code te pregunta antes de
ejecutar `atipspec accept` y antes de que sus herramientas de edición cambien
`.github/workflows/**`, `.gitlab-ci.yml` o `.claude/settings*.json`, y sus
herramientas de edición no pueden escribir los registros de aprobación, de
evidencia, de rondas de revisión ni del archivo. Nada más cambia en ese fichero, y un fichero que no es JSON puro se
deja intacto y se imprimen las reglas para añadirlas a mano. Consulta las
[reglas de permisos de aprobación](../clients.md#reglas-de-permisos-de-aprobacion).

Los flags se saltan las preguntas, que es lo que necesitan los scripts:

```bash
atipspec init --name shop --language es --client claude --client cursor
```

!!! tip "¿Ya está inicializado?"
    Ejecutar `atipspec init` de nuevo muestra el estado del proyecto y
    ofrece un menú: añadir o quitar clientes, actualizar el framework y los
    skills a la versión instalada del CLI, cambiar el nombre o el idioma.
    Después de actualizar AtipSpec, ejecuta `atipspec install --update` en
    cada proyecto; también repara las reglas de permisos que falten. Hasta
    entonces `audit`, `check` y `merge-check` fallan: el framework que
    imprime cada fase tiene que ser el de la versión instalada.

`init` avisa cuando el repositorio no tiene `.gitignore`: las cachés de
build como `__pycache__/` o `node_modules/` cambian el árbol de trabajo y
dejan la evidencia obsoleta, así que haz commit de uno antes de
`atipspec new`: uno añadido dentro de una entrega es un fichero fuera de su
scope.

## Haz commit de lo que creó init

`.atipspec/` es parte de tu repositorio: el contrato, las specs vivas, las
entregas y su evidencia se comparten con el equipo a través de git. Solo
`.atipspec/tmp/` está ignorado.

```bash
git add .atipspec .claude .cursor
git commit -m "chore: initialize AtipSpec"
```

Siguiente: los [primeros pasos](quick-start.md).
