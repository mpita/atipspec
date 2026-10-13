# spec

**From intent to scenarios the reviewer can verify.** The phase where you
decide what gets built.

| | |
| --- | --- |
| Role | The analyst. Cares about the observable result, not the solution. Asks at most three questions per round, proposes defaults, never accepts "works well" as an outcome. |
| Who decides | You approve the proposal in the conversation: these scenarios together with the approach and the tests of the [plan](plan.md); the assistant records it with `atipspec accept <slug> proposal --code <code>`. **Stop point 1.** |
| Produces | requirements and scenarios in `.atipspec/specs/<capability>.md`; the delivery's `spec.md` with the intent, what is out of scope, the quality limits and the IDs it lists |

## How to run it

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

If the delivery does not exist yet, the model creates it with `atipspec new`.
Then the skill runs `atipspec spec password-reset`, which prints the
workflow, the rules and the context. A guided delivery needs nothing else to
start; `check` warns while the contract is not accepted. A fix delivery uses
[fix](fix.md) instead, and a [legacy delivery](../reference/legacy.md#approvals)
needs the contract's acceptance first.

## What the model does

1. Reads the context the command printed: the contract, overview, glossary,
   the living specs in the impact list and the decisions that affect them. It
   uses the glossary's words and asks before accepting a synonym.
2. Asks only what the project does not already answer, in rounds of at most
   three questions, highest impact first, each tied to the decision it changes
   and with a proposed default; it asks another round while a consequential
   decision is open. It settles, in this order: actor and trigger; happy path;
   failure paths (invalid input, missing data, permissions, timeouts); data
   created, changed or deleted; out of scope; quality attributes as a number
   with how it is measured, or none; conflicts with existing behavior or the
   contract.
3. Takes an ID prefix once for the delivery with `atipspec ids auth` and
    writes the requirements and their scenarios in the capability's living
    spec, `.atipspec/specs/auth.md`:

    ```markdown
    ### REQ-AUTH-7KQ2M-001: The user can request a reset link

    From the sign-in screen the user enters an email and receives a link.

    Why: support tickets for forgotten passwords are 40% of the queue.

    #### AC-AUTH-7KQ2M-001: Registered email
    - **GIVEN** a registered user with the email "ana@example.com"
    - **WHEN** the user requests a reset for "ana@example.com"
    - **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

    #### AC-AUTH-7KQ2M-002: Unknown email
    - **WHEN** a reset is requested for "nobody@example.com", which no user has
    - **THEN** the system shows "Check your email" and sends nothing

    ### REQ-AUTH-7KQ2M-002: The link expires

    #### AC-AUTH-7KQ2M-003: Link older than 30 minutes
    - **WHEN** a link issued 31 minutes ago is opened
    - **THEN** the page shows "link expired" and sends nothing

    ### REQ-AUTH-7KQ2M-003: Reset requests under load

    #### AC-AUTH-7KQ2M-004: One hundred requests a minute
    - **WHEN** 100 users request a reset within one minute
    - **THEN** the p95 response time measured at the API gateway is below 300 ms
    ```

4. Fills the delivery's `spec.md`: `requirements` lists the IDs this change
    writes, `## Intent` states the actor, the trigger, the observable result and
    how you will know it worked, `## Out of scope` and `## Quality attributes`
    (one `- REQ-...: limit` line per requirement that states a limit) are
    decided, `- None` included:

    ```markdown
    ---
    title: "Password reset"
    status: draft
    capability: auth
    owner: ana
    requirements: [REQ-AUTH-7KQ2M-001, REQ-AUTH-7KQ2M-002, REQ-AUTH-7KQ2M-003]
    risk: normal
    ---

    # Password reset

    ## Intent

    A user who forgot the password requests a reset link by email and sets a new
    password with it, without contacting support.

    ## Out of scope

    - Password policy changes.

    ## Quality attributes

    - REQ-AUTH-7KQ2M-003: p95 below 300 ms with 100 requests per minute

    ## Assumptions

    - The link is single-use.

    ## Open questions

    - None
    ```

    When you bring a document or a list of acceptance criteria, the model
    runs `atipspec spec-bind password-reset --file <path>`, which writes the
    living spec and the IDs; for a list, it keeps the original and lists under
    `## Import review notes` what to check.

5. Runs `atipspec check password-reset` and rewrites what it flags until the
   only remaining todo is your approval. It quotes only text the interface
   shows word for word, and names each warning it keeps when presenting.
6. Proposes the delivery's [risk](#risk), prepares the [plan](plan.md) and
   presents `atipspec proposal password-reset`, which shows the approval code,
   the kind and risk, how strictly the criteria are checked, the
   specification warnings and the diff of the living spec, and asks for your
   approval in the conversation.

## Rules of the interview

- At most three questions per round, each tied to the decision it changes;
  more rounds while a consequential decision is open.
- A default the model proposes becomes a requirement and an assumption you
  confirm at acceptance, never a silent choice.
- Every scenario with WHEN and THEN and a concrete value in each THEN, no
  vague terms, and marked `[manual]` when a person observes it; `check`
  reports it otherwise. See [writing criteria](../reference/spec-quality.md).
- One requirement per behavior a user values, independent of other open
  changes, small enough for the delivery and testable.
- Quality attributes are numbers with a way to measure them, or nothing.
- An empty `## Intent` blocks the proposal, and so does an empty `## Out of
  scope` or `## Quality attributes`: write `- None` when nothing applies.
- A delivery fits in a working day. Above `max_requirements` the model
  proposes splitting it into deliveries under an initiative before asking
  for the acceptance; `check` warns either way.
- Behavior, never implementation.
- A spec with open questions cannot be approved: the proposal shows no code.
- `capability` is the living spec that holds the requirements.
  `impact` lists every other living spec or contract section the delivery
  touches: `context` loads them and `status` warns about overlaps with other
  open deliveries.
- `### REQ-AUTH-7KQ2M-003 [remove]: Exact title` in the living spec, listed
  under `requirements`, deletes that requirement on deliver. This is how
  behavior is retired: explicitly.
- Requirements another open delivery or the living spec already holds keep
  their IDs; the delivery lists only what it writes.
- A requirement the delivery adds, changes or removes in `specs/` without
  listing it, in its capability's living spec or in another one, is an error
  at every risk level: the approval hashes only the listed ones, and
  `merge-check` blocks the rest.

## Risk

A guided delivery's `spec.md` states `risk: low`, `normal` (what `new`
writes) or `high`. The model proposes the level; you approve it with the
proposal, which shows `Kind: ... · Risk: ...` and what the level asks of the
gate. `risk` is part of what the proposal's approval hashes, so changing it
afterwards voids that approval. The level adds or removes no approval.

