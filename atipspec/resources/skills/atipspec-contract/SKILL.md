---
name: atipspec-contract
description: AtipSpec phase contract. Use right after atipspec init, to define or change the architecture contract, its machine-checked rules and the decisions behind it.
---

# Phase contract

1. Run `atipspec contract` and do exactly what it prints: role, steps, rules
   and the current contract.
2. Present `atipspec proposal contract`: the contract, its rules, the audit and
   the decisions it includes, with the approval code. Offer approval, changes or
   cancellation in the same conversation, following the printed rules.
3. After explicit human approval of that content, run `atipspec accept contract
   --code <code>` yourself with that code; it sets the contract and the listed
   decisions to accepted. Never edit a decision's status. Continue with the
   requested delivery. Never require the user to edit a status or run a command.
