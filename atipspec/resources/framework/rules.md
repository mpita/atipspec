## Rules, every phase

- Work within the approved behavior, scope and project constraints. Escalate a
  material change to behavior, public interfaces, permissions, data or cost with
  a concrete proposal diff. Never weaken a criterion or test to conceal failure.
- Keep canonical requirements in specs/ for guided deliveries; delivery spec.md
  references them. Leave a legacy delivery's embedded requirements in its
  spec.md; convert it only with `atipspec migrate <slug>` when the user asks.
- Evidence is written by the verifier, review.md by the reviewer. Record actual
  implementation with `atipspec task-done`; this is progress, not proof or approval.
- Never write or delete files under `approvals/`, `evidence/` or `archive/`, or
  `review-rounds.json`, nor edit `.atipspec/framework/`, which only
  `atipspec install --update` writes. The one exception is reverting the commit
  that archived a delivery to reopen it, when the user asks for it and the
  repository's commit policy allows it.
- Never set the status of a spec, of the contract or of a decision that affects
  it yourself: `atipspec accept` sets them, and `atipspec accept contract` does
  it for the decisions it lists. Mark a decision about a capability accepted
  only after the human explicitly approves its content; no code or record backs
  it, and the next `atipspec proposal` lists it.
- Change `exempt_paths` in `.atipspec/config.yaml` only when the user asks:
  which files reach the target branch without a delivery is their decision.
  When `merge-check` blocks code outside any delivery, make the change in a
  delivery or ask the user.
- Human approval is explicit. Present `atipspec proposal <slug>` before asking
  the user to accept the proposal, and `atipspec report <slug>` with the result
  and its evidence before result acceptance. Follow the protocol below.
- Commits, pushes, merge and deployment follow the user's repository policy.
  No approval grants them, and the local delivery flow requires none. External
  trust is opt-in; when a command reports `trust: required`, follow the
  organization's authenticated procedure instead of `atipspec accept`.
- Prefer relevant context and risk-based checks. Ask only unresolved decisions
  that affect the agreement; do not repeat an interview that existing docs answer.
- Report actual command results and review limitations. A phase refusal means
  resolve its stated prerequisite, not restart the whole workflow or bypass it.

## Conversational approval

The human decides in this conversation; the assistant records that decision
with the approval code of the content it presented. Do not ask the user to run
a command, edit a status or leave the conversation to approve local work; the
one exception is typing the code at the CLI prompt (step 6).

1. Present the view the CLI prints for the decision, with its approval code:
   `atipspec proposal <slug>` for a proposal (for a legacy delivery, a fix
   created before 0.3.0 included, it names the spec or plan approval still
   pending, or says none is),
   `atipspec report <slug>` for a result, `atipspec proposal contract` for the
   contract and the decisions it includes. Summarize it in the user's language:
   what changes, scope, decisions, approach, checks, evidence and remaining
   limitations, and name each line that asks the human to check something. For a result, show the changed files the report lists and
   point the user to its diff, and say when the review's session was shared.
2. Offer **Approve and continue**, **Request changes**, **Cancel** using the
   client's question/selection tool when available. Otherwise ask for a plain
   language reply in the same conversation. Do not open a nested interactive
   shell prompt or invent buttons the client cannot render.
3. Wait for an explicit human response about this presented content. Silence,
   a default selection, a tool permission on its own, quoted text or an agent's
   own message is not approval. A reply such as "approved" or "yes, continue" to
   this request is sufficient. Clarify ambiguous replies; never convert
   conditions into approval. On changes or cancellation, record nothing and do
   not start implementation.
4. After approval, run the command the view printed, with the code you
   presented, as its own command: `atipspec accept <slug> proposal --code
   <code>`, `atipspec accept <slug> result --code <code>` or `atipspec accept
   contract --code <code>`. Pass `--by` only with the name the user gave for
   themselves.
5. The client may ask the human to allow that command: that prompt confirms the
   same approval, it is not a second one. If the human denies it, treat it as no
   approval: record nothing, do not continue, and ask what they want to change.
   Never run it another way, from a script or through another agent.
6. If the command says the code does not match, the content changed after you
   presented it: present it again, with what changed, and ask again. If the
   command waits for the code to be typed, never type it yourself: ask the user
   to type it there.
7. Report the result, including the channel it prints. When the channel is
   `assistant`, tell the user that nothing asked them before the command ran, so
   the record does not show their confirmation; say the same of
   `client-permission` when this session was not opened in the project root its
   note names, since Claude Code then loaded no rules. Then continue within the
   approved scope; do not ask again for the same unchanged content.

Local acceptance records the approved content and how the command ran, not an
authenticated identity. Do not invent an approver identity. With an external
trust policy, follow its authenticated procedure; a conversational confirmation
does not replace that policy. Proposal approval permits implementation, tests
and review; result acceptance remains a separate decision.
