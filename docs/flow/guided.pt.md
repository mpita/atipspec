# Entrega guiada, de ponta a ponta

Esta página acompanha uma mudança do pedido até o archive: quem faz o quê,
qual comando o assistente executa, o que a CLI verifica e quais arquivos cada
passo escreve. Os [primeiros passos](../getting-started/quick-start.md) são a
versão curta, do seu lado da conversa.

## O que é uma entrega guiada

`atipspec new` cria uma entrega guiada (`schema: 2` em seu `spec.md`), para
uma feature e, com `--kind fix`, para um [fix](fix.md). Seus requisitos vivem
na spec viva da capacidade, `.atipspec/specs/<capability>.md`; o `spec.md` da
entrega guarda para que serve a mudança e o que ela decide em torno deles:

- a intenção, o que fica fora do escopo, as suposições e as perguntas em
  aberto;
- `requirements`, os IDs dos requisitos que esta mudança adiciona, altera ou
  remove na spec viva;
- `owner`, `ticket`, `initiative` e `depends_on`;
- `base`, o commit a partir do qual `new` começou; `change_id`; `created`,
  onde começa o lead time; e `risk`, quanto o portão pede.

`new` não começa enquanto a spec viva da capacidade tem mudanças sem commit,
então o commit base a tem como a mudança parte dela: a proposta mostra a
mudança como um diff contra ele, e `check` distingue as edições desta entrega
do que o branch de integração trouxe. `baseline.json` registra esse commit;
uma entrega criada antes da 0.3.0 continua sendo comparada com a spec viva
que guardou ali. Entregas criadas antes da
0.2.0, e fixes criados antes da 0.3.0, mantêm seus requisitos dentro do
`spec.md`; veja [entregas antigas](../reference/legacy.md).

## Três decisões humanas

| Decisão | Quando | Apresentada com | Registrada com |
| --- | --- | --- | --- |
| O contrato e as decisões que ele inclui | uma vez por projeto, e quando o contrato muda | `atipspec proposal contract` | `atipspec accept contract --code <code>` |
| A proposta: cenários, abordagem, testes e risco | **ponto de parada 1**, antes de qualquer código | `atipspec proposal <slug>` | `atipspec accept <slug> proposal --code <code>` |
| O resultado revisado | **ponto de parada 2**, antes do archive | `atipspec report <slug>` | `atipspec accept <slug> result --code <code>` |

