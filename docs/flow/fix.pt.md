# fix

**De um relatório de defeito a um critério de regressão, um plano de uma
tarefa e o mesmo portão.** Sem entrevista, sem aceitação de plano, sem
atalho na evidência ou no review.

| | |
| --- | --- |
| Papel | Quem conserta sem ampliar. Reproduz primeiro, escreve o critério que falha hoje e passa amanhã, muda apenas o que o defeito exige. |
| Quem decide | Você aceita a spec com `atipspec accept <slug> spec`. **Ponto de parada 1.** |
| Produz | `spec.md` com um requisito e um critério de regressão, `plan.md` com uma tarefa, código, evidência, um commit |

## Como executar

```bash
atipspec new bug-123 --title "Reset link never expires" --capability auth --ticket SHOP-9 --kind fix
```

```text
/atipspec-fix bug-123: a reset link created yesterday still works
```

A skill executa `atipspec fix bug-123`, que recusa em uma entrega que não é
um fix ou enquanto o contrato não está aceito, e caso contrário imprime o
workflow, as regras e o contexto.

## O que `new --kind fix` cria

Uma spec com `kind: fix`, `## Intent` nomeando o defeito, um `REQ-001` com
Observed, Expected e Why, e um `AC-001` para preencher em forma EARS:

```markdown
### REQ-001: Reset link never expires

Observed: a link created 26 hours ago still resets the password.

Expected: a link older than 30 minutes is refused.

Why: auth/REQ-002 in the living spec.

Acceptance criteria:
- AC-001: When a reset link is 31 minutes old, the system returns "link expired" and sends nothing.
```

E um plano com uma tarefa, `T1: Fix and regression test`, cobrindo
`REQ-001`, testando `AC-001`, cujo `Verify:` já lista todo `require-command`
do contrato.

## O que difere de uma entrega

- Sem entrevista: o critério vem do relatório. O modelo só faz uma pergunta
  quando o comportamento esperado não está claro no relatório ou nas specs
  vivas.
- Sem aceitação de plano, seja qual for o valor de `approve_plan`: o plano é
  uma tarefa só.
- `max_requirements` é 2. Um reparo que precisa de mais não é um fix.
- Se o reparo muda um comportamento que uma spec viva declara, é uma
  entrega: o modelo para e avisa.

Todo o resto é igual: sua aceitação da spec, evidência vinculada à árvore,
um commit com `[bug-123:T1]`, o review em um contexto limpo, o portão
confiável e o `deliver`.
