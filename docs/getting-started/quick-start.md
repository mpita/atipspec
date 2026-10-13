# Quick start

One change, from your side of the conversation. You make three decisions: the
contract, once per project; the proposal of each change; and its reviewed
result. The assistant runs every command below and records each decision with
`atipspec accept --code <code>`, the code of the view it showed you; Claude
Code, opened at the project root, asks you before that command runs. The examples use Claude Code; the
[clients page](../clients.md) shows the equivalent in the others. The
[guided delivery](../flow/guided.md) page has every step in detail.

## 1. Define the contract

The first thing to do in a project is the **contract phase**. Open a session
in the project and say:

```text
/atipspec-contract
```

The skill runs `atipspec contract`, which prints the workflow and the current
contract. The model records what you already decided (say, Django and
PostgreSQL) as decisions, asks only what affects the rules, fills
`.atipspec/contract.md` and writes the rules the CLI will check:

```text
dependencies pyproject.toml django psycopg "pytest*"
forbid-pattern "shop/domain/**" "from shop\.infrastructure"
require-command "python -m pytest -q"
```

The assistant checks the repository against it and presents it with the
decisions it includes and an approval code. Approve it in the conversation;
the assistant records your approval with that code:

```bash
atipspec audit
atipspec proposal contract
atipspec accept contract --code 11HN-G0QN
git add .atipspec && git commit -m "chore: architecture contract"
```

Until the contract's acceptance is recorded, `atipspec check` warns about it.

## 2. Ask for the change

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

The assistant creates the delivery on its own branch:

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

`new` creates `.atipspec/deliveries/password-reset/` with `spec.md`, `plan.md`,
`deferred.md` and `baseline.json`, records the current commit as the
delivery's base, and switches to the branch `delivery/password-reset`. Then the
skill runs `atipspec spec password-reset`, which prints the **spec phase**:
its workflow, the rules and exactly the context the delivery needs.

The model interviews you in rounds of at most three questions, then writes the
requirements and their scenarios in the living spec, `.atipspec/specs/auth.md`,
with IDs from `atipspec ids auth`:

```markdown
### REQ-AUTH-7KQ2M-001: The user can request a reset link

#### AC-AUTH-7KQ2M-001: Registered email
- **WHEN** a user requests a reset for the registered email "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds
```

In the delivery's `spec.md` it lists those IDs under `requirements` and writes
the intent, what is out of scope and the quality limits. A vague outcome, such
as "works correctly", blocks the proposal.

## 3. Approve the proposal

The model prepares the approach and how each scenario is tested, in
`plan.md`, and presents everything together:

```bash
atipspec proposal password-reset
```

The view shows the scenarios, the scope, the approach, the tests, the risk
level, the diff of the living spec and the approval code. This is **stop point
1**: read it, then request changes or approve in the conversation. The
assistant records your approval with the code it presented:

```bash
atipspec accept password-reset proposal --code K7M2-QX4P
```

Claude Code, opened at the project root, asks you before that command runs.
It sets `status: ready` and
records what you approved and through which channel; if anyone edits the
scenarios, the approach or the tests afterwards, the gate names what changed
and asks you again.

## 4. Build and review

```text
/atipspec-ship password-reset
```

`atipspec ship password-reset` names the next phase the delivery can enter,
and each phase command refuses while a required step is missing. Ship mode
runs the remaining phases without pausing until the result:

- **build**: code and tests, task by task, each recorded with `atipspec
  task-done password-reset T1 --note "..."`; then `atipspec verify
  password-reset` runs the final checks once on the finished candidate.
- **review**: `atipspec review password-reset` writes a packet; a reviewer in
  an isolated session writes `review.md` with one verdict per criterion, each
  pointing to a test that passed, a `file:line` or a `file::test`.

Watch it from another terminal at any time:

```bash
atipspec status password-reset
```

```text
password-reset  [in_progress]  tasks 1/2
  todo    T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
  todo    FINAL: no evidence; run `atipspec verify password-reset`
  todo    No review.md: run `atipspec review password-reset` and give the packet to a reviewer in an isolated session
  info    lead time 3h: since creation, until the result is accepted
  info    risk normal: every criterion needs a reviewer verdict
  info    Local mode: acceptance records detect drift; identity and evidence provenance are not externally authenticated
Next: T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
```

## 5. Accept the result

When `atipspec check password-reset` is green, the delivery is `checked`. The
assistant presents the result:

```bash
atipspec report password-reset
```

The dossier shows each criterion with its evidence and the reviewer's
verdict, and every file changed since the base commit with the diff, and the
result's approval code. This is **stop point 2**: inspect it and accept or
request changes. The assistant records your acceptance and archives the
delivery:

```bash
atipspec accept password-reset result --code 3C1Q-4VN7
atipspec deliver password-reset
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Result archived. Commit, merge and deployment follow the repository's explicit policy.
```

`deliver` does not commit, push or merge. Before the merge, the assistant runs
`atipspec merge-check --base <target>`, which confirms that the delivery is
accepted and the code is still the code you accepted; after `deliver`, a later
change reopens the delivery (see
[deliver](../flow/deliver.md#after-deliver-the-code-is-fixed)). Organizations
that need authenticated approvals configure [trusted
acceptance](../enterprise.md) instead of the local records.

## What you just got

- Scenarios you approved, kept in the living spec of the `auth` capability.
- Evidence files with the exact commands, exit codes and tree hash of the
  final verification.
- A review with a verdict per criterion, each pointing to proof the gate
  resolves, and the session the reviewer declares: `check` warns when the
  reviewer saw the author's conversation, and blocks it at `risk: high` or
  with `require_isolated_review`.
- A record of each decision, bound to the content you saw, and a contract
  enforced on every file the delivery touched.

Next: [how it works](how-it-works.md), or the [flow](../flow/index.md) phase
by phase.
