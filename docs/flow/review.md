# review

**A reviewer that did not write the code writes `review.md`.** One
adversarial pass, in an isolated session, bound to the tree.

| | |
| --- | --- |
| Role, driver side | The author handing over. Does not argue inside the reviewer's context, never edits `review.md`. Fixes, verifies, asks again. |
| Role, reviewer side | Adversarial. Judges against the spec and the contract, one verdict per criterion, with a pointer to the proof. |
| Who decides | `atipspec check`. |
| Produces | `review.md` |

## How to run it

```text
/atipspec-review password-reset
```

## What happens

1. The model runs `atipspec review password-reset`. The CLI refuses while a
   task is not complete, evidence is stale or the contract is violated, and
   writes no packet. Otherwise it counts the review (see
   [review rounds](#review-rounds)) and writes a packet to
   `.atipspec/tmp/password-reset-review-packet.md` with: the rubric, the
   delivery's risk and what it asks, the architecture contract, the living specs the delivery declares in its
   impact list, the accepted decisions that affect them, the spec, the plan,
   deferred items, an evidence summary, the files changed outside the plan's
   `scope`, and the diff against the delivery's base commit plus untracked
   files. A diff over 200 KB is replaced by its `--stat` and a truncated
   excerpt, with a note telling the reviewer to inspect the repository. Then
   the command prints `review N of M` and the workflow.
2. The model gives the packet to a reviewer **in an isolated session**: a
   session that has not seen the conversation, given only the packet path. In
   Claude Code this is a subagent; see [clients](../clients.md) for the
   others. When the client cannot provide one, the reviewer still writes the
   review and declares `session: shared`. With `risk: high` or
   `require_isolated_review`, the model asks you to open a new session for
   the reviewer instead.
3. The reviewer reads the packet, inspects the repository, runs commands if
   reading is not enough, and writes:

```markdown
---
tree: cd03ae507b3605b12a497fcbcf590894a0073076
reviewer: claude-code subagent
session: isolated
---

# Review: Password reset

## Criteria

- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. tests.auth.test_reset.test_unknown_email_same_response
- AC-003: FAIL. consume() checks the age but the boundary of exactly 30 minutes is accepted.

## Findings

- F1 [blocker]: shop/domain/reset.py imports shop.infrastructure.mail, forbidden by the contract.
- F2 [minor]: request() lacks a docstring.

## Notes

The spec does not say whether a used link may be reused; assumed no.
```

4. The model runs `atipspec check password-reset`:
    - A `FAIL` or a `blocker`: fix the code and verify again. Any change to
      the tree makes the review stale, so it runs `review` and the reviewer
      again.
    - A minor finding you decide not to fix now goes to `deferred.md` with
      a reason: `- F2: cosmetic, handled in the docs cleanup delivery`. A
      blocker or major finding is fixed: only a risk exception under a trust
      policy defers it. Criteria can never be deferred.
5. When `atipspec review` refuses because the review rounds are used up, the
   model stops and presents `atipspec check password-reset` with the
   findings that remain. You decide.

## What the gate checks in `review.md`

- `tree:` is the packet's: the candidate the last `atipspec review` counted. A
  review of another candidate is stale, unless only task titles changed, and
  one written without running `review` waits for it (see
  [review rounds](#review-rounds)).
- `reviewer:` names the client or model that wrote the review; without it,
  `check` reports an error.
- `session:` is `isolated` (the reviewer never saw the author's
  conversation) or `shared`. A review that leaves it out counts as `shared`.
  A shared review is a warning, and an error when the spec says `risk: high`
  or `require_isolated_review` is on in `config.yaml` or in the trust policy.
  Any other value is an error. In the guided flow the reviewer declares the
  session; the declaration is recorded, shown in the dossier and acted on by
  the gate, but nothing measures it. The [process runner](../reference/execution-adapter.md)
  holds it to the adapter's declared `isolated_review`.
- Every criterion has a verdict, except, with `risk: low`, one whose test
  named in `Proof:` passed in the current evidence: `check` notes it with an
  info. A `FAIL` blocks at every level. See [risk](spec.md#risk).
- Every `PASS` needs a pointer the gate resolves, one of:
    - a test that passed in the current evidence's JUnit report, named as
      the report names it (`tests.auth.test_reset.test_link`), or as in a
      Proof entry; a name with spaces goes in backticks;
    - `path:line` or `path:line-line`, a line that exists in a file of the
      candidate: outside `.atipspec/` and `.git` and not ignored by git. The
      delivery's evidence logs count, even where git ignores `*.log`, as
      `evidence/logs/FINAL-<run>-1.log:12` from the delivery folder;
    - `path::test`, such a file that holds that name as a word (a `[param]`
      suffix is ignored); the dossier shows it as a name found in the file,
      since the gate does not run it.

    For a criterion marked `[manual]`, a description of what was done and
    observed, three words or more, also passes. A `FAIL` needs its reason.
    `PASS. ok` is an error. While the review is stale its pointers are not
    judged, and while the evidence is not current an unresolved pointer is a
    todo: the test it names may be in the next run. A pointer that resolves
    shows that it names something real, not that it proves the criterion: the
    dossier shows what each one resolved to for you to judge, and
    [Proof](build.md) entries, required with `require_proof`, bind a criterion
    to its test: a `PASS` for such a criterion that does not name that test is
    a warning.

## Review rounds

`review_rounds` in `config.yaml` (default 3) is how many reviews a delivery
gets per approved agreement, the first included: a first review and two of
corrected candidates. `atipspec review` counts a review each time it writes a packet for
another candidate than the last packet's, whatever `review.md` says: a review
that passed counts too, because the reviewer writes that file and the CLI
cannot tell its verdicts from ones edited afterwards. Writing the packet again
for the same candidate counts nothing, and neither does a packet that cannot
be built. Once the reviews are used and the candidate changes again,
`review` refuses, counting nothing, and names the decision: change the
proposal, raise `review_rounds`, or stop. Until then `check` reports the
used-up reviews as an error, whatever `review.md` says, and the dossier shows
the count. `check` takes only the review of the last packet `atipspec review`
counted: a `review.md` written for a candidate without running the command is
a todo that asks for it, so skipping it saves no review. The count lives in
`review-rounds.json` in the delivery folder, which the CLI writes, and starts
again when the approved agreement changes: the proposal of a guided delivery,
the spec of a legacy one. `atipspec accept <slug> proposal` starts the file,
so in a guided delivery created since 0.3.0 a missing file was deleted:
`review` refuses and `check` fails until you decide, by restoring it from git
or approving the proposal again, which starts a new count. The Claude Code
rules keep the client's edit tools off that file, not a shell command. When
the file is missing in a delivery approved under a trust policy, `atipspec
review` counts again from the `review.md` in the folder, as the first review;
in one created before 0.3.0 it counts from the next packet, since a
`review.md` written before names a tree of the earlier fingerprint. Raising `review_rounds` in a guided delivery changes `config.yaml`,
which the proposal's approval hashes, so the proposal is presented again. In a
legacy delivery (a fix created before 0.3.0 included), whose approval is the
spec's, no approval covers
`config.yaml`: a raised limit applies at once, so the model raises it only
when you say so, and the dossier shows `Review N of M`. `atipspec status
password-reset` shows `review N of M`. `atipspec run` counts the reviews it
asks for the same way and stops at `needs_decision` once they are used up. It
also keeps its own count: `--max-rounds`, which defaults to `review_rounds`
less one, as each correction is reviewed again, and cannot exceed it, limits
every automatic correction, whether a review or a check asked for it.

## Why an isolated session

The context that wrote the code will confirm it. The reviewer's verdicts are
the only ones the gate accepts, and the gate rejects them as soon as the code
changes, unless only task titles in a plan changed. A contract violation is
always a blocker.

Blocker and major findings require resolution or a trusted risk exception.
Local green is `checked`: the assistant then presents `atipspec report <slug>`
for your acceptance of the result, and `deliver` requires it. Under
[trusted acceptance](../enterprise.md), green is `verified`, and QA's signed
approval binds the review, exceptions and evidence.
