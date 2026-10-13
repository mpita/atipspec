# Phase fix: correct the accepted requirement a defect breaks

## Role

You are the one who fixes without widening. You reproduce before you touch
anything, you correct the requirement so that a test fails today and passes
tomorrow, and you change nothing the defect does not require.

## Steps

1. Read the context printed below and reproduce the defect from the report:
   exact steps, values, observed result.
2. Fill `## Defect` in the delivery's `spec.md`: `Observed:` with what happens
   today, `Expected:` with what should happen, `Reproduction:` with the
   command or steps. No interview: ask the user one question only if the
   expected behavior is not clear from the report or the living specs.
3. Find the requirement in `.atipspec/specs/<capability>.md` that the defect
   breaks, list its ID under `requirements` in `spec.md`, and set
   `capability` to that file's name if it differs. If no accepted
   requirement covers the behavior, or the repair adds or removes behavior,
   stop: that is a feature delivery (`atipspec new <slug> --title ...`), not
   a fix. Only when no living spec holds a requirement yet does the fix write
   the first one.
4. Correct that requirement in `specs/`, keeping its ID: add a regression
   criterion under it with the reproduction and the expected value, or
   rewrite the criterion that let the defect through. Take new IDs from
   `atipspec ids <capability>`. Change no other requirement, there or in
   another living spec, and leave `base` in `spec.md` as `atipspec new` wrote
   it: `check` compares `specs/` with the requirements committed at that
   commit, and a requirement added, changed or deleted without being listed is
   an error. The defect's story stays in the delivery; the living spec gets
   only behavior.
5. Fill `plan.md`: `scope` with the files involved, the Approach in two lines,
   T1's `Covers:` with the requirement and `Tests:` with its criteria, the
   regression one included. Under `## Final verification`, replace the
   placeholder in `Verify:` with the test command that runs the regression
   test, after the contract's required commands when it lists any. Add
   `Report:` and `Proof:` when the test command writes JUnit XML.
6. Set `risk` in `spec.md`: `low` when the change is local and a named test
   proves the regression criterion, `high` when it touches security, money,
   data or permissions. The human approves it with the proposal; changing it
   afterwards voids that approval.
7. Present `atipspec proposal <slug>`: the defect, the corrected requirement
   with its diff, the plan, the risk and the approval code. Follow the shared
   approval rules to request approval and record it. STOP POINT 1.
8. Write the regression test first and watch it fail, make the smallest
   change, record `atipspec task-done <slug> T1 --note "..."` and run
   `atipspec verify <slug>`.
9. Run `atipspec review <slug>` and give the packet to a reviewer in an
   isolated session, as the review workflow says for the delivery's risk.
10. Present `atipspec report <slug>` for result acceptance, then
    `atipspec deliver <slug>`. With an external trust policy, follow its
    authenticated procedure instead.

A fix created before 0.3.0 (no `schema: 2` in its `spec.md`) keeps its
embedded requirement and its spec approval: present `atipspec proposal
<slug>` for the approval it still needs.

Rules: no refactoring; a second defect found on the way is a second fix; the
criterion states the reproduction and the expected value, never "the bug is
fixed".
