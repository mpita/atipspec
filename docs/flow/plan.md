# plan

**From a ready spec to tasks the gate can prove.** The phase where
architecture compliance is decided.

| | |
| --- | --- |
| Role | The one who has to maintain this in a year. Prefers the simplest shape inside the contract, reuses what exists, tells you the choices with consequences before making them. |
| Who decides | You, with `atipspec accept <slug> plan`, when `approve_plan: true` in `config.yaml` (the default). |
| Produces | `plan.md`: approach and tasks |

## How to run it

```text
/atipspec-plan password-reset
```

The skill runs `atipspec plan password-reset`, which refuses while the spec is
not ready and otherwise prints the workflow, the rules and the context.

## What the model does

1. Reads the context the command printed, and the code areas involved.
2. Checks the contract. If the spec needs something the contract forbids, it
   stops: that needs a [decision](contract.md#changing-the-contract), never a
   workaround.
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

Covers: REQ-001
Verify:
- `python -m pytest -q tests/auth/test_reset.py`

### T2: Expire links after 30 minutes

Covers: REQ-002
Verify:
- `python -m pytest -q tests/auth/test_reset.py`
- `python -m pytest -q`
```

4. `atipspec check password-reset` until there are no plan errors.
5. Shows you the plan if `approve_plan` is on and asks you to run
   `atipspec accept password-reset plan`; `atipspec build` refuses until
   then. A task added during the build changes the plan, so you accept it
   again.

## What `check` requires from a plan

- Every active requirement is covered by at least one task (`Covers:`), and
  every criterion is listed once under `Tests:` or `Manual:`, following its
  `[manual]` mark in the spec; until then `atipspec build` refuses.
- Every `require-command` of the contract appears in at least one task's
  `Verify:`.
- Commands are real commands of the project. `verify` will run them from the
  project root through the shell.
- `Verify: none` is allowed when the only proof is observation, with a note
  of what the reviewer must observe.
- `scope` names the files the tasks will change, with the glob syntax of the
  [contract rules](../reference/contract-rules.md#globs): `**` crosses
  directories, `*` does not. A touched file outside it, a deletion included,
  is a warning in `check` and an error with `strict_scope: true`; the review
  packet lists them whenever it is written. Unforeseen work widens `scope` in
  the same edit that adds its task.

## Tasks, not stories

A task is one coherent change that can be committed on its own and leaves the
project working. Tasks run in sequence inside a delivery, and above
`max_tasks` the plan is too big for a working day: `check` warns and the
model proposes an initiative. Work you want to
run in parallel across people belongs in separate deliveries; see
[teams and scale](../teams.md).
