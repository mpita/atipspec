# Times e escala

O AtipSpec é construído para projetos que rodam por meses com várias pessoas
e seus agentes. Duas ideias sustentam tudo: a unidade de atribuição é a
entrega, e o custo de uma requisição é limitado pela entrega, não pelo
projeto.

## Entregas, não tarefas

| Jira | AtipSpec | Unidade de |
| --- | --- | --- |
| Epic | iniciativa | meses de trabalho, várias pessoas |
| Story | entrega | atribuição a uma pessoa, um branch |
| Sub-task | tarefa | uma execução de agente com contexto limpo |

As tarefas dentro de uma entrega compartilham uma spec e um branch e rodam
em sequência. Uma entrega é dimensionada para fechar dentro de um dia de
trabalho: `check` avisa acima de `max_requirements` e `max_tasks`, e
`status` mostra há quanto tempo cada entrega está aberta e avisa acima de
`max_age_hours`. Trabalho maior vira várias entregas sob uma iniciativa.
Trabalho que duas pessoas deveriam fazer em paralelo vira duas entregas,
divididas por posse, com a interface entre elas fixada na iniciativa:

```bash
atipspec initiative orders --title "Orders"
atipspec new orders-api    --title "Orders API"    --capability orders    --owner ana  --initiative orders --worktree
atipspec new orders-screen --title "Orders screen" --capability orders-ui --owner luis --initiative orders --worktree --impact orders
```

Criar uma entrega com `--initiative` a lista no roadmap. O roadmap tem uma
seção *Interfaces* para o que os dois lados concordam (o formato de uma API,
um evento, um schema) e o arquivo que é sua fonte da verdade.

```bash
atipspec status
```

```text
- orders-screen [in_progress]  tasks 1/3 @luis, open 1d 3h: Orders screen
    next: T2 is not committed: build it, run `atipspec verify orders-screen --task T2` and commit with [orders-screen:T2]
initiatives:
- orders 1/2: orders-api delivered; orders-screen in_progress
```

Tickets: `--ticket SHOP-12` registra o id externo na spec; os marcadores de
commit `[orders-api:T1]` são seus para combinar com qualquer convenção.

## Uma entrega, um branch, um worktree

```bash
atipspec new orders-api --title "Orders API" --worktree
```

cria o branch `delivery/orders-api` em uma pasta irmã
`../<repo>-orders-api`. Cada pessoa, e cada agente, trabalha na sua própria
árvore; nada é compartilhado até o pull request. `--branch` faz o mesmo na
pasta atual.

Fazer rebase sobre a main muda a árvore, o que torna a evidência e a revisão
obsoletas. O portão exige que você verifique e faça a revisão de novo depois
de integrar, então não existe "funcionou no meu branch".

## Sobreposições

`status` e `audit` avisam quando duas entregas abertas declaram a mesma spec
viva em seu `impact`:

```text
  warning: orders-api and orders-screen both touch orders
```

Esse é o conflito que vale a pena pegar antes que o código exista. Conflitos
do Git continuam sendo problema do Git.

## Vários repositórios

Cada repositório tem seu próprio `.atipspec/`, porque o git é a máquina de
estados e a evidência é por árvore. Para as partes compartilhadas, um
pequeno repositório **system** contém o contrato do sistema, o glossário
compartilhado, os contratos de API e schemas, e as iniciativas que
atravessam repositórios. Aponte cada projeto para um checkout dele:

```yaml
# .atipspec/config.yaml
system: ../shop-system
```

`atipspec context` então inclui o `contract.md` e o `glossary.md` do system
no material de cada entrega.

## Mantendo o contexto pequeno

Todo comando de fase imprime a saída de `atipspec context <slug>`, que
carrega o contrato, a visão geral, o glossário, as specs vivas na lista de
impacto, as decisões aceitas que as afetam, e os próprios arquivos da
entrega. Ele imprime o tamanho:

```text
Context for orders-api: 184 lines (budget 800)
     43  contract (.atipspec/contract.md)
     22  overview (.atipspec/overview.md)
     10  glossary (.atipspec/glossary.md)
     37  decision DEC-001
     48  spec (.atipspec/deliveries/orders-api/spec.md)
     24  plan (.atipspec/deliveries/orders-api/plan.md)
```

Duas coisas mantêm isso limitado ao longo do tempo: a fase
[curate](flow/curate.md) com seus limites, e a lista de impacto, que é o
motivo pelo qual uma spec declara o que ela toca em vez do modelo adivinhar.

## Políticas por projeto

Cerimônia é um dial em `config.yaml`, não uma propriedade da ferramenta:

```yaml
approve_plan: true      # build refuses until a person runs `atipspec accept <slug> plan`
review_rounds: 2        # rounds before the model stops and reports
context_budget: 800     # lines; context warns above it
max_requirements: 5     # check warns above it: split the delivery
max_tasks: 8            # same, for the plan
max_age_hours: 48       # status warns when a delivery has been open longer
```

Um projeto pequeno define `approve_plan: false` e entrega tudo de uma vez.
Um projeto regulado mantém os dois pontos de parada, a aprovação do plano e
um orçamento baixo.
