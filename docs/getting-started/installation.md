# Installation

## Requirements

- Python 3.11 or newer.
- git. AtipSpec reads the base commit, the contract rules, the freshness of
  the evidence and the diff from git; without it the gate is red.
- A coding client with file access: Claude Code, Codex, Cursor, GitHub
  Copilot agent mode, Gemini CLI or Antigravity.

AtipSpec has no third-party dependencies and never calls a model API. The
model that does the work is the one inside your client.

## Platforms

Linux, macOS and Windows; CI runs the test suite on Linux and on Windows,
whose code page is not UTF-8. On Windows:

- `atipspec run`, the optional process runner, needs a POSIX system (Linux,
  macOS or WSL) to stop an adapter's processes. The guided conversation in your client
  works everywhere, with the same phases and gate.
- The plan's Verify commands run in the platform's shell, `cmd.exe` on
  Windows. Write commands both shells accept, such as `python -m pytest`, or
  call a script.
- Approvals and evidence do not depend on line endings: AtipSpec reads CRLF
  as LF wherever it hashes a file or checks a signature, so what is approved,
  accepted or verified in a checkout with `core.autocrlf` (the Git for Windows
  default) holds on Linux and macOS, and the other way round. AtipSpec writes
  its files as UTF-8 with LF.

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
  spec-driven delivery with a deterministic gate · v0.3.0

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

For Claude Code, `init` also merges two kinds of permission rules into the
shared `.claude/settings.json`: Claude Code asks you before it runs `atipspec
accept` and before its edit tools change `.github/workflows/**`,
`.gitlab-ci.yml` or `.claude/settings*.json`, and its edit tools may not write
approval, evidence, review round or archive records.
Nothing else in that file changes, and a file that is not plain JSON is left
alone with the rules printed to add by hand. See
[approval permission rules](../clients.md#approval-permission-rules).

Flags skip the questions, which is what scripts need:

```bash
atipspec init --name shop --language es --client claude --client cursor
```

!!! tip "Already initialized?"
    Running `atipspec init` again shows the state of the project and offers a
    menu: add or remove clients, update the framework and skills to the
    installed CLI version, change the name or the language. After upgrading
    AtipSpec, run `atipspec install --update` in each project; it also repairs
    missing permission rules. Until then `audit`, `check` and `merge-check`
    fail: the framework every phase prints must be the installed version's.

`init` warns when the repository has no `.gitignore`: build caches such as
`__pycache__/` or `node_modules/` change the working tree and make evidence
stale, so commit one before `atipspec new`: one added inside a delivery is a
file outside its scope.

## Commit what init created

`.atipspec/` is part of your repository: the contract, the living specs, the
deliveries and their evidence are shared with the team through git. Only
`.atipspec/tmp/` is ignored.

```bash
git add .atipspec .claude .cursor
git commit -m "chore: initialize AtipSpec"
```

Next: the [quick start](quick-start.md).
