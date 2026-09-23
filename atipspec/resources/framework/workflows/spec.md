# Phase spec: define observable behavior

Act as product analyst and guide. Read the request, existing specs, relevant code
and tests before asking questions. Group consequential uncertainties in a short
round, distinguishing user decisions, repository facts and proposed assumptions.
A small reversible change does not need a full architecture interview.

For guided deliveries (schema: 2), author complete requirements in
`.atipspec/specs/<capability>.md` and list their IDs under `requirements` in the
delivery spec.md. `atipspec spec-bind <slug> --file <authored.md>` can install and
reference them together. Do not create empty capability documents. Delivery
spec.md holds intent, scope and assumptions, not a second functional definition.
For legacy deliveries retain the embedded spec until an explicit migration.

Use stable REQ IDs and nested AC scenario headings, with GIVEN when context is
needed, WHEN for the action and THEN for observable results. AND/BUT extend the
previous step. English, Spanish and Portuguese step words are supported.
`[manual]` identifies human observation; `[invariant]` allows an INVARIANT assertion
without an artificial trigger. Markdown scenarios are not executable tests.
Preserve existing IDs. Use `atipspec ids <capability>` for independent new IDs;
the optional --legacy counter only sees local history and is not concurrency-safe.
Include negative and boundary cases appropriate to risk.

Prepare the approach and test strategy before seeking approval. Guided deliveries
can enter `atipspec plan <slug>` while the proposal is still a draft. Present
`atipspec proposal <slug>` and request one explicit human approval of the combined
agreement with `atipspec accept <slug> proposal`. Never accept it on the user's
behalf without their explicit instruction. Legacy spec/plan approvals still work.
