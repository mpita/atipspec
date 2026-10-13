---
name: atipspec-fix
description: "AtipSpec phase fix. Use when the user reports a bug or defect to repair: correct the accepted requirement it breaks with a regression criterion and a one-task plan, one proposal approval, the same gate, without the spec interview."
---

# Phase fix

1. If the delivery does not exist, create it with
   `atipspec new <slug> --title "..." --kind fix --capability <capability>`, where
   `<capability>` names the living spec in `.atipspec/specs/` whose requirement the
   defect breaks (add `--ticket` with the key, issue number or https URL the
   user gives).
2. Run `atipspec fix <slug>` and do exactly what it prints: reproduce, state
   the defect, correct the accepted requirement with a regression criterion,
   plan, present the proposal for approval, then build, verify and review.
3. If the command refuses, tell the user what it asks for and stop. If no
   accepted requirement covers the behavior, or the repair adds or removes
   behavior, say so: it is a feature delivery, not a fix.
