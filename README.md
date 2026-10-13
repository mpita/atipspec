# AtipSpec

Spec-driven delivery with verifiable evidence and human acceptance.

**Current version: 0.3.0.** See the [release history](CHANGELOG.md).

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

Approve in the same conversation: the assistant presents the agreement with its
approval code and offers **Approve and continue**, **Request changes** or
**Cancel**. Use the client's selector when available, or reply in plain language.
After your explicit approval the assistant records it with `atipspec accept ...
--code <code>`, naming the code of the content it showed you; if that content
changed in the meantime, the command refuses. `init` and `install` configure
Claude Code (`.claude/settings.json`) to ask you before it runs `atipspec accept`
or edits the CI workflows and its own settings, and to deny its edit tools the
approval and evidence records, in a session opened
at the project root; that prompt confirms the same approval. Each record states
its channel: `terminal` (the code was typed at the CLI prompt),
`client-permission` (this project's rules make Claude Code ask you) or
`assistant` (nothing asked you, as in clients without such rules). A channel
describes how the command ran, not who approved. You do not have
to type commands or edit statuses. Contract approval, presented with `atipspec
proposal contract`, includes the listed architecture decisions. Changed agreements
need renewed approval, and the finished result has its own acceptance. External
trust policies retain their authenticated procedure.

The commands below are what the assistant runs (also available for manual use;
in a terminal, `accept` asks you to type the code):

```sh
atipspec proposal password-reset                         # scenarios, approach, tests, diff and approval code
atipspec accept password-reset proposal --code K7M2-QX4P # after your explicit approval of that proposal
# The agent implements and records tasks with task-done; no commits are required.
atipspec verify password-reset
atipspec review password-reset
atipspec check password-reset
atipspec report password-reset                           # the reviewed result, its evidence and approval code
atipspec accept password-reset result --code 3C1Q-4VN7   # after your explicit acceptance of that result
atipspec deliver password-reset                          # local archive; does not commit, push or merge
atipspec merge-check --base origin/main                  # before the merge: every delivery accepted, the code still the accepted code
```

For existing projects, install the updated ATIPSpec package, then have the agent
run `atipspec install --update` in the target project to refresh the framework and
installed skills and to merge the Claude Code permission rules into
`.claude/settings.json` (nothing else in that file changes). This replaces
customized framework/skill files; inspect the changes first. Until it runs,
`audit`, `check` and `merge-check` fail: every phase prints the framework's
rules to the agent, so they must be the installed version's. Reload the client's skills or start a fresh session if it has
cached the old instructions. Those files are part of the tree hash, so the
evidence and review of deliveries in progress become stale, and a result
accepted but not yet delivered must be presented again: deliver accepted
results before updating.

New feature deliveries reference canonical requirements in `.atipspec/specs/`.
Write complete scenarios there or use `spec-bind <slug> --file <authored.md>`,
which also imports a list of acceptance criteria with notes for the human to
check; empty capabilities are not created.
`atipspec migrate <slug>` shows how a legacy delivery becomes a guided one and
`--apply` writes it. The delivery's `spec.md` states the intent,
what is out of scope and which requirements are quality attributes; an empty
intent blocks the proposal. `proposal` shows changes from the baseline, how
strictly the criteria are checked and the specification warnings.
Existing embedded specs remain supported. A plan's `## Final verification`
commands execute once for the finished candidate and can support multiple tasks.
Task-level Verify commands remain available for focused development checks.

A defect gets a guided fix (`atipspec new bug-1 --title "..." --capability auth
--kind fix`): it names the accepted requirement it breaks, corrects it in
`specs/` with a regression criterion and changes no other, and needs one
proposal approval and no accepted contract; the defect's story stays in the
archived delivery. Every guided delivery states `risk: low|normal|high`,
approved with the proposal: `low` lets a criterion whose named test passed go
without a reviewer verdict and removes no requirement, and `high` requires a
scope, a named test with a JUnit report for every automated criterion and a
review from an isolated session. `check`, `status` and the dossier show the
lead time, from `new` to the result's acceptance, and warn above
`max_age_hours` (8 hours).

`accept` records a hash of what you accepted, with the approval code, the
channel and per-file digests; changing the agreement invalidates its approval and
`check` names the files that changed. Plans declare the files they will touch (`scope`) and,
when the tests write JUnit XML, the test that proves each criterion (`Proof:`).

The gate fails closed. Without git it is red. New projects are strict: a plan
without a scope, a file outside it, a vague requirement, criterion or scenario
step, or a quality attribute without a number is an error. `deliver`
stores the hash of the accepted code in its receipt, and `atipspec merge-check
--base <target>` blocks a branch whose deliveries are not accepted, whose
code changed after `deliver`, or that changes code no delivery of it changed
after its base commit, unless `exempt_paths` on the target branch exempts
those files; the CI examples from `enterprise-init` run it as
the pull request's check. `trust: required` in `.atipspec/config.yaml` makes
the external trust policy mandatory.

A green local check is **checked**, not **verified**. It checks command/result
consistency, coverage, tree freshness and structural rules; it never runs the
tests itself, it judges the evidence `verify` wrote. It does not authenticate
provenance. Explicit local result acceptance changes it to
**accepted** and permits `deliver` without keys or a trust service. Organizations
can opt into the authenticated **verified** path below.

## Trusted acceptance

```sh
atipspec enterprise-init
```

This writes example trust policies (`policy.example.toml` for ssh mode,
`policy.provider.example.toml` for provider mode), GitHub/GitLab merge-check
jobs, the provider-mode evidence workflow (`github-evidence-trusted.yml` for a
separate trusted repository, `github-evidence-caller.yml` for each candidate
repository), a protected acceptance script and an adoption guide into `.atipspec/enterprise/`. Configure
real identities and install the policy **outside the candidate checkout** under
organization control. Pin its digest in protected CI. An example policy with
placeholder keys deliberately fails validation.

```sh
# Each human signs from their own enrolled key and trusted environment;
# product confirms the delivery owner, who cannot sign the later phases.
atipspec approve password-reset spec --identity product@example.com \
  --owner ana --key /secure/product-key --policy /secure/company.toml
atipspec approve password-reset plan --identity architect@example.com \
  --key /secure/architect-key --policy /secure/company.toml

# Trusted producer executes after those approvals; isolated collector attests.
atipspec verify password-reset --policy /secure/company.toml
atipspec attest password-reset --identity ci-producer --key /secure/ci-key \
  --run-url https://ci.example/runs/123 --policy /secure/company.toml

# Review in an isolated session, then QA inspects the dossier (diff included) and signs.
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

- The contract exists. Changes require a **new** decision affecting the contract,
  included in the contract's recorded acceptance (`atipspec accept contract`);
  a status edited by hand does not count. Trusted mode requires the decision's
  engineering approval instead. Guided deliveries also require the current
  proposal's acceptance record; a spec and plan pair does not replace it.
- Every requirement has acceptance criteria and task coverage, and each
  criterion maps through `Tests:` or `Manual:` to verification and review.
- Evidence commands exactly match the plan, exit codes agree with the result,
  before/after trees match, timestamps and execution environment are present.
  A JUnit `Report:` lives at a path git ignores and counts only when the run
  wrote it: `verify` deletes it first and checks its modification time.
  With `require_proof: true` (in `config.yaml` or the trust policy), every
  criterion under `Tests:` names its passing test in `Proof:`.
- Trusted evidence carries an enrolled CI signature and policy/repository scope.
- Every criterion has PASS with a pointer the gate resolves: a test that passed
  in the report, a `path:line` or a `path::test` (a `[manual]` criterion may
  describe what was observed instead). `review.md` names its `reviewer:` and
  declares its `session:`; a shared session is a warning, an error with
  `risk: high` or `require_isolated_review`. Reviews bind to the content tree
  and to the last packet `review` counted, and `review` refuses once the
  candidate changed after `review_rounds` reviews, the first included.
- Blocker and major findings block acceptance. Deferral requires a signed risk
  approval with an expiry and renewed QA acceptance. Criteria cannot be waived.
- Product, engineering and QA approvals bind to their actual subjects. Edited
  subjects, altered signatures, expired exceptions and revoked trust fail closed.
- External corporate contract rules cannot be relaxed by editing the project.

Signatures establish enrolled key identity. Human-only key custody and trusted
provider account enrollment are organizational responsibilities. A compromised
signer, verifier or CI producer is outside the local CLI's trust guarantee.

## Durable traceability

Living specs keep requirement and criterion IDs scoped to a capability
(`auth/REQ-AUTH-7KQ2M-001`); they survive title changes and are never reset.
`atipspec ids auth` gives each delivery a short prefix no visible ID uses,
such as `REQ-AUTH-7KQ2M-001`, and the delivery numbers its further IDs with
it, so parallel branches do not collide; the numbered `REQ-001` IDs of
deliveries created before 0.2.0 stay valid. Concurrent work that changes the
same baseline requirement is reported for reconciliation, and integrating
another delivery from main does not void an open delivery's approval (see
[teams](docs/teams.md#when-main-moves)).

```markdown
### T1: Request reset link
Covers: REQ-AUTH-7KQ2M-001
Tests: AC-AUTH-7KQ2M-001, AC-AUTH-7KQ2M-002

## Final verification
Verify:
- `python -m unittest tests.test_reset`
```

Use `Manual: AC-AUTH-7KQ2M-003` for criteria requiring a human observation;
the reviewer records what was observed, and you see it before accepting the
result (QA approves it under a trust policy). Automated mapping
is a traceability claim validated by review, not a proof that any named test is
semantically sufficient; `require_proof` makes every automated criterion name
its test, and a pointer that resolves still only shows it names something real.

```sh
atipspec ids auth
atipspec report password-reset --format json --out .atipspec/tmp/acceptance.json
```

Reports include the requirement/criterion/task/evidence matrix, what each
review pointer resolved to, the reviewer and session, human identities,
approvals, findings, policy version, artifact hashes, and the changed files with
the diff from the base commit, so the human sees the code before accepting. `deliver` archives an
acceptance receipt. Archived reports describe historical acceptance and do not
claim that remote approvals remain current after archival.

## Measure a real pilot

```sh
atipspec pilot init quality
atipspec pilot record quality --delivery reset --cohort atipspec \
  --human-review-minutes 20 --rework-minutes 10 \
  --escaped-defects 0 --criteria-total 4 --criteria-tested 3 \
  --observation-days 14 --source ticket:SHOP-12 --collector qa
atipspec pilot report quality
```

The record above is an invocation example, not a measured result. Complete the
protocol with a real team and collect comparable baseline/AtipSpec observations.
Unknown values must not be entered as zero. For the AtipSpec cohort, the lead
hours come from the delivery's archived receipt when `--lead-hours` is omitted:
wall-clock hours from `new` to the result's acceptance. Measure the baseline
between the same two events. Reports show sample sizes, medians,
defects and tested-criterion coverage; unequal observation windows are flagged.

## Other commands

`status`, `context`, `ids`, `spec-bind`, `decision`, `initiative`, `audit`,
`curate` and `new --branch/--worktree` support everyday planning and delivery;
`team` and `contract-pin` coordinate several people and repositories; `run`
and `adapter` execute an approved delivery through a configured process. See
the [guided delivery](docs/flow/guided.md) end to end, the [CLI
reference](docs/reference/cli.md) and the [adoption guide](docs/enterprise.md).

## Verify this checkout

```sh
python -m unittest discover -s tests -t . -v
python scripts/smoke_test.py             # exercises a non-editable installed CLI
```
