# spec

These examples show the legacy spec/plan sequence. In guided deliveries, review
behavior, approach and tests together and approve once in the conversation; the
assistant records `accept <slug> proposal`. All local approval commands below can
be run by the assistant after your explicit confirmation.

**From intent to a specification the reviewer can verify.** The phase where
you decide what gets built.

| | |
| --- | --- |
| Role | The specifier. Cares about the observable result, not the solution. Asks in short batches, proposes defaults, never accepts "works well" as a criterion. |
| Who decides | You, by running `atipspec accept <slug> spec`. **Stop point 1.** |
| Produces | `spec.md` with requirements and acceptance criteria; your acceptance sets `status: ready` |

## How to run it

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

If the delivery does not exist yet, the model creates it with `atipspec new`.
Then the skill runs `atipspec spec password-reset`. The command refuses until
the contract has `status: accepted`; otherwise it prints the workflow, the
rules and the context.

## What the model does

1. Reads the context the command printed: the contract, overview, glossary,
   the living specs in the impact list and the decisions that affect them. It
   uses the glossary's words and asks before accepting a synonym.
2. Covers, asking only what the project does not already answer: actor and
   trigger, happy path, failure paths, data created, changed, deleted or never
   touched, out of scope, non-functional limits, conflicts with existing
   behavior or the contract.
3. Writes `spec.md`:

```markdown
---
title: "Password reset"
status: draft
capability: auth
impact: [notifications]
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...
created: 2026-09-12
---

# Password reset

## Intent

Let a user who forgot the password recover access without support.

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

Acceptance criteria:
- AC-001: When a registered email requests a reset, the system sends a link to that email within 60 seconds.
- AC-002: When an unknown email requests a reset, the system responds exactly like a valid one.

### REQ-002: The link expires

Acceptance criteria:
- AC-003: If a link is older than 30 minutes, then the system shows "link expired" and sends nothing.

## Quality attributes

### REQ-003: Reset requests under load

Acceptance criteria:
- AC-004: When 100 users request a reset within one minute, the p95 response time at the API gateway is below 300 ms.

## Assumptions

- The link is single-use.

## Out of scope

- Password policy changes.

## Open questions

- None
```

4. Runs `atipspec check password-reset` until the only remaining todo is
   your acceptance.
5. Presents the spec and asks you to run `atipspec accept password-reset spec`.

## Rules of the interview

- At most five questions per batch, each tied to the requirement it changes.
- A default the model proposes becomes a requirement and an assumption you
  confirm at acceptance, never a silent choice.
- Every criterion in EARS or scenario form with concrete values, no vague
  terms, and marked `[manual]` when a person observes it; `check` warns
  otherwise. See [writing criteria](../reference/spec-quality.md).
- Quality attributes are numbers with a way to measure them, or nothing.
- A delivery fits in a working day. Above `max_requirements` the model
  proposes splitting it into deliveries under an initiative before asking
  for the acceptance; `check` warns either way.
- Behavior, never implementation.
- A spec with open questions cannot be ready. `check` refuses it.
- `capability` is the living spec that receives the requirements on deliver.
  `impact` lists every other living spec or contract section the delivery
  touches: `context` loads them and `status` warns about overlaps with other
  open deliveries.
- `### REQ-003 [remove]: Exact title` deletes that section from the living
  spec on deliver. This is how behavior is retired: explicitly.

## Your part

Read it as the contract it is. Change wording, add criteria, cut scope. When
it says what you want, approve in the conversation. For a legacy spec, the assistant then runs:

```bash
atipspec accept password-reset spec
```

It refuses while a question is open or a requirement has no criterion;
otherwise it sets `status: ready` and records a hash of the spec and the
contract. From then on, any edit to either file turns the delivery back into
a draft until you accept again. The assistant runs this command only after your explicit approval in the conversation.

!!! note "Changing the spec later"
    If the build reveals that a criterion cannot be met, the model must stop
    and tell you. The spec changes with your agreement, and the delivery goes
    through the gate again. Criteria are never weakened silently and never
    deferred.
