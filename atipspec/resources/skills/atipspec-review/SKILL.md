---
name: atipspec-review
description: AtipSpec phase review. Use when every task is committed and the delivery needs its adversarial review by a reviewer that did not write the code.
---

# Phase review

1. Run `atipspec review <slug>`. It refuses until every task is committed with
   fresh evidence; otherwise it writes the packet and prints what to do.
2. Launch the reviewer in a context that has not seen this conversation, with
   only the packet path. You never write review.md and never run `atipspec accept`.
3. Then `atipspec check <slug>`; fix, verify, commit and review again as the
   workflow says. If the command refuses, tell the user what it asks for and stop.
