# fix

**From a defect report to the accepted requirement it breaks, corrected, a
one-task plan and the same gate.** No interview and no contract to accept
first; one proposal approval, and no shortcut on evidence or review.

| | |
| --- | --- |
| Role | The one who fixes without widening. Reproduces first, corrects the requirement so that a test fails today and passes tomorrow, changes nothing the defect does not require. |
| Who decides | You approve the proposal in the conversation: the defect, the corrected requirement and the plan; the assistant records it with `atipspec accept <slug> proposal --code <code>`, the code `atipspec proposal <slug>` showed. **Stop point 1.** Then you accept the result, as for any delivery. |
| Produces | the requirement in `specs/<capability>.md` corrected, `spec.md` with the defect, `plan.md` with one task, code, evidence |

## How to run it

```bash
atipspec new bug-123 --title "Reset link never expires" --capability auth --ticket SHOP-9 --kind fix
```

```text
/atipspec-fix bug-123: a reset link created yesterday still works
```

The skill runs `atipspec fix bug-123`, which refuses on a delivery that is
not a fix, and otherwise prints the workflow, the rules and the context. A
fix, like a feature delivery, does not need the contract's acceptance to
start; while the contract is not accepted, `check` shows a warning.

## What `new --kind fix` creates

A guided delivery (`schema: 2`), like a feature, with `kind: fix`,
`requirements: []`, `risk: normal` and `baseline.json`, which records the
commit it starts from; `new` refuses while the capability's living spec has
changes not committed. Its `spec.md` holds the defect, not a requirement:

```markdown
---
title: "Reset link never expires"
status: draft
kind: fix
capability: auth
ticket: SHOP-9
schema: 2
requirements: [REQ-002]
risk: normal
---

# Reset link never expires

## Defect

Observed: a link created 26 hours ago still opens the reset form.

Expected: the page shows "link expired", as REQ-002 states.

Reproduction: `python -m pytest tests/auth/test_reset.py -k expired`
```

The plan has one task, `T1: Regression test and fix`, and a
`## Final verification` whose `Verify:` lists every `require-command` of the
contract and a placeholder for the command that runs the regression test.

## What the model does

1. Reproduces the defect and fills `## Defect`: `Observed:` and `Expected:`
   are required, `Reproduction:` is advised.
2. Finds the requirement the defect breaks in `.atipspec/specs/auth.md`,
   lists its ID under `requirements`, and corrects it there, keeping its ID:
   it adds a regression criterion under it, or rewrites the criterion that
   let the defect through.

    ```markdown
    ### REQ-002: The link expires

    #### AC-003: Link older than 30 minutes
    - **WHEN** a link issued 31 minutes ago is opened
    - **THEN** the page shows "link expired"

    #### AC-007: Link issued the day before
    - **GIVEN** a link issued 26 hours ago
    - **WHEN** the user opens it
    - **THEN** the page shows "link expired" and sends nothing
    ```

3. Fills the plan: `scope`, the approach, `Covers: REQ-002`, the
   requirement's criteria under `Tests:`, the regression one included, and
   the test command under `Verify:` in place of the placeholder.
4. Proposes the [risk](#risk) in `spec.md`.
5. Presents `atipspec proposal bug-123`, which shows `Kind: fix · Risk: ...`,
   `Corrects: REQ-002 (accepted requirement)` and the diff of the living
   spec against the requirements accepted at the delivery's base commit, and
   asks for your approval.
6. After the approval, writes the regression test, watches it fail, makes
   the smallest change, records `task-done`, runs `verify`, and gives the
   review packet to a reviewer.
7. Presents `atipspec report bug-123` for your acceptance of the result, then
   `deliver` writes the corrected requirement in the living spec. The defect's
   story stays in the archived delivery.

About ten commands: `new`, `fix`, `proposal`, `accept proposal`,
`task-done`, `verify`, `review`, `report`, `accept result`, `deliver`.

## What `check` requires from a fix

- `base` in `spec.md` is the full id of the commit `atipspec new` recorded:
  a commit in the history of `HEAD`, and the head `baseline.json` records. A
  name such as `HEAD` or a branch, or another commit, is an error: a later one
  would leave the commits between the recorded one and it out of the
  comparison, the scope check and the dossier's diff, and an earlier one would
  compare with requirements that were not yet accepted. A delivery migrated
  from a legacy one keeps its earlier base, which may not be later than that
  head.
- `requirements` lists at least one requirement, and each one is among the
  requirements `specs/<capability>.md` held at the delivery's base commit, or
  that reached it since through the integration branch (see
  [teams](../teams.md#when-main-moves)) or a delivery archived in the branch
  after the base, as its receipt records that delivery wrote it: a fix
  corrects a requirement the capability already accepted. The
  working file and `baseline.json` do not change that list, and `capability`
  is the one `spec.md` names, even when `new` was given another.
  A requirement that is not there is an error, since a behavior no
  requirement covers is a feature delivery. Only in a project whose living
  specs held no requirement at the base (an existing project without specs)
  may the fix write the first one, with an info; a fix whose capability has
  none while others do is an error that asks for the right `capability`.
- A fix changes only the requirements it lists, and removes none: a
  requirement added, changed, deleted or marked `[remove]` in its
  capability's living spec without being listed is an error, and so is a
  listed one marked `[remove]` or any requirement changed in another
  capability's living spec, which the proposal also shows as a diff. What the
  integration branch or a delivery archived since the base brought is not the
  fix's change; what a merge of any other branch brings is. When the change is
  committed in the branch, the message says that another change may have made
  it, which then needs a delivery of its own.
- `merge-check` checks the same against the target branch: a fix archived in
  the branch whose requirement was not in the living spec at the merge base,
  nor written by an earlier delivery of the branch, blocks the merge, and so
  does a requirement changed outside the deliveries that list it.
- At least one criterion of the corrected requirements is under `Tests:`:
  the automated regression test.
- `## Defect` states `Observed:` and `Expected:`.
- More than 2 requirements is a warning (`max_requirements` when lower): a
  repair that needs more is not a fix.

Everything else is a guided delivery's: one proposal approval, evidence bound
to the tree, the review in an isolated session (declared in `session:`), your
acceptance of the result, `deliver` and `merge-check`.

## Risk

`risk` in `spec.md` sets how much ceremony the gate asks, for a fix as for
any delivery: `low` for a local repair whose regression test the plan names in
`Proof:`, which then needs no reviewer verdict; `high` for security, money,
data or permissions. You approve it with the proposal; changing it voids that
approval. See [risk](spec.md#risk).

## Fixes created before 0.3.0

A fix without `schema: 2` in its `spec.md` keeps its own flow until it is
archived: it needs the contract's acceptance to start, its embedded
requirement and `accept <slug> spec`, and no plan acceptance. `deliver`
merges its requirement into the living spec as before.
