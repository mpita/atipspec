---
name: atipspec-build
description: AtipSpec phase build. Use when the user wants the planned tasks implemented, one task at a time, with evidence and one commit per task.
---

# Phase build

1. Run `atipspec build <slug>` and do exactly what it prints. It names the next
   task that is not committed.
2. Work one task at a time; after each commit run `atipspec build <slug> --no-context`
   for the next one. Never touch evidence/; `atipspec verify` writes it.
3. If the command refuses, tell the user what it asks for and stop.
