---
name: atipspec-fix
description: "AtipSpec phase fix. Use when the user reports a bug or defect to repair: a regression criterion, a one-task plan and the same gate, without the spec interview."
---

# Phase fix

1. If the delivery does not exist, create it: `atipspec new <slug> --title "..." --kind fix`
   (add `--capability` and `--ticket` when the user gives them).
2. Run `atipspec fix <slug>` and do exactly what it prints: reproduce, write
   the regression criterion, ask the user to accept, build, review.
3. If the command refuses, tell the user what it asks for and stop. If the
   repair changes a living behavior, say so: it is a delivery, not a fix.
