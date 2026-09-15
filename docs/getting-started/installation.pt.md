# Instalação

## Requisitos

- Python 3.11 ou mais recente.
- git. O AtipSpec lê a conclusão de tarefas e a atualidade da evidência a
  partir do git.
- Um cliente de programação com acesso a arquivos: Claude Code, Codex,
  Cursor, GitHub Copilot agent mode, Gemini CLI ou Antigravity.

O AtipSpec não tem dependências de terceiros e nunca chama uma API de
modelo. O modelo que faz o trabalho é aquele dentro do seu cliente.

## Instale a CLI

=== "uv (recomendado)"

    ```bash
    uv tool install atipspec
    ```

    Atualize depois com `uv tool upgrade atipspec`.

=== "pip"

    ```bash
    python -m pip install --user atipspec
    ```

=== "A partir de um clone"

    ```bash
    git clone https://github.com/mpita/atipspec.git
    cd atipspec
    uv tool install .            # or: python -m pip install .
    ```

    Para trabalhar no próprio AtipSpec, instale-o em modo editável para que
    o comando acompanhe o checkout: `uv tool install --reinstall -e .`

Verifique:

```bash
atipspec --version
```

## Configure um projeto

A partir da raiz de um repositório git:

```bash
atipspec init
```

`init` pergunta o nome do projeto, o idioma de saída para os artefatos, e os
clientes que você usa, com um seletor (setas ou ++j++/++k++ para mover,
++space++ para selecionar, ++a++ para todos, ++enter++ para confirmar). Em
seguida, ele cria `.atipspec/` e instala uma skill por fase onde cada
cliente as descobre.

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

Flags pulam as perguntas, que é o que os scripts precisam:

```bash
atipspec init --name shop --language es --client claude --client cursor
```

!!! tip "Já inicializado?"
    Executar `atipspec init` novamente mostra o estado do projeto e oferece
    um menu: adicionar ou remover clientes, atualizar o framework e as
    skills para a versão da CLI instalada, mudar o nome ou o idioma. Depois
    de atualizar o AtipSpec, execute `atipspec install --update` em cada
    projeto.

O `init` avisa quando o repositório não tem `.gitignore`: caches de build como
`__pycache__/` ou `node_modules/` mudam a árvore de trabalho e tornam a
evidência obsoleta, então adicione um antes do primeiro `atipspec verify`.

## Faça commit do que o init criou

`.atipspec/` é parte do seu repositório: o contrato, as specs vivas, as
entregas e suas evidências são compartilhadas com o time através do git.
Apenas `.atipspec/tmp/` é ignorado.

```bash
git add .atipspec .claude .cursor
git commit -m "chore: initialize AtipSpec"
```

Próximo: os [primeiros passos](quick-start.md).
