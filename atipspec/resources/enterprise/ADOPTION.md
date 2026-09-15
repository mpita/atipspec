# Organization adoption

These are reviewable examples, not an already configured trust service.
Install a pinned AtipSpec wheel in a protected environment. The candidate
checkout must not provide the verifier, trust policy or signing credentials.

1. Enroll actual human identities and public keys for product, engineering, QA
   and risk. Keep CI/collector keys separate. Set the `owner` to the actual
   delivery owner. Key custody and human-account enrollment are organizational
   responsibilities; SSH signatures cannot distinguish a person from an agent
   with access to the same key.
2. Edit `policy.example.toml`, replace every placeholder, and move the policy
   outside the checkout to an administrator-managed location. Set its version,
   repository and corporate contract rules. Pin its SHA-256 in a protected CI
   variable (`ATIPSPEC_POLICY_SHA256`). Do not read that pin from the PR/MR.
3. Add the local GitHub/GitLab verification example to a pilot repository. Pin
   `ATIPSPEC_PACKAGE` to your immutable wheel or released version. The examples
   require Python 3.11+, Git and OpenSSH with `ssh-keygen -Y` support.
4. Configure branch protections / approval rules and require the protected
   acceptance result. Protect policy, workflow and verifier changes with owners.
   Fetch full history and check the actual source head; do not substitute the
   provider's synthetic merge commit for the approved source commit.
5. Build a trusted producer/collector boundary. Candidate tests run on an
   ephemeral worker without signing keys or approval credentials. A separate
   protected collector verifies the producer workflow identity, repository,
   source SHA and run/artifact provenance, then attests the results. Never sign
   arbitrary JSON supplied by a PR or an unauthenticated artifact download.
   `attest` validates and signs records; the CI orchestrator authenticates their
   producer. A separate job on the same compromised persistent host is not an
   isolation boundary. Keep keys off candidate execution machines.
6. Retain the signed evidence, signed approvals and exported dossier as CI
   artifacts. The generated hashes index the artifacts; the report itself is
   not an independent signature or certification. Configure retention to match
   your contracts. Revalidate source changes and re-obtain QA acceptance.

## Provider mode: no signing keys

`policy.provider.example.toml` and `github-evidence.yml` set up the mode
most organizations can run in an afternoon. The evidence workflow runs the
candidate's commands without any key and attests the evidence records with
GitHub artifact attestations. The protected acceptance worker, with a
read-only `GITHUB_TOKEN`, a pinned `gh` binary and the policy pinned by
digest, runs:

```sh
python -I -m atipspec check password-reset --policy /secure/company.toml --number 42
python -I -m atipspec deliver password-reset --policy /secure/company.toml --number 42
```

It reads the PR approvals live (product, engineering and QA accounts from
`[provider.roles]`, each with the `approval-subject` marker on its own line
in an APPROVED review at the current head), verifies each evidence record
with `gh attestation verify --owner --signer-workflow`, and fails closed on
any API error, revoked review, changed head or digest mismatch. `verify`
must run in the attested workflow, after the spec and plan approvals.

Not available in provider mode: risk exceptions that defer a blocker or
major finding, because the provider cannot carry an expiry. Fix the finding,
or run ssh mode for that delivery.

Pull requests from forks: GitHub gives `pull_request` workflows from forks a
read-only token and no OIDC token unless the repository setting "Send write
tokens to workflows from pull requests" is enabled, so the evidence workflow
produces no attestation and the gate fails closed. Enable that setting only
if your organization accepts it, or keep contributors on branches of the
repository. Never switch the workflow to `pull_request_target`: it would run
the candidate's commands with the base branch's permissions and secrets.

## Human approvals with SSH

Each approver runs these on their own trusted machine with their own enrolled
key, after inspecting `approval-subject`, the spec/plan or full review packet.
The developer's agent must never sign on a person's behalf.

```sh
atipspec approval-subject password-reset spec
atipspec approve password-reset spec --identity product-owner@example.com \
  --key /secure/personal-key --policy /secure/company.toml
# engineering signs plan; QA signs acceptance AFTER CI evidence is attested.
atipspec approve password-reset exception:F1 --identity risk-owner@example.com \
  --key /secure/personal-key --policy /secure/company.toml \
  --expires 2026-12-01T00:00:00Z
```

A changed subject, changed policy, removed signer, invalid signature or expired
exception no longer satisfies the gate. Retain earlier approvals if your
organization needs a historical audit trail. `approve` replaces the same
identity's same-phase local record; Git/CI retention preserves revisions.

## GitHub and GitLab (read-only adapters)

Run `approval-subject <slug> <phase>` and give that exact marker to a human
reviewer. It contains delivery, phase, subject digest and current head SHA.

- GitHub: the enrolled human includes the marker on its own line in an
  APPROVED PR review at that head. A bot or the PR author cannot qualify.
- GitLab: the enrolled human posts the marker as a non-system MR note and
  approves the MR. The adapter requires both the current approval and that
  note, and checks that the account is active and not a bot. API/tier access
  must expose approval state; unavailable APIs fail closed.

A protected collector, using a read-only GITHUB_TOKEN or GITLAB_TOKEN, runs:

```sh
atipspec sync-approvals password-reset acceptance --number 42 \
  --identity approval-collector --key /secure/collector-key \
  --policy /secure/company.toml
atipspec check password-reset --policy /secure/company.toml
```

The adapters never post messages, approve reviews or merge. Every trusted gate
re-fetches remote approvals to detect revocation. API outages fail closed.
Provider approvals bind to the exact head; after a new commit obtain new
markers and approvals. SSH spec/plan approvals bind to their content and can
survive unrelated code commits. Plan/spec approval must precede verification.

## Pilot

```sh
atipspec pilot init quality
# Complete .atipspec/pilots/quality/protocol.md with your real team first.
atipspec pilot report quality
```

Collect matched baseline and AtipSpec deliveries, human review/rework time,
escaped defects with the same observation window, and executed-test coverage.
Use `pilot record --help` for required fields. Unknown is not zero. The tool
starts with no observations and does not fabricate an improvement claim.
