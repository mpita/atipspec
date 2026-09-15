# Installation

## Requirements

- Python 3.11 or newer.
- git. AtipSpec reads task completion and evidence freshness from git.
- A coding client with file access: Claude Code, Codex, Cursor, GitHub
  Copilot agent mode, Gemini CLI or Antigravity.

AtipSpec has no third-party dependencies and never calls a model API. The
model that does the work is the one inside your client.

## Install the CLI

=== "uv (recommended)"

    ```bash
    uv tool install atipspec
    ```

    Upgrade later with `uv tool upgrade atipspec`.

=== "pip"

    ```bash
    python -m pip install --user atipspec
    ```

=== "From a clone"

    ```bash
    git clone https://github.com/mpita/atipspec.git
    cd atipspec
    uv tool install .            # or: python -m pip install .
    ```

    To work on AtipSpec itself, install it editable so the command follows
    the checkout: `uv tool install --reinstall -e .`

Check it:

```bash
atipspec --version
```

## Set up a project

From the root of a git repository:

```bash
atipspec init
```

`init` asks for the project name, the output language for the artifacts, and
the clients you use, with a selector (arrows or ++j++/++k++ to move, ++space++
to select, ++a++ for all, ++enter++ to confirm). It then creates `.atipspec/`
and installs one skill per phase where each client discovers them.

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

Flags skip the questions, which is what scripts need:

```bash
atipspec init --name shop --language es --client claude --client cursor
```

!!! tip "Already initialized?"
    Running `atipspec init` again shows the state of the project and offers a
    menu: add or remove clients, update the framework and skills to the
    installed CLI version, change the name or the language. After upgrading
    AtipSpec, run `atipspec install --update` in each project.

`init` warns when the repository has no `.gitignore`: build caches such as
`__pycache__/` or `node_modules/` change the working tree and make evidence
stale, so add one before the first `atipspec verify`.

## Commit what init created

`.atipspec/` is part of your repository: the contract, the living specs, the
deliveries and their evidence are shared with the team through git. Only
`.atipspec/tmp/` is ignored.

```bash
git add .atipspec .claude .cursor
git commit -m "chore: initialize AtipSpec"
```

Next: the [quick start](quick-start.md).
