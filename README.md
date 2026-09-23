# AtipSpec

Spec-driven delivery with verifiable evidence and human acceptance.

**Current version: 0.1.0.** See the [release history](CHANGELOG.md).

AtipSpec connects requirements, tasks, executable verification, review and
approval. It works with Claude Code, Codex, Cursor, Copilot, Gemini CLI and
Antigravity. Python 3.11+, Git. Optional trusted signatures use OpenSSH (`ssh-keygen -Y`).
No third-party Python runtime dependencies. MIT licensed.

**Documentation:** <https://mpita.github.io/atipspec/>

## Start locally

```sh
uv tool install .                       # or python -m pip install .
atipspec init --client codex --name MyProject --language es
atipspec new password-reset --title "Password reset" --capability auth --owner ana
```

One skill per phase is installed in your client: `atipspec-contract`,
`atipspec-spec`, `atipspec-fix`, `atipspec-plan`, `atipspec-build`,
`atipspec-review`, `atipspec-deliver`, plus `atipspec-explore`,
`atipspec-curate` and `atipspec-ship`. Each runs the matching CLI command, which refuses while a
required step is missing and otherwise prints the workflow, the rules and the
context. The developer leads; the model proposes. A local CLI cannot establish
that a human approved simply because a Markdown field says so.

Approve in the same conversation: the assistant presents the agreement and offers
**Approve and continue**, **Request changes** or **Cancel**. Use the client's
selector when available, or reply in plain language. After explicit confirmation,
the assistant records acceptance and continues; you do not have to type commands
or edit statuses. Contract approval can include the listed architecture decisions.
Changed agreements need renewed approval, and the finished result has its own
acceptance. External trust policies retain their authenticated procedure.

The commands below are what the assistant runs (also available for manual use):

```sh
atipspec proposal password-reset         # review scenarios, approach, tests and diff
atipspec accept password-reset proposal  # explicit human approval of the agreement
# The agent implements and records tasks with task-done; no commits are required.
atipspec verify password-reset
atipspec review password-reset
atipspec check password-reset
atipspec report password-reset           # inspect the reviewed result and evidence
atipspec accept password-reset result    # explicit human result acceptance
atipspec deliver password-reset          # local archive; does not commit, push or merge
```

For existing projects, install the updated ATIPSpec package, then have the agent
run `atipspec install --update` in the target project to refresh the framework and
installed skills. This replaces customized framework/skill files; inspect the
changes first. Reload the client's skills or start a fresh session if it has
cached the old instructions.

New feature deliveries reference canonical requirements in `.atipspec/specs/`.
Write complete scenarios there or use `spec-bind <slug> --file <authored.md>`;
empty capabilities are not created. `proposal` shows changes from the baseline.
Existing embedded specs remain supported. A plan's `## Final verification`
commands execute once for the finished candidate and can support multiple tasks.
Task-level Verify commands remain available for focused development checks.

`accept` records a hash of what you accepted; changing the agreement invalidates
its approval. Plans declare the files they will touch (`scope`) and,
when the tests write JUnit XML, the test that proves each criterion (`Proof:`).

A green local check is **checked**, not **verified**. It checks command/result
consistency, coverage, tree freshness and structural rules. It does not
authenticate provenance. Explicit local result acceptance changes it to
**accepted** and permits `deliver` without keys or a trust service. Organizations
can opt into the authenticated **verified** path below.

## Trusted acceptance

```sh
atipspec enterprise-init
```

This writes an example trust policy, GitHub/GitLab verification jobs, a protected
acceptance script and an adoption guide into `.atipspec/enterprise/`. Configure
real identities and install the policy **outside the candidate checkout** under
organization control. Pin its digest in protected CI. An example policy with
placeholder keys deliberately fails validation.

```sh
# Each human signs from their own enrolled key and trusted environment.
atipspec approve password-reset spec --identity product@example.com \
  --key /secure/product-key --policy /secure/company.toml
atipspec approve password-reset plan --identity architect@example.com \
  --key /secure/architect-key --policy /secure/company.toml

# Trusted producer executes after those approvals; isolated collector attests.
atipspec verify password-reset --policy /secure/company.toml
atipspec attest password-reset --identity ci-producer --key /secure/ci-key \
  --run-url https://ci.example/runs/123 --policy /secure/company.toml

# Fresh-context technical review, then QA inspects the dossier and signs.
atipspec approve password-reset acceptance --identity qa@example.com \
  --key /secure/qa-key --policy /secure/company.toml
atipspec check password-reset --policy /secure/company.toml
atipspec report password-reset --format html --out .atipspec/tmp/acceptance.html \
  --policy /secure/company.toml
atipspec deliver password-reset --policy /secure/company.toml
```

