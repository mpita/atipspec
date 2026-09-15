# Clientes

O AtipSpec funciona dentro do cliente de programação que você já usa.
`atipspec init` instala as mesmas skills onde cada cliente as descobre; a CLI
é a mesma em todos os lugares. O que muda é como você invoca uma skill e como
o revisor recebe um contexto limpo.

## Uma skill por fase

Cada fase tem sua própria skill, nomeada conforme a fase, além de uma skill
guarda-chuva para status e perguntas sobre o fluxo:

| Skill | O que faz |
| --- | --- |
| `atipspec-contract` | define ou altera o contrato de arquitetura |
| `atipspec-explore` | esclarece uma ideia que ainda não está clara |
| `atipspec-spec` | requisitos e critérios de aceitação; termina no ponto de parada 1 |
| `atipspec-fix` | um defeito: um critério de regressão e um plano de uma tarefa, sem entrevista |
| `atipspec-plan` | tarefas que o portão consegue comprovar |
| `atipspec-build` | código, evidência e um commit por tarefa |
| `atipspec-review` | a revisão adversarial em um contexto limpo |
| `atipspec-deliver` | faz o merge na spec viva e arquiva; termina no ponto de parada 2 |
| `atipspec-curate` | mantém o contexto do projeto pequeno |
| `atipspec-ship` | executa as fases restantes, parando apenas onde a CLI para |
| `atipspec` | status, ajuda e qual fase vem a seguir |

Uma skill de fase tem poucas linhas: executa o comando da fase, faz o que ele
imprime e para se ele recusar. A CLI decide se a fase pode começar, então a
fase ativa nunca é a interpretação do modelo sobre o seu pedido.

| Cliente | `--client` | Skills instaladas em |
| --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/atipspec*/SKILL.md` |
| Codex | `codex` | `.agents/skills/atipspec*/SKILL.md` |
| Cursor | `cursor` | `.cursor/skills/atipspec*/SKILL.md` |
| GitHub Copilot | `github-copilot` | `.github/skills/atipspec*/SKILL.md` |
| Antigravity | `antigravity` | `.agents/skills/atipspec*/SKILL.md` |
| Gemini CLI | `gemini` | `.gemini/skills/atipspec*/SKILL.md` |

Codex e Antigravity compartilham uma pasta. Alguns clientes também descobrem
as pastas de skills de outros clientes; se você vir duplicatas, instale
apenas uma.

=== "Claude Code"

    **Invocar**

    ```text
    /atipspec-contract
    /atipspec-spec password-reset: users should be able to reset a forgotten password
    /atipspec-ship password-reset
    ```

    **Revisor em um contexto limpo**: o modelo usa a ferramenta Agent com um
    subagente general-purpose e o prompt "Read
    `.atipspec/tmp/password-reset-review-packet.md` and do what it says." O
    subagente nunca vê a conversa.

=== "Codex"

    **Invocar**

    ```text
    $atipspec-spec password-reset: users should be able to reset a forgotten password
    ```

    **Revisor**: um sub-agente quando sua versão do Codex oferece um; caso
    contrário, abra uma segunda sessão do Codex no projeto e cole o prompt do
    pacote.

=== "Cursor"

    **Invocar**: escolha *atipspec-spec* (ou a fase que você precisa) no
    seletor de skills, ou peça ao Agent para usá-la e descreva a entrega.

    **Revisor**: um agente em segundo plano com o prompt do pacote, ou um
    novo chat que não viu o trabalho.

=== "GitHub Copilot"

    **Invocar**: no modo agente, peça ao Copilot para usar a skill
    atipspec-spec e descreva a entrega.

    **Revisor**: uma nova sessão de agente com o prompt do pacote.

=== "Gemini CLI"

    **Invocar**: verifique `/skills list`, depois peça a ele para usar
    atipspec-spec. Skills de projeto exigem um workspace confiável.

    **Revisor**: uma nova sessão com o prompt do pacote.

=== "Antigravity"

    **Invocar**: peça ao agente para usar a skill atipspec-spec.

    **Revisor**: um sub-agente ou uma nova sessão com o prompt do pacote.

## O que o modelo carrega

Uma skill de fase tem menos de quinze linhas. O comando da fase imprime tudo
o mais: o cabeçalho da fase com o status derivado, o workflow da fase em
`.atipspec/framework/workflows/`, as regras compartilhadas em
`.atipspec/framework/rules.md`, e a saída de `atipspec context <slug>`. O
modelo nunca navega por `specs/` ou `archive/`, e nunca lê um workflow para
uma fase que não pode entrar.

## Idioma

O inglês é o idioma principal; espanhol e português são suportados. Os
arquivos do framework, as skills e a saída da CLI permanecem em inglês: uma
única fonte, lida por um modelo que segue instruções em inglês e responde a
você no seu idioma. O que uma pessoa lê segue `language` em `config.yaml`: o
dossiê de aceitação de `atipspec report`, e este site, que existe nos três
idiomas com um seletor. O que o modelo escreve no seu idioma é entendido pela
CLI: nomes de seção como `Preguntas abiertas` ou `Questões em aberto`,
marcadores de vazio como `Ninguna` ou `Nenhuma`, e os gatilhos e termos vagos
do lint de critérios. IDs, cabeçalhos de template e status permanecem como os
templates os definem, porque a CLI os interpreta.

## Atualizando

Depois de atualizar a CLI, execute em cada projeto:

```bash
atipspec install --update
```

Isso substitui os arquivos de framework e de skill que diferem da versão
instalada e nunca toca em mais nada. Uma instalação anterior à 0.1.0 tinha
uma única skill `atipspec`; a atualização substitui seu conteúdo e adiciona
as skills de fase ao lado dela.
