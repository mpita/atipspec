# Quick start

Start with local specification and verification, then configure trusted acceptance. The examples use
Claude Code; the [clients page](../clients.md) shows the equivalent in the
others.

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

Check the repository against it, accept it when you agree, and commit:

```bash
atipspec audit
atipspec accept contract
git add .atipspec && git commit -m "chore: architecture contract"
```

Until the contract is accepted, `atipspec spec` refuses to start a delivery.

## 2. Start a delivery

```bash
atipspec new password-reset --title "Password reset" --capability auth --owner ana --branch
```

This creates `.atipspec/deliveries/password-reset/` with `spec.md`, `plan.md`
and `deferred.md`, records the current commit as the delivery's base, and
switches to the branch `delivery/password-reset`.

## 3. Spec it, and approve it

```text
/atipspec-spec password-reset: users should be able to reset a forgotten password by email
```

The skill runs `atipspec spec password-reset`, which prints the **spec
phase**: its workflow, the rules and exactly the context the delivery needs.
The model interviews you in short batches and writes requirements with
acceptance criteria:

```markdown
### REQ-001: The user can request a reset link

Acceptance criteria:
- AC-001: A request with a registered email sends a link to that email.
- AC-002: A request with an unknown email responds like a valid one.
```

When the gate says the spec is complete, the model presents it and waits.
This is **stop point 1**: read it, correct it, and accept it yourself:

```bash
atipspec accept password-reset spec
```

That sets `status: ready` and records what you accepted; if anyone edits the
spec afterwards, the gate asks you again. The model never runs this command.

## 4. Plan, build, review

```text
/atipspec-ship password-reset
```

`atipspec ship password-reset` names the next phase the delivery can enter,
and each phase command refuses while a required step is missing. Ship mode
runs the remaining phases without pausing, except where you asked it to:

- **plan**: approach and tasks, each with the requirements it covers and the
  commands that prove it. If `approve_plan` is on, it shows you the plan and
  waits for `atipspec accept password-reset plan`.
- **build**: task by task. Code, tests, `atipspec verify`, one commit per
  task carrying `[password-reset:T1]`.
- **review**: `atipspec review` writes a packet; a reviewer in a fresh
  context writes `review.md` with one verdict per criterion.

Watch it from another terminal at any time:

```bash
atipspec status password-reset
```

```text
AtipSpec: shop (en)
git: branch delivery/password-reset
contract: accepted
living specs: none
- password-reset [in_progress] tasks 1/2 @ana, open 3h: Password reset
    accepted: spec accepted by ana@example.com at 2026-09-13T12:39:09Z (current)
    accepted: plan accepted by ana@example.com at 2026-09-13T13:02:41Z (current)
    next: T2 is not committed: build it, run `atipspec verify password-reset --task T2` and commit with [password-reset:T2]
```

## 5. Deliver

A green local check means `checked`. Configure [trusted acceptance](../enterprise.md),
collect product/engineering approvals before CI verification, obtain the CI
attestation and QA approval, then run:

```bash
atipspec check password-reset --policy /secure/company.toml
atipspec deliver password-reset --policy /secure/company.toml
```

The requirements are merged into `.atipspec/specs/auth.md`, the folder moves
to `.atipspec/archive/`, and the model asks you to merge the branch. This is
**stop point 2**.

## What you just got

- A spec you approved, kept forever in the living spec of the `auth`
  capability.
- Evidence files with the exact commands, exit codes and tree hash for every
  task.
- A review by a context that never saw the author's reasoning.
- A commit per task, and a contract that was enforced on every file the
  delivery touched.

Next: [how it works](how-it-works.md), or the [flow](../flow/index.md) phase
by phase.
