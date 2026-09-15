# explore

**De uma ideia vaga a um briefing de uma página.** Opcional: pule quando você
já sabe o que quer.

| | |
| --- | --- |
| Papel | O investigador. Encontra o problema, o que existe, as opções e seu custo. Cético em relação ao primeiro enquadramento. |
| Quem decide | Você: transforma em spec, restringe ou descarta. |
| Produz | `.atipspec/deliveries/<slug>/brief.md` |

## Como executar

```bash
atipspec new checkout-v2 --title "Checkout redesign" --capability checkout
```

```text
/atipspec-explore checkout-v2: customers abandon the checkout on the address step
```

O skill executa `atipspec explore checkout-v2`, que imprime o workflow, as
regras e o contexto: as specs vivas e decisões que a ideia parece tocar. O
modelo olha o código e escreve o briefing:

```markdown
# Brief: Checkout redesign

## Problem
## Today
## Options
### A. Inline address validation
### B. Single-page checkout
## Recommendation
## Questions for the user
```

## O que não deve fazer

Sem IDs, sem critérios, sem plan, sem código. Uma página. O modelo não inicia
a fase spec por conta própria; ele para e espera por você.

## Em seguida

- "Transformar em spec": continue com [spec](spec.md). O briefing fica na
  pasta e o contexto da fase spec o inclui.
- Descartar: `git rm -r .atipspec/deliveries/checkout-v2`.
