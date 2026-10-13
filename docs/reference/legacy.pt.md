# Entregas antigas

Uma entrega antiga mantém seus requisitos dentro do seu próprio `spec.md`,
sem `schema: 2`. `atipspec new` cria entregas guiadas desde a 0.2.0, e fixes
guiados desde a 0.3.0, então as entregas antigas de um projeto são:

- entregas criadas com o AtipSpec 0.1.x;
- fixes criados com `new --kind fix` antes da 0.3.0.

O AtipSpec as lê como estão, com o mesmo portão para a evidência, a revisão e
o resultado, até que sejam arquivadas. Nada as converte por conta própria.
Esta página descreve o que muda; a [entrega guiada](../flow/guided.md) é o
fluxo para tudo o que é novo.

## `spec.md` com requisitos embutidos

```markdown
---
title: "Password reset"
status: draft          # draft or ready; `atipspec accept` sets ready when it records the human's approval
kind: feature          # or fix: a fix created before 0.3.0, one regression criterion, no plan acceptance
capability: auth       # living spec that receives the requirements on deliver
impact: [notifications]  # other living specs or contract sections touched
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...        # commit the delivery started from; diff and rules use it
created: 2026-09-12T15:41:45Z   # the lead time counts from here
---

# Password reset

## Intent

Let a user who forgot the password recover access without support.

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

Acceptance criteria:
- AC-001: When a registered email requests a reset, the system sends a link to that email within 60 seconds.
- AC-002 [manual]: When the reset email is opened on a 375 px wide screen, a person sees the "Reset password" button without scrolling sideways.

### REQ-002 [remove]: Security questions
- AC-003: If a user opens "/account/questions", then the system responds with status 404.

## Quality attributes

### REQ-003: Reset requests under load

Acceptance criteria:
- AC-004: When 100 users request a reset within one minute, the p95 response time measured at the API gateway is below 300 ms.

## Assumptions
- The link is single-use.

## Out of scope
- Password policy changes.

## Open questions
- None
```

Analisado: cabeçalhos `### REQ-nnn[ [remove]]: title` (níveis 2 a 4), linhas
`- AC-nnn[ [test|manual]]: text` sob um requisito, que podem continuar em
linhas recuadas, cabeçalhos de cenário como em uma spec viva guiada, e os
itens de lista sob `## Assumptions` e `## Open questions` (`- None` conta como
vazio). `deliver` mescla os requisitos em `specs/<capability>.md` por ID e
remove os marcados `[remove]`. Veja [escrever critérios](spec-quality.md)
para as verificações; são as mesmas.

## Aprovações

| | Entrega antiga | Entrega guiada |
| --- | --- | --- |
| Para iniciar `spec` ou `fix` | a aceitação do contrato, registrada para seu conteúdo atual | nada; `check` avisa enquanto o contrato não estiver aceito |
| Antes de `plan` | `accept <slug> spec --code <code>` | os cenários completos, nenhuma pergunta aberta |
| Antes de `build` | com `approve_plan: true` (o padrão), `accept <slug> plan --code <code>`; um fix criado antes da 0.3.0 não tem aceitação do plano | `accept <slug> proposal --code <code>` |
| O resultado | `accept <slug> result --code <code>` | o mesmo |

`atipspec proposal <slug>` em uma entrega antiga apresenta a aprovação ainda
pendente, com seu código e o comando `accept` que a registra, ou diz que não
há nenhuma: a spec até que seja aceita, depois o plano quando `approve_plan`
o pede. Uma feature cuja spec e cujo plano estão ambos prontos é apresentada
como uma só proposta, e `accept <slug> proposal` com esse código registra a
spec e o plano juntos; um fix apresenta apenas sua spec. Um código registra
apenas a fase com que a visão o mostrou, então execute o comando que a visão
imprime. A aprovação da spec inclui no hash `spec.md` e `contract.md`; a
aprovação do plano acrescenta `plan.md` inteiro, de modo que qualquer edição
do plano, incluída uma nova tarefa, a pede de novo. `review_rounds` recomeça
a cada nova aprovação da spec; nenhuma aprovação cobre `config.yaml`.
`accept <slug> spec` e `accept <slug> plan` são recusados em entregas
guiadas.

## Conclusão de tarefas

Uma tarefa está completa quando `atipspec task-done <slug> Tn --note "..."` a
registra, ou quando um commit no branch desde a base carrega o marcador
`[<slug>:Tn]` (vários ids podem compartilhar um,
`[password-reset:T1,T2]`). As entregas guiadas ignoram os marcadores de
commit. Um plano antigo não tem `## Final verification` a menos que alguém a
adicione: `verify` executa os comandos Verify de cada tarefa, e todo
`require-command` do contrato deve aparecer em um deles.

## IDs

Os requisitos e critérios antigos são numerados por capacidade, `REQ-001`,
`AC-001`, acima do maior número na spec viva, nas entregas abertas e no
arquivamento. `atipspec ids <capability> --legacy` imprime o próximo par.
Duas pessoas numerando ao mesmo tempo podem colidir; o
`atipspec ids <capability>` do fluxo guiado sorteia um prefixo que nenhum ID
visível usa. Os IDs numerados continuam válidos em todo fluxo e nunca são
renumerados.

## Vários repositórios

Com `system:` em `config.yaml`, uma entrega antiga lê o contrato e o
glossário do repositório de sistema a partir do checkout como está; uma
guiada os lê a partir do commit que `new` fixou (veja [vários
repositórios](../teams.md#varios-repositorios)).

## Converter uma feature antiga

`atipspec migrate <slug>` mostra, como um diff, como uma feature antiga se
torna uma entrega guiada, e não escreve nada: seus requisitos passam para
`specs/<capability>.md`, `spec.md` lista seus IDs sob `requirements` e recebe
`schema: 2`, `status: draft`, `risk: normal` e um novo `baseline.json`.
`atipspec migrate <slug> --apply` o escreve depois de fazer backup dos
originais e dos registros de aprovação em `.atipspec/migrations/<digest>/`.
Não aprova nada: a entrega volta a draft e sua proposta é apresentada para
aprovação. O plano existente é mantido; mova as verificações compartilhadas
para uma `## Final verification` quando o revisar. Um fix antigo mantém seu
fluxo até ser entregue, e `migrate` o recusa.
