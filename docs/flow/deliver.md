# deliver

**Merge the requirements into the living spec and archive the delivery.**
Only when the gate is green and you accepted the current result: locally,
the record `atipspec accept <slug> result` writes after your approval; with a
trust policy, the trusted gate verified with signed approvals. The result you
accept is what `atipspec report <slug>` shows: the criteria with their
evidence and review verdicts, and the files changed since the base commit with
the diff.

| | |
| --- | --- |
| Who decides | You accept the reviewed result in the conversation: **stop point 2**. Under a trust policy, the signed QA acceptance, and `atipspec check --policy` must exit 0. The merge follows your repository's policy, after `merge-check`. |
| Produces | `.atipspec/specs/<capability>.md` updated, `.atipspec/archive/<slug>/` with the receipt |

## How to run it

```text
/atipspec-deliver password-reset
```

The skill runs `atipspec check password-reset`, presents `atipspec report
password-reset` and, after your acceptance, records `atipspec accept
password-reset result --code <code>`. Then:

```bash
git add -A && git commit -m "feat: password reset"   # when the repository's policy commits: the accepted code first
atipspec deliver password-reset                      # --policy /secure/company.toml under a trust policy
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Result archived. Commit, merge and deployment follow the repository's explicit policy.
Before merging, `atipspec merge-check --base <target branch>` confirms the branch still matches this acceptance; any later change outside .atipspec/ requires reopening the delivery: revert the archive commit, then verify, review and accept again.
```

## What it does

1. Runs the gate. Anything but green is refused with the full report.
2. Merges each requirement by stable capability-scoped **ID**. A title change
   updates the same requirement. Criterion IDs are retained. Concurrent baseline
   conflicts fail for explicit reconciliation. Every requirement needs an ID.
3. Writes the receipt `reports/acceptance.json`, with `code_tree`: the hash
   of everything outside `.atipspec/` that you accepted. `deliver` and later
   AtipSpec bookkeeping (curate, other deliveries, approvals) never change it;
   any code change does. It also records `living_spec`, the digest of the
   living spec it wrote, and `living_requirements`, the text of each
   requirement the delivery lists as written there, so a later edit to the
   accepted requirements shows, and the dossier's `changes`: the changed files
   with their status and the diff's size and sha256, without the diff's text,
   which git history keeps.
4. Sets `status: delivered` in the delivery's spec and moves the folder to
   `archive/`. Evidence, approvals and review travel with it.

The living spec after the example holds each listed requirement as the
delivery wrote it, by ID; a requirement marked `[remove]` is gone:

```markdown
# auth

## Requirements

### REQ-AUTH-7KQ2M-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

#### AC-AUTH-7KQ2M-001: Registered email
- **WHEN** a user requests a reset for the registered email "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

### REQ-AUTH-7KQ2M-002: The link expires

#### AC-AUTH-7KQ2M-003: Link older than 30 minutes
- **WHEN** a link issued 31 minutes ago is opened
- **THEN** the page shows "link expired" and sends nothing
```

## Then

When your repository's policy lets the assistant commit and push:

```bash
git add -A
git commit -m "chore: deliver password-reset"   # only .atipspec/ changes: the archive commit
atipspec merge-check --base origin/main
git push -u origin delivery/password-reset
```

`merge-check` blocks the merge while a delivery the branch touches is not
accepted, when the code at the head is not the code a receipt accepted, when
a living spec or the accepted contract changed outside their acceptance, or
when the branch changes a file outside `.atipspec/` that no delivery of it
changed after its base commit, such as code committed before `atipspec new`,
and that `exempt_paths` on the target branch does not exempt.
The CI examples run it as the pull request's check, whose summary lists each
delivery with its state and ticket (see
[enterprise](../enterprise.md#ci-before-the-merge)). Open the pull request with
the ticket and the output of `atipspec report <slug> --format markdown` in its
description, and merge it. After the merge, `atipspec status` on main shows the delivery under
`delivered`, and the [curate](curate.md) phase refreshes the overview.

## After `deliver`, the code is fixed

Change nothing outside `.atipspec/` on the branch after `deliver`, nor the
living spec it wrote, and do not bring the target branch into it: either
changes what the receipt accepted, and `merge-check` fails. Bring in the target branch before the final
verification instead, with a merge: what it brings does not void the
approved proposal (see [teams](../teams.md#when-main-moves)). When a change is needed, reopen the delivery:

```bash
git revert <the archive commit>          # the delivery returns to deliveries/, the living spec to its previous text
```

then verify, review, present `atipspec report <slug>` for your acceptance of
the changed result, and deliver again. It is the same acceptance, repeated
because the result changed. Keeping the code and the archive in separate
commits makes the revert touch only `.atipspec/`.
