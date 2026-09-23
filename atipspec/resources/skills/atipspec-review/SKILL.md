---
name: atipspec-review
description: Review a completed ATIPSpec candidate against the approved behavior and present its evidence for human acceptance.
---

# Phase review

1. Run `atipspec review <slug>` and follow the printed workflow and rules. Resolve
   its prerequisites without bypassing them.
2. Use an isolated reviewer when supported and authorized; otherwise disclose
   shared context. Only the reviewer writes review.md. A review verdict is not
   human approval.
3. Run `atipspec check <slug>`; fix, verify and review again as needed. Present
   the result and evidence. Offer approval, changes or cancellation in the same
   conversation. After explicit human confirmation, the coordinating assistant
   records local acceptance with `atipspec accept <slug> result` and delivers.
   Follow an external trust policy's authenticated procedure when configured.
