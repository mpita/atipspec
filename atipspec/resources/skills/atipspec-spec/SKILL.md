---
name: atipspec-spec
description: AtipSpec phase spec. Use when the user wants to specify a delivery, write requirements and acceptance criteria, or says "spec it". Ends at stop point 1, the user's approval.
---

# Phase spec

1. If the delivery does not exist, create it: `atipspec new <slug> --title "..."`
   (add `--capability`, `--owner`, `--branch` when the user gives them).
2. Run `atipspec spec <slug>` and do exactly what it prints. It contains the
   role, the interview, the rules and the context.
3. If the command refuses, tell the user what it asks for and stop. Never edit
   the contract or the spec status, and never run `atipspec accept`: the
   person does, at stop point 1.
