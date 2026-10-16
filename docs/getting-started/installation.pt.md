# Instalação

## Requisitos

- Python 3.11 ou mais recente.
- git. O AtipSpec lê do git o commit base, as regras do contrato, a
  atualidade da evidência e o diff; sem ele, o portão fica vermelho.
- Um cliente de programação com acesso a arquivos: Claude Code, Codex,
  Cursor, GitHub Copilot agent mode, Gemini CLI ou Antigravity.

O AtipSpec não tem dependências de terceiros e nunca chama uma API de
modelo. O modelo que faz o trabalho é aquele dentro do seu cliente.

## Plataformas

Linux, macOS e Windows; a CI executa a suíte de testes no Linux e no
Windows, cuja página de código não é UTF-8. No Windows:

- `atipspec run`, o executor de processos opcional, precisa de um sistema
  POSIX (Linux, macOS ou WSL) para encerrar os processos de um adaptador. A conversa guiada
  no seu cliente funciona em qualquer lugar, com as mesmas fases e o mesmo
  portão.
- Os comandos de Verify do plano rodam no shell da plataforma, `cmd.exe` no
  Windows. Escreva comandos que os dois shells aceitem, como
  `python -m pytest`, ou chame um script.
- As aprovações e a evidência não dependem dos finais de linha: o AtipSpec
  lê CRLF como LF sempre que calcula o hash de um arquivo ou verifica uma
  assinatura, então o que é aprovado, aceito ou verificado em um checkout com
  `core.autocrlf` (o padrão do Git for Windows) vale no Linux e no macOS, e
  vice-versa. O AtipSpec escreve seus arquivos em UTF-8 com LF.

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

Para o Claude Code, o `init` também mescla dois tipos de regras de permissão
no `.claude/settings.json` compartilhado: o Claude Code pergunta a você antes
de executar `atipspec accept` e antes que suas ferramentas de edição alterem
`.github/workflows/**`, `.gitlab-ci.yml` ou `.claude/settings*.json`, e suas
ferramentas de edição não podem escrever registros de aprovação, de
evidência, de rodadas de revisão nem do archive.
Nada mais muda nesse arquivo, e um arquivo que não é JSON puro fica
intocado, com as regras impressas para que você as adicione manualmente.
Veja as [regras de permissão de aprovação](../clients.md#regras-de-permissao-de-aprovacao).

Flags pulam as perguntas, que é o que os scripts precisam:

```bash
atipspec init --name shop --language es --client claude --client cursor
```

!!! tip "Já inicializado?"
    Executar `atipspec init` novamente mostra o estado do projeto e oferece
    um menu: adicionar ou remover clientes, atualizar o framework e as
    skills para a versão da CLI instalada, mudar o nome ou o idioma. Depois
    de atualizar o AtipSpec, execute `atipspec install --update` em cada
    projeto; ele também repara as regras de permissão que estiverem
    faltando. Até lá `audit`, `check` e `merge-check` falham: o framework que
    cada fase imprime precisa ser o da versão instalada.

O `init` avisa quando o repositório não tem `.gitignore`: caches de build como
`__pycache__/` ou `node_modules/` mudam a árvore de trabalho e tornam a
evidência obsoleta, então faça commit de um antes de `atipspec new`: um
adicionado dentro de uma entrega é um arquivo fora do seu escopo.

## Faça commit do que o init criou

`.atipspec/` é parte do seu repositório: o contrato, as specs vivas, as
entregas e suas evidências são compartilhados com a equipe através do git.
Apenas `.atipspec/tmp/` é ignorado.

```bash
git add .atipspec .claude .cursor
git commit -m "chore: initialize AtipSpec"
```

Próximo: os [primeiros passos](quick-start.md).
