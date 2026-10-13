# Enterprise acceptance

AtipSpec separates **checked** (local structural/technical checks) from
**verified** (trusted evidence and human acceptance). Under a trust policy,
`deliver` requires verified; `trust: required` makes the policy mandatory.

## Local acceptance and trusted acceptance

Without a policy, `atipspec accept --code <code>` records what a person
approved in the conversation (the proposal, the result, the contract; the spec
and plan of legacy deliveries) and the gate detects later edits. The record
states its channel: `terminal` (the code was typed at the CLI prompt),
`client-permission` (Claude Code was configured to ask the person before the
command) or `assistant` (nothing asked). Even the strongest local channel says
how the client was configured, not who confirmed: that is drift detection plus
an honest account of the path, not identity. With a policy, the gate ignores
those records and requires the signed, role-bound approvals below, which
authenticate each approver with an enrolled key or the provider's own review.

## Requiring the trust policy

The policy stays outside the repository; the repository can only declare that
it is required. Set `trust: required` in `.atipspec/config.yaml` and protect
that file with CODEOWNERS. Without a policy (`--policy` or
`ATIPSPEC_TRUST_POLICY`), `check` is red, local `accept` is disabled except for
the project's contract, `deliver` refuses and `run` does not start. `verify`
still runs for local iteration; the trusted check requires attested evidence
anyway. `merge-check` applies the requirement when the head, the target
branch or the merge base sets it, so a branch cannot remove it for its own
merge, nor skip it by forking from a commit before it. It then blocks a receipt
accepted locally, and a trusted receipt the policy does not authenticate (see
[CI before the merge](#ci-before-the-merge)).

## Two trust modes

| | `mode = "ssh"` | `mode = "provider"` |
| --- | --- | --- |
| Human approvals | detached SSH signatures from enrolled keys (`approve`), or provider reviews collected and signed by a collector key (`sync-approvals`) | read live from the pull request by the protected worker with a read-only token; no collector |
| CI evidence | signed by an enrolled CI collector key (`attest`) | attested with GitHub artifact attestations by the trusted evidence workflow, in a separate repository and pinned to a commit, and verified with a pinned `gh` |
| Keys to enroll | one per human role, one for CI, one for the collector | none |
| Risk exceptions | `approve <slug> exception:Fn --expires` | not available: fix the finding or use ssh mode |
| Policy | `schema = 1` | `schema = 2`, `[provider.roles]` and `[attestation]` |

Provider mode is the default recommendation: it needs a protected worker
with `GITHUB_TOKEN`, the pinned policy and the pinned `gh`, and a trusted
repository of the organization that holds the evidence workflow, and nothing
else. Provider mode is GitHub-only. The gate re-reads the provider on every
run and fails closed on any API error, revoked review, changed head or digest
mismatch. `check`, `deliver`, `report` and `merge-check` take the PR number
with `--number` or `ATIPSPEC_PR_NUMBER`. `enterprise-init` writes
`policy.provider.example.toml`, `github-evidence-trusted.yml` and
`github-evidence-caller.yml`. SSH mode stays the strict option for
organizations that need signatures under their own key custody, GitLab, or
risk exceptions.

In a pull request GitHub runs the workflows the pull request carries, so a
workflow of the candidate repository can be rewritten by the change it
attests. The policy therefore binds each evidence attestation to four things:
the candidate repository (`repository`, verified with `--repo`), the pull
request (`refs/pull/<number>/merge`, the ref GitHub records for a
`pull_request` run), the trusted workflow in a separate repository of the same
organization (`[attestation] signer_workflow`) at one commit
(`signer_digest`), and GitHub-hosted runners (`allow_self_hosted_runners =
true` lifts this). A policy whose workflow lives in the candidate repository,
or whose commit is not pinned, does not load. The gate also requires each
record's `head` to be the commit the worker checked out. Pull requests from
forks get no OIDC token by default, so their evidence carries no attestation
and the gate fails closed; enable GitHub's "send write tokens to workflows
from pull requests" only if you accept it, and never use
`pull_request_target` for the evidence workflow.

## Trust boundary

The candidate repository is editable by its author and coding agent. Files in
it, including evidence JSON, review text and local approval metadata, cannot be
their own authority. A protected acceptance worker uses a pinned installed CLI,
an external versioned trust policy and enrolled public keys. Pin the policy's
SHA-256 in protected configuration (`ATIPSPEC_POLICY_SHA256`).

`enterprise-init` generates configuration examples and an adoption guide. Move
and configure the policy outside the checkout; do not use the template directly.
The template intentionally contains invalid placeholder keys. CI signing and
provider collector roles cannot also hold human approval roles.

Corporate `contract_rules` are evaluated across the repository, in addition to
the project contract. A project cannot waive a corporate rule with a local
architecture decision. Update and approve the corporate policy separately.

The policy can also impose two gate minimums, top-level booleans next to
`contract_rules`: `require_proof = true` (every criterion under `Tests:` names
its JUnit test in `Proof:`, and the verification has a `Report:`) and
`require_isolated_review = true` (a review whose `session:` is not `isolated`
is an error). Any other value fails to load. The gate applies a requirement
when the policy or the project's `config.yaml` sets it, so a project can add
it but not lift it.

## Roles and approval subjects

| Phase | Role | Bound content |
| --- | --- | --- |
| spec | product | specification and architecture contract |
| plan | engineering | specification, plan and architecture contract |
| decision:DEC-nnn | engineering | decision document and changed contract |
| exception:Fn | risk | tree, review, deferral terms, expiry |
| acceptance | qa | tree, review, deferral terms and evidence artifacts |

In a guided delivery, spec and plan bind the requirements the delivery lists
one by one, not the rest of its capability's living spec, whose other
requirements `check` and `merge-check` hold as they were (subject version 2;
see [when main moves](teams.md#when-main-moves)). What the integration branch
brought is not the delivery's change; under a policy, only its `integration`
key names that branch, such as `integration = "refs/remotes/origin/main"`:
`teams.json` is part of the candidate. Without the key nothing is attributed,
and what taking the target branch in brings counts as the delivery's change
in `check`. Approvals signed
before 0.3.0, and provider reviews that carry their marker, are compared with
the version 1 subject they were made for. A subject reads CRLF line endings
as LF, and so do the signature checks of approvals and evidence records and
the digests of command output logs and test report copies: a checkout with
`core.autocrlf` (the Git for Windows default) and one without give the same
subject and verify the same signatures.

The declared delivery owner cannot approve their own work, whatever the case
it is written in: an owner `Engineering` is the identity or account
`engineering`. The owner is written as identities are, in ASCII letters,
digits, `_`, `.`, `@` and `-`: `check` and `approve` refuse one that only
reads as an identity, with a Cyrillic letter or an invisible character in it.
Provider adapters also reject the actual PR/MR author. In ssh mode `spec.md` is the author's
word, so the product approver confirms the owner: `approve <slug> spec
--owner <identity>` fails unless it is the `owner` `spec.md` declares, and
signs it with the approval. A spec approval that confirms no owner (signed
before 0.3.0) or another one does not count: sign it again with `--owner`.
Changing the owner changes the spec's subject, so product approves again, and
the new owner cannot sign the later phases. Administrators must still ensure
that enrolled human keys are not accessible to developer agents or service
accounts. A valid signature proves key possession, not human presence or a
complete semantic review.

Get the subject with `approval-subject`. Each approver reviews the actual
subject and runs `approve` on a trusted machine with their enrolled key. The
command does not create keys or manufacture identity. Risk approvals require a
future ISO timestamp via `--expires`; changing terms requires reapproval.

Plan and spec approval must precede evidence execution. A new policy digest,
changed subject, unknown signer, altered signature or expired approval fails
closed. To revoke an SSH signer, remove its key from the external policy and
roll out the new pinned policy. This invalidates previous-policy artifacts;
collect new approvals/evidence under the new policy.

## GitHub and GitLab

Adapters are read-only. Configure provider kind, HTTPS API URL, repository and
role-to-account lists in the external policy. Supply GITHUB_TOKEN or GITLAB_TOKEN
only to the protected collector/check worker.

For GitHub an enrolled human submits an APPROVED review containing the exact
`approval-subject` marker on a separate line. The review must target the current
head. For GitLab the human posts that marker in a non-system note and approves
the MR; both must exist and the account must be active and non-bot.

```sh
atipspec sync-approvals reset acceptance --number 42 \
  --identity approval-collector --key /secure/collector-key \
  --policy /secure/company.toml
```

The collector signs the normalized record, and every trusted gate reads the
provider again. Revoked or changed reviews fail. A stale head, API error,
unsupported approval endpoint or insufficient token access fails closed.
GitLab approval API access depends on deployment/tier. Self-hosted API origins
must be explicitly configured by the policy administrator.

The integrations are covered by mocked API contract tests. Live connection and
branch protection must be configured and tested in your actual organization.

API references: [GitHub reviews](https://docs.github.com/en/rest/pulls/reviews),
[GitLab approvals](https://docs.gitlab.com/api/merge_request_approvals/).

## CI before the merge

`github-local.yml` and `gitlab-local.yml` from `enterprise-init` run
`atipspec merge-check` as the pull request's check: make that job required on
the target branch. It fails while a delivery the branch touches is a draft or
not accepted, when the code at the head differs from the code a receipt
accepted, when the branch rewrites an earlier archive, changes a living spec
outside `deliver`, changes the accepted contract without its new acceptance,
or changes code outside `.atipspec/` that no delivery of the branch changed
after its base commit, such as code committed before `atipspec new`, unless
`exempt_paths` in the target branch's `config.yaml` exempts those files
(see the [CLI reference](reference/cli.md#atipspec-merge-check)). It fails
too while `.atipspec/framework/` is not what the pinned version installs,
since every phase prints those rules and workflows to the agent: run
`atipspec install --update` with that version. It warns, without blocking,
when the branch relaxes a policy of `config.yaml` against the target branch,
or changes `overview.md`, `glossary.md`, a decision (naming each decision
with its status), `adapter.json` or `teams.json`; and when the branch changes the contract or a decision that
affects it, the result shows the contract's acceptance and its channel. The job
checks out the branch head, not the provider's synthetic merge commit, with
full history, and nothing may write into the checkout before `merge-check`,
which judges the committed head. It installs the pinned verifier from outside
the checkout with `python -I`, so a `pip/` package or a wheel the candidate
commits is never loaded, runs no command from the candidate and needs no
credentials; the project's tests run in their own job. The GitLab job fetches
the target branch, so its `trust: required` applies. The GitHub job writes the
result to the job summary (`--format markdown`): a table of the deliveries the
branch touches with their state and ticket, then the checks. When the agent
opens the pull request at the user's request, its description carries the
ticket and `atipspec report <slug> --format markdown`. In local mode a receipt
is not authenticated: the check shows that the branch matches what was
accepted, not who accepted it, and how each approval was recorded (its
channel), not who gave it.

A limit to close with the provider, not with AtipSpec: the provider runs the
workflow the branch carries, so a branch can rewrite or remove the check.
Require it from outside the candidate: on GitHub, a ruleset that requires the
workflow from a protected repository, or CODEOWNERS on `.github/workflows/`
with required code owner review; on GitLab, a pipeline execution policy or a
compliance pipeline. Locally, Claude Code asks before its edit tools change
`.github/workflows/**`, `.gitlab-ci.yml` or its own settings (see [approval
permission rules](clients.md#approval-permission-rules)); that is no control
over the branch.

`exempt_paths` on the target branch lets a branch change the files it
matches with no delivery and no acceptance at all, under a policy too. Keep it
to files that need none, such as documentation, and review a change to it as a
change to the CI: it exempts nothing until it is merged into the target
branch, and `merge-check` warns on the branch that changes it. Which files
need no delivery is the user's decision: the installed rules tell the agent to
change `exempt_paths` only when the user asks. No approval hashes it, so
setting it on main sends no open delivery's proposal back to draft; a branch
that takes it in verifies and reviews again, as after any change of the tree.

A list to start from, for the user to adapt. Each entry is code that no human
approves in a delivery: a branch changes the files it matches with no
delivery at all.

```yaml
exempt_paths:
  - "docs/**"
  - "README.md"
  - "CHANGELOG.md"
  - "LICENSE"
  - "package-lock.json"
  - "uv.lock"
```

Documentation and lockfiles are the usual candidates. A lockfile sets the
versions of the dependencies the code runs with: exempt it only where
something else reviews dependency updates, such as a required review of the
update bot's pull requests. Never list code, tests, `.github/**`, `.claude/**`
or files the agent reads as instructions, such as `AGENTS.md` or `CLAUDE.md`;
a broad glob such as `**/*.md` matches those too.

The file that adds the job is code outside `.atipspec/` too, and no delivery
covers it: the pull request that adds it fails its own `merge-check`, while
the target branch has no `exempt_paths` yet, so merge it before you require
the job. A later change to that file, such as a new pin of
`ATIPSPEC_PACKAGE`, fails the same way: make it in a delivery or, if the user
decides it needs none, list that file alone in `exempt_paths` on the target
branch first, under the owners that review the CI; `.github/**` would let a
branch change every workflow with no delivery.

With `trust: required`, these jobs fail closed: run `merge-check --base <ref>
--policy /secure/company.toml` on the protected worker and require that result
instead. Given a policy, `merge-check` requires trusted acceptance even where
`trust: required` is not set, so a locally accepted receipt blocks. A receipt
is a file in the branch, so with the policy `merge-check` does not read it as
proof: it checks each delivery the branch archives again as `deliver` found
it. In a temporary clone with the repository's refs it checks out the commit
before the archive commit, restores the evidence, review, deferral terms and
approvals archived with the delivery, and requires its trusted check there to be `verified` (the product,
engineering and QA approvals and the attested evidence `deliver` requires;
provider reviews collected with `sync-approvals` are read again), that commit
to hold the code at the head, and the living spec at the head to be what
`deliver` writes from it, each requirement the delivery lists included. Commit the archive on its own right after `deliver`.
In provider mode it reads the pull request's reviews of that commit, or of the
new head when they carry the same marker lines: if pushing the archive
dismisses stale reviews, the reviewers approve the new head again with the
same lines. Under a policy the contract and the decisions that affect it
change only in a delivery checked this way, `contract.md` with a new decision
that affects it, accepted and approved by engineering; a draft contract is
first accepted with such a delivery, whose plan approval names it. A branch
that changes them otherwise blocks, whatever the local contract record says.

## CI execution and collection

Evidence jobs run candidate commands without signing keys. Use full history.
Protect the verifier package pin and workflows. A protected orchestrator must
authenticate the producer workflow, repository, source head, successful run
and artifact download before attesting.

In provider mode, `github-evidence-trusted.yml` is that orchestrator. Copy it
to the trusted repository; each candidate repository calls it at the pinned
commit with `github-evidence-caller.yml`, on `pull_request` only. Its
`produce` job checks out the pull request's head, deletes the evidence
committed to the branch, runs the Verify commands with read access only and
uploads the records it wrote. Its `attest` job runs no candidate command: it
takes those records by the artifact's ID, so an artifact another job of the
run replaced fails the download, requires exactly one passing record per
verified task of each active delivery, written on that head and tree, and
attests only them. The protected worker deletes the committed evidence too,
downloads from the latest successful run on the head the artifact of that
run's attempt, `atipspec-evidence-<attempt>`, copies only its `evidence/`
folders and runs `check` or `deliver` with `--number`, which fail on a record
`attest` did not attest; `ADOPTION.md` lists the commands. Verification
follows the spec and plan approvals: re-run the workflow on the head once they
are given, and QA approves after it. The attestation proves where, when and on
which head the evidence was produced, not that the code under test is
honest: it runs in `produce` and could fake its own results there, which the
review and the approvals at the head cover.

Run candidate commands on an ephemeral worker with no signing keys. Collect
and sign on a separate protected worker, using a fresh sanitized checkout and
`python -I -m atipspec` from an installed pinned package. `attest` signs, for
each task, the record in `evidence/` that finished last: delete the evidence
the branch committed (`atipspec.verify.clear_evidence`) before the producer
verifies and before the collector restores its records. Do not install or import
the candidate's implementation of AtipSpec. Never run candidate commands on the
collector. Isolating credentials in another step on a compromised persistent
worker does not suffice.

Each command has a complete output log whose hash is checked against the signed
evidence record, and so does the copied JUnit report when a task names one.
Retain those logs and reports with the evidence.

`attest` validates and signs records on behalf of that trusted collector. It
does not independently query or authenticate the claimed CI run URL. Signing
arbitrary author-provided JSON would defeat the trust boundary. Provider-native
artifact attestation/orchestrator integration is deployment-specific and must
be configured before using the protected acceptance script in production.

Require the protected acceptance result with branch protection or MR rules.
Local checks remain diagnostic and can report a blocker awaiting a trusted risk
exception. The CLI cannot prevent an administrator bypassing repository rules.

## Dossier and pilot

`report --format json|markdown|html` exports a traceability matrix, proof pointers
with what each one resolved to, the reviewer and the review's session, CI run
references, verified approvals, findings, policy/version information, and the
changes QA signs for: every changed file since the base commit with its status,
lines and whether it is outside the plan's scope, and the diff (up to 200 KB,
50 KB in markdown, with the full diff's size and sha256). HTML escapes
untrusted text. The signed artifacts are the evidence; a report's
own hashes are an index, not a separate certification. Retain both.

`pilot init <name>` creates a protocol with no measurements. The team completes
cohorts, eligibility, observation window, thresholds and accountable humans.
`pilot record` requires actual measurements with source and collector;
`pilot report` gives descriptive comparisons and flags incompatible windows.
Real performance claims require a completed pilot; generated examples are not
measurements. Use a matched baseline and the same defect observation window.
