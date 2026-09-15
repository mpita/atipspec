# build

**From plan to code, evidence and commits.** Task by task.

| | |
| --- | --- |
| Role | The one who signs the commit. Small changes, tests that exercise the criteria, the conventions of this codebase. Says it now when a criterion cannot be met. |
| Who decides | The developer, with the model. |
| Produces | code and tests, `evidence/*.json`, one commit per task |

## How to run it

```text
/atipspec-build password-reset
```

The skill runs `atipspec build password-reset`, which refuses without a valid
plan and otherwise prints the workflow, the rules, the context and the next
task that has no commit. After each commit, `atipspec build password-reset
--no-context` names the following one.

## The loop, for each task

1. Read the task, its requirements and criteria, the contract sections it
   touches, the code.
2. Make the smallest change that satisfies the criteria within the contract.
   Add or update tests so the Verify commands actually exercise the criteria.
3. Run the evidence:

    ```bash
    atipspec verify password-reset --task T1
    ```

    ```text
    [T1] $ python -m pytest -q tests/auth/test_reset.py
        3 passed in 0.21s
    [T1] ok (0.6s)
    T1: pass -> .atipspec/deliveries/password-reset/evidence/T1-20260913T154145Z-3f9a1c2e.json
    ```

4. When the test framework writes JUnit XML, name the file in the task's
   `Report:` and each criterion's test under `Proof:`; `verify` copies the
   report next to the evidence and `check` requires the named test to have
   run and passed:

    ```markdown
    ### T1: Request a reset link

    Covers: REQ-001
    Tests: AC-001, AC-002
    Report: .atipspec/tmp/junit.xml
    Proof:
    - AC-001: tests/auth/test_reset.py::test_registered_email_sends_link
    - AC-002: tests/auth/test_reset.py::test_unknown_email_same_response
    Verify:
    - `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
    ```

    A test id is the case's name, `Class.name`, `module.Class.name` or
    `path/to/file.py::Class::name`. Without `Proof:`, a criterion under
    `Tests:` is proven by the reviewer, as before.

5. Commit with the marker in the message, evidence included:

    ```bash
    git add -A
    git commit -m "feat(auth): request password reset link [password-reset:T1]"
    ```

6. `atipspec status password-reset` and on to the next task.

## What makes a task done

A commit in the current branch whose message carries `[<slug>:Tn]`. Nothing
else. Not a checkbox, not a sentence from the model. Several ids in one marker
are fine: `[password-reset:T1,T2]`.

## What the evidence contains

```json
{
  "delivery": "password-reset",
  "task": "T1",
  "result": "pass",
  "tree": "cd03ae507b3605b12a497fcbcf590894a0073076",
  "head": "9f2c1e4...",
  "started": "2026-09-12T15:41:45Z",
  "finished": "2026-09-12T15:41:46Z",
  "commands": [
    {"command": "python -m pytest -q tests/auth/test_reset.py", "exit_code": 0,
     "duration_s": 0.58, "output_tail": "3 passed in 0.21s"}
  ]
}
```

`tree` is the fingerprint of the working tree the commands ran against. The
gate accepts the evidence only while the tree still matches. With a
`Report:`, the file also carries `reports` (the copy under `evidence/logs/`
with its hash) and `tests` (every case with its status), and altering the
copy is detected like an altered command log. If a command
modifies the tree (a formatter, a generated file), `verify` says so and the
evidence is already stale: commit or discard and run it again.

## Rules

- Never touch `evidence/` by hand.
- Unforeseen work becomes a new task with `Covers` and `Verify`, never hidden
  inside another; a file outside the plan's `scope` is added to `scope` in the
  same edit that adds the task that needs it.
- No refactoring beyond the task.
- A contract violation reported by `check` is fixed in the code or escalated
  as a decision, never silenced.
- If a criterion cannot be met, stop and tell the user before changing the
  spec.
- Real output only. If a command could not run in this environment, say so.
