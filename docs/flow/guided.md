# Guided delivery, end to end

This page follows one change from the request to the archive: who does what,
which command the assistant runs, what the CLI checks and which files each
step writes. The [quick start](../getting-started/quick-start.md) is the short
version, from your side of the conversation.

## What a guided delivery is

`atipspec new` creates a guided delivery (`schema: 2` in its `spec.md`), for a
feature and, with `--kind fix`, for a [fix](fix.md). Its requirements live in
the capability's living spec, `.atipspec/specs/<capability>.md`; the
delivery's `spec.md` holds what the change is for and what it decides around
them:

- the intent, what is out of scope, the assumptions and the open questions;
- `requirements`, the IDs of the requirements this change adds, changes or
  removes in the living spec;
- `owner`, `ticket`, `initiative` and `depends_on`;
- `base`, the commit `new` started from; `change_id`; `created`, where the
  lead time starts; and `risk`, how much the gate asks.

`new` refuses to start while the capability's living spec has changes not
committed, so the base commit holds it as the change starts from it: the
proposal shows the change as a diff against it, and `check` tells this
delivery's edits from what the integration branch brought. `baseline.json`
records that commit; a delivery created before 0.3.0 keeps comparing with the
living spec it saved there. Deliveries created before 0.2.0, and fixes
created before 0.3.0, keep their requirements inside `spec.md`; see [legacy
deliveries](../reference/legacy.md).

## Three human decisions

| Decision | When | Presented with | Recorded with |
| --- | --- | --- | --- |
| The contract and the decisions it includes | once per project, and when the contract changes | `atipspec proposal contract` | `atipspec accept contract --code <code>` |
| The proposal: scenarios, approach, tests and risk | **stop point 1**, before any code | `atipspec proposal <slug>` | `atipspec accept <slug> proposal --code <code>` |
| The reviewed result | **stop point 2**, before the archive | `atipspec report <slug>` | `atipspec accept <slug> result --code <code>` |

