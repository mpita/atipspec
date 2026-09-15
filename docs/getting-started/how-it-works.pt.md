# Como funciona

## Três verdades com tempos de vida diferentes

| Verdade | Onde | Vive | Muda através de |
| --- | --- | --- | --- |
| O **contrato** | `.atipspec/contract.md` | o projeto inteiro | uma decisão aceita |
| As **specs vivas** | `.atipspec/specs/<capability>.md` | o produto | `atipspec deliver` |
| Uma **entrega** | `.atipspec/deliveries/<slug>/` | dias ou semanas | as fases |

O contrato diz como o sistema é construído: stack, estrutura, política de
dependências, convenções, portões de qualidade, e um bloco de regras que a
CLI avalia. As specs vivas dizem o que o produto faz, um arquivo por
capacidade. Uma entrega é a unidade de mudança: sua própria spec, plan,
evidência, review e achados adiados, criada, verificada e arquivada como um
todo.

Ao redor delas ficam o registro de decisões, iniciativas que agrupam
entregas ao longo de meses, e dois documentos curados, `overview.md` e
`glossary.md`, que mantêm o projeto explicável em uma página.

## Quem decide o quê

| Pergunta | Respondida por |
| --- | --- |
| O que construímos? | Você, executando `atipspec accept <slug> spec` |
| Sob quais regras? | O contrato que você aceitou com `atipspec accept contract`, aplicado por `check` e `audit` |
| Uma tarefa está concluída? | git: um commit carregando `[slug:Tn]` |
| Ela passa nas verificações? | `atipspec verify`, que registra os códigos de saída e o hash da árvore |
| Ela atende à spec? | Um revisor em um contexto limpo, um veredito por critério |
| Está verificada? | `check --policy` com evidência de CI confiável e aprovações de produto/engenharia/QA |
| Ela faz ship? | Você, fazendo merge |

O modelo propõe a cada passo. Ele nunca escreve evidência, nunca escreve
veredictos, nunca marca uma tarefa como concluída, nunca define `ready`,
`accepted` ou `verified`, e nunca executa `atipspec accept`.

## Aceitação que você pode verificar

`atipspec accept <slug> spec` é como você aprova uma spec: ele define
`status: ready` e registra um hash da spec e do contrato em
`approvals/local-spec.json`. `check` compara esse hash com os arquivos em
disco a cada execução; um único byte editado depois da sua aceitação faz a
entrega voltar para `draft` com um `todo` que te nomeia. O mesmo vale para
`atipspec accept <slug> plan` quando `approve_plan` está ativado, e
`atipspec accept contract` define o `status: accepted` do contrato.

Isso é detecção de desvio, não autenticação: o registro prova o que foi
aceito, não quem executou o comando. Aprovações assinadas sob uma política
externa são a forma autenticada, e quando uma política é definida o portão
ignora os registros locais. Veja [aceitação empresarial](../enterprise.md).

## Fases que a CLI abre

Uma fase começa com seu comando: `atipspec spec <slug>`, `atipspec plan
<slug>`, e assim por diante. O comando verifica o que a fase exige e recusa
com uma linha quando algo está faltando: o contrato não aceito, a spec não
ready, uma tarefa sem commit. Caso contrário, ele imprime o workflow, as
regras e o contexto, para que o modelo trabalhe a partir do que a CLI abriu
e não da sua leitura do pedido. `atipspec ship <slug>` indica a próxima fase
que uma entrega pode iniciar. Veja [o fluxo](../flow/index.md#o-que-cada-fase-exige).

## O portão

`atipspec check <slug>` verifica a consistência local. A aceitação confiável exige adicionalmente `--policy`. Ele lê os arquivos
e o git, e reporta três tipos de coisas:

- **error**: algo está errado ou falhou. O portão está vermelho.
- **todo**: algo ainda não aconteceu. O portão ainda não está verde.
- **warning** e **info**: vale a pena prestar atenção, não bloqueiam.

```text
password-reset  [implemented]  tasks 2/2
  error   AC-003 FAIL: the link never expires
  error   F1 [blocker] contract: shop/domain/order.py:3 contains forbidden pattern 'from shop\.infrastructure'
  todo    review.md is stale (the working tree changed since the review); run `atipspec review password-reset` and review again
  info    F2 [minor] Missing docstring
Next: Fix: AC-003 FAIL: the link never expires
```

O código de saída 0 significa que as verificações selecionadas passaram, 1
significa erros, 2 significa incompleto. Sem uma política, verde é apenas
`checked`. `deliver` exige um portão confiável verde e a
[política externa](../enterprise.md).

## Evidência vinculada à árvore

`atipspec verify` executa os comandos que uma tarefa declara e escreve um
arquivo JSON com os comandos, códigos de saída, trechos finais da saída,
duração e a **impressão digital da árvore de trabalho**: um hash de conteúdo
computado através de um índice git temporário, idêntico antes e depois de
fazer commit do mesmo conteúdo. A revisão registra a mesma impressão
digital. Quando a árvore muda, ambos ficam obsoletos e o portão os solicita
novamente. Rebasear sobre a main também muda a árvore, e esse é o objetivo:
não existe "funcionou na minha branch".

## Status derivado

Nada é armazenado. `status` e `check` calculam onde uma entrega está:

`draft` → `ready` → `planned` → `in_progress` → `implemented` → `checked` (local) / `verified` (confiável) → `delivered`

Nenhum status é escrito manualmente: `atipspec accept` move uma spec para
`ready` e um contrato para `accepted`, e o portão trata um `ready` escrito
manualmente sem um registro de aceitação correspondente como um draft.

## Contexto que não cresce com o projeto

`atipspec context <slug>` monta exatamente o que uma fase precisa: o
contrato, o overview, o glossary, as specs vivas que a lista `impact` da
entrega nomeia, as decisões aceitas que as afetam, e os próprios arquivos da
entrega. Nunca o archive. Ele imprime o tamanho contra `context_budget`, e
`audit` avisa quando um documento ultrapassa seu limite para que a fase
**curate** possa reduzi-lo.

Próximo: [o fluxo](../flow/index.md).
