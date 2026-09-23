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
  acceptance. Never infer approval from an agent's own text or mark accepted by hand.
- Commits, pushes, merge and deployment follow the user's repository policy.
  None is required by the local delivery flow. External trust is opt-in.
- Prefer relevant context and risk-based checks. Ask only unresolved decisions
  that affect the agreement; do not repeat an interview that existing docs answer.
- Report actual command results and review limitations. A phase refusal means
  resolve its stated prerequisite, not restart the whole workflow or bypass it.