Nada mais pede uma aprovação registrada; uma decisão sobre uma capacidade
que surja é aprovada na conversa, e a próxima proposta a lista. Você decide
na conversa: o assistente
apresenta a visão, com seu código de aprovação, e oferece **Aprovar e
continuar**, **Pedir alterações** ou **Cancelar** com o seletor do cliente, ou
pede uma resposta escrita. Após sua aprovação explícita, ele executa o
comando `accept` com o código do conteúdo que mostrou a você; se esse
conteúdo mudou nesse meio-tempo, o comando recusa e o assistente o apresenta
de novo. O Claude Code, configurado pelo `init` e aberto na raiz do projeto,
pergunta a você antes de esse comando rodar: a pergunta confirma a mesma aprovação, não é uma
segunda. O registro declara seu canal, `terminal`, `client-permission` ou
`assistant` (veja [accept](../reference/cli.md#atipspec-accept)). O contrato
não é necessário para iniciar uma entrega guiada: enquanto ele não está
aceito, `check` mostra um aviso.

## Passo a passo

| Passo | Você | O assistente executa | Escreve |
| --- | --- | --- | --- |
| 1. Contrato | aprova, uma vez | `contract`, `audit`, `proposal contract`, `accept contract` | `contract.md`, `decisions/`, `approvals/contract.json` |
| 2. Criar | pede a mudança | `new` | `deliveries/<slug>/`: `spec.md`, `plan.md`, `deferred.md`, `baseline.json` |
| 3. Especificar | responde às perguntas | `spec`, `ids`, `check`, opcionalmente `spec-bind` | `specs/<capability>.md`, `spec.md` |
| 4. Planejar | | `plan`, `check` | `plan.md` |
| 5. Proposta | aprova: **ponto de parada 1** | `proposal`, `accept <slug> proposal` | `approvals/local-proposal.json`, `status: ready` |
| 6. Build | | `build`, `task-done` | código e testes, `progress.json` |
| 7. Verificar | | `verify` | `evidence/` |
| 8. Review | | `review`; um revisor em uma sessão isolada | `review-rounds.json`, `review.md` |
| 9. Resultado | aceita: **ponto de parada 2** | `check`, `report`, `accept <slug> result` | `approvals/local-result.json` |
| 10. Deliver | decide o commit e o merge | `deliver`, `merge-check` | a spec viva, `reports/acceptance.json`, `archive/<slug>/` |

### 1. O contrato

Uma vez por projeto, a [fase contract](contract.md) escreve
`.atipspec/contract.md` com as regras que a CLI verifica, e uma decisão para
cada escolha que você já fez. O assistente executa `atipspec audit`,
apresenta `atipspec proposal contract` e, após sua aprovação, registra
`atipspec accept contract --code <code>`, que define o contrato e as decisões
que ele lista como `accepted` e escreve `.atipspec/approvals/contract.json`.

### 2. Crie a entrega

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

`new` escreve `spec.md` com `status: draft`, `base` (o id completo do commit
atual), `requirements: []` e `risk: normal`; um `plan.md` para preencher; um
`deferred.md` vazio; e `baseline.json`. `--branch` cria e muda para
`delivery/password-reset`, `--worktree` faz isso em uma pasta irmã; trabalhe
com um branch por entrega (veja [equipes](../teams.md)). `--ticket` vincula
um ticket; `--depends-on` nomeia uma entrega cujo recibo aceito precisa estar
no archive antes que o check desta fique verde.

### 3. Especifique

`/atipspec-spec password-reset: <what you want>` executa `atipspec spec
password-reset`, que imprime o workflow, as regras e o contexto. O
assistente lê o código e as specs vivas, pergunta apenas o que continua em
aberto, em rodadas de no máximo três perguntas, e escreve os requisitos e
seus cenários na spec viva. Ele obtém um prefixo de ID uma vez por entrega:

```bash
atipspec ids auth
```

```text
auth/REQ-AUTH-7KQ2M-001 auth/AC-AUTH-7KQ2M-001
Number further requirements and criteria of this delivery with the same prefix: -002, -003.
```

```markdown
### REQ-AUTH-7KQ2M-001: The user can request a reset link

Why: support tickets for forgotten passwords are 40% of the queue.

#### AC-AUTH-7KQ2M-001: Registered email
- **GIVEN** a registered user with the email "ana@example.com"
- **WHEN** the user requests a reset for "ana@example.com"
- **THEN** the system answers "Check your email" and sends one reset link to "ana@example.com"

#### AC-AUTH-7KQ2M-002 [manual]: The email reads well on a phone
- **WHEN** the reset email is opened on a 375 px wide screen
- **THEN** the "Reset password" button is visible without scrolling sideways
```

Um cenário precisa de WHEN e THEN, na ordem GIVEN, WHEN, THEN; AND e BUT
estendem o passo anterior. `[manual]` marca um cenário que uma pessoa
observa, `[invariant]` um que vale sem gatilho. `### REQ-... [remove]: Title`
aposenta um requisito no deliver. O `spec.md` da entrega lista os IDs em
`requirements` e preenche `## Intent`, `## Out of scope` e
`## Quality attributes` (`- None` quando nada se aplica). Um documento
redigido por você, ou uma lista de critérios de aceitação, entra com
`atipspec spec-bind password-reset --file <path>`, que escreve a spec viva e
os IDs e não aprova nada.

`atipspec check password-reset` lista o que falta e o que o lint aponta; um
resultado vago, como "funciona corretamente", bloqueia a proposta. Veja
[spec](spec.md) e [como escrever critérios](../reference/spec-quality.md).

### 4. Planeje

O plano pode começar antes da aprovação: `atipspec plan password-reset` abre
assim que os cenários estão completos, a intenção está declarada e nenhuma
pergunta está em aberto. O assistente escreve `plan.md`:

```markdown
---
scope: ["src/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

A `request_reset(email)` function in `src/auth/reset.py` that answers the same
message for every email and sends the link only to registered ones.

## Tasks

### T1: Request a reset link

Covers: REQ-AUTH-7KQ2M-001
Tests: AC-AUTH-7KQ2M-001
Manual: AC-AUTH-7KQ2M-002

## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
Verify:
- `python -m pytest -q --junitxml .atipspec/tmp/junit.xml`
```

Todo requisito listado é coberto por uma tarefa, todo critério está em
`Tests:` ou `Manual:`, e todo `require-command` do contrato roda na
verificação final. Veja [plan](plan.md).

### 5. A proposta: ponto de parada 1

```bash
atipspec proposal password-reset
```

A visão mostra o tipo e o risco com o que o nível pede, com que rigor os
critérios são verificados, o que a evidência e o review precisam, a intenção
da mudança, os requisitos com seus cenários, o plano e o diff da spec viva
contra o commit base, com o código de aprovação. Quando algo bloqueia, ela
o lista em "Not ready for approval" e não mostra nenhum código. Após sua
aprovação, o assistente registra:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

Isso define `status: ready` e escreve `approvals/local-proposal.json` com o
hash do que você aprovou: o `spec.md` exceto seu `status` e seu `ticket`,
cada requisito que ela lista da spec viva da capacidade, `baseline.json`,
o escopo, a abordagem e a verificação final do plano, `contract.md`,
`config.yaml` exceto seu `exempt_paths`, `adapter.json`, os responsáveis
pela capacidade e `integration` de `teams.json`, e `contracts.json`. Editar
qualquer um deles
faz a entrega voltar para `draft`, e `check` nomeia o que mudou. Tarefas
adicionadas ou divididas dentro do plano não fazem isso, já que a verificação
final as cobre; outra entrega integrada a partir da main também não (veja
[quando a main avança](../teams.md#quando-a-main-avanca)).

### 6. Build

`atipspec build password-reset` recusa até a proposta estar aceita para seu
conteúdo atual, e então imprime o workflow e a próxima tarefa. O assistente
implementa cada tarefa com seus testes, dentro do `scope` do plano, e a
registra:

```bash
atipspec task-done password-reset T1 --note "request_reset answers the same message and sends only to registered emails"
```

`task-done` escreve `progress.json`: uma declaração de progresso vinculada ao
acordo aprovado, não uma prova. Ele recusa antes da aprovação. Os commits
seguem a política do seu repositório; nenhum é obrigatório. Veja
[build](build.md).

### 7. Verifique

```bash
atipspec verify password-reset
```

executa os comandos de `## Final verification` uma única vez sobre o
candidato terminado e escreve `evidence/FINAL-<time>.json` com os comandos,
os códigos de saída, os logs de saída e a impressão digital da árvore de
trabalho. Com um `Report:`, ele apaga esse arquivo antes e exige que os
comandos o escrevam de novo, e `check` exige que todo teste nomeado em
`Proof:` tenha rodado e passado. Qualquer mudança posterior na árvore torna a
evidência obsoleta. `--task T1` executa os comandos de Verify da própria
tarefa, uma verificação de desenvolvimento.

### 8. Review

```bash
atipspec review password-reset
```

recusa enquanto uma tarefa não está registrada, a evidência está obsoleta ou
o contrato é violado. Caso contrário, conta o review, escreve o pacote em
`.atipspec/tmp/password-reset-review-packet.md` e imprime `review N of M`. Um
revisor em uma sessão isolada, um
subagente ou uma nova sessão que recebe apenas o pacote, escreve
`review.md`: `tree`, `reviewer`, `session`, um PASS ou FAIL por critério com
uma referência que o portão resolve, e os achados. As correções voltam a
passar por verify e review; `review_rounds` limita quantas vezes. Veja
[review](review.md).

### 9. O resultado: ponto de parada 2

`atipspec check password-reset` passa a `checked` quando tudo está verde. O
assistente apresenta:

```bash
atipspec report password-reset
```

o dossiê: cada critério com sua evidência e seu veredito, o revisor e a
sessão, as aprovações, e cada arquivo alterado desde o commit base com o
diff, e o código de aprovação do resultado. Após sua aceitação:

```bash
atipspec accept password-reset result --code 3C1Q-4VN7
```

escreve `approvals/local-result.json`, vinculado à árvore, ao review, aos
achados adiados e à evidência. A entrega fica `accepted`; o lead time para.

### 10. Deliver

```bash
atipspec deliver password-reset
```

mescla os requisitos em `specs/auth.md` por ID, escreve o recibo
`reports/acceptance.json` (com `code_tree`, o hash de tudo o que está fora de
`.atipspec/`), define `status: delivered` e move a pasta para
`.atipspec/archive/password-reset/`. Ele não faz commit, push nem merge.
Antes do merge, `atipspec merge-check --base <target>` confirma que cada
entrega que o branch toca está aceita e que seu código ainda é o código
aceito. Veja [deliver](deliver.md).

## Valores de status

`status` e `check` derivam onde uma entrega está a partir dos seus arquivos
e do git:

`draft` → `planned` → `in_progress` → `implemented` → `checked` → `accepted` → `delivered`

| Status | Significado |
| --- | --- |
| `draft` | a proposta não está aceita para seu conteúdo atual |
| `ready` | aceita, mas o plano não tem tarefas: em uma entrega guiada, só quando suas tarefas foram removidas depois da aprovação |
| `planned` | proposta aceita, nenhuma tarefa registrada |
| `in_progress` | algumas tarefas registradas com `task-done` |
| `implemented` | todas as tarefas registradas, o portão ainda não está verde |
| `checked` | o portão local está verde; o resultado não está aceito |
| `accepted` | a aceitação do resultado atual está registrada; `deliver` pode rodar |
| `delivered` | mesclada na spec viva e arquivada |

Sob uma política de confiança externa, `verified` substitui `checked` e
`accepted`.

## Modo ship e o executor

`/atipspec-ship <slug>` mantém uma única conversa: `atipspec ship <slug>`
nomeia a próxima fase em que a entrega pode entrar, e o assistente entra
nela, parando nos dois pontos de parada, diante de uma mudança material e
diante de um bloqueio. `atipspec run <slug>` executa uma entrega aprovada por
meio de um adaptador de processos configurado, com checkpoints e orçamentos;
ele nunca aceita nada. Veja o [adaptador de
execução](../reference/execution-adapter.md).

## Com uma política de confiança externa

Uma organização que precisa de aprovações autenticadas adiciona uma política
de confiança externa. O portão então ignora os registros locais e exige
aprovações assinadas de produto, engenharia e QA e evidência de CI atestada;
o sucesso é `verified`, e `deliver` o exige. Com `trust: required` em
`config.yaml`, a aceitação local é desativada. Veja
[aceitação empresarial](../enterprise.md).

## O que é registrado onde

| Arquivo | Escrito por | Contém |
| --- | --- | --- |
| `deliveries/<slug>/spec.md` | `new`, o assistente; `status` por `accept` | a intenção e as decisões da mudança, os IDs que ela lista |
| `specs/<capability>.md` | o assistente, `spec-bind`; `deliver` ao arquivar | os requisitos e seus cenários |
| `deliveries/<slug>/baseline.json` | `new` | a spec viva quando a entrega começou |
| `deliveries/<slug>/plan.md` | o assistente | escopo, abordagem, tarefas, verificação final |
| `deliveries/<slug>/approvals/local-*.json` | `accept` | o que você aprovou, seu código, quando e o canal |
| `deliveries/<slug>/progress.json` | `task-done` | as tarefas registradas como implementadas |
| `deliveries/<slug>/evidence/` | `verify` | comandos, códigos de saída, logs, relatórios de teste |
| `deliveries/<slug>/review-rounds.json` | `review`, `run` | os reviews contados |
| `deliveries/<slug>/review.md` | o revisor | vereditos e achados |
| `deliveries/<slug>/run.json` | `run` | o checkpoint do executor |
| `archive/<slug>/reports/acceptance.json` | `deliver` | o recibo que `merge-check` lê |

Ninguém escreve manualmente os registros em `approvals/`, `evidence/` ou
`archive/`, nem `review-rounds.json`; as regras de permissão do Claude Code
negam esses arquivos às suas ferramentas de edição. Veja
[artefatos](../reference/artifacts.md).

## Entregas antigas

Entregas criadas antes da 0.2.0, e fixes criados antes da 0.3.0, mantêm seus
requisitos no `spec.md`, aprovam a spec (e o plano, com `approve_plan`) em
vez de uma proposta, e também concluem tarefas com marcadores de commit.
Veja [entregas antigas](../reference/legacy.md).
