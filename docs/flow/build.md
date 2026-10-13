# build

**From the approved plan to code, task records and evidence.** Task by task,
then one final verification.

| | |
| --- | --- |
| Role | The implementer. Small changes, tests that exercise the criteria, the conventions of this codebase. Says it now when a criterion cannot be met. |
| Who decides | The developer, with the model, within the approved agreement. |
| Produces | code and tests, `progress.json` with the tasks recorded as implemented, `evidence/*.json` |

## How to run it

```text
/atipspec-build password-reset
```

The skill runs `atipspec build password-reset`, which refuses until the
proposal is accepted for its current content and otherwise prints the
workflow, the rules, the context and the next task not yet recorded. After
each task, `atipspec build password-reset --no-context` names the following
one.

## The loop, for each task

1. Read the task, its requirements and scenarios, the contract sections it
   touches, the code.
2. Make the smallest change that satisfies the scenarios within the contract
   and the plan's `scope`. Add or update tests so they exercise the criteria;
   run focused tests while you work, or the task's own `Verify:` with
   `atipspec verify password-reset --task T1`.
3. Record the task:

    ```bash
    atipspec task-done password-reset T1 --note "request() sends the link to registered emails only"
    ```

    ```text
    AtipSpec: T1 of password-reset recorded as implemented (progress, not verification) in .atipspec/deliveries/password-reset/progress.json
    Next: T2 is not complete: implement it and record `atipspec task-done password-reset T2 --note <summary>`
    ```

4. On to the next task. Commits follow your repository's policy; AtipSpec
   requires none.

## What makes a task done

A record `atipspec task-done` writes in `progress.json`: the note, the time,
the hash of the approved agreement and of the task without its title. It is
the assistant's declaration of progress, never proof: the final verification
and the review check the work. It refuses before the proposal is approved,
and a record stays valid while the approved agreement and the task are
unchanged; renaming the task keeps it. A [legacy
delivery](../reference/legacy.md#task-completion) also counts a commit marker
`[<slug>:Tn]`.

## The final verification

When every task is recorded, the candidate is finished:

```bash
atipspec verify password-reset
```

```text
[FINAL] $ python -m pytest -q --junitxml .atipspec/tmp/junit.xml
    4 passed in 0.31s
[FINAL] ok (0.9s)
[FINAL] report .atipspec/tmp/junit.xml: 4 test(s), 0 failed
FINAL: pass -> .atipspec/deliveries/password-reset/evidence/FINAL-20260913T154145.218304Z-3f9a1c2e.json
```

It runs the plan's `## Final verification` commands once and writes the
evidence. When the test framework writes JUnit XML, the plan names the file
in `Report:` and each criterion's test under `Proof:`; `verify` copies the
report next to the evidence and `check` requires each named test to have run
and passed. The Verify command itself writes the report, at a path git
ignores:

```markdown
## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
- AC-AUTH-7KQ2M-002: tests/auth/test_reset.py::test_unknown_email_same_answer
Verify:
- `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
```

A test id is the case's name, `Class.name`, `module.Class.name` or
`path/to/file.py::Class::name`. When it names several cases (a parametrized
test, or the same name in several classes), all of them must pass. Without
`Proof:`, a criterion under `Tests:` is proven by the reviewer, unless the
project sets `require_proof: true` (or the trust policy does), or the delivery
sets `risk: high`: then every criterion under `Tests:` needs its `Proof:`
entry and the verification needs a `Report:`, an error that blocks the
proposal until the plan names them.

Only a report this run writes counts. Before the commands run, `verify`
deletes the file named in `Report:`; afterwards the file must exist and be
modified after that deletion (two seconds of tolerance), or the evidence fails
with `test report not found` or `predates this verification`. That is why the
path must be one git ignores, such as `.atipspec/tmp/junit.xml`: a committed or
hand-written report is the one that could stand in for a run, and `check`
reports a `Report:` at a path git does not ignore as a plan error. Never point
`Report:` at a file you keep: `verify` deletes it.

If the code changes after the final verification, run it again on the
finished candidate. Then `atipspec review password-reset`.

## What the evidence contains

```json
{
  "delivery": "password-reset",
  "task": "FINAL",
  "result": "pass",
  "tree": "cd03ae507b3605b12a497fcbcf590894a0073076",
  "head": "9f2c1e4...",
  "started": "2026-09-12T15:41:45Z",
  "finished": "2026-09-12T15:41:46Z",
  "commands": [
    {"command": "python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml", "exit_code": 0,
     "duration_s": 0.58, "output_tail": "4 passed in 0.31s",
     "output_path": "logs/FINAL-5d0c...-1.log", "output_sha256": "8a1f..."}
  ]
}
```

`tree` is the fingerprint of the working tree the commands ran against. The
gate accepts the evidence only while the tree still matches. Renaming a task
in `plan.md` (the text after `### T1:`) is the one change it tolerates: the
evidence and the review stay valid, and in a guided plan with a final
verification, whose approval leaves the tasks out, the task stays complete
too: the fingerprint reads each task heading reduced to its id, so this holds
in a fresh clone too, such as CI. With a `Report:`, the file also
carries `reports` (the copy under `evidence/logs/` with its hash, the path it
was read from and `fresh: true`) and `tests` (every case with its status), and
altering the copy is detected like an altered command log. Evidence with a
report written by AtipSpec 0.2.x has no `fresh` mark: `check` asks to verify
again. If a command
modifies the tree (a formatter, a generated file), `verify` says so, exits 1
and the evidence is already stale: keep or discard the change, then run it
again.

## Rules

- Never touch `evidence/` by hand.
- `check` never runs the tests: `verify` is the only command that executes
  them, and the gate judges the evidence it wrote.
- Unforeseen work becomes a new task with `Covers` and `Tests` or `Manual`,
  never hidden inside another; a file outside the plan's `scope` is added to
  `scope` in the same edit that adds the task that needs it, and a wider scope
  goes back to you as a changed proposal.
- No refactoring beyond the task.
- A contract violation reported by `check` is fixed in the code or escalated
  as a decision, never silenced.
- If a criterion cannot be met, stop and tell the user before changing the
  spec.
- Real output only. If a command could not run in this environment, say so.
