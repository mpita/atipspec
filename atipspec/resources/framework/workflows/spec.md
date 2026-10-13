# Phase spec: define observable behavior

Act as product analyst and guide. Read the request, existing specs, relevant code
and tests before asking. Ask only what stays open, in rounds of at most three
questions, highest impact first; tie each question to the decision it changes
and propose a default. Ask another round while a consequential decision is open.
Separate user decisions, repository facts and proposed assumptions, and record
every assumption under `## Assumptions`. A small reversible change does not need
a full interview.

Settle, in this order: actor and trigger; happy path; failure paths (invalid
input, missing data, permissions, timeouts); data created, changed or deleted;
out of scope; quality attributes as a number with how it is measured, or none;
conflicts with existing behavior or the contract. Describe behavior, never
implementation. Never accept "works well", "correctly" or another adjective as an
outcome: ask for the value a test or a person would observe.

For guided deliveries (schema: 2), author complete requirements in
`.atipspec/specs/<capability>.md` and list their IDs under `requirements` in the
delivery spec.md. `atipspec spec-bind <slug> --file <authored.md>` can install and
reference them together. When the user provides a list of acceptance
criteria, run `atipspec spec-bind <slug> --file <path>`: it converts and binds
it, and you present its import review notes with the proposal. Before editing
a capability others may be changing, run `atipspec team` and reconcile the
requirements that overlap. Do not create empty capability documents. In the
delivery spec.md, fill `## Intent` (actor, trigger, observable result and how
the user will know it worked) and
`## Out of scope`, and list under
`## Quality attributes` one `- REQ-...: limit` line per requirement in specs/ that
states a limit. Write `- None` where nothing applies. Delivery spec.md holds no
second functional definition. For legacy deliveries keep the embedded spec;
`atipspec migrate <slug>` converts one only when the user asks.

Write one requirement per behavior a user values, independent of other open
changes, small enough for this delivery and testable (INVEST); split any other.
Use stable REQ IDs and nested AC scenario headings, with GIVEN when context is
needed, WHEN for the action and THEN for observable results. AND/BUT extend the
previous step. English, Spanish and Portuguese step words are supported. Give
each THEN a concrete value: a number, quoted text, a path or a name as displayed.
A quality attribute's criterion states the number with its unit and how it is
measured (its fit criterion), such as "the p95 response time measured at the API
gateway is below 300 ms".
`[manual]` identifies human observation; `[invariant]` allows an INVARIANT assertion
without an artificial trigger. Markdown scenarios are not executable tests.
Preserve existing IDs. Run `atipspec ids <capability>` once for this delivery and
number further requirements and criteria with the same prefix (-002, -003); the
optional --legacy counter only sees local history and is not concurrency-safe.
Include negative and boundary cases appropriate to risk.

Propose `risk` in the delivery's spec.md: `low` for a local change whose
criteria named tests will prove, `high` for security, money, personal data,
permissions or a change hard to revert, `normal` otherwise. `low` cannot remove
a requirement or change the contract. The proposal shows what the level asks of
the gate; the human approves it with the proposal, and changing it afterwards
voids that approval.

Run `atipspec check <slug>` and rewrite what it flags with the observable value.
Quote only text the interface shows word for word, never an adjective to hide it.
Name any warning you keep when presenting.

Prepare the approach and test strategy before seeking approval. Guided deliveries
can enter `atipspec plan <slug>` while the proposal is still a draft. Present
`atipspec proposal <slug>` with its approval code and request one explicit human
approval of the combined agreement in the conversation. After the user's explicit
approval, run `atipspec accept <slug> proposal --code <code>` yourself with that
code and continue to build. Follow the shared approval rules; no command is
required from the user. For legacy deliveries `atipspec proposal <slug>` shows the
code and the command of the spec or plan approval still pending, if any.
