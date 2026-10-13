# Configuração

`.atipspec/config.yaml`, escrito por `init`:

```yaml
name: shop
language: es
approve_plan: true
review_rounds: 3
context_budget: 800
strict_scope: true
criteria_syntax: ears
strict_criteria: true
max_requirements: 5
max_tasks: 8
max_age_hours: 8
trust: optional
require_proof: false
require_isolated_review: false
exempt_paths: []
```

| Chave | Padrão | Significado |
| --- | --- | --- |
| `name` | nome da pasta | nome do projeto, exibido por `status` |
| `language` | `en` | idioma em que o modelo escreve os artefatos; `en`, `es` e `pt` também orientam o lint de critérios, os nomes de seção que o parser aceita e o dossiê de aceitação. Outro código funciona com as tabelas em inglês, e `audit` avisa isso |
| `approve_plan` | `true` | apenas entregas antigas: `atipspec build` recusa até que a aprovação própria do plano seja registrada (`accept <slug> plan`). Uma entrega guiada aprova seu plano com a proposta, diga o que disser esta chave |
| `review_rounds` | `3` | quantas revisões uma entrega tem por acordo aprovado, contando a primeira, digam o que disserem as revisões; as saídas dizem `review N of M`. `atipspec review` e `atipspec run` as contam e param quando se esgotam; menos um, também é o padrão e o máximo que `--max-rounds` permite. A aprovação de uma proposta guiada a cobre; em uma entrega antiga, nenhuma aprovação a cobre. Veja [rodadas de revisão](../flow/review.md#rodadas-de-revisao) |
| `context_budget` | `800` | linhas; `atipspec context` avisa acima disso |
| `strict_scope` | `true` | um plano deve declarar seu `scope`, e globs que juntos correspondem a todo caminho (`**`, `**/*`, `*` com `*/**`) não declaram nenhum; um arquivo alterado fora dele é um erro. Com `false`, um arquivo fora de um escopo declarado é um aviso e um escopo vazio é permitido |
| `criteria_syntax` | `ears` | `ears` reporta declarações de critério que não começam com um gatilho nem trazem um shall; `free` desliga apenas essa verificação |
| `strict_criteria` | `true` | as verificações estritas da especificação são erros e bloqueiam a proposta: a forma EARS, termos vagos em requisitos, critérios e passos de cenário, e o número no critério de um atributo de qualidade. Com `false`, são avisos. A recomendação de valores concretos e de métodos de medição é um aviso em qualquer caso; veja [escrever critérios](spec-quality.md) |
| `max_requirements` | `5` | `check` avisa quando uma spec tem mais requisitos: uma entrega deve caber em um dia de trabalho |
| `max_tasks` | `8` | `check` avisa quando um plano tem mais tarefas |
| `max_age_hours` | `8` | `check`, `status` e o dossiê avisam quando o lead time de uma entrega é maior que isso: horas de relógio desde sua criação (`created`, escrito por `new`) até a aceitação de seu resultado, ou até agora enquanto isso não acontece. Um aviso, nunca um bloqueio |
| `require_proof` | `false` | `true`: todo critério sob `Tests:` precisa de uma entrada `Proof:` que nomeie seu teste, e a verificação que o executa, de um `Report:`; a falta de um é um erro que bloqueia a proposta. Uma política de confiança também pode defini-la, e então o projeto não pode desligá-la. Veja [build](../flow/build.md) |
| `require_isolated_review` | `false` | `true`: uma revisão com `session: shared`, ou sem sessão, é um erro em vez de um aviso, como já é com `risk: high`. Uma política de confiança também pode defini-la |
| `trust` | `optional` | `required`: o projeto precisa de uma política de confiança externa. Sem ela, `check` e `merge-check` ficam vermelhos, `accept` recusa toda forma local exceto `contract`, `deliver` recusa e `run` não inicia; `proposal` não mostra nenhum código local. `merge-check` a aplica quando o head, o branch de destino ou a base de merge a definem, de modo que um branch não pode retirá-la para o seu próprio merge, nem mesmo um criado antes dela |
| `exempt_paths` | `[]` | globs de arquivos fora de `.atipspec/` que um branch pode alterar sem que nenhuma entrega os cubra, como `["docs/**", "*.md"]`: `**` atravessa diretórios, `*` e `?` não. `merge-check` os lê do `config.yaml` do branch de destino (a revisão `--base`), nunca do branch que julga, de modo que um branch não pode isentar as próprias mudanças, e avisa em um branch que os altera. Quem decide é a pessoa. Nenhuma aprovação o inclui no hash. Veja [merge-check](cli.md#atipspec-merge-check) |
| `system` | não definido | caminho para um checkout do repositório de sistema. `atipspec new` fixa seu `contract.md`, e seu `glossary.md` quando ele tem um, no commit atual do checkout, no `contracts.json` da entrega guiada, e o contexto dessa entrega os lê dali; as entregas antigas leem o checkout como está. Veja [vários repositórios](../teams.md#varios-repositorios) |

Apenas `name` e `language` são gerenciados por `atipspec init`; edite o
restante à mão. `init --language en` em um projeto existente mantém as outras
chaves.

Todo comando, exceto `init`, valida as políticas primeiro e para com
`Invalid .atipspec/config.yaml: <key> must be ...`: booleanos são `true` ou
`false`, números são inteiros positivos (`max_age_hours` pode ter fração,
como `7.5`), `criteria_syntax` é `ears` ou `free`, `trust` é `optional` ou
`required`, `exempt_paths` é uma lista de globs. Uma chave omitida assume seu
padrão.

Os padrões só se aplicam onde falta uma chave. Projetos criados antes da
0.3.0 têm `strict_scope: false`, `strict_criteria: false` e
`max_age_hours: 48` escritos por extenso e os mantêm; `audit` aponta os dois
primeiros, e `install --update` lista toda política que difere dos padrões
desta versão sem editar o arquivo. `config.yaml`, exceto `exempt_paths`, faz
parte do que a aprovação de uma proposta guiada inclui no hash: altere-o
quando nenhuma entrega guiada estiver entre sua proposta e seu resultado, ou
apresente essas propostas de novo.

## `.atipspec/teams.json`

Opcional, escrito à mão: as refs que o quadro da equipe lê, os donos de cada
capacidade, os outros repositórios de onde os contratos são fixados, o branch
de integração e o endereço do rastreador de tickets. Veja [configuração da
equipe](../teams.md#configuracao-da-equipe). A aprovação de uma proposta
guiada inclui no hash apenas os donos de sua capacidade e `integration`,
então adicionar refs, repositórios ou `ticket_url` não anula nenhuma
aprovação.

## `.atipspec/adapter.json`

Opcional, escrito à mão: o adaptador de processo que `atipspec run` chama,
como `{"schema": 1, "name": ..., "command": [...], "isolated_review": false}`.
O comando é um array argv, não código de shell. A aprovação de uma proposta
guiada inclui o arquivo no hash. Veja [o adaptador de
execução](execution-adapter.md).

## `.atipspec/.gitignore`

Criado por `init`; ignora `tmp/`, onde os pacotes de revisão são escritos e
onde fica o `Report:` JUnit de um plano, como `.atipspec/tmp/junit.xml`. Todo
o resto sob `.atipspec/` deve ser commitado: o contrato, as specs vivas, as
entregas com suas evidências e revisões, o arquivamento.

## `.claude/settings.json`

Escrito ou mesclado por `init` e `install` quando o Claude Code é um cliente:
regras `ask` para `Bash(*atipspec accept *)` e para `Edit` sobre
`.github/workflows/**`, `.gitlab-ci.yml` e `.claude/settings*.json`, e regras
`deny` para `Edit` sobre os registros de aprovação, de evidência, de rodadas de revisão
(`review-rounds.json`) e do arquivamento. Toda outra chave e entrada é
mantida. Veja [regras de permissão de
aprovação](../clients.md#regras-de-permissao-de-aprovacao).

## Ambiente

| Variável | Efeito |
| --- | --- |
| `NO_COLOR` | desabilita cores na saída do terminal |
| `TERM=dumb` | o mesmo |
| `ATIPSPEC_TRUST_POLICY` | caminho da política de confiança externa; todo comando a usa, como `--policy` (veja [confiança da organização](#confianca-da-organizacao)) |
| `ATIPSPEC_POLICY_SHA256` | o SHA-256 que a política deve ter, como `--policy-sha256` |
| `ATIPSPEC_PR_NUMBER` | o pull request que uma política no modo provider lê, como `--number` |
| `GITHUB_TOKEN`, `GITLAB_TOKEN` | tokens somente leitura dos adaptadores de provedor, apenas no worker protegido; `verify` os remove, junto com o agente SSH e os tokens dos jobs de CI e de OIDC, dos comandos que executa |
| `CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`, `COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT` | definidas pelos agentes de programação; `accept` nunca registra o canal `terminal` enquanto uma delas estiver definida, nem `client-permission` enquanto uma delas nomear um agente diferente do Claude Code (os valores `0`, `false`, `no` e `off` são ignorados) |
| `CLAUDE_CODE_ENTRYPOINT` | definida pelo Claude Code; `sdk-ts` e `sdk-py` (o Agent SDK) e `sdk-cli` (`claude -p`) fazem `accept` registrar o canal `assistant` |

## Confiança da organização

As configurações locais do projeto orientam o assistente; elas não podem
flexibilizar a aceitação confiável. `approve_plan: false` pula a aprovação do
plano de uma entrega antiga, não a exigência de aprovação confiável da
engenharia. A política TOML externa controla papéis, chaves públicas, regras
corporativas e identidades de provedores. Ela deve viver fora do candidato.
Seus `require_proof` e `require_isolated_review` se somam aos do projeto: o
portão aplica uma exigência quando qualquer um dos dois a define como `true`.
Seu `integration` opcional, um nome de ref completo como
`refs/remotes/origin/main`, nomeia o branch cujo histórico conta como
integrado, de modo que o que uma entrega incorpora a partir dele não é
mudança da entrega em `check`, no pacote de revisão e no dossiê; sob uma
política, o `integration` de teams.json
não nomeia nenhum branch, embora as aprovações ainda o incluam no hash. Veja
[quando a main avança](../teams.md#quando-a-main-avanca). No modo provider
(apenas GitHub), seu bloco `[attestation]` nomeia o workflow de evidência
confiável, `signer_workflow`, em outro repositório da mesma organização, e
fixa seu commit, `signer_digest`; uma política sem eles não carrega. Veja
[dois modos de confiança](../enterprise.md#dois-modos-de-confianca).

`ATIPSPEC_TRUST_POLICY` seleciona essa política; `ATIPSPEC_POLICY_SHA256`
fixa seu conteúdo. Use a configuração protegida da organização, não valores
fornecidos pelo projeto. Os adaptadores GitHub/GitLab usam `GITHUB_TOKEN` /
`GITLAB_TOKEN` somente leitura no coletor confiável. O executor de
verificação remove essas credenciais dos ambientes de comando. Veja a
[aceitação empresarial](../enterprise.md).
