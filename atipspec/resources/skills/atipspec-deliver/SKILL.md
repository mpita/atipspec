---
name: atipspec-deliver
description: AtipSpec phase deliver. Use when the gate is green and verified and the user wants the delivery merged into the living spec and archived. Ends at stop point 2, the user's merge.
---

# Phase deliver

1. Run `atipspec check <slug> --policy <external policy>`; it must be green and
   `verified`. A local `checked` is not acceptance: report what is missing.
2. Run `atipspec deliver <slug> --policy <external policy>`, commit, and ask the
   user to merge the branch. AtipSpec never pushes or merges.
3. If the command refuses, tell the user what it asks for and stop.
