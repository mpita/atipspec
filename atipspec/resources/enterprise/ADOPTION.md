# Organization adoption

These are reviewable examples, not an already configured trust service.
Install a pinned AtipSpec wheel in a protected environment. The candidate
checkout must not provide the verifier, trust policy or signing credentials.

1. Enroll actual human identities and public keys for product, engineering, QA
   and risk. Keep CI/collector keys separate. The product approver confirms
   the delivery's `owner` when signing the spec (`--owner`), and that owner
   cannot approve the later phases. Key custody and human-account enrollment
   are organizational responsibilities; SSH signatures cannot distinguish a
   person from an agent with access to the same key.
2. Edit `policy.example.toml`, replace every placeholder, and move the policy
   outside the checkout to an administrator-managed location. Set its version,
   repository and corporate contract rules. Uncomment `require_proof = true`
   to make every criterion under Tests name its JUnit test, and
   `require_isolated_review = true` to reject reviews from a shared session;
   no project can lift them. Uncomment `integration` with the target branch's
   full ref name, as the protected worker fetches it, so that what a
   delivery takes in from that branch is not its change in `check`;
   under a policy, `integration` in teams.json names no branch, but approvals
   still hash it, so editing it voids them. Pin its
   SHA-256 in a protected CI variable (`ATIPSPEC_POLICY_SHA256`). Do not read
   that pin from the PR/MR.
3. Add `github-local.yml` or `gitlab-local.yml` to a pilot repository and make
   its job a required check of the target branch. Pin `ATIPSPEC_PACKAGE` to
   your immutable wheel or released version; the job installs it from outside
   the checkout with `python -I`, so nothing the candidate commits is loaded.
   The job checks out the branch head with full history and runs `atipspec
   merge-check` before anything writes into the checkout: it fails while a
   delivery the branch touches is not accepted, or when the code at the head
   is not the code a delivery receipt accepted. Its job summary lists each
   delivery the branch touches with its state and ticket. It runs no candidate
   command and holds no credentials; run the project's tests in their own job. The examples require Python
   3.11+, Git and, for signatures, OpenSSH with `ssh-keygen -Y` support.
   The provider runs the workflow the branch carries, so a branch can rewrite
   or remove the check: require it from outside the candidate (on GitHub a
   ruleset that requires the workflow from a protected repository, or
   CODEOWNERS on `.github/workflows/` with required code owner review; on
   GitLab a pipeline execution policy or a compliance pipeline). `merge-check`
   also fails on code a branch changes outside `.atipspec/` that no delivery
   of the branch changed after its base commit, unless `exempt_paths` in the
   target branch's `.atipspec/config.yaml` matches it: list there only files
   that need no acceptance, such as documentation, and protect that file with
   owners too. A list to start from, which the user adapts:

   ```yaml
   exempt_paths: ["docs/**", "README.md", "CHANGELOG.md", "LICENSE", "package-lock.json", "uv.lock"]
   ```

   Each entry is code that no human approves in a delivery. Exempt a lockfile,
   which sets the dependency versions the code runs with, only where something
   else reviews dependency updates, and never code, tests, `.github/**`,
   `.claude/**` or the files the agent reads as instructions (`AGENTS.md`,
   `CLAUDE.md`), which a broad glob such as `**/*.md` also matches. The
   framework in `.atipspec/framework/` must be what the pinned version
   installs, or `merge-check` fails: run `atipspec install --update` with that
   version when you change the pin. The file that adds the job is code outside
   any delivery too: the pull request that adds it fails its own
   `merge-check`, while the target branch has no `exempt_paths` yet, so merge
   it before you make the job required. A later
   change to that file, such as a new pin of `ATIPSPEC_PACKAGE`, fails the
   same way: make it in a delivery or, if the user decides it needs none, list
   that file alone in `exempt_paths` on the target branch first, under the
   owners that review the CI; `.github/**` would let a branch change every
   workflow with no delivery.
4. Add `trust: required` to `.atipspec/config.yaml` and protect that file with
   owners (CODEOWNERS). Without a policy, `check` and `merge-check` then fail,
   local `accept` is disabled except for the contract, and `deliver` refuses;
   a branch cannot remove the requirement for its own merge, nor skip it by
   forking before it. The job from step 3 then fails closed: run `python -I -m
   atipspec merge-check --base <target> --policy /secure/company.toml` on the
   protected worker and require that result. With a policy, even without
   `trust: required`, it blocks a receipt accepted locally and checks each
   delivery the branch archives again as `deliver` found it: at the commit
   before its archive commit, with the evidence, review and approvals archived
   with it. Commit the archive on its own right after `deliver`; in provider
   mode add `--number`.
5. Configure branch protections / approval rules and require the protected
   acceptance result. Protect policy, workflow and verifier changes with owners.
   Fetch full history and check the actual source head; do not substitute the
   provider's synthetic merge commit for the approved source commit.
6. Build a trusted producer/collector boundary. Candidate tests run on an
   ephemeral worker without signing keys or approval credentials; `verify`
   and `run` withhold provider and CI job tokens, OIDC request tokens and the
   SSH agent from the Verify commands, but an approver never runs them where
   an unlocked SSH agent or another credential is within reach. A separate
   protected collector verifies the producer workflow identity, repository,
   source SHA and run/artifact provenance, then attests the results. Never sign
   arbitrary JSON supplied by a PR or an unauthenticated artifact download.
   `attest` validates and signs, for each task, the record in `evidence/` that
   finished last, so a record the branch committed could stand in for the
   run: the producer runs `python -I -c 'from atipspec.project import Project;
   from atipspec.verify import clear_evidence; clear_evidence(Project.find())'`
   before verifying, and the collector runs it on its checkout before it
   restores the producer's `evidence/` folders and calls `attest`. The CI
   orchestrator authenticates their producer. A separate job on the same
   compromised persistent host is not an isolation boundary. Keep keys off
   candidate execution machines.