| Level | What the gate asks |
| --- | --- |
| `low` | a criterion under `Tests:` whose test named in `Proof:` passed in the current evidence needs no reviewer verdict (`check` says so with an info, and the dossier shows `NOT NEEDED` with the reason); `review.md` is still required, every other criterion, manual ones included, needs its verdict and a `FAIL` still blocks. Removing a requirement (marked `[remove]` or deleted from `specs/`), even a listed one, or changing `contract.md` is an error: `check` compares `specs/` with the requirements committed at the delivery's base and what the integration branch and the deliveries archived in the branch since brought |
| `normal` | a reviewer verdict for every criterion |
| `high` | `plan.md` declares a `scope`, and a file outside it is an error, even with `strict_scope: false`; every criterion under `Tests:` names its test in `Proof:`, with a `Report:` (an error that blocks the proposal); the review comes from an isolated session (`session: isolated`) |

A delivery without `risk`, legacy ones included, is `normal`; a legacy
delivery that sets it by hand gets its effects, and `check` notes the level.
Another value is an error. The review packet states the level, and the
dossier shows it.

## Your part

Read the proposal as the agreement it is. Change wording, add scenarios, cut
scope. When it says what you want, approve in the conversation; the assistant
then runs, with the code it presented:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

It refuses while a question is open, a scenario is incomplete or the plan has
an error, and when the code does not match the current content; otherwise it
sets `status: ready` and records a hash of the scenarios, the delivery's
`spec.md`, the plan's commitments, the contract and the configuration, the
code and the channel. From then on, any edit to them turns the delivery back
into a draft until you approve again, and `check` names what changed. Claude
Code asks you before the command runs.

!!! note "Changing the spec later"
    If the build reveals that a criterion cannot be met, the model must stop
    and tell you. The spec changes with your agreement, and the delivery goes
    through the gate again. Criteria are never weakened silently and never
    deferred.
