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

Ao redor delas ficam o registro de **decisões**, **iniciativas** que agrupam
entregas ao longo de meses, e dois documentos curados, `overview.md` e
`glossary.md`, que mantêm o projeto explicável em uma página.

## Quem decide o quê

| Pergunta | Respondida por |
| --- | --- |
| O que construímos? | Você, aprovando a proposta (cenários, abordagem e testes) na conversa |
| Sob quais regras? | O contrato que você aprovou, registrado com `atipspec accept contract --code <code>` e aplicado por `check` e `audit` |
| Uma tarefa está concluída? | O assistente a declara com `atipspec task-done`, vinculada ao acordo aprovado; uma declaração de progresso, não uma prova |
| Ela passa nas verificações? | `atipspec verify`, que executa a verificação final e registra os códigos de saída e o hash da árvore |
| Ela atende à spec? | Um revisor em uma sessão isolada, declarada em `review.md`, um veredito por critério com uma referência que o portão resolve |
| O resultado está aceito? | Você, aceitando o resultado revisado que `atipspec report` mostra; ou, sob uma política de confiança, `check --policy` com evidência de CI confiável e aprovações de produto/engenharia/QA (`verified`) |
| Quando é feito o merge? | A política do seu repositório; `atipspec merge-check` confirma o branch antes |

O assistente apresenta o acordo com seu código de aprovação e oferece
**Aprovar e continuar**, **Pedir alterações** ou **Cancelar**, pelo seletor do
cliente ou por uma resposta escrita. Após sua aprovação explícita, ele executa
`atipspec accept ... --code <code>` e continua. O Claude Code, configurado pelo
`init` e aberto na raiz do projeto, pergunta a você antes de esse comando
rodar; essa pergunta confirma a mesma aprovação. Você não precisa executar comandos nem editar estados. O
verificador registra evidências e o revisor registra vereditos; nenhum deles
substitui sua decisão. Acordos alterados exigem nova aprovação. Políticas de
confiança externas mantêm seu procedimento autenticado.

## Aceitação que você pode verificar

Há três decisões humanas, cada uma apresentada por uma visão que imprime um
código de aprovação (`XXXX-XXXX`, os primeiros 40 bits do sha256 do conteúdo
em base32 de Crockford):

| Decisão | Apresentada com | Registrada com |
| --- | --- | --- |
| A proposta: cenários, abordagem e testes | `atipspec proposal <slug>` | `atipspec accept <slug> proposal --code <code>` |
| O resultado revisado | `atipspec report <slug>` | `atipspec accept <slug> result --code <code>` |
| O contrato e suas decisões, uma vez por projeto | `atipspec proposal contract` | `atipspec accept contract --code <code>` |

`accept` recusa quando o código não nomeia o conteúdo atual, então o registro
vincula a versão que você viu. Ele escreve um hash desse conteúdo, digests por
arquivo, o código e o canal em `approvals/local-<phase>.json` (o do contrato em
`.atipspec/approvals/contract.json`). `check` compara o hash com os arquivos em
disco a cada execução; um único byte editado depois da sua aceitação faz a
entrega voltar para `draft` com um `todo` que nomeia o arquivo que mudou.
Entregas guiadas, fixes incluídos, precisam do registro da proposta; um par de
spec e plan não o substitui. Entregas antigas aprovam sua spec, e seu plan
quando `approve_plan` está ativado, com `accept <slug> spec|plan --code <code>`;
um fix criado antes da 0.3.0 aprova apenas sua spec.

O canal diz como o comando chegou até você:

| Canal | Significado |
| --- | --- |
| `terminal` | O código foi digitado no prompt da CLI em um terminal sem marcadores de agente |
| `client-permission` | O próprio Claude Code executou `atipspec accept`, e as regras deste projeto, intactas, fazem com que ele pergunte a você antes em uma sessão aberta na raiz do projeto |
| `assistant` | Nada perguntou a você: um cliente sem regras de permissão, regras alteradas, o marcador de outro agente junto ao do Claude Code, o Claude Code executado pelo Agent SDK ou por `claude -p`, ou uma linha de comando que a regra não reconhece, como `python -m atipspec.cli` |

