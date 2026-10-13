# review

**Um revisor que não escreveu o código escreve `review.md`.** Uma passada
adversarial, em uma sessão isolada, vinculada à árvore.

| | |
| --- | --- |
| Papel, lado do autor | O autor entregando. Não discute dentro do contexto do revisor, nunca edita `review.md`. Corrige, verifica, pergunta de novo. |
| Papel, lado do revisor | Adversarial. Julga contra a spec e o contrato, um veredito por critério, com uma referência à prova. |
| Quem decide | `atipspec check`. |
| Produz | `review.md` |

## Como executar

```text
/atipspec-review password-reset
```

## O que acontece

1. O modelo executa `atipspec review password-reset`. A CLI recusa enquanto
   uma tarefa não está concluída, a evidência está desatualizada ou o
   contrato é violado, e não escreve pacote. Caso contrário, conta o
   review (veja [rodadas de revisão](#rodadas-de-revisao)) e escreve um
   pacote em `.atipspec/tmp/password-reset-review-packet.md` com: a rubrica,
   o risco da entrega e o que ele pede, o contrato de arquitetura, as specs
   vivas que a entrega declara em sua lista de impacto, as decisões aceitas
   que as afetam, a spec, o plano, itens adiados, um resumo de evidência, os
   arquivos alterados fora do `scope` do plano, e o diff contra o commit
   base da entrega mais os arquivos não rastreados. Um diff acima de 200 KB
   é substituído por seu `--stat` e um trecho truncado, com uma nota dizendo
   ao revisor para inspecionar o repositório. Depois o comando imprime
   `review N of M` e o workflow.
2. O modelo entrega o pacote a um revisor **em uma sessão isolada**: uma
   sessão que não viu a conversa e que recebe apenas o caminho do pacote. No
   Claude Code isso é um subagente; veja [clientes](../clients.md) para os
   outros. Quando o cliente não consegue oferecer uma, o revisor ainda assim
   escreve o review e declara `session: shared`. Com `risk: high` ou
   `require_isolated_review`, o modelo pede que você abra uma nova sessão
   para o revisor.
3. O revisor lê o pacote, inspeciona o repositório, executa comandos se a
   leitura não for suficiente, e escreve:

```markdown
---
tree: cd03ae507b3605b12a497fcbcf590894a0073076
reviewer: claude-code subagent
session: isolated
---

# Review: Password reset

## Criteria

- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. tests.auth.test_reset.test_unknown_email_same_response
- AC-003: FAIL. consume() checks the age but the boundary of exactly 30 minutes is accepted.

## Findings

- F1 [blocker]: shop/domain/reset.py imports shop.infrastructure.mail, forbidden by the contract.
- F2 [minor]: request() lacks a docstring.

## Notes

The spec does not say whether a used link may be reused; assumed no.
```

4. O modelo executa `atipspec check password-reset`:
    - Um `FAIL` ou um `blocker`: corrige o código e verifica de novo.
      Qualquer mudança na árvore torna o review desatualizado, então ele
      executa `review` e o revisor de novo.
    - Um achado minor que você decide não corrigir agora vai para
      `deferred.md` com um motivo: `- F2: cosmetic, handled in the docs
      cleanup delivery`. Um achado blocker ou major é corrigido: só uma
      exceção de risco sob uma política de confiança o adia. Critérios nunca
      podem ser adiados.
5. Quando `atipspec review` recusa porque as rodadas de revisão se esgotaram,
   o modelo para e apresenta `atipspec check password-reset` com os achados
   que restam. Você decide.

## O que o portão verifica em `review.md`

- `tree:` é o do pacote: o candidato que o último `atipspec review` contou.
  Um review de outro candidato está desatualizado, a menos que só os títulos
  das tarefas tenham mudado, e um escrito sem executar `review` fica à espera
  dele (veja [rodadas de revisão](#rodadas-de-revisao)).
- `reviewer:` nomeia o cliente ou o modelo que escreveu o review; sem ele,
  `check` reporta um erro.
- `session:` é `isolated` (o revisor nunca viu a conversa do autor) ou
  `shared`. Um review que o omite conta como `shared`. Um review
  compartilhado é um aviso, e um erro quando a spec diz `risk: high` ou
  `require_isolated_review` está ativado em `config.yaml` ou na política de
  confiança. Qualquer outro valor é um erro. No fluxo guiado, o revisor
  declara a sessão; a declaração é registrada, mostrada no dossiê e levada
  em conta pelo portão, mas nada a mede. O
  [executor de processos](../reference/execution-adapter.md) a vincula ao
  `isolated_review` declarado pelo adaptador.
- Todo critério tem um veredito, exceto, com `risk: low`, um cujo teste
  nomeado em `Proof:` passou na evidência atual: `check` o registra com um
  info. Um `FAIL` bloqueia em qualquer nível. Veja [risco](spec.md#risco).
- Todo `PASS` precisa de uma referência que o portão resolve, uma destas:
    - um teste que passou no relatório JUnit da evidência atual, nomeado
      como o relatório o nomeia (`tests.auth.test_reset.test_link`), ou como
      em uma entrada de Proof; um nome com espaços vai entre crases;
    - `path:line` ou `path:line-line`, uma linha que existe em um arquivo do
      candidato: fora de `.atipspec/` e `.git` e não ignorado pelo git. Os
      logs de evidência da entrega contam, mesmo onde o git ignora `*.log`,
      como `evidence/logs/FINAL-<run>-1.log:12` a partir da pasta da
      entrega;
    - `path::test`, um arquivo assim que contém esse nome como palavra (um
      sufixo `[param]` é ignorado); o dossiê o mostra como um nome
      encontrado no arquivo, já que o portão não o executa.

    Para um critério marcado `[manual]`, uma descrição do que foi feito e
    observado, de três palavras ou mais, também passa. Um `FAIL` precisa do
    seu motivo. `PASS. ok` é um erro. Enquanto o review está desatualizado,
    suas referências não são julgadas, e enquanto a evidência não está
    atualizada uma referência não resolvida é um todo: o teste que ela nomeia
    pode estar na próxima execução. Uma referência que se resolve mostra que
    nomeia algo real, não que prova o critério: o dossiê mostra a que cada
    uma se resolveu para que você julgue, e as entradas de [Proof](build.md),
    exigidas com `require_proof`, vinculam um critério ao seu teste: um `PASS`
    de um critério assim que não nomeia esse teste é um aviso.

## Rodadas de revisão

`review_rounds` em `config.yaml` (padrão 3) é quantos reviews uma entrega
tem por acordo aprovado, contando o primeiro: um primeiro review e dois de
candidatos corrigidos. `atipspec review` conta um review cada vez que escreve um pacote
para um candidato diferente daquele do último pacote, diga o que disser
`review.md`: um review que passou também conta, porque o revisor escreve
esse arquivo e a CLI não consegue distinguir seus vereditos de outros
editados depois. Escrever o pacote de novo para o mesmo candidato não conta
nada, assim como um pacote que não pode ser montado. Depois que os reviews
se esgotam e o candidato muda de novo, `review` recusa, sem contar nada, e
nomeia a decisão: mudar a proposta, aumentar `review_rounds` ou parar. Até
lá, `check` reporta os reviews esgotados como um erro, diga o que disser
`review.md`, e o dossiê mostra a contagem. `check` considera apenas o review
do último pacote que `atipspec review` contou: um `review.md` escrito para um
candidato sem executar o comando é um todo que o pede, então pulá-lo não
economiza nenhum review. A contagem fica em `review-rounds.json`, na pasta
da entrega, que a CLI escreve, e recomeça quando o acordo aprovado muda: a
proposta de uma entrega guiada, a spec de uma antiga. As regras do Claude
Code mantêm as ferramentas de edição do cliente longe desse arquivo, mas não
um comando de shell. `atipspec accept <slug> proposal` cria o arquivo, então
em uma entrega guiada criada desde a 0.3.0 um arquivo que falta foi apagado:
`review` recusa e `check` falha até você decidir, restaurando-o a partir do
git ou aprovando a proposta de novo, o que começa uma nova contagem. Quando
o arquivo falta em uma entrega aprovada sob uma política de confiança,
`atipspec review` volta a contar a partir do `review.md` da pasta, como
primeiro review; em uma criada antes da 0.3.0 conta a partir do próximo
pacote, porque um `review.md` escrito antes nomeia uma árvore da impressão
digital anterior.
Aumentar `review_rounds` em uma entrega guiada muda `config.yaml`, que a
aprovação da proposta inclui no hash, então a proposta é apresentada de
novo. Em uma entrega antiga (um fix criado antes da 0.3.0 inclusive), cuja
aprovação é a da spec, nenhuma aprovação cobre `config.yaml`: um limite
aumentado vale de imediato, então o modelo só o aumenta quando você pede, e
o dossiê mostra `Revisão N de M`. `atipspec status password-reset` mostra
`review N of M`. `atipspec run` conta da mesma forma os reviews que pede e
para em `needs_decision` quando eles se esgotam. Ele também mantém sua
própria contagem: `--max-rounds`, que por padrão é `review_rounds` menos um,
porque cada correção é revisada de novo, e não pode excedê-lo, limita toda
correção automática, seja pedida por um review ou por um check.

## Por que uma sessão isolada

O contexto que escreveu o código vai confirmá-lo. Os vereditos do revisor
são os únicos que o portão aceita, e o portão os rejeita assim que o código
muda, a menos que só tenham mudado títulos de tarefas em um plano. Uma
violação do contrato é sempre um blocker.

Achados blocker e major exigem resolução ou uma exceção de risco confiável.
O verde local é `checked`: o assistente então apresenta
`atipspec report <slug>` para sua aceitação do resultado, e `deliver` a
exige. Sob a [aceitação confiável](../enterprise.md), o verde é `verified`,
e a aprovação assinada de QA vincula o review, as exceções e a evidência.
