---
name: atipspec-plan
description: AtipSpec phase plan. Use when the user wants the tasks for an approved spec, or after stop point 1 in ship mode.
---

# Phase plan

1. Run `atipspec plan <slug>` and do exactly what it prints: role, steps, rules
   and context.
2. If the command refuses, the spec is not accepted: tell the user what it asks
   for and stop. When `approve_plan` is on, the person accepts the plan with
   `atipspec accept <slug> plan`; you never run it.
