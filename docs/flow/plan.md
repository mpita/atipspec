# plan

**From the scenarios to the approach, the tasks and the tests the gate can
prove.** The phase where architecture compliance is decided.

| | |
| --- | --- |
| Role | The designer and the tester: the one who has to maintain this in a year. Prefers the simplest shape inside the contract, reuses what exists, tells you the choices with consequences before making them, and picks the tests by risk. |
| Who decides | You, as part of the proposal: scenarios, approach and tests are approved together (**stop point 1**). A [legacy delivery](../reference/legacy.md#approvals) approves its plan apart when `approve_plan: true`. |
| Produces | `plan.md`: scope, approach, tasks and the final verification |

## How to run it

```text
/atipspec-plan password-reset
```

The skill runs `atipspec plan password-reset`. A guided delivery may plan
before its approval, once its scenarios are complete without a blocking
finding, its intent is stated, its out-of-scope and quality sections are
decided and no question is open; the command refuses with the first thing
missing, and otherwise prints the workflow, the rules and the context.

## What the model does

1. Reads the context the command printed, and the code areas involved.
2. Checks the contract. If the scenarios need something the contract
   forbids, it stops: that needs a [decision](contract.md#changing-the-contract),
   never a workaround.
3. Writes `plan.md`:

    ```markdown
    ---
    scope: ["shop/auth/**", "tests/auth/**"]
    ---

    # Plan: Password reset

    ## Approach

    A `reset` module under `shop/auth/` with `request()` and `consume()`,
    following the contract's structure (domain must not import infrastructure,
    DEC-002). Tokens stored in the existing `auth_token` table.

    ## Tasks

    ### T1: Request a reset link

    Covers: REQ-AUTH-7KQ2M-001
    Tests: AC-AUTH-7KQ2M-001, AC-AUTH-7KQ2M-002

    ### T2: Expire links after 30 minutes

    Covers: REQ-AUTH-7KQ2M-002
    Tests: AC-AUTH-7KQ2M-003

    ### T3: Reset requests under load

    Covers: REQ-AUTH-7KQ2M-003
    Tests: AC-AUTH-7KQ2M-004

    ## Final verification

    Report: .atipspec/tmp/junit.xml
    Proof:
    - AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
    - AC-AUTH-7KQ2M-002: tests/auth/test_reset.py::test_unknown_email_same_answer
    - AC-AUTH-7KQ2M-003: tests/auth/test_reset.py::test_link_expires_after_30_minutes
    - AC-AUTH-7KQ2M-004: tests/auth/test_load.py::test_p95_below_300_ms
    Verify:
    - `python -m pytest -q --junitxml .atipspec/tmp/junit.xml`
    ```

4. `atipspec check password-reset` until there are no plan errors.
5. Presents the plan with the scenarios in `atipspec proposal password-reset`
   and asks for your approval in the conversation; the assistant records it
   with `atipspec accept password-reset proposal --code <code>`, and
   `atipspec build` refuses until then. The approval binds the plan's scope,
   approach and final verification. Splitting or adding a task inside them
   needs no new approval, since the final verification covers every task,
   though `check` still checks coverage and scope; a wider scope, another
   approach or a changed final verification is presented to you again.

## What `check` requires from a plan

- Every active requirement is covered by at least one task (`Covers:`), and
  every criterion is listed once under `Tests:` or `Manual:`, following its
  `[manual]` mark in the spec; until then `atipspec build` refuses.
- Every `require-command` of the contract appears in the `## Final
  verification` commands, or, in a plan without one, in at least one task's
  `Verify:`.
- Commands are real commands of the project. `verify` runs them from the
  project root through the shell: the final verification once for the
  finished candidate; a task's own `Verify:` is a development check.
- A task with only `Manual:` criteria may say `Verify: none`, with a note of
  what the reviewer must observe.
- A `Report:` names a path git ignores, such as `.atipspec/tmp/junit.xml`,
  which the Verify commands write. With `require_proof: true` or
  `risk: high`, every criterion under `Tests:` has a `Proof:` entry naming its
  test, and its verification has a `Report:`; `proposal` shows that
  requirement next to the criteria check (see [build](build.md)). With
  `risk: low`, a criterion under `Tests:` whose test named in `Proof:`
  passed needs no reviewer verdict (see [risk](spec.md#risk)).
- `scope` names the files the tasks will change, with the glob syntax of the
  [contract rules](../reference/contract-rules.md#globs): `**` crosses
  directories, `*` does not. With `strict_scope: true`, the default, or
  `risk: high`, a plan without `scope`, or with globs that together match
  every path (`**`, `**/*`, `*` with `*/**`), is an error that blocks the
  approval, so you see the scope before you approve. A touched file outside
  it, a deletion included, is an error (a warning with `strict_scope: false`
  and a risk other than `high`); the review
  packet lists them whenever it is written. The skills and permission rules
  AtipSpec installs do not count while they hold only its content; removing one
  of those rules counts. Unforeseen work widens `scope` in the same edit that
  adds its task, and a wider scope changes what you approved, so it is
  presented to you again.

## Tasks, not stories

A task is one coherent change that leaves the project working, recorded with
`task-done` when it is implemented. Tasks run in sequence inside a delivery, and above
`max_tasks` the plan is too big for a working day: `check` warns and the
model proposes an initiative. Work you want to
run in parallel across people belongs in separate deliveries; see
[teams and scale](../teams.md).
