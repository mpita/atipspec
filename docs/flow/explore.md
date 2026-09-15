# explore

**From a vague idea to a one-page brief.** Optional: skip it when you already
know what you want.

| | |
| --- | --- |
| Role | The investigator. Finds the problem, what exists, the options and their cost. Skeptical of the first framing. |
| Who decides | You: spec it, narrow it, or drop it. |
| Produces | `.atipspec/deliveries/<slug>/brief.md` |

## How to run it

```bash
atipspec new checkout-v2 --title "Checkout redesign" --capability checkout
```

```text
/atipspec-explore checkout-v2: customers abandon the checkout on the address step
```

The skill runs `atipspec explore checkout-v2`, which prints the workflow, the
rules and the context: the living specs and decisions the idea seems to
touch. The model looks at the code and writes the brief:

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

## What it must not do

No IDs, no criteria, no plan, no code. One page. The model does not start the
spec phase on its own; it stops and waits for you.

## Then

- "Spec it": continue with [spec](spec.md). The brief stays in the folder and
  the spec phase's context includes it.
- Drop it: `git rm -r .atipspec/deliveries/checkout-v2`.
