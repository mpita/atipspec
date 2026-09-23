# Phase review: compare the candidate with the approved behavior

Use the packet produced by `atipspec review <slug>`: requirements, plan, applicable
constraints, evidence and diff. Prefer an isolated reviewer session when the
adapter supports it and delegation is authorized. Otherwise disclose that the
review shares context; do not claim independent execution or require a new human
interview just because a client lacks subagents.

The reviewer may write review.md, with one PASS/FAIL and a precise evidence pointer
per criterion. Review tests for what they actually observe, including relevant
negative cases. Reuse current verification results; rerun or add checks when a
finding or risk justifies it. A clean review with no findings is valid. Do not
invent a quota of defects. Manual criteria require actual observations.

Fix blockers and major findings, rerun affected verification and review the new
candidate. Do not change the criterion or fabricate evidence to get green. After
the configured review_rounds without resolution, report the remaining decision.
Criteria cannot be deferred; significant risk exceptions use optional trust policy.

A green local check is ready for the human to inspect, not yet accepted. Present
`atipspec report <slug>` with a brief demonstration and remaining limitations.
Request result acceptance in the conversation. After the human explicitly approves,
the coordinating assistant runs `atipspec accept <slug> result`, then
`atipspec deliver <slug>` archives it. The reviewer cannot grant human acceptance.
No signatures are required in local mode. Projects
with an external trust policy retain their authenticated CI and approval gates.
Merge and deployment follow the repository's explicit policy.
