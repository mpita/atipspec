# Artefatos

Especificações e planos usam Markdown com um pequeno frontmatter YAML.
Evidência, registros de aprovação e recibos de relatório usam JSON;
assinaturas são arquivos SSH destacados. A CLI analisa algumas formas de
linha e ignora comentários HTML e blocos de código, então os templates podem
carregar orientações que o modelo apaga ao escrever.

## Identificadores

| Tipo | Formato | Escopo |
| --- | --- | --- |
| Slug de entrega, capacidade, iniciativa, decisão | `[a-z0-9-]`, ex.: `password-reset` | projeto |
| Requisito | `REQ-PRICING-7KQ2M-001`, de `atipspec ids`; `REQ-001` em entregas antigas | capacidade, estável entre entregas |
| Critério de aceitação | `AC-PRICING-7KQ2M-001`; `AC-001` em entregas antigas | capacidade, estável entre entregas |
| Tarefa | `T1` | a entrega |
| Achado | `F1` | a revisão |
| Decisão | `DEC-001` | projeto, nunca reutilizado |

Equipes que trabalham em paralelo em uma mesma capacidade obtêm IDs de
`atipspec ids <capability>`: a capacidade em maiúsculas, um token de cinco
caracteres em base32 de Crockford (sem I, L, O nem U) que nenhum ID visível
usa, e um número; cada entrega numera seus demais requisitos e critérios com
seu token, `-002`, `-003`. Os IDs mais longos de versões anteriores, com 32
caracteres hexadecimais, e os IDs numerados das [entregas
antigas](legacy.md#ids) continuam válidos e nunca são renumerados. Os IDs
importados são derivados do título da mesma forma.

## `spec.md`

O `spec.md` de uma entrega guiada (`schema: 2`, o que `atipspec new` cria)
contém para que serve a mudança e o que ela decide. Seus requisitos vivem em
`specs/<capability>.md`, e `requirements` lista seus IDs:

```markdown
---
title: "Password reset"
status: draft          # `atipspec accept <slug> proposal` sets ready when it records the human's approval
capability: auth
impact: []
owner: ana
ticket: SHOP-12        # a key, an issue number such as "#42" or an https URL; not part of the approval
initiative: null
base: 9f2c1e...        # the full id of the commit `new` recorded; check compares with it, so it never changes
created: 2026-09-12T15:41:45Z
schema: 2
change_id: 0c5e7a...
requirements: [REQ-001, REQ-002, REQ-004]
risk: normal
---

# Password reset

## Intent

A user who forgot the password requests a reset link by email and sets a new
password with it, without contacting support.

## Out of scope

- Password policy changes.

## Quality attributes

- REQ-004: p95 below 300 ms with 100 requests per minute

## Assumptions

- The link is single-use.

## Open questions

- None
```

| Seção | O que `check` pede |
| --- | --- |
| `## Intent` | o ator, o gatilho, o resultado observável e como o usuário saberá que funcionou; vazia, ou apenas com `TBD`, `TODO` ou `...`, é uma pendência que bloqueia a proposta até que ela seja aprovada, e um aviso depois disso |
| `## Out of scope` | pelo menos um item, incluído `- None`; sem nenhum, está indecidida, uma pendência até que a proposta seja aprovada |
| `## Quality attributes` | uma linha `- REQ-...: limit` por requisito desta mudança que declara um limite, ou `- None`; uma linha que não nomeia nenhum é uma pendência até que a proposta seja aprovada, e um erro depois disso. Os critérios do requisito precisam de um critério de adequação (veja [escrever critérios](spec-quality.md#atributos-de-qualidade-e-criterios-de-adequacao)) |
| `## Assumptions` | cada item é um padrão que a pessoa confirma ao aprovar |
| `## Open questions` | qualquer item bloqueia a proposta |

`risk` é `low`, `normal` ou `high`: o que o portão pede do plano, da
evidência e da revisão (veja [risco](../flow/spec.md#risco)). Faz parte do
que a aprovação da proposta inclui no hash. Um `risk` ausente conta como
`normal`; outro valor é um erro.

Um fix guiado (`kind: fix`, o que `new --kind fix` cria) tem o mesmo
frontmatter. Seu `requirements` nomeia os requisitos aceitos da capacidade
que ele corrige, e seu corpo declara o defeito em vez da intenção:

```markdown
## Defect

Observed: a link created 26 hours ago still opens the reset form.

Expected: the page shows "link expired", as REQ-002 states.

Reproduction: `python -m pytest tests/auth/test_reset.py -k expired`

## Assumptions

- None

## Open questions

- None
```

`Observed:` e `Expected:` são obrigatórios (uma pendência até que a proposta
seja aprovada, um aviso depois); `Reproduction:` é recomendado. Os rótulos
também são lidos em espanhol (`Observado`, `Esperado`, `Reproducción`) e em
português (`Observado`, `Esperado`, `Reprodução`), e o cabeçalho como
`Defecto` ou `Defeito`. Um fix não tem `## Intent`, `## Out of scope` nem
`## Quality attributes`. Veja [fix](../flow/fix.md#o-que-check-exige-de-um-fix)
para o que `check` pede de seus requisitos e de seu plano.

Aprovado significa que o registro de aprovação local corresponde ao conteúdo
atual; a linha `status` não conta. Sob uma política de confiança, cujas
assinaturas são a aprovação, `check` considera em vez disso o `status` que as
pessoas definem, enquanto `proposal` e `accept proposal` continuam
considerando apenas o registro local. Uma entrega criada com essas seções,
que `baseline.json` lista sob `sections`, as mantém: apagar uma delas é uma
pendência, como uma seção indecidida. Uma entrega criada antes da 0.3.0 sem
`## Out of scope` ou `## Quality attributes` recebe um aviso. Em uma entrega
aprovada, esses avisos esperam a próxima mudança da sua proposta: editar
`spec.md` só por causa deles anula a aprovação. Os nomes das seções também
são lidos em espanhol (`Intención`, `Fuera de alcance`,
`Atributos de calidad`) e em português (`Intenção`, `Fora do escopo`,
`Atributos de qualidade`).

O `spec.md` de uma [entrega antiga](legacy.md) contém ele próprio os seus
requisitos, no formato que aquela página mostra.

## `plan.md`

```markdown
---
scope: ["shop/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

## Tasks

### T1: Task title
Covers: REQ-AUTH-7KQ2M-001, REQ-AUTH-7KQ2M-002
Tests: AC-AUTH-7KQ2M-001, AC-AUTH-7KQ2M-002

### T2: Observed only
Covers: REQ-AUTH-7KQ2M-003
Manual: AC-AUTH-7KQ2M-004
Verify: none

## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
Verify:
- `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
- `ruff check .`
```

Analisado: `### Tn: title`; uma linha `Covers:` com ids de REQ; linhas
`Tests:` e `Manual:` com os critérios que a tarefa prova por um teste ou pela
observação de uma pessoa, seguindo a marca `[manual]` de cada critério; e uma
seção opcional `## Final verification` (também `Verificación final` ou
`Verificação final`) com sua lista `Verify:`, que `verify` executa uma vez
para o candidato finalizado. Uma tarefa pode ter seu próprio `Verify:`, uma
verificação de desenvolvimento, ou `Verify: none` quando só uma observação a
prova. `Verify:` é seguido de itens de lista (crases opcionais) ou da palavra
`none`. Uma linha opcional `Report:` nomeia o XML JUnit que os comandos
escrevem, em um caminho relativo dentro do projeto que o git ignora (`check`
reporta como erro qualquer outro caminho e, em toda plataforma, um caminho
que o Windows lê como absoluto ou fora do projeto, como `/x`, `C:\x` ou
`..\x`), e uma linha opcional `Proof:` seguida de itens `- AC-...: test id`
que `check` verifica contra a evidência (veja [build](../flow/build.md)); com
`require_proof: true` ou `risk: high`, todo critério sob `Tests:` precisa de
um, e sua verificação, de um `Report:`. Em um plano com verificação final,
`Report:` e `Proof:` vão nessa seção. `scope` no frontmatter lista globs dos
arquivos que as tarefas podem alterar, com a [sintaxe de glob das regras do
contrato](contract-rules.md#globs). Com `strict_scope: true`, o padrão, um
`scope` vazio ou ausente, ou um cujos globs juntos correspondem a todo
caminho, é um erro; arquivos tocados fora dele, incluídas as exclusões,
também são erros (avisos com `strict_scope: false`, em que um `scope` vazio
não declara nada), e o pacote de revisão os lista. Arquivos sob `.atipspec/`
nunca contam, nem as skills de cliente e as regras de permissão que o
AtipSpec instala enquanto contêm apenas o conteúdo dele; remover uma dessas
regras conta.

A aprovação de uma proposta guiada vincula o frontmatter, a abordagem e a
verificação final do plano, não sua seção `## Tasks`: tarefas divididas ou
adicionadas sob eles não precisam de nova aprovação. Um plano sem verificação
final é vinculado inteiro.

## `review.md`

Escrito apenas pelo revisor.

```markdown
---
tree: <fingerprint from the packet>
reviewer: <client or model>
session: isolated        # or shared; a review without it counts as shared
---

## Criteria
- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. src/auth/reset.py:42-48
- AC-003: FAIL. precise gap

## Findings
- F1 [blocker]: text
- F2 [major]: text
- F3 [minor]: text

## Notes
```

Todo critério precisa de exatamente um veredito. Um `PASS` precisa de um
ponteiro que `check` resolva: um teste que passou no relatório JUnit da
evidência atual, um `path:line` ou `path:line-line` que existe em um arquivo
do candidato, fora de `.atipspec/` e não ignorado pelo git (os logs de
evidência da entrega contam, como `evidence/logs/<file>.log:<line>`), ou um
`path::test` cujo arquivo contém esse nome como palavra; para um critério
`[manual]`, uma descrição de três palavras ou mais também passa. Um `FAIL`
precisa de seu motivo. `reviewer:` é obrigatório. `session:` é `isolated` ou
`shared`: uma revisão compartilhada é um aviso, e um erro com `risk: high` ou
`require_isolated_review`. Com `risk: low`, um critério cujo teste nomeado em
`Proof:` passou na evidência atual pode ficar sem veredito. Achados blocker e
major bloqueiam; adiar qualquer um deles exige uma aprovação de risco
confiável com expiração. Achados minor apenas informam. Veja
[review](../flow/review.md#o-que-o-portao-verifica-em-reviewmd).

## `deferred.md`

```markdown
- F2: reason, and where it will be handled
```

Apenas achados podem ser adiados. Uma entrada `AC-` ou `REQ-` é um erro.

## `brief.md`

O resultado da fase explore: Problem, Today, Options, Recommendation,
Questions for the user. Não é analisado; é incluído no contexto.

## `evidence/<task>-<timestamp>.json`

Gerado por `atipspec verify`, um arquivo por execução: `FINAL-...` para a
verificação final, `T1-...` para os comandos próprios de uma tarefa. Versão
do schema, entrega, tarefa, resultado, árvore antes e depois (impressões
digitais que deixam de fora os títulos das tarefas, de modo que a evidência
de uma tarefa renomeada continua atual), head, timestamps, ambiente e os comandos exatos com
códigos de saída, duração, cauda da saída, caminho do log completo e hash do
log; com um `Report:`, o XML JUnit copiado com seu hash, o caminho de onde
foi lido e `fresh: true` (os comandos o escreveram depois que `verify` o
apagou), e cada caso de teste com seu status. Conta o arquivo mais recente
por tarefa. Evidência com relatório mas sem a marca `fresh`, escrita pela
0.2.x, é uma pendência até que `verify` rode de novo. A atestação confiável
de CI adiciona signatário, repositório, digest da política, URL da execução e
uma assinatura destacada `.json.sig`. Arquivos não assinados são apenas
evidência local. No modo provider o arquivo não é alterado: uma atestação de
artefato do GitHub feita pelo workflow de evidência confiável cobre seu hash,
e seu `head` deve ser o commit do qual o worker protegido fez checkout. Os
caminhos de log e de relatório são escritos com `/` em toda plataforma.

## `review-rounds.json`

Escrito por `atipspec accept <slug> proposal`, que o cria, e por `atipspec
review` e `atipspec run`: o acordo aprovado para o qual
conta, quantas revisões foram contadas (pacotes de outro candidato, contando
o primeiro) e a árvore do último pacote. `check` considera apenas a revisão
desse pacote. Fica fora da impressão
digital, e as regras de permissão do Claude Code negam sua edição com as
ferramentas de edição do cliente; elas não impedem que um comando de shell o
apague. Em uma entrega guiada criada desde a 0.3.0 um arquivo que falta foi
apagado, então `review` recusa e `check` falha até a pessoa decidir; em uma
aprovada sob uma política de confiança, `atipspec review` conta de novo a
partir do `review.md` na pasta, como primeira revisão, e em uma criada antes
da 0.3.0, cujo `review.md` nomeia uma árvore da impressão digital anterior, a
partir do próximo pacote. Veja [rodadas de revisão](../flow/review.md#rodadas-de-revisao).

## `specs/<capability>.md`

A spec viva de uma capacidade: a verdade atual sobre seu comportamento, uma
seção por requisito com seus cenários.

```markdown
# auth

## Requirements

### REQ-AUTH-7KQ2M-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

#### AC-AUTH-7KQ2M-001: Registered email
- **GIVEN** a registered user with the email "ana@example.com"
- **WHEN** the user requests a reset for "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

#### AC-AUTH-7KQ2M-002 [manual]: The email reads well on a phone
- **WHEN** the reset email is opened on a 375 px wide screen
- **THEN** the "Reset password" button is visible without scrolling sideways

### REQ-AUTH-7KQ2M-004 [remove]: Security questions

#### AC-AUTH-7KQ2M-009: Questions page removed
- **WHEN** a user opens "/account/questions"
- **THEN** the system responds with status 404
```

Analisado: cabeçalhos `### REQ-...[ [remove]]: title` (níveis 2 a 4); sob
cada um, cabeçalhos de cenário `#### AC-...[ [manual|invariant]]: title` com
um passo por linha, `GIVEN`, `WHEN`, `THEN`, `AND`, `BUT` (ou `INVARIANT` em
um invariante, e as palavras de passo em espanhol e português), em negrito ou
não; e declarações de critério `- AC-...: text`, a forma antiga. Linhas
`Why:` e exemplos são para as pessoas e para o revisor. `deliver` atualiza o
arquivo por ID estável, preservando a identidade em caso de renomeação, e
remove um requisito marcado `[remove]`. Todo requisito e critério de
aceitação da spec viva tem um ID desde o início. O `requirements` de uma
entrega guiada lista os que ela escreve; veja [escrever
critérios](spec-quality.md) para o que `check` espera deles.

## `baseline.json`, `progress.json` e `run.json`

`baseline.json`, escrito por `new`: a spec viva da capacidade quando a
entrega começou (`content`), o commit (`head`) e as seções decididas do novo
`spec.md` (`sections`). O `base` da entrega tem de ser esse commit, e o diff
da proposta e a comparação de `specs/` leem a spec viva como esse commit a
tem; só uma entrega criada antes da 0.3.0, sem `sections`, compara com
`content`. A aprovação da proposta o inclui no hash.

`progress.json`, escrito por `task-done`: para cada tarefa, a nota, a hora, o
hash do acordo aprovado com seu `subject_version`, e o hash da tarefa sem seu
título. Uma tarefa conta como completa enquanto os dois coincidirem.

`run.json`, escrito por `atipspec run`: o checkpoint do executor, com seu
estado, fase, tempo decorrido, rodadas de correção e o acordo para o qual ele
executa. `progress.json` e `run.json` ficam fora da impressão digital da
árvore.

## `contracts.json` e `sources/`

O `contracts.json` de uma entrega guiada (`schema: 1`) lista os contratos que
ela fixou de outros repositórios, com `contract-pin` ou, para o repositório
de sistema, em `new`: cada um com `name`, `repository`, `revision` (um id de
commit completo), `path` e o `sha256` de seu conteúdo. A aprovação da
proposta o inclui no hash.

`sources/<sha256>.md` guarda cada documento que `spec-bind` importou, tal
como era; `sources` em `spec.md` os lista e `## Import review notes` diz o
que verificar antes de aprovar.

## `decisions/DEC-nnn-<slug>.md`

```markdown
---
id: DEC-003
title: "Use httpx for outbound HTTP"
status: accepted        # proposed, accepted, superseded, rejected; set by `accept contract` when it affects the contract
affects: [contract:dependencies, notifications]
supersedes: null
date: 2026-09-12
---

## Context
## Decision
## Alternatives
## Consequences
## Revisit when
```

`context` carrega as decisões aceitas cujo `affects` nomeia a capacidade da
entrega, um item de impact, `contract` ou `*`, ou está vazio (tudo). Uma
decisão cujo `affects` nomeia `contract`, `contract:<section>` ou `*`, ou
está vazio, é aceita com o contrato: `atipspec accept contract --code <code>`
define seu status. Uma decisão assim só conta com o conteúdo que a aceitação
registrada do contrato nomeia, de modo que uma marcada como `accepted` à mão
não faz parte do contrato nem é carregada por `context`. Sem um registro,
`context` as carrega pelo status apenas quando o próprio contrato foi aceito
antes da 0.3.0.

## `initiatives/<slug>/roadmap.md`

```markdown
## Deliveries
- orders-api: Orders API
- orders-screen: Orders screen

## Interfaces
```

Analisado: linhas `- <slug>: title` sob `## Deliveries`. O status por
entrega é derivado: pending, seu status atual, ou delivered.

## Status derivado de uma entrega

| Status | Significado |
| --- | --- |
| `draft` | a proposta (em uma entrega antiga: a spec) não está aceita para seu conteúdo atual |
| `ready` | aceita, mas o plano não tem nenhuma tarefa |
| `planned` | plano com tarefas, nenhuma registrada; um plano antigo com `approve_plan` também precisa de sua aceitação |
| `in_progress` | algumas tarefas registradas com `task-done` (ou, em uma entrega antiga, com um marcador de commit) |
| `implemented` | todas as tarefas registradas, portão ainda não verde |
| `checked` | checks locais verdes; o resultado não está aceito |
| `accepted` | checks locais verdes e a aceitação do resultado atual registrada; `deliver` pode rodar |
| `verified` | portão confiável verde com política aprovada, evidência de CI assinada e aprovações humanas |
| `delivered` | mesclado na spec viva e arquivado |

## Aprovações e recibos

`approvals/local-<phase>.json` é escrito por `atipspec accept`:
`local-proposal.json` e `local-result.json` para entregas guiadas, mais
`local-spec.json` e `local-plan.json` para as antigas, incluídos os fixes
criados antes da 0.3.0. Campos (schema 2):

| Campo | Significado |
| --- | --- |
| `kind`, `delivery`, `phase` | `local-acceptance`, o slug e a fase |
| `subject` | sha256 do conteúdo aceito; `check` o compara a cada execução |
| `subject_version` | como o subject foi calculado: 2 desde a 0.3.0; um registro sem ele é da versão 1 |
| `code` | o código de aprovação que foi apresentado e passado com `--code` |
| `files` | o digest de cada parte do subject, para que o desvio nomeie o arquivo, ou o requisito, que mudou |
| `accepted_at`, `by`, `head` | quando, o rótulo declarado de `--by` (por padrão, a identidade do git), o commit |
| `channel`, `client` | `terminal`, `client-permission` ou `assistant`, e o cliente que o executou |

A versão 2 inclui no hash, da spec viva da capacidade de uma proposta
guiada, apenas cada requisito que a entrega lista, como
`specs/<capability>.md#REQ-...`: `check` e `merge-check` bloqueiam uma
mudança de qualquer outro, então incorporar a main não anula nenhuma
aprovação (veja [quando a main avança](../teams.md#quando-a-main-avanca)). De
`teams.json`, inclui no hash apenas os donos da capacidade e `integration`,
também sob uma política de confiança, e de `spec.md`, tudo exceto `status` e
`ticket`. A aceitação de um resultado também inclui no hash, como
`integrated`, a base de merge com o branch de integração (o da política sob
uma política) quando a entrega devolve o que esse branch alterou: o seu
dossiê mostra esses arquivos em relação a esse commit, então integrar o
branch de novo depois anula a aceitação, mesmo mantendo a árvore. A versão 1 calculava o hash dos dois arquivos inteiros; `check`
compara cada registro com a versão com que foi escrito. Os registros escritos
pela 0.2.x (schema 1, sem code, files, channel nem `subject_version`)
continuam válidos enquanto seu conteúdo não mudar; `status` os mostra como
`channel not recorded`. Eles são detecção de desvio para o portão local e são
ignorados sob uma política. Os registros `task-done` de `progress.json` e as
aprovações assinadas carregam `subject_version` da mesma forma.

`.atipspec/approvals/contract.json` é escrito por `atipspec accept contract`:
kind `contract-acceptance`, o hash do subject, o código, `content` (o digest
de `contract.md` e de cada decisão que afeta o contrato, sem suas linhas de
status), os IDs das decisões, quem, quando, o commit e o canal. Uma decisão
adicionada, editada, retirada ou marcada como aceita à mão depois disso deixa
a aceitação desatualizada até que o contrato seja apresentado e aceito de
novo.

Os registros assinados `approvals/*.json` gravam fase, identidade, papel,
timestamp da aprovação, hash do subject, repositório, digest da política e
expiração opcional. Cada um tem uma assinatura SSH `.json.sig`. Os registros
de provedor também carregam a identidade do PR/MR e a URL de origem, e são
revalidados contra o provedor no momento da aceitação e por `merge-check`.
`reports/acceptance.json` é o recibo arquivado e o índice de artefatos:
`accepted`, `acceptance_mode` (`local` ou `trusted`), as verificações do
portão, a matriz de rastreabilidade, as aprovações, os digests dos
artefatos, `kind`, `risk`, `lead_time` (`created`, `proposal_accepted_at`,
`result_accepted_at`, `hours` e `complete`: as horas de relógio desde a
criação da entrega até a aceitação de seu resultado; sob uma política, até a
última aceitação assinada), `tree` (a impressão digital da entrega), `review`
(revisor, sessão e árvore), `changes` (o commit base, cada arquivo alterado
com seu status, linhas e id de objeto, `outside_scope`, `diff_bytes` e
`diff_sha256` do diff, cujo texto fica no histórico do git, e `integrated`, a
ref de integração e os arquivos que ela trouxe, deixados de fora do resto),
`ticket` e `ticket_url`, `code_tree`, o hash de tudo o que estava fora de
`.atipspec/` quando foi entregue, `living_spec`, o digest da spec viva que
`deliver` escreveu, e `living_requirements`, o texto de cada requisito que a
entrega lista tal como `deliver` o escreveu ali (`null` para um que ela
removeu). Cada linha da matriz carrega `pointer`, aquilo a que seu veredito
PASS foi resolvido. Recibos escritos antes da 0.3.0 não têm `review`,
`changes`, `pointer`, `kind`, `risk` nem `lead_time` e continuam sendo
exibidos. `merge-check` compara `code_tree` com o head do branch e
`living_spec` com a spec viva ali, e mantém cada requisito listado no texto
que `living_requirements` registra, tal como o commit que arquivou a entrega
o adicionou, mesmo quando o texto que `deliver` escreveu nunca foi commitado
inteiro; `check` também compara com esses textos a spec viva de uma entrega
aberta, para os requisitos que o `spec.md` arquivado lista. Recibos escritos
antes da 0.3.0 não têm `code_tree` e bloqueiam um branch que os adiciona. Com
uma política de confiança, `merge-check` não aceita a palavra do recibo para
uma aceitação confiável: verifica a entrega de novo no commit anterior ao
commit de arquivamento, com os arquivos arquivados com ela, e compara a spec
viva, e cada requisito que a entrega lista, com o que `deliver` escreve a
partir desse commit. Do código, `merge-check` toma como da entrega os
arquivos que `changes` lista e os que nomeia como `integrated`, tal como
estavam ao ser entregue (com uma política, os que o seu dossiê mostra nesse
commit). Veja [aceitação empresarial](../enterprise.md).
