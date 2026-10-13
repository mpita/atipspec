# Clientes

O AtipSpec funciona dentro do cliente de programação que você já usa.
`atipspec init` instala as mesmas skills onde cada cliente as descobre; a CLI
é a mesma em todos os lugares. O que muda é como você invoca uma skill e como
o revisor recebe uma sessão isolada.

## Uma skill por fase

Cada fase tem sua própria skill, nomeada conforme a fase, além de uma skill
guarda-chuva para status e perguntas sobre o fluxo:

| Skill | O que faz |
| --- | --- |
| `atipspec-contract` | define ou altera o contrato de arquitetura |
| `atipspec-explore` | resume em um briefing uma ideia que ainda não está clara |
| `atipspec-spec` | a entrevista e os cenários na spec viva; com o plano, a proposta que você aprova no ponto de parada 1 |
| `atipspec-fix` | um defeito: o requisito aceito que ele quebra, corrigido com um critério de regressão, e um plano de uma tarefa, sem entrevista |
| `atipspec-plan` | abordagem, escopo, tarefas e testes, apresentados com a proposta |
| `atipspec-build` | código e testes, cada tarefa registrada com `task-done`, e depois a verificação final |
| `atipspec-review` | a revisão adversarial em uma sessão isolada |
| `atipspec-deliver` | o resultado para sua aceitação no ponto de parada 2, e depois o arquivamento na spec viva |
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

    **Revisor em uma sessão isolada**: o modelo usa a ferramenta Agent com
    um subagente general-purpose e o prompt "Read
    `.atipspec/tmp/password-reset-review-packet.md` and do what it says." O
    subagente nunca vê a conversa, então escreve `session: isolated`.

=== "Codex"

    **Invocar**

    ```text
    $atipspec-spec password-reset: users should be able to reset a forgotten password
    ```

    **Revisor**: um subagente quando sua versão do Codex oferece um; caso
    contrário, abra uma segunda sessão do Codex no projeto e cole o prompt do
    pacote. Qualquer um dos dois escreve `session: isolated`; um review
    escrito na mesma sessão escreve `session: shared`.

=== "Cursor"

    **Invocar**: escolha *atipspec-spec* (ou a fase que você precisa) no
    seletor de skills, ou peça ao Agent para usá-la e descreva a entrega.

    **Revisor**: um agente em segundo plano com o prompt do pacote, ou um
    novo chat que não viu o trabalho: `session: isolated`. No mesmo chat:
    `session: shared`.

=== "GitHub Copilot"

    **Invocar**: no modo agente, peça ao Copilot para usar a skill
    atipspec-spec e descreva a entrega.

    **Revisor**: uma nova sessão de agente com o prompt do pacote:
    `session: isolated`. Na mesma sessão: `session: shared`.

=== "Gemini CLI"

    **Invocar**: verifique `/skills list`, depois peça a ele para usar
    atipspec-spec. Skills de projeto exigem um workspace confiável.

    **Revisor**: uma nova sessão com o prompt do pacote: `session: isolated`.
    Na mesma sessão: `session: shared`.

=== "Antigravity"

    **Invocar**: peça ao agente para usar a skill atipspec-spec.

    **Revisor**: um subagente ou uma nova sessão com o prompt do pacote:
    `session: isolated`. Na mesma sessão: `session: shared`.

O revisor declara `session:` em `review.md`; nada no cliente o comprova. Um
review compartilhado é um aviso, e um erro com `risk: high` ou
`require_isolated_review` (veja [review](flow/review.md)): nesse caso, peça
uma nova sessão para o revisor.

## O que o modelo carrega

Uma skill de fase tem poucas linhas. O comando da fase imprime todo o resto:
o cabeçalho da fase com o status derivado, o workflow da fase em
`.atipspec/framework/workflows/`, as regras compartilhadas em
`.atipspec/framework/rules.md`, e a saída de `atipspec context <slug>`. O
modelo lê `specs/` apenas conforme o contexto o seleciona e escreve a spec
viva que altera, nunca lê o archive por inteiro, e nunca lê um workflow de
uma fase em que não pode entrar.

## Regras de permissão de aprovação

Você aprova na conversa, e o assistente registra isso com
`atipspec accept ... --code <code>`. Onde o cliente pode ser configurado para
perguntar a você antes de esse comando rodar, `init` e `install` o
configuram, e o registro diz isso em seu `channel`:

| Cliente | O que o AtipSpec instala | Canal de um `accept` do assistente |
| --- | --- | --- |
| Claude Code | `.claude/settings.json`: `ask` para `Bash(*atipspec accept *)`, e para `Edit` em `.github/workflows/**`, `.gitlab-ci.yml` e `.claude/settings*.json`; `deny` de `Edit` em `.atipspec/deliveries/*/approvals/**`, `.atipspec/deliveries/*/evidence/**`, `.atipspec/deliveries/*/review-rounds.json`, `.atipspec/approvals/**` e `.atipspec/archive/**` | `client-permission` enquanto essas regras estiverem intactas e nenhum hook do projeto responder à pergunta, `assistant` caso contrário |
| Codex | nada ainda: as regras de projeto em `.codex/rules/*.rules` podem perguntar antes de um prefixo de comando, mas só carregam em uma camada de projeto confiável e seu comportamento com `approval_policy = never` não foi verificado | `assistant` |
| Cursor | nada: `.cursor/cli.json` tem listas de permissão e de negação, sem perguntar, e só para sua CLI | `assistant` |
| GitHub Copilot | nada: a configuração de aprovação automática do terminal do VS Code é de melhor esforço, não uma fronteira de segurança | `assistant` |
| Gemini CLI | nada: seu motor de políticas pode perguntar, mas as políticas de workspace hoje não carregam | `assistant` |
| Antigravity | nada: suas regras de permissão são globais ou definidas na IDE | `assistant` |

