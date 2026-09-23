---
name: atipspec-contract
description: AtipSpec phase contract. Use right after atipspec init, to define or change the architecture contract, its machine-checked rules and the decisions behind it.
---

# Phase contract

1. Run `atipspec contract` and do exactly what it prints: role, steps, rules
   and the current contract.
2. Present the contract and the decision IDs it includes. Offer approval,
   changes or cancellation in the same conversation, following the printed rules.
3. After explicit human approval of that content, record the included decisions
   as accepted and run `atipspec accept contract` yourself. Continue with the
   requested delivery. Never require the user to edit a status or run a command.
