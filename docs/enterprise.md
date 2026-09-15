# Enterprise acceptance

AtipSpec separates **checked** (local structural/technical checks) from
**verified** (trusted evidence and human acceptance). `deliver` requires verified.

## Local acceptance and trusted acceptance

Without a policy, `atipspec accept` records what a person accepted (spec,
plan, contract) and the gate detects later edits. That is drift detection: the
record proves the content, not the identity. With a policy, the gate ignores
those records and requires the signed, role-bound approvals below.

## Two trust modes

| | `mode = "ssh"` | `mode = "provider"` |
| --- | --- | --- |
| Human approvals | detached SSH signatures from enrolled keys (`approve`), or provider reviews collected and signed by a collector key (`sync-approvals`) | read live from the PR or MR by the protected worker with a read-only token; no collector |
| CI evidence | signed by an enrolled CI collector key (`attest`) | attested by the evidence workflow with GitHub artifact attestations and verified with a pinned `gh` |
| Keys to enroll | one per human role, one for CI, one for the collector | none |
| Risk exceptions | `approve <slug> exception:Fn --expires` | not available: fix the finding or use ssh mode |
| Policy | `schema = 1` | `schema = 2`, `[provider.roles]` and `[attestation]` |

Provider mode is the default recommendation: it needs a protected worker
with `GITHUB_TOKEN`, the pinned policy and the pinned `gh`, and nothing else.
The gate re-reads the provider on every run and fails closed on any API
error, revoked review, changed head or digest mismatch. `check`, `deliver`
and `report` take the PR or MR number with `--number` or
`ATIPSPEC_PR_NUMBER`. `enterprise-init` writes `policy.provider.example.toml`
and `github-evidence.yml`. SSH mode stays the strict option for
organizations that need signatures under their own key custody, GitLab
attestations, or risk exceptions.

The policy binds the attestation to one workflow of the policy's own
repository. Pull requests from forks get no OIDC token by default, so their
evidence carries no attestation and the gate fails closed; enable GitHub's
"send write tokens to workflows from pull requests" only if you accept it,
and never use `pull_request_target` for the evidence workflow.

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

## Roles and approval subjects

| Phase | Role | Bound content |
| --- | --- | --- |
| spec | product | specification and architecture contract |
| plan | engineering | specification, plan and architecture contract |
| decision:DEC-nnn | engineering | decision document and changed contract |
| exception:Fn | risk | tree, review, deferral terms, expiry |
| acceptance | qa | tree, review, deferral terms and evidence artifacts |

The declared delivery owner cannot approve their own work. Provider adapters
also reject the actual PR/MR author. For SSH approvals, administrators must
ensure `owner` corresponds to the real owner and that enrolled human keys are
not accessible to developer agents or service accounts. A valid signature
proves key possession, not human presence or a complete semantic review.

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

## CI execution and collection

The generated GitHub and GitLab jobs run local verification without signing
keys. Use full history. Protect the verifier package pin and workflows. A
protected orchestrator must authenticate the producer workflow, repository,
source head, successful run and artifact download before attesting.

Run candidate commands on an ephemeral worker with no signing keys. Collect
and sign on a separate protected worker, using a fresh sanitized checkout and
`python -I -m atipspec` from an installed pinned package. Do not install or import
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

`report --format json|markdown|html` exports a traceability matrix, proof pointers,
CI run references, verified approvals, findings and policy/version information.
HTML escapes untrusted text. The signed artifacts are the evidence; a report's
own hashes are an index, not a separate certification. Retain both.

`pilot init <name>` creates a protocol with no measurements. The team completes
cohorts, eligibility, observation window, thresholds and accountable humans.
`pilot record` requires actual measurements with source and collector;
`pilot report` gives descriptive comparisons and flags incompatible windows.
Real performance claims require a completed pilot; generated examples are not
measurements. Use a matched baseline and the same defect observation window.