Como as regras do Claude Code se comportam:

- O Claude Code avalia `deny`, depois `ask`, depois `allow`; uma regra
  `allow` nunca as sobrepõe, e as regras `ask` perguntam em todos os modos de
  permissão. Nos modos que não podem perguntar, o comando é negado, então
  nada é registrado.
- A pergunta pede que você permita o comando exato, com o código do
  conteúdo que você aprovou; ela confirma essa mesma aprovação, não é uma
  segunda.
- As regras `deny` cobrem as ferramentas de edição do Claude Code, os
  comandos de arquivo que ele reconhece e os redirecionamentos; versões
  anteriores à 2.1.210 tratam as regras de `Edit` e os redirecionamentos de
  outra forma. Elas não cobrem programas arbitrários, como um script que
  escreve um arquivo.
- As regras `ask` para `Edit` em `.github/workflows/**`, `.gitlab-ci.yml` e
  `.claude/settings*.json` fazem as ferramentas de edição do Claude Code
  perguntarem a você antes de alterar a CI que executa `merge-check`, ou as
  configurações que guardam estas regras. Ao contrário das regras `deny`, elas
  não barram um redirecionamento: com o Claude Code 2.1.296 no modo
  `acceptEdits`, um comando Bash que as configurações permitem, como `echo`,
  `printf` ou `python3 -c`, escreveu em `.github/workflows/` com um
  redirecionamento sem perguntar, e qualquer programa que a sessão possa
  executar pode escrever ali. A proteção que se mantém é o `merge-check`: ele
  bloqueia um branch que altera a CI, as configurações do cliente ou as skills
  fora de uma entrega, e a CI em si é protegida no provedor (veja [CI antes do
  merge](enterprise.md#ci-antes-do-merge)).
- As regras são carregadas do `.claude/settings.json` do projeto: abra a
  sessão na raiz do projeto. Uma sessão aberta em um subdiretório, ou em uma
  pasta pai ou outro repositório que entra no projeto com `cd` (algumas
  sessões de workflows e de subagentes fazem isso), `--setting-sources` sem
  `project`, as configurações de usuário ou gerenciadas, e os hooks nelas
  que respondem aos pedidos de permissão as contornam sem que a CLI consiga
  perceber. Um hook `PreToolUse` ou `PermissionRequest` para Bash no
  `.claude/settings.json` ou no `.claude/settings.local.json` do projeto é
  visível: `status` e `audit` o nomeiam e o canal é `assistant`. Sessões
  executadas pelo Agent SDK, que não carrega configurações de projeto a
  menos que seu programa peça e repassa as perguntas a esse programa, e
  `claude -p` registram `assistant`.
- A mesclagem mantém todas as outras chaves e entradas, adiciona apenas as
  regras que faltam e não escreve nada quando todas estão presentes. Um
  arquivo que não é JSON puro (com comentários, por exemplo) ou um link
  simbólico fica intocado, e as regras são impressas para que você as
  adicione manualmente. Remover o Claude Code no menu do `init` remove
  apenas essas regras.
- `audit` avisa quando as regras estão ausentes ou incompletas, nomeando as
  que faltam, e `status` imprime uma linha `approvals:` com o estado delas.
  Até que todas estejam lá, as aceitações são registradas com o canal
  `assistant`. `atipspec install --update` as repara.

`client-permission` significa que as regras que fazem o Claude Code perguntar
a você estão neste projeto, não que a sessão as carregou nem que a CLI viu
você confirmar. Em um terminal sem marcadores de agente, `accept` pede que
você digite o código (canal `terminal`); um agente pode remover seus
marcadores e responder a esse prompt a partir de um terminal que ele cria,
então nenhum canal identifica quem aprovou: eles descrevem como o comando
foi executado. Para aprovações autenticadas, use uma
[política de confiança externa](enterprise.md).

## Idioma

O inglês é o idioma principal; espanhol e português são suportados. Os
arquivos do framework, as skills e a saída da CLI permanecem em inglês: uma
única fonte, lida por um modelo que segue instruções em inglês e responde a
você no seu idioma. O que uma pessoa lê segue `language` em `config.yaml`: o
dossiê de aceitação de `atipspec report`, e este site, que existe nos três
idiomas com um seletor. O que o modelo escreve no seu idioma é entendido pela
CLI: nomes de seção como `Intención` ou `Intenção`, `Fuera de alcance` ou
`Fora do escopo`, `Atributos de calidad` ou `Atributos de qualidade`,
`Preguntas abiertas` ou `Questões em aberto`; marcadores de vazio como
`Ninguna` ou `Nenhuma`; rótulos como `Por qué:` ou `Observado:`; e os
gatilhos do lint, os termos vagos e as palavras de medição. IDs, cabeçalhos
de template e status permanecem como os templates os definem, porque a CLI
os interpreta.

## Atualizando

Depois de atualizar a CLI, execute em cada projeto:

```bash
atipspec install --update
```

Isso substitui os arquivos de framework e de skill que diferem da versão
instalada, remove os arquivos de `.atipspec/framework/` que essa versão não
instala, mescla em `.claude/settings.json` as regras de permissão do
Claude Code que faltarem sem remover nada, e nunca toca em mais nada.
Enquanto ele não é executado, `audit`, `check` e `merge-check` falham: cada
fase imprime ao agente as regras e os workflows do framework, então eles
precisam ser os que a versão instalada traz, como as skills. Fixe a mesma
versão na CI que executa `merge-check`. Uma
instalação anterior à 0.1.0 tinha uma única skill `atipspec`; a atualização
substitui seu conteúdo e adiciona as skills de fase ao lado dela.
