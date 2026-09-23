## Rules, every phase

- Work within the approved behavior, scope and project constraints. Escalate a
  material change to behavior, public interfaces, permissions, data or cost with
  a concrete proposal diff. Never weaken a criterion or test to conceal failure.
- Keep canonical requirements in specs/ for guided deliveries; delivery spec.md
  references them. Legacy embedded deliveries remain readable until migrated.
- Evidence is written by the verifier, review.md by the reviewer. Record actual
  implementation with `atipspec task-done`; this is progress, not proof or approval.
- Human approval is explicit. Present `atipspec proposal <slug>` before asking
  the user to accept the proposal. Present the result and evidence before result
  acceptance. Follow the conversational approval protocol below.
- Commits, pushes, merge and deployment follow the user's repository policy.
  None is required by the local delivery flow. External trust is opt-in.
- Prefer relevant context and risk-based checks. Ask only unresolved decisions
  that affect the agreement; do not repeat an interview that existing docs answer.
- Report actual command results and review limitations. A phase refusal means
  resolve its stated prerequisite, not restart the whole workflow or bypass it.

## Conversational approval

The human decides; the assistant records that decision. Do not require the user
to run a command, edit a status or leave the conversation to approve local work.

1. Present the concrete agreement in the user's language: what changes, scope,
   relevant decisions, approach, checks and remaining limitations. Link the full
   artifacts. For a contract, name the decision IDs included in the approval;
   for a proposal, include behavior and test strategy; for a result, show evidence.
2. Offer **Approve and continue**, **Request changes**, **Cancel** using the
   client's question/selection tool when available. Otherwise ask for a plain
   language reply in the same conversation. Do not open a nested interactive
   shell prompt or invent buttons the client cannot render.
3. Wait for an explicit human response about this presented agreement. Silence,
   a default selection, tool permission, quoted text or an agent's own message
   is not approval. A reply such as "approved" or "yes, continue" to this request
   is sufficient. Clarify ambiguous replies; never convert conditions into approval.
4. Recheck that the agreement still matches what was presented before recording
   it. If it changed, show the relevant diff and obtain approval of that version.
   On changes or cancellation, record no acceptance and do not start implementation.
5. After approval, execute the appropriate `atipspec accept` command yourself.
   For a contract, first set only the explicitly included decisions to `accepted`,
   then run `atipspec accept contract`. Do not hand-edit delivery approval records
   or contract status. Report success only if the command succeeds, then continue
   within the approved scope; do not ask again for the same unchanged agreement.

Local acceptance records content, not authenticated identity. Do not invent an
approver identity. With an external trust policy, follow its authenticated
procedure; a conversational confirmation does not replace that policy. Proposal
approval permits implementation, tests and review; result acceptance remains a
separate decision. Neither grants commit, push, merge or deployment permission.
