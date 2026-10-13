# AtipSpec design

AtipSpec separates planning assistance, local technical checks, and trusted
acceptance. Each has a different authority and a different failure mode.

## Three lifetimes

The architecture contract defines local structural rules. Living specs preserve
capability-scoped requirement and criterion IDs across changes. Deliveries hold
the proposed specification, tasks, test mappings, evidence, technical review,
risk exceptions and approvals. Archival preserves an acceptance receipt.

The CLI computes state from these artifacts and Git. A `task-done` record is
the assistant's declaration of progress, not semantic correctness. A command
exit code records an execution result, not complete test coverage. A review proof pointer is a claim
that the technical reviewer and human QA must assess.

## Local acceptance

The human decides in the conversation; the assistant records the decision
with `atipspec accept`. There are three decisions: the proposal (scenarios,
approach, tests and risk; the spec, for legacy deliveries), the reviewed
result, and the contract with the decisions that affect it, once per project.
None is added by the mechanism below; the client's permission prompt confirms
the same decision.

Each decision is presented by a view that prints an **approval code**:
`proposal <slug>`, `report <slug>` or `proposal contract`. The code is the first
40 bits of the content's sha256 in Crockford base32 (`XXXX-XXXX`), easy to read
and dictate; typing ignores case and the hyphen. It is not a secret. It binds
the record to the version presented: if the content changed in between,
`accept --code` refuses without revealing the current code. It makes the
client's permission prompt show what is being approved, and it makes the
assistant go through the presentation view.

The record stores the hash of the accepted content, per-file digests, the code,
who (`--by`, a declared label that defaults to git's identity), when, and the
**channel**: `terminal` when someone typed the code at the CLI prompt in an
interactive terminal with no agent marker; `client-permission` when Claude Code
is the only agent marker, it does not run through the Agent SDK or `claude -p`
(which may not load the project's settings, and whose prompts go to a program),
the interpreter received the command line its ask rule matches (`atipspec
accept` or `python -m atipspec accept`) and the CLI found its AtipSpec
permission rules intact in `.claude/settings.json`; `assistant` otherwise.
Claude Code passes its marker to every process it starts, so another agent's
marker next to it means that agent ran the command, outside Claude Code's
rules. Agent markers in the environment (`CLAUDECODE`, `CODEX_SANDBOX`,
`CODEX_THREAD_ID`, `COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT`) can
only lower the channel, never raise it. The gate compares the hash with the
files on every run, so a change made after the acceptance, by a model or by
anyone, is visible, names the file, and sends the delivery back to the person.
Guided deliveries need the proposal record; a spec and plan pair does not
replace it.
The contract's record, `.atipspec/approvals/contract.json`, hashes the contract
and each decision that affects it without their status lines: a decision added,
edited or marked accepted by hand afterwards leaves the acceptance outdated.
Delivery approvals hash `contract.md` whole, as signed approvals always have,
so the status lines `accept contract` writes leave them outdated; `proposal
contract` names those approvals before the human decides.
Records live outside the tree fingerprint and carry no signature: they bind
content and state the channel, not identity.

What this covers: a cooperative but hasty assistant that would record an
approval on its own through the normal path. It cannot do so without the code,
the record says how it was made, and with the Claude Code rules the client asks
the person first and denies its edit tools the approval and evidence records.
What it does not cover: an agent that sets out to bypass the protections, for
example by writing files from a script or deleting `review-rounds.json` with a
shell command, which restarts the round count from the `review.md` in the
folder, by running `atipspec accept` inside a
script or program Claude Code starts, such as an agent that sets none of the
markers (the CLI sees only its own process, so the record still says
`client-permission`), by running the command in a terminal without an agent
marker and typing the code itself, by starting the session outside the project
root so the settings do not load, or through managed settings or hooks that
answer permission prompts. `approval-subject` stays,
because provider mode needs it; computing a hash was never the barrier. The
authenticated path is an external trust policy.

## Two gates

Without external trust, `check` validates grammar, coverage, the person's
acceptance records, the declared scope, the form of the criteria, exact
evidence commands/results, the tests named per criterion, freshness and local
contract rules. Success is **checked**.
Because candidate files are author-editable, it does not claim authenticated
execution or human acceptance. Without a policy, `deliver` also requires the
recorded acceptance of the current result.

Both gates fail closed. The base commit, contract rules and freshness come
from git, so without git `check` is an error rather than a warning. A plan must
declare a scope narrower than the repository (`strict_scope`), and
requirements and criteria must pass the form, vague-term and fit-criterion
checks (`strict_criteria`); both are on for new projects. `trust: required` in `config.yaml` turns a missing policy into an
error and disables local acceptance, and a branch cannot drop it for its own
merge. Invalid policy values stop every command before it runs.

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
artifact attestation that binds its digest to the candidate repository, the
pull request, and a trusted workflow outside the candidate repository pinned
to one commit, verified with the platform's own tool. The workflow lives
outside because in a pull request the platform runs the workflows the pull
request carries: a workflow of the candidate repository is part of the change
it would attest. Provider mode was chosen as the
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

`deliver` changes the delivery's own fingerprint (the folder moves and the
living spec absorbs it), so the receipt also stores `code_tree`: the hash of
everything outside `.atipspec/`. Nothing AtipSpec writes afterwards changes it,
and any code change does. `merge-check` compares it with the branch head
before the merge, and checks that every open delivery the branch touches is
accepted: the gap between the acceptance and the merge is closed by the same
hash, not by trust in the branch.

## Durable identities

Living specs merge by requirement ID, keeping criterion IDs. Titles can change
without changing identity. `atipspec ids` gives each delivery a short random
prefix no ID visible in the checkout or the team's refs uses, so parallel
branches do not collide; the numbered IDs of legacy deliveries, allocated
above the maximum found in living, active and archived artifacts, stay valid.
Three-way comparison detects concurrent edits to the same requirement or
criterion ownership collisions, and `check` reports duplicate IDs. Every
requirement and acceptance criterion receives a stable ID from the start.

## Operational limits

Contract rules check paths, patterns, dependencies and required commands; they
do not prove architectural correctness. Test mappings and proof pointers need
semantic review. Git excludes ignored files from source fingerprints, so keep
build inputs and lockfiles tracked and reproduce the execution environment.
Reports are indexes and summaries of signed evidence, not certifications.
Archived reports describe historical acceptance. `merge-check` compares the
whole code tree, so bringing the target branch into a delivered branch, or any
later fix, reopens the delivery: revert the archive commit, then verify,
review, accept and deliver again. Bring in the target branch with a merge
before the final verification; one delivery per branch keeps that cheap. In local mode the
receipt is a declaration in the branch: an edit to its `code_tree` shows in the
pull request's diff. With a trust policy, `merge-check` does not take the
receipt's word: it checks the delivery again at the commit before the archive
commit, with the files archived with it, as `deliver` did (in provider mode
with the pull request's reviews of that commit), requires that commit to hold
the code at the head, and compares the living spec, each requirement the
delivery lists included, with what `deliver` writes from it. Pilots report actual sourced
observations with sample sizes and limitations; they do not invent ROI.
