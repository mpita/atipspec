# review

**Um revisor que não escreveu o código escreve `review.md`.** Uma passada
adversarial, em um contexto limpo, vinculada à árvore.

| | |
| --- | --- |
| Papel, lado do autor | O autor entregando. Não discute dentro do contexto do revisor, nunca edita `review.md`. Corrige, verifica, commita, pergunta de novo. |
| Papel, lado do revisor | Adversarial. Julga contra a spec e o contrato, um veredito por critério, com uma referência à prova. |
| Quem decide | `atipspec check`. |
| Produz | `review.md` |

## Como executar

```text
/atipspec-review password-reset
```

## O que acontece

1. O modelo executa `atipspec review password-reset`. A CLI recusa enquanto
   uma tarefa não tem commit, a evidência está desatualizada ou o contrato
   é violado, e não escreve pacote. Caso contrário, escreve um pacote em
   `.atipspec/tmp/password-reset-review-packet.md` com: a rubrica, o
   contrato de arquitetura, as specs vivas que a entrega declara em sua
   lista de impacto, as decisões aceitas que as afetam, a spec, o plano,
   itens adiados, um resumo de evidência, os arquivos alterados fora do
   `scope` do plano, e o diff contra o commit base da entrega mais os
   arquivos não rastreados. Um diff acima de 200 KB é substituído por seu
   `--stat` e um trecho truncado, com uma nota dizendo ao revisor para
   inspecionar o repositório. Depois o comando imprime o workflow.
2. O modelo aciona o revisor **em um contexto que não viu a conversa**,
   passando a ele apenas o caminho do pacote. No Claude Code isso é um
   subagent; veja [clientes](../clients.md) para os outros.
3. O revisor lê o pacote, inspeciona o repositório, executa comandos se a
   leitura não for suficiente, e escreve:

```markdown
---
tree: cd03ae507b3605b12a497fcbcf590894a0073076
reviewer: claude-code subagent
---

# Review: Password reset

## Criteria

- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. tests/auth/test_reset.py::test_unknown_email_same_response
- AC-003: FAIL. consume() checks the age but the boundary of exactly 30 minutes is accepted.

## Findings

- F1 [blocker]: shop/domain/reset.py imports shop.infrastructure.mail, forbidden by the contract.
- F2 [minor]: request() lacks a docstring.

## Notes

The spec does not say whether a used link may be reused; assumed no.
```

4. O modelo executa `atipspec check password-reset`:
    - Um `FAIL` ou um `blocker`: corrige o código, verifica, commita.
      Qualquer mudança na árvore torna o review desatualizado, então ele
      executa `review` e o revisor de novo.
    - Um achado que você decide não corrigir agora vai para `deferred.md`
      com um motivo: `- F2: cosmetic, handled in the docs cleanup delivery`.
      Critérios nunca podem ser adiados.
5. Depois de `review_rounds` rodadas (padrão 2) sem um check verde, o modelo
   para e relata o que falta. Você decide.

## Por que um contexto separado

O contexto que escreveu o código vai confirmá-lo. Os veredictos do revisor
são os únicos que o portão aceita, e o portão os rejeita assim que o código
muda. Uma violação do contrato é sempre um blocker.

Achados blocker e major exigem resolução ou uma exceção de risco confiável.
O verde local é `checked`; a [aceitação confiável](../enterprise.md) é
exigida para `verified` e para `deliver`. A aprovação de QA vincula o
review, as exceções e a evidência assinada.
