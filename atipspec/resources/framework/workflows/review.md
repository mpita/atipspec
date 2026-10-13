# Phase review: compare the candidate with the approved behavior

`atipspec review <slug>` writes the packet: requirements, plan, applicable
constraints, evidence and diff. Give the packet to a reviewer in an isolated
session: a subagent or a new session that has not seen this conversation, given
only the packet path. If the client cannot isolate it, the reviewer writes
`session: shared` in review.md; never write `session: isolated` from a session
that saw the author's conversation. `risk: high` and `require_isolated_review`
need an isolated reviewer: when the client cannot provide one, ask the user to
open a new session in the project and give it only this request: "Read
`.atipspec/tmp/<slug>-review-packet.md` and do what it says". That session is
the reviewer and writes review.md, nothing else; you then run `atipspec check
<slug>`.

The packet states the delivery's risk. With `risk: low`, a criterion under
Tests whose test named in Proof passed in the current evidence needs no
verdict; the reviewer still reads the diff, gives a verdict to every other
criterion, manual ones included, and writes the findings.

The reviewer writes review.md with `reviewer:`, `session:` and one PASS or FAIL
per criterion, except those `risk: low` exempts. Each PASS points to its proof
in a form the gate resolves: a test that passed in the evidence report,
`path:line` of a file outside `.atipspec/` (the evidence logs under
`evidence/logs/` included) or `path::test`. For a manual criterion, state what
was done and what was observed. Review tests for what they actually observe,
including relevant negative cases. Reuse current verification results; rerun or
add checks when a finding or risk justifies it. A clean review with no findings
is valid. Do not invent a quota of defects.

Fix blockers and major findings, rerun affected verification and run
`atipspec review <slug>` again for the new candidate. Do not change the
criterion or fabricate evidence to get green. When `atipspec review` refuses
because review_rounds is used up, stop: present `atipspec check <slug>` and the
remaining findings, and let the user decide. Criteria cannot be deferred;
significant risk exceptions use optional trust policy.

A green local check is ready for the human to inspect, not yet accepted. Present
`atipspec report <slug>`, which shows the changed files, the diff and the
result's approval code, with a brief demonstration and remaining limitations.
Request result acceptance in the conversation. After the human explicitly
approves, the coordinating assistant runs
`atipspec accept <slug> result --code <code>` with that code, then
`atipspec deliver <slug>` archives it. The reviewer cannot grant human acceptance.
No signatures are required in local mode. Projects with an external trust
policy retain their authenticated CI and approval gates. Merge and deployment
follow the repository's explicit policy.
