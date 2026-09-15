# fix

**From a defect report to a regression criterion, a one-task plan and the
same gate.** No interview, no plan acceptance, no shortcut on evidence or
review.

| | |
| --- | --- |
| Role | The one who fixes without widening. Reproduces first, writes the criterion that fails today and passes tomorrow, changes nothing the defect does not require. |
| Who decides | You accept the spec with `atipspec accept <slug> spec`. **Stop point 1.** |
| Produces | `spec.md` with one requirement and one regression criterion, `plan.md` with one task, code, evidence, one commit |

## How to run it

```bash
atipspec new bug-123 --title "Reset link never expires" --capability auth --ticket SHOP-9 --kind fix
```

```text
/atipspec-fix bug-123: a reset link created yesterday still works
```

The skill runs `atipspec fix bug-123`, which refuses on a delivery that is
not a fix or while the contract is not accepted, and otherwise prints the
workflow, the rules and the context.

## What `new --kind fix` creates

A spec with `kind: fix`, `## Intent` naming the defect, one `REQ-001` with
Observed, Expected and Why, and one `AC-001` to fill in EARS form:

```markdown
### REQ-001: Reset link never expires

Observed: a link created 26 hours ago still resets the password.

Expected: a link older than 30 minutes is refused.

Why: auth/REQ-002 in the living spec.

Acceptance criteria:
- AC-001: When a reset link is 31 minutes old, the system returns "link expired" and sends nothing.
```

And a plan with one task, `T1: Fix and regression test`, covering `REQ-001`,
testing `AC-001`, whose `Verify:` already lists every `require-command` of
the contract.

## What differs from a delivery

- No interview: the criterion comes from the report. The model asks one
  question only when the expected behavior is not clear from the report or
  the living specs.
- No plan acceptance, whatever `approve_plan` says: the plan is one task.
- `max_requirements` is 2. A repair that needs more is not a fix.
- If the repair changes a behavior a living spec declares, it is a delivery:
  the model stops and says so.

Everything else is the same: your acceptance of the spec, evidence bound to
the tree, one commit with `[bug-123:T1]`, the review in a fresh context, the
trusted gate and `deliver`.