7. Retain the signed evidence, signed approvals and exported dossier as CI
   artifacts. The generated hashes index the artifacts; the report itself is
   not an independent signature or certification. Configure retention to match
   your contracts. Revalidate source changes and re-obtain QA acceptance.

## Provider mode: no signing keys

`policy.provider.example.toml`, `github-evidence-trusted.yml` and
`github-evidence-caller.yml` set up the mode most organizations can run in an
afternoon. Provider mode is GitHub-only. In a pull request GitHub runs the
workflows the pull request carries, so the workflow that produces and attests
evidence lives outside the candidate repository:

1. Create a repository of the organization for it, such as
   `your-organization/atipspec-trusted`, protect its default branch so only
   administrators change it, and, if it is private or internal, set Settings >
   Actions > Access to "Accessible from repositories in the organization".
2. Copy `github-evidence-trusted.yml` there as
   `.github/workflows/atipspec-evidence.yml`, pin `ATIPSPEC_PACKAGE` and every
   action to a full commit SHA, and commit it.
3. In the policy, set `[attestation] signer_workflow` to that file and
   `signer_digest` to the full SHA of that commit; pin the policy's new
   SHA-256. A policy whose workflow is in the candidate repository, or whose
   commit is not pinned, does not load.
4. In each candidate repository, copy `github-evidence-caller.yml` to
   `.github/workflows/atipspec-evidence.yml`, calling the same commit. When
   the trusted workflow changes, update the commit in the policy and in the
   callers together.

The workflow's `produce` job checks out the pull request's head, deletes the
evidence committed to the branch, runs the candidate's Verify commands with
read access only and uploads the records it wrote. Its `attest` job runs no
candidate command: it downloads that artifact by the ID `produce` got for
it, so one that another job of the run replaced fails the download, checks
the records against the head (one passing record per verified task of each
active delivery, written on that head and tree, nothing else) and attests
exactly them. The worker verifies each record with `gh attestation verify
--repo <repository> --signer-workflow <signer_workflow> --signer-digest
<signer_digest> --source-ref refs/pull/<number>/merge
--deny-self-hosted-runners`, and requires the record's `head` to be the
commit it checked out.

The protected acceptance worker, with a read-only `GITHUB_TOKEN`, a pinned
`gh` binary and the policy pinned by digest, checks out the pull request's
head and takes the evidence of the latest successful run on it: the artifact
of that run's attempt, `atipspec-evidence-<attempt>`, and only its
`evidence/` folders, since another job in the caller, which the pull request
can edit, may upload other artifacts to the same run. That job can also
replace this one after `attest` took it, and then `check` fails on the
records `attest` did not attest:

```sh
# HEAD_SHA: the pull request's head.
git checkout --detach "$HEAD_SHA"
python -I -c 'from atipspec.project import Project; from atipspec.verify import clear_evidence; clear_evidence(Project.find())'
read -r run attempt <<EOF
$(gh run list --workflow atipspec-evidence.yml --event pull_request --commit "$HEAD_SHA" \
  --status success --limit 1 --json databaseId,attempt --jq '.[0] | "\(.databaseId) \(.attempt)"')
EOF
download=$(mktemp -d)
gh run download "$run" --name "atipspec-evidence-$attempt" --dir "$download"
for folder in "$download"/*/evidence; do
  cp -R "$folder" ".atipspec/deliveries/$(basename "$(dirname "$folder")")/"
done
python -I -m atipspec check password-reset --policy /secure/company.toml --number 42
```

It reads the PR approvals live (product, engineering and QA accounts from
`[provider.roles]`, each with the `approval-subject` marker on its own line
in an APPROVED review at the current head), verifies each evidence record's
attestation as above, and fails closed on any API error, revoked review,
changed head or digest mismatch. Verification must follow the spec and plan
approvals: once they are given, re-run the evidence workflow on the same head
(Re-run all jobs), then QA approves, since the acceptance subject includes the
evidence. Do not trigger the workflow on reviews: a new run changes the
evidence QA approved.

The attestation proves where, when and on which head the evidence was
produced, not that the candidate's code is honest: code under test runs in
the `produce` job and could fake its own results there. The review and the
approvals at the head cover that.

Run `deliver password-reset --policy /secure/company.toml --number 42` with
the same evidence where the archive can be committed, commit the archive on
its own and push it to the pull request. On the new head the worker runs
the check to require:

```sh
python -I -m atipspec merge-check --base origin/main --policy /secure/company.toml --number 42
```

It checks the delivery at the commit before the archive commit and reads the
reviews of that commit, or of the new head when they carry the same marker
lines: if the push dismisses stale reviews, each reviewer approves the new
head again with the same lines.

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
  --owner dev@example.com --key /secure/personal-key --policy /secure/company.toml
# --owner confirms the owner spec.md declares; that owner cannot sign later phases.
# engineering signs plan; QA signs acceptance AFTER CI evidence is attested.
atipspec approve password-reset exception:F1 --identity risk-owner@example.com \
  --key /secure/personal-key --policy /secure/company.toml \
  --expires 2026-12-01T00:00:00Z
```

A changed subject, changed policy, removed signer, invalid signature or expired
exception no longer satisfies the gate, nor does a spec approval that does not
confirm the current owner (one signed before 0.3.0: sign it again with
`--owner`). Retain earlier approvals if your
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
