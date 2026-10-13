# explore

**De una idea vaga a un brief de una página.** Opcional: sáltatela cuando ya
sepas lo que quieres.

| | |
| --- | --- |
| Rol | El investigador. Encuentra el problema, lo que ya existe, las opciones y su coste. Escéptico del primer planteamiento. |
| Quién decide | Tú: haz la spec, acótala, o descártala. |
| Produce | `.atipspec/deliveries/<slug>/brief.md` |

## Cómo ejecutarla

```bash
atipspec new checkout-v2 --title "Checkout redesign" --capability checkout
```

```text
/atipspec-explore checkout-v2: customers abandon the checkout on the address step
```

El skill ejecuta `atipspec explore checkout-v2`, que imprime el workflow, las
reglas y el contexto: las specs vivas y las decisiones que la idea parece
tocar. El modelo mira el código y escribe el brief:

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

## Qué no debe hacer

Sin IDs, sin criterios, sin plan, sin código. Una página. El modelo no
empieza la fase spec por su cuenta; se detiene y te espera.

## Luego

- «Haz la spec»: continúa con [spec](spec.md). El brief se queda en la
  carpeta y el contexto de la fase spec lo incluye.
- Descártala: `git rm -r .atipspec/deliveries/checkout-v2`.
