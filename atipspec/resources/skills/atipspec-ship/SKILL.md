---
name: atipspec-ship
description: AtipSpec ship mode. Use when the user says "ship <slug>" or "do everything": run the remaining phases without pausing except at the stop points and the questions that change the spec.
---

# Ship mode

1. Run `atipspec ship <slug>`. It prints the next phase and the command to run.
2. Enter that phase with its skill, finish it, and run `atipspec ship <slug>`
   again. Stop only where the CLI stops you: the user's approval of the spec,
   the plan approval when the policy asks for it, and the merge.
3. End with one report: what changed, evidence, review outcome, deferred
   items, next action.