The producer and collector are separate trust boundaries, not instructions to
put the signing key next to arbitrary test commands. The collector must verify
CI run/artifact provenance before `attest`; that command cannot establish the
origin of an arbitrary downloaded JSON. Use an installed, pinned verifier in
the protected worker, not code imported from the candidate checkout.

Alternatively, humans approve in GitHub or GitLab. `approval-subject` generates
a content/head-bound marker; `sync-approvals` reads existing reviews using an
enrolled collector. The gate re-fetches remote state to detect revocation. No
adapter posts a message, approves a review or merges a branch.

## What the gate checks

- The contract exists. Changes require a **new, accepted** decision affecting
  the contract; trusted mode also requires its engineering approval.
- Every requirement has acceptance criteria and task coverage. In trusted mode,
  each criterion maps through `Tests:` or `Manual:` to verification and review.
- Evidence commands exactly match the plan, exit codes agree with the result,
  before/after trees match, timestamps and execution environment are present.
- Trusted evidence carries an enrolled CI signature and policy/repository scope.
- Every criterion has PASS and a proof pointer; reviews bind to the content tree.
- Blocker and major findings block acceptance. Deferral requires a signed risk
  approval with an expiry and renewed QA acceptance. Criteria cannot be waived.
- Product, engineering and QA approvals bind to their actual subjects. Edited
  subjects, altered signatures, expired exceptions and revoked trust fail closed.
- External corporate contract rules cannot be relaxed by editing the project.

Signatures establish enrolled key identity. Human-only key custody and trusted
provider account enrollment are organizational responsibilities. A compromised
signer, verifier or CI producer is outside the local CLI's trust guarantee.

## Durable traceability

Living specs retain `REQ-nnn` and `AC-nnn`. IDs are scoped to a capability
(`auth/REQ-001`), survive title changes and are not reset per delivery. `new`
allocates the next IDs from active, living and archived specs. Concurrent work
that changes the same baseline requirement is reported for reconciliation.

```markdown
### T1: Request reset link
Covers: REQ-001
Tests: AC-001, AC-002
Verify:
- `python -m unittest tests.test_reset`
```

Use `Manual: AC-003` for criteria requiring a human observation; the reviewer
must record proof and QA must approve the acceptance subject. Automated mapping
is a traceability claim validated by review, not a proof that any named test is
semantically sufficient.

```sh
atipspec ids auth
atipspec report password-reset --format json --out .atipspec/tmp/acceptance.json
```

Reports include the requirement/criterion/task/evidence matrix, human identities,
approvals, findings, policy version and artifact hashes. `deliver` archives an
acceptance receipt. Archived reports describe historical acceptance and do not
claim that remote approvals remain current after archival.

## Measure a real pilot

```sh
atipspec pilot init quality
atipspec pilot record quality --delivery reset --cohort atipspec \
  --lead-hours 4 --human-review-minutes 20 --rework-minutes 10 \
  --escaped-defects 0 --criteria-total 4 --criteria-tested 3 \
  --observation-days 14 --source ticket:SHOP-12 --collector qa
atipspec pilot report quality
```

The record above is an invocation example, not a measured result. Complete the
protocol with a real team and collect comparable baseline/AtipSpec observations.
Unknown values must not be entered as zero. Reports show sample sizes, medians,
defects and tested-criterion coverage; unequal observation windows are flagged.

## Other commands

`status`, `context`, `decision`, `initiative`, `audit`, `curate`, and
`new --branch/--worktree` support everyday planning and delivery. See the
[CLI reference](docs/reference/cli.md) and [adoption guide](docs/enterprise.md).

## Verify this checkout

```sh
python -m unittest discover -s tests -t . -v
python scripts/smoke_test.py             # exercises a non-editable installed CLI
```