Nothing else asks for a recorded approval; a decision about a capability that
comes up is approved in the conversation, and the next proposal lists it. You
decide in the conversation: the
assistant presents the view, with its approval code, and offers **Approve and
continue**, **Request changes** or **Cancel** with the client's selector, or
asks for a plain reply. After your explicit approval it runs the `accept`
command with the code of the content it showed you; if that content changed in
the meantime, the command refuses and the assistant presents it again. Claude
Code, configured by `init` and opened at the project root, asks you before
that command runs: the prompt
confirms the same approval, it is not a second one. The record states its
channel, `terminal`, `client-permission` or `assistant` (see
[accept](../reference/cli.md#atipspec-accept)). The contract is not required to
start a guided delivery: while it is not accepted, `check` shows a warning.

## Step by step

| Step | You | The assistant runs | Writes |
| --- | --- | --- | --- |
| 1. Contract | approve it, once | `contract`, `audit`, `proposal contract`, `accept contract` | `contract.md`, `decisions/`, `approvals/contract.json` |
| 2. Create | ask for the change | `new` | `deliveries/<slug>/`: `spec.md`, `plan.md`, `deferred.md`, `baseline.json` |
| 3. Specify | answer the questions | `spec`, `ids`, `check`, optionally `spec-bind` | `specs/<capability>.md`, `spec.md` |
| 4. Plan | | `plan`, `check` | `plan.md` |
| 5. Proposal | approve it: **stop point 1** | `proposal`, `accept <slug> proposal` | `approvals/local-proposal.json`, `status: ready` |
| 6. Build | | `build`, `task-done` | code and tests, `progress.json` |
| 7. Verify | | `verify` | `evidence/` |
| 8. Review | | `review`; a reviewer in an isolated session | `review-rounds.json`, `review.md` |
| 9. Result | accept it: **stop point 2** | `check`, `report`, `accept <slug> result` | `approvals/local-result.json` |
| 10. Deliver | decide the commit and the merge | `deliver`, `merge-check` | the living spec, `reports/acceptance.json`, `archive/<slug>/` |

### 1. The contract

Once per project, the [contract phase](contract.md) writes
`.atipspec/contract.md` with the rules the CLI checks, and a decision for each
choice you already made. The assistant runs `atipspec audit`, presents
`atipspec proposal contract` and, after your approval, records `atipspec accept
contract --code <code>`, which sets the contract and the decisions it lists to
`accepted` and writes `.atipspec/approvals/contract.json`.

### 2. Create the delivery

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

`new` writes `spec.md` with `status: draft`, `base` (the full id of the current
commit), `requirements: []` and `risk: normal`; a `plan.md` to fill; an empty
`deferred.md`; and `baseline.json`. `--branch` creates and switches to
`delivery/password-reset`, `--worktree` does it in a sibling folder; work on
one branch per delivery (see [teams](../teams.md)). `--ticket` links a ticket;
`--depends-on` names a delivery whose accepted receipt must be in the archive
before this one's check turns green.

### 3. Specify

`/atipspec-spec password-reset: <what you want>` runs `atipspec spec
password-reset`, which prints the workflow, the rules and the context. The
assistant reads the code and the living specs, asks only what stays open, in
rounds of at most three questions, and writes the requirements and their
scenarios in the living spec. It takes an ID prefix once per delivery:

```bash
atipspec ids auth
```

```text
auth/REQ-AUTH-7KQ2M-001 auth/AC-AUTH-7KQ2M-001
Number further requirements and criteria of this delivery with the same prefix: -002, -003.
```

```markdown
### REQ-AUTH-7KQ2M-001: The user can request a reset link

Why: support tickets for forgotten passwords are 40% of the queue.

#### AC-AUTH-7KQ2M-001: Registered email
- **GIVEN** a registered user with the email "ana@example.com"
- **WHEN** the user requests a reset for "ana@example.com"
- **THEN** the system answers "Check your email" and sends one reset link to "ana@example.com"

#### AC-AUTH-7KQ2M-002 [manual]: The email reads well on a phone
- **WHEN** the reset email is opened on a 375 px wide screen
- **THEN** the "Reset password" button is visible without scrolling sideways
```

A scenario needs WHEN and THEN, in GIVEN, WHEN, THEN order; AND and BUT extend
the step before. `[manual]` marks one a person observes, `[invariant]` one that
holds without a trigger. `### REQ-... [remove]: Title` retires a requirement
on deliver. The delivery's `spec.md` lists the IDs under `requirements` and
fills `## Intent`, `## Out of scope` and `## Quality attributes` (`- None` when
nothing applies). An authored document, or a list of acceptance criteria,
goes in with `atipspec spec-bind password-reset --file <path>`, which writes
the living spec and the IDs and approves nothing.

`atipspec check password-reset` lists what is missing and what the lint
flags; a vague outcome, such as "works correctly", blocks the proposal. See
[spec](spec.md) and [writing criteria](../reference/spec-quality.md).

### 4. Plan

The plan can start before the approval: `atipspec plan password-reset` opens
once the scenarios are complete, the intent is stated and no question is
open. The assistant writes `plan.md`:

```markdown
---
scope: ["src/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

A `request_reset(email)` function in `src/auth/reset.py` that answers the same
message for every email and sends the link only to registered ones.

## Tasks

### T1: Request a reset link

Covers: REQ-AUTH-7KQ2M-001
Tests: AC-AUTH-7KQ2M-001
Manual: AC-AUTH-7KQ2M-002

## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
Verify:
- `python -m pytest -q --junitxml .atipspec/tmp/junit.xml`
```

Every listed requirement is covered by a task, every criterion is under
`Tests:` or `Manual:`, and every `require-command` of the contract runs in the
final verification. See [plan](plan.md).

### 5. The proposal: stop point 1

```bash
atipspec proposal password-reset
```

The view shows the kind and the risk with what the level asks, how strictly
the criteria are checked, what the evidence and the review need, the change's
intent, the requirements with their scenarios, the plan, and the diff of the
living spec against the base commit, with the approval code. When something
blocks, it lists it under "Not ready for approval" and shows no code. After
your approval the assistant records:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

It sets `status: ready` and writes `approvals/local-proposal.json` with the
hash of what you approved: `spec.md` but its `status` and `ticket`, each
requirement it lists from the capability's living spec, `baseline.json`,
the plan's scope, approach and final verification, `contract.md`,
`config.yaml` but its `exempt_paths`, `adapter.json`, the capability's owners
and `integration` from `teams.json`, and `contracts.json`. Editing any of them
sends the delivery back to `draft`, and `check` names what changed. Tasks
added or split inside the plan do not, since the final verification covers
them; another delivery integrated from main does not either (see [when main
moves](../teams.md#when-main-moves)).

### 6. Build

`atipspec build password-reset` refuses until the proposal is accepted for
its current content, then prints the workflow and the next task. The assistant
implements each task with its tests, within the plan's `scope`, and records
it:

```bash
atipspec task-done password-reset T1 --note "request_reset answers the same message and sends only to registered emails"
```

`task-done` writes `progress.json`: a declaration of progress bound to the
approved agreement, not proof. It refuses before the approval. Commits follow
your repository's policy; none is required. See [build](build.md).

### 7. Verify

```bash
atipspec verify password-reset
```

runs the `## Final verification` commands once on the finished candidate and
writes `evidence/FINAL-<time>.json` with the commands, exit codes, output
logs and the fingerprint of the working tree. With a `Report:`, it deletes
that file first and requires the commands to write it again, and `check`
requires every test named in `Proof:` to have run and passed. Any later change
to the tree makes the evidence stale. `--task T1` runs a task's own Verify
commands, a development check.

### 8. Review

```bash
atipspec review password-reset
```

refuses while a task is not recorded, the evidence is stale or the contract is
violated. Otherwise it counts the review, writes the packet to
`.atipspec/tmp/password-reset-review-packet.md` and prints `review N of M`. A
reviewer in an isolated session, a subagent or a new
session given only the packet, writes `review.md`: `tree`, `reviewer`,
`session`, one PASS or FAIL per criterion with a pointer the gate resolves, and
the findings. Fixes go back through verify and review; `review_rounds` limits
how often. See [review](review.md).

### 9. The result: stop point 2

`atipspec check password-reset` turns `checked` when everything is green.
The assistant presents:

```bash
atipspec report password-reset
```

the dossier: each criterion with its evidence and verdict, the reviewer and
the session, the approvals, and every file changed since the base commit with
the diff, and the result's approval code. After your acceptance:

```bash
atipspec accept password-reset result --code 3C1Q-4VN7
```

writes `approvals/local-result.json`, bound to the tree, the review, the
deferred findings and the evidence. The delivery is `accepted`; the lead time
stops.

### 10. Deliver

```bash
atipspec deliver password-reset
```

merges the requirements into `specs/auth.md` by ID, writes the receipt
`reports/acceptance.json` (with `code_tree`, the hash of everything outside
`.atipspec/`), sets `status: delivered` and moves the folder to
`.atipspec/archive/password-reset/`. It does not commit, push or merge. Before
the merge, `atipspec merge-check --base <target>` confirms that every delivery
the branch touches is accepted and that its code is still the accepted code.
See [deliver](deliver.md).

## Status values

`status` and `check` derive where a delivery is from its files and git:

`draft` → `planned` → `in_progress` → `implemented` → `checked` → `accepted` → `delivered`

| Status | Meaning |
| --- | --- |
| `draft` | the proposal is not accepted for its current content |
| `ready` | accepted, but the plan has no task: in a guided delivery, only when its tasks were removed after the approval |
| `planned` | proposal accepted, no task recorded |
| `in_progress` | some tasks recorded with `task-done` |
| `implemented` | every task recorded, the gate not green yet |
| `checked` | the local gate is green; the result is not accepted |
| `accepted` | the current result's acceptance is recorded; `deliver` may run |
| `delivered` | merged into the living spec and archived |

Under an external trust policy, `verified` replaces `checked` and `accepted`.

## Ship mode and the runner

`/atipspec-ship <slug>` keeps one conversation: `atipspec ship <slug>` names
the next phase the delivery can enter, and the assistant enters it, stopping
at the two stop points, at a material change and at a blocker. `atipspec run
<slug>` executes an approved delivery through a configured process adapter,
with checkpoints and budgets; it never accepts anything. See the [execution
adapter](../reference/execution-adapter.md).

## With an external trust policy

An organization that needs authenticated approvals adds an external trust
policy. The gate then ignores the local records and requires signed product,
engineering and QA approvals and attested CI evidence; success is `verified`,
and `deliver` requires it. With `trust: required` in `config.yaml`, local
acceptance is disabled. See [enterprise acceptance](../enterprise.md).

## What is recorded where

| File | Written by | Holds |
| --- | --- | --- |
| `deliveries/<slug>/spec.md` | `new`, the assistant; `status` by `accept` | the change's intent and decisions, the IDs it lists |
| `specs/<capability>.md` | the assistant, `spec-bind`; `deliver` on archive | the requirements and their scenarios |
| `deliveries/<slug>/baseline.json` | `new` | the living spec when the delivery started |
| `deliveries/<slug>/plan.md` | the assistant | scope, approach, tasks, final verification |
| `deliveries/<slug>/approvals/local-*.json` | `accept` | what you approved, its code, when and the channel |
| `deliveries/<slug>/progress.json` | `task-done` | the tasks recorded as implemented |
| `deliveries/<slug>/evidence/` | `verify` | commands, exit codes, logs, test reports |
| `deliveries/<slug>/review-rounds.json` | `review`, `run` | the reviews counted |
| `deliveries/<slug>/review.md` | the reviewer | verdicts and findings |
| `deliveries/<slug>/run.json` | `run` | the runner's checkpoint |
| `archive/<slug>/reports/acceptance.json` | `deliver` | the receipt `merge-check` reads |

Nobody writes the records under `approvals/`, `evidence/` or `archive/`, or
`review-rounds.json`, by hand; Claude Code's permission rules deny its edit
tools those files. See [artifacts](../reference/artifacts.md).

## Legacy deliveries

Deliveries created before 0.2.0, and fixes created before 0.3.0, keep their
requirements in `spec.md`, approve the spec (and the plan with `approve_plan`)
instead of a proposal, and also complete tasks with commit markers. See
[legacy deliveries](../reference/legacy.md).
