# Artefatos

Especificações e planos usam Markdown com um pequeno frontmatter YAML.
Evidência, registros de aprovação e recibos de relatório usam JSON;
assinaturas são arquivos SSH destacados. A CLI analisa algumas formas de
linha e ignora comentários HTML e blocos de código, então os templates
podem carregar orientações que o modelo apaga ao escrever.

## Identificadores

| Tipo | Formato | Escopo |
| --- | --- | --- |
| Slug de entrega, capacidade, iniciativa, decisão | `[a-z0-9-]`, ex.: `password-reset` | projeto |
| Requisito | `REQ-001` | capacidade, estável entre entregas |
| Critério de aceitação | `AC-001` | capacidade, estável entre entregas |
| Tarefa | `T1` | a entrega |
| Achado | `F1` | a review |
| Decisão | `DEC-001` | projeto, nunca reutilizado |

## `spec.md`

```markdown
---
title: "Password reset"
status: draft          # draft or ready; `atipspec accept <slug> spec`, run by a person, sets ready
kind: feature          # or fix: a defect repair, one regression criterion, no plan acceptance
capability: auth       # living spec that receives the requirements on deliver
impact: [notifications]  # other living specs or contract sections touched
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...        # commit the delivery started from; diff and rules use it
created: 2026-09-12T15:41:45Z   # `status` shows the age from here
---

# Password reset

## Intent

## Requirements

### REQ-001: Behavior title
Description.

Why: the reason, one line.

Acceptance criteria:
- AC-001: When <trigger>, the system <observable outcome with concrete values>.
- AC-002 [manual]: When <trigger>, a person observes <outcome>.

### REQ-002 [remove]: Behavior being removed
- AC-003: If the removed behavior is requested, then the system responds with <outcome>.

## Quality attributes

## Assumptions
- None

## Out of scope

## Open questions
- None
```

Analisado: cabeçalhos `### REQ-nnn[ [remove]]: title` (níveis 2 a 4),
linhas `- AC-nnn[ [test|manual]]: text` sob um requisito (`[manual]` marca
um critério que uma pessoa observa; o plan deve listá-lo sob `Manual:`),
itens de lista sob `## Assumptions` e `## Open questions` (`- None` conta
como vazio). Linhas `Why:` e exemplos são para pessoas e para o revisor.
Veja [escrevendo critérios](spec-quality.md) para a forma que `check` espera.

## `plan.md`

```markdown
---
scope: ["shop/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

## Tasks

### T1: Task title
Covers: REQ-001, REQ-002
Tests: AC-001, AC-002
Verify:
- `python -m pytest -q tests/auth`
- `ruff check .`

### T2: Observed only
Covers: REQ-003
Manual: AC-003
Verify: none
```

Analisado: `### Tn: title`, uma linha `Covers:` com ids de REQ, uma linha
`Verify:` seguida de itens de lista (crases opcionais) ou a palavra
`none`, uma linha opcional `Report:` com o XML JUnit que os comandos
escrevem, e uma linha opcional `Proof:` seguida de itens
`- AC-nnn: test id` que `check` verifica contra a evidência (veja
[build](../flow/build.md)). `scope` no frontmatter lista globs dos
arquivos que as tarefas podem alterar, com a [sintaxe de glob das regras
do contrato](contract-rules.md#globs): `check` avisa sobre arquivos
tocados fora deles, incluindo exclusões (um erro com `strict_scope: true`),
e o pacote de review os lista. Arquivos sob `.atipspec/` nunca contam.
Um `scope` vazio ou ausente não declara nada.

## `review.md`

Escrito apenas pelo revisor.

```markdown
---
tree: <fingerprint from the packet>
reviewer: <client or model>
---

## Criteria
- AC-001: PASS. proof pointer
- AC-002: FAIL. precise gap

## Findings
- F1 [blocker]: text
- F2 [major]: text
- F3 [minor]: text

## Notes
```

Todo critério precisa de exatamente um veredito com um indicador de prova
ou motivo da falha. Achados blocker e major bloqueiam; adiar qualquer um
deles exige uma aprovação de risco confiável com expiração. Achados minor
apenas informam.

## `deferred.md`

```markdown
- F2: reason, and where it will be handled
```

Apenas achados podem ser adiados. Uma entrada `AC-` ou `REQ-` é um erro.

## `brief.md`

O resultado da fase explore: Problem, Today, Options, Recommendation,
Questions for the user. Não analisado; incluído no contexto.

## `evidence/Tn-<timestamp>.json`

Gerado por `atipspec verify`: versão do schema, delivery, task, resultado,
árvore antes/depois, head, timestamps, ambiente e os comandos exatos com
códigos de saída, duração, cauda da saída, caminho completo do log e hash
do log; com um `Report:`, o XML JUnit copiado com seu hash e cada caso de
teste com seu status. O arquivo mais recente por task conta. A atestação
confiável de CI adiciona signatário, repositório, digest da política, URL
da execução e uma assinatura `.json.sig` destacada. Arquivos não assinados
são apenas evidência local.

## `specs/<capability>.md`

A spec viva mantém as seções `### REQ-nnn: Title` e os critérios `AC-nnn`.
`deliver` atualiza por ID estável, preservando a identidade em caso de
renomeação. Todo requisito e critério de aceitação da spec viva precisa
ter um ID desde o início.

## `decisions/DEC-nnn-<slug>.md`

```markdown
---
id: DEC-003
title: "Use httpx for outbound HTTP"
status: accepted        # proposed, accepted, superseded, rejected
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

`context` carrega as decisões aceitas cujo `affects` nomeia a capacidade
da entrega, um item de impact, `contract` ou `*`.

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
| `draft` | spec não aceita para seu conteúdo atual |
| `ready` | spec aceita, ainda sem plan |
| `planned` | plan com tarefas, nada commitado; com `approve_plan`, o plan também precisa de aceitação |
| `in_progress` | algumas tarefas commitadas |
| `implemented` | todas as tarefas commitadas, portão ainda não verde |
| `checked` | checks locais verdes; sem aceitação autenticada |
| `verified` | portão confiável verde com política aprovada, evidência de CI assinada e aprovações humanas |
| `delivered` | mesclado na spec viva e arquivado |

## Aprovações e recibos

`approvals/local-spec.json` e `approvals/local-plan.json` são escritos por
`atipspec accept`: kind `local-acceptance`, phase, hash do subject, quem e
quando. São detecção de desvio para o portão local e são ignorados sob
uma política.

Registros assinados `approvals/*.json` gravam phase, identidade, papel,
timestamp de aprovação, hash do subject, repositório, digest da política e
expiração opcional. Cada um tem uma assinatura SSH `.json.sig`. Registros
de provedor também carregam a identidade do PR/MR e a URL de origem, e são
revalidados contra o provedor no momento da aceitação. `reports/acceptance.json`
é o recibo arquivado e o índice de artefatos. Veja
[aceitação empresarial](../enterprise.md).
