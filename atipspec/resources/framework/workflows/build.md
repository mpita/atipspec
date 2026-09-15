# Phase build: from plan to code, evidence and commits

## Role

You are the one who signs the commit. Small changes, tests that exercise the
criteria, the conventions of this codebase, and when the code cannot meet a
criterion you say it now instead of resolving it on your own.

## Steps, for the task named below, then the next

1. Read the task, the REQs it covers with their criteria, the contract sections
   it touches, and the code.
2. Make the smallest change that satisfies the criteria within the contract.
   Add or update tests so the Verify commands exercise the criteria. When the
   test framework can write JUnit XML, make a Verify command write it, name
   it in the task's `Report:` and list each criterion's test under `Proof:`;
   the gate then checks that the named test ran and passed.
3. `atipspec verify <slug> --task Tn`. Read the output. Fix until it passes.
   Never touch evidence/.
4. Commit with `[<slug>:Tn]` in the message, for example
   `feat(auth): request reset link [password-reset:T1]`, evidence included.
5. `atipspec build <slug> --no-context` names the next task.

Rules: unforeseen work becomes a new task with Covers and Verify, never hidden
inside another, and a file outside `scope` is added to `scope` in the same
edit that adds the task that needs it; no refactoring beyond the task; a contract violation reported
by `check` is fixed in the code or escalated as a decision, never silenced; if
a criterion cannot be met, stop and tell the user before changing the spec;
report real output, and say so when a command could not run.

When every task is committed, `atipspec review <slug>` writes the reviewer
packet; until then it refuses.
