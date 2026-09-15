# AtipSpec design

AtipSpec separates planning assistance, local technical checks, and trusted
acceptance. Each has a different authority and a different failure mode.

## Three lifetimes

The architecture contract defines local structural rules. Living specs preserve
capability-scoped requirement and criterion IDs across changes. Deliveries hold
the proposed specification, tasks, test mappings, evidence, technical review,
risk exceptions and approvals. Archival preserves an acceptance receipt.

The CLI computes state from these artifacts and Git. A commit marker records
work attribution, not semantic correctness. A command exit code records an
execution result, not complete test coverage. A review proof pointer is a claim
that the technical reviewer and human QA must assess.

## Local acceptance

`atipspec accept` writes, on a person's command, the hash of what they
accepted: the spec and the contract, or the spec, the plan and the contract.
The gate compares it with the files on every run, so a change made after the
acceptance, by a model or by anyone, is visible and sends the delivery back
to the person. The records live under `approvals/`, outside the tree
fingerprint, and carry no signature: they bind content, not identity. They
exist so the two stop points are facts the CLI can check rather than
sentences in a conversation.

## Two gates

Without external trust, `check` validates grammar, coverage, the person's
acceptance records, the declared scope, the form of the criteria, exact
evidence commands/results, the tests named per criterion, freshness and local
contract rules. Success is **checked**.
Because candidate files are author-editable, it does not claim authenticated
execution or human acceptance. `deliver` rejects a local-only check.

With an external versioned policy, success is **verified**. The gate additionally
requires signed CI evidence, product and engineering approvals preceding
verification, QA acceptance, criterion-to-task mappings, committed candidate
content and corporate rules. Blocker/major deferrals require signed risk
approval with expiry. Contract changes require new accepted related decisions,
with trusted engineering approval. Deleted contracts and missing history fail.

## Trust modes

Two modes carry the same gate. In `ssh` mode, authority is an enrolled key:
humans sign approvals, a collector signs CI evidence, and a compromised key
is revoked by rolling the policy. In `provider` mode, authority is the
provider's account and the CI platform's identity: the protected worker reads
the PR approvals live with a read-only token, and the evidence carries an
artifact attestation that binds its digest to the workflow that produced it,
verified with the platform's own tool. Provider mode was chosen as the
default recommendation because it removes key custody, the cost that kept
most organizations from running the trusted gate at all, while keeping the
properties that matter: content-bound approvals, revocation detected on every
run, evidence that cannot be replaced after the fact. What it cannot carry is
an expiry, so risk exceptions stay in ssh mode.

## Authority and cryptography

Detached SSH signatures bind exact artifact bytes to an identity enrolled in
an organization-controlled policy outside the candidate repository. Each
artifact also binds repository and policy digest. The policy's digest is pinned
in protected CI. A candidate-local allowed-signers file would not be a trust
anchor, so the gate refuses candidate-local policies.

A human key is only as independent as its custody. An agent with that key can
sign; no CLI can infer human presence from a signature. Human identity enrollment,
key isolation, installed verifier integrity and protected branch configuration
belong to the organization's trust boundary.

For GitHub/GitLab, a collector reads existing human approvals, checks role,
author separation and head/content marker, then signs the normalized record.
The gate re-fetches provider state on every check so a cached signed response
cannot override a revocation. Provider failures fail closed.

CI collection has a separate boundary: the orchestrator authenticates the
producer workflow, source SHA, run result and artifact provenance before the
collector uses `attest`. That command does not authenticate an arbitrary CI URL.
Candidate code must never execute with signing keys. Use ephemeral execution
and a separate protected collector; a second step on a compromised worker is
insufficient isolation.

## Freshness without circular hashes

The source/specification fingerprint excludes delivery evidence, review,
deferral, approval and report files. Those files describe the candidate and
must not recursively invalidate themselves. Approval subjects solve the
remaining dependency problem: risk approval binds the review and deferral terms;
QA acceptance binds those plus the signed evidence set. Changing excluded files
therefore invalidates the relevant acceptance even when the source hash stays
constant.

## Durable identities

Living specs merge by requirement ID, keeping criterion IDs. Titles can change
without changing identity. New IDs are allocated above the maximum found in
living, active and archived artifacts. Three-way comparison detects concurrent
edits to the same requirement or criterion ownership collisions. Every
requirement and acceptance criterion receives a stable ID from the start.

## Operational limits

Contract rules check paths, patterns, dependencies and required commands; they
do not prove architectural correctness. Test mappings and proof pointers need
semantic review. Git excludes ignored files from source fingerprints, so keep
build inputs and lockfiles tracked and reproduce the execution environment.
Reports are indexes and summaries of signed evidence, not certifications.
Archived reports describe historical acceptance. Pilots report actual sourced
observations with sample sizes and limitations; they do not invent ROI.
