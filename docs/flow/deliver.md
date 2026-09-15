# deliver

**Merge the requirements into the living spec and archive the delivery.**
Only when the trusted gate is verified. A green local check is insufficient.

| | |
| --- | --- |
| Who decides | `atipspec check --policy` must exit 0 with trusted approvals. Then you merge the branch. **Stop point 2.** |
| Produces | `.atipspec/specs/<capability>.md` updated, `.atipspec/archive/<slug>/` |

## How to run it

```text
/atipspec-deliver password-reset --policy /secure/company.toml
```

or directly:

```bash
atipspec deliver password-reset --policy /secure/company.toml
```

```text
AtipSpec: merged into .atipspec/specs/auth.md and moved to .atipspec/archive/password-reset/
Next: commit, then ask the user to merge the branch
```

## What it does

1. Runs the gate. Anything but green is refused with the full report.
2. Merges each requirement by stable capability-scoped **ID**. A title change
   updates the same requirement. Criterion IDs are retained. Concurrent baseline
   conflicts fail for explicit reconciliation. Every requirement needs an ID.
3. Sets `status: delivered` in the delivery's spec and moves the folder to
   `archive/`. Signed evidence, approvals, review and an acceptance receipt
   travel with it. The receipt describes historical acceptance of the candidate.

The living spec after the example:

```markdown
# auth

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Acceptance criteria:
- AC-001: A request with a registered email sends a link to that email within 60 seconds.
- AC-002: A request with an unknown email responds exactly like a valid one.

### REQ-002: The link expires

Acceptance criteria:
- AC-003: A link older than 30 minutes shows "link expired" and sends nothing.
```

## Then

```bash
git add -A
git commit -m "chore: deliver password-reset"
git push -u origin delivery/password-reset
```

Open the pull request and merge it. After the merge, `atipspec status` on
main shows the delivery under `delivered`, and the [curate](curate.md) phase
refreshes the overview.
