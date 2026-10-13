---
name: atipspec-explore
description: AtipSpec phase explore. Use when the user has an idea that is not clear yet and wants a brief with the problem, what exists, options and a recommendation, before any spec.
---

# Phase explore

1. If the delivery does not exist, create it: `atipspec new <slug> --title "..."`.
2. Run `atipspec explore <slug>` and do exactly what it prints. It contains the
   role, the steps, the rules and the context.
3. If the command refuses, tell the user what it asks for and stop.
