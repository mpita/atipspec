---
name: atipspec-review
description: Review a completed ATIPSpec candidate against the approved behavior and present its evidence for human acceptance.
---

# Phase review

1. Run `atipspec review <slug>` and follow the printed workflow and rules. Resolve
   its prerequisites without bypassing them.
2. Give the packet to a reviewer in an isolated session (a subagent or a new
   session, given only the packet path). If the client cannot provide one, the
   reviewer writes `session: shared`; with `risk: high` or
   `require_isolated_review`, ask the user to open a new session for the
   reviewer instead, given only the packet path. Only the reviewer writes
   review.md. A review verdict is not human approval. If this session was
   opened only to review a packet, you are the reviewer: follow the packet,
   write review.md and stop.
3. Run `atipspec check <slug>`; fix, verify and review again as needed. If
   `atipspec review` refuses because review_rounds is used up, stop and present
   `atipspec check <slug>` with the remaining findings; the user decides. Present
   `atipspec report <slug>`: the result, its evidence and its approval code. Offer
   approval, changes or cancellation in the same conversation. After explicit
   human approval, the coordinating assistant records local acceptance with
   `atipspec accept <slug> result --code <code>` and delivers. Follow an external
   trust policy's authenticated procedure when configured.
