---
name: atipspec-ship
description: Guide an ATIPSpec change from proposal through implementation and review to human result acceptance.
---

Keep one conversation with the user. Read `atipspec ship <slug>` and enter the
indicated phase. Before approval, prepare scenarios, approach and verification
strategy together and present `atipspec proposal <slug>`. Record approval only in
response to the user's explicit instruction for that proposal.

After approval, implement, test and review within the agreement. Fix defects
without returning routine orchestration to the user. Pause for a material change,
a real blocker, an exhausted retry budget or final result acceptance. Present the
result and its evidence before accepting it. Respect repository commit/push policy.

This skill drives an active assistant session; it does not by itself provide a
persistent background runner or isolated review. Disclose unsupported capabilities.
