# Phase build: implement the approved agreement

Read the relevant requirements, task and code. Implement behavior and useful
regression tests within the approved scope. Use focused tests during development;
for a defect, reproduce the failure first when practical. Do not run the entire
project suite after every task just to create evidence.

Record each finished task with `atipspec task-done <slug> Tn --note "what changed"`.
The record is a declaration: final verification and review independently check
quality. Existing commit markers remain supported; commits are not mandatory.

Once the candidate is complete, run `atipspec verify <slug>`. A plan's
`## Final verification` commands execute once for all mapped tasks and scenarios.
Per-task Verify commands are development checks when final verification exists.
Repeated commands in a final list execute as written; no unsafe deduplication.

Use a JUnit report and Proof mapping when available. A successful build is not
proof of a business scenario. Manual observations remain manual and need a
reviewer observation with a precise pointer. If code changes after final checks,
rerun verification on the finished candidate. Then `atipspec review <slug>`.

Fix within the agreement automatically. If fulfilling a requirement needs a
material scope or contract change, present that decision before proceeding.
