# review

**A reviewer that did not write the code writes `review.md`.** One
adversarial pass, in a fresh context, bound to the tree.

| | |
| --- | --- |
| Role, driver side | The author handing over. Does not argue inside the reviewer's context, never edits `review.md`. Fixes, verifies, commits, asks again. |
| Role, reviewer side | Adversarial. Judges against the spec and the contract, one verdict per criterion, with a pointer to the proof. |
| Who decides | `atipspec check`. |
| Produces | `review.md` |

## How to run it

```text
/atipspec-review password-reset
```

## What happens

1. The model runs `atipspec review password-reset`. The CLI refuses while a
   task has no commit, evidence is stale or the contract is violated, and
   writes no packet. Otherwise it writes a packet to
   `.atipspec/tmp/password-reset-review-packet.md` with: the rubric, the
   architecture contract, the living specs the delivery declares in its
   impact list, the accepted decisions that affect them, the spec, the plan,
   deferred items, an evidence summary, the files changed outside the plan's
   `scope`, and the diff against the delivery's base commit plus untracked
   files. A diff over 200 KB is replaced by its `--stat` and a truncated
   excerpt, with a note telling the reviewer to inspect the repository. Then
   the command prints the workflow.
2. The model launches the reviewer **in a context that has not seen the
   conversation**, giving it only the packet path. In Claude Code this is a
   subagent; see [clients](../clients.md) for the others.
3. The reviewer reads the packet, inspects the repository, runs commands if
   reading is not enough, and writes:

```markdown
---
tree: cd03ae507b3605b12a497fcbcf590894a0073076
reviewer: claude-code subagent
---

# Review: Password reset

## Criteria

- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. tests/auth/test_reset.py::test_unknown_email_same_response
- AC-003: FAIL. consume() checks the age but the boundary of exactly 30 minutes is accepted.

## Findings

- F1 [blocker]: shop/domain/reset.py imports shop.infrastructure.mail, forbidden by the contract.
- F2 [minor]: request() lacks a docstring.

## Notes

The spec does not say whether a used link may be reused; assumed no.
```

4. The model runs `atipspec check password-reset`:
    - A `FAIL` or a `blocker`: fix the code, verify, commit. Any change to the
      tree makes the review stale, so it runs `review` and the reviewer
      again.
    - A finding you decide not to fix now goes to `deferred.md` with a
      reason: `- F2: cosmetic, handled in the docs cleanup delivery`.
      Criteria can never be deferred.
5. After `review_rounds` rounds (default 2) without a green check, the model
   stops and reports what remains. You decide.

## Why a separate context

The context that wrote the code will confirm it. The reviewer's verdicts are
the only ones the gate accepts, and the gate rejects them as soon as the code
changes. A contract violation is always a blocker.

Blocker and major findings require resolution or a trusted risk exception.
Local green is `checked`; [trusted acceptance](../enterprise.md) is required for
`verified` and `deliver`. QA approval binds the review, exceptions and signed evidence.