A CLI vê apenas o próprio processo, então cada canal é o que esse processo
declara. Ela não consegue ver se a sessão carregou as regras: uma sessão
aberta em outra pasta que entra no projeto com `cd` não pergunta e registra
`client-permission`. Um script, ou um agente que não define nenhum dos
marcadores listados em [ambiente](../reference/configuration.md#ambiente),
que o Claude Code executa e que chama `atipspec accept` dentro dele também
registra `client-permission`, embora o Claude Code só tenha perguntado a você
sobre o script ou o agente. E um agente pode remover seus marcadores e
responder ao prompt da CLI a partir de um terminal que ele cria, o que
registra `terminal`.

Isso é detecção de desvio, não autenticação: o registro prova o que foi
aceito e como o comando rodou, não quem você é. Aprovações assinadas sob uma
política externa são a forma autenticada, e quando uma política é definida o
portão ignora os registros locais. Veja [aceitação empresarial](../enterprise.md).

## Fases que a CLI abre

Uma fase começa com seu comando: `atipspec spec <slug>`, `atipspec plan
<slug>`, e assim por diante. O comando verifica o que a fase exige e recusa
com uma linha quando algo está faltando: os cenários incompletos, a proposta
não aprovada, uma tarefa não registrada. Caso contrário, ele imprime o
workflow, as regras e o contexto, para que o modelo trabalhe a partir do que
a CLI abriu e não da sua leitura do pedido. `atipspec ship <slug>` indica a
próxima fase em que uma entrega pode entrar. Veja
[o fluxo](../flow/index.md#o-que-cada-fase-exige).

## O portão

`atipspec check <slug>` verifica a consistência local. A aceitação confiável
exige adicionalmente `--policy`. Ele lê os arquivos e o git, e reporta três
tipos de coisas:

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
significa erros, 2 significa incompleto. O portão falha fechado: sem git ele
fica vermelho, porque o commit base, as regras do contrato e a atualidade da
evidência vêm do git. Sem uma política, verde é apenas `checked`, e `deliver`
também exige sua aceitação registrada do resultado; com a
[política externa](../enterprise.md), ele exige um portão confiável verde.
Antes do merge, `atipspec merge-check --base <target>` verifica o branch
inteira: cada entrega que ela toca está aceita, e o código ainda é o código
que cada recibo aceitou.

## Evidência vinculada à árvore

`atipspec verify` executa os comandos que uma tarefa declara e escreve um
arquivo JSON com os comandos, códigos de saída, trechos finais da saída,
duração e a **impressão digital da árvore de trabalho**: um hash de conteúdo
computado através de um índice git temporário, idêntico antes e depois de
fazer commit do mesmo conteúdo. A revisão registra a mesma impressão
digital. Quando a árvore muda, ambas ficam obsoletas e o portão as solicita
novamente; renomear uma tarefa no plano é a única mudança à qual elas
sobrevivem. Trazer a main também muda a árvore, e esse é o objetivo: não
existe "funcionou na minha branch". Um relatório JUnit só conta quando foi
escrito por essa execução: `verify` o apaga antes, e `check` nunca executa
os testes por conta própria.

## Status derivado

O status nunca é armazenado: `status` e `check` calculam onde uma entrega
está a partir dos seus arquivos e do git a cada execução. O que eles leem
são registros no repositório: as aprovações, `progress.json`, a evidência,
`review.md` e o recibo.

`draft` → `planned` → `in_progress` → `implemented` → `checked` → `accepted` → `delivered`

`checked` é o portão local verde; `accepted` acrescenta sua aceitação
registrada desse resultado; sob uma política de confiança, `verified` é o
portão confiável verde. Uma entrega antiga também passa por `ready`, sua spec
aceita antes de existir um plano. `atipspec accept` move uma spec para
`ready` e o contrato e suas decisões para `accepted`. O portão trata um
`ready` escrito manualmente sem um registro de aceitação correspondente como
um draft, e um contrato, ou uma decisão que o afeta, marcados como
`accepted` manualmente sem um registro correspondente como não aceitos. Uma
decisão sobre uma capacidade é o único status que o assistente escreve: ele
a marca `accepted` depois que você a aprova na conversa, sem código nem
registro, e a próxima `atipspec proposal` a lista para que você veja o que a
implementação e a revisão vão seguir.

## Contexto que não cresce com o projeto

`atipspec context <slug>` monta exatamente o que uma fase precisa: o
contrato, o overview, o glossary, as specs vivas que a lista `impact` da
entrega nomeia, as decisões aceitas que as afetam, e os próprios arquivos da
entrega. Nunca o archive. Ele imprime o tamanho contra `context_budget`, e
`audit` avisa quando um documento ultrapassa seu limite para que a fase
**curate** possa reduzi-lo.

Próximo: [o fluxo](../flow/index.md).
