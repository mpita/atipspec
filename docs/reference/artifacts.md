# Artifacts

Specifications and plans use Markdown with small YAML frontmatter. Evidence,
approval records and report receipts use JSON; signatures are detached SSH files. The CLI parses a
few line shapes and ignores HTML comments and fenced code, so the templates
can carry guidance the model deletes as it writes.

## Identifiers

| Kind | Format | Scope |
| --- | --- | --- |
| Delivery, capability, initiative, decision slug | `[a-z0-9-]`, e.g. `password-reset` | project |
| Requirement | `REQ-PRICING-7KQ2M-001`, from `atipspec ids`; `REQ-001` in legacy deliveries | capability, stable across deliveries |
| Acceptance criterion | `AC-PRICING-7KQ2M-001`; `AC-001` in legacy deliveries | capability, stable across deliveries |
| Task | `T1` | the delivery |
| Finding | `F1` | the review |
| Decision | `DEC-001` | project, never reused |

Teams that work on one capability in parallel take IDs from `atipspec ids
<capability>`: the capability in capitals, a five-character token in Crockford
base32 (no I, L, O or U) that no visible ID uses, and a number; each delivery
numbers its further requirements and criteria with its token, `-002`, `-003`.
The longer IDs of earlier versions, with 32 hexadecimal characters, and the
numbered IDs of [legacy deliveries](legacy.md#ids) stay valid and are never
renumbered. Imported IDs are derived from the title the same way.

## `spec.md`

A guided delivery's `spec.md` (`schema: 2`, what `atipspec new` creates) holds
what the change is for and what it decides. Its requirements live in
`specs/<capability>.md`, and `requirements` lists their IDs:

```markdown
---
title: "Password reset"
status: draft          # `atipspec accept <slug> proposal` sets ready when it records the human's approval
capability: auth
impact: []
owner: ana
ticket: SHOP-12        # a key, an issue number such as "#42" or an https URL; not part of the approval
initiative: null
base: 9f2c1e...        # the full id of the commit `new` recorded; check compares with it, so it never changes
created: 2026-09-12T15:41:45Z
schema: 2
change_id: 0c5e7a...
requirements: [REQ-001, REQ-002, REQ-004]
risk: normal
---

# Password reset

## Intent

A user who forgot the password requests a reset link by email and sets a new
password with it, without contacting support.

## Out of scope

- Password policy changes.

## Quality attributes

- REQ-004: p95 below 300 ms with 100 requests per minute

## Assumptions

- The link is single-use.

## Open questions

- None
```

| Section | What `check` asks |
| --- | --- |
| `## Intent` | the actor, the trigger, the observable result and how the user will know it worked; empty, or only `TBD`, `TODO` or `...`, it is a todo that blocks the proposal until the proposal is approved, and a warning afterwards |
| `## Out of scope` | at least one item, `- None` included; with none it is undecided, a todo until the proposal is approved |
| `## Quality attributes` | one `- REQ-...: limit` line per requirement of this change that states a limit, or `- None`; a line that names none is a todo until the proposal is approved and an error afterwards. The requirement's criteria need a fit criterion (see [writing criteria](spec-quality.md#quality-attributes-and-fit-criteria)) |
| `## Assumptions` | each item is a default the human confirms when approving |
| `## Open questions` | any item blocks the proposal |

`risk` is `low`, `normal` or `high`: what the gate asks of the plan, the
evidence and the review (see [risk](../flow/spec.md#risk)). It is part of what
the proposal's approval hashes. A missing `risk` counts as `normal`; another
value is an error.

A guided fix (`kind: fix`, what `new --kind fix` creates) has the same
frontmatter. Its `requirements` names the accepted requirements of the
capability it corrects, and its body states the defect instead of the intent:

```markdown
## Defect

Observed: a link created 26 hours ago still opens the reset form.

Expected: the page shows "link expired", as REQ-002 states.

Reproduction: `python -m pytest tests/auth/test_reset.py -k expired`

## Assumptions

- None

## Open questions

- None
```

`Observed:` and `Expected:` are required (a todo until the proposal is
approved, a warning afterwards); `Reproduction:` is advised. The labels are
also read in Spanish (`Observado`, `Esperado`, `Reproducción`) and Portuguese
(`Observado`, `Esperado`, `Reprodução`), and the heading as `Defecto` or
`Defeito`. A fix has no `## Intent`, `## Out of scope` or `## Quality
attributes`. See [fix](../flow/fix.md#what-check-requires-from-a-fix) for what
`check` asks of its requirements and plan.

Approved means that the local approval record matches the current content; the
`status` line does not count. Under a trust policy, whose signatures are the
approval, `check` counts the `status` that people set instead, while
`proposal` and `accept proposal` still count only the local record. A delivery
created with these sections, which `baseline.json` lists under `sections`,
keeps them: deleting one is a todo, like an undecided one. A delivery created
before 0.3.0 without `## Out of scope` or `## Quality attributes` gets a
warning. On an approved delivery these warnings wait for the next change to
its proposal: editing `spec.md` only for them voids the approval. The section
names are also read in Spanish (`Intención`, `Fuera de alcance`, `Atributos de
calidad`) and Portuguese (`Intenção`, `Fora do escopo`, `Atributos de
qualidade`).

A [legacy delivery](legacy.md)'s `spec.md` holds its requirements itself, in
the format that page shows.

## `plan.md`

```markdown
---
scope: ["shop/auth/**", "tests/auth/**"]
---

# Plan: Password reset

## Approach

## Tasks

### T1: Task title
Covers: REQ-AUTH-7KQ2M-001, REQ-AUTH-7KQ2M-002
Tests: AC-AUTH-7KQ2M-001, AC-AUTH-7KQ2M-002

### T2: Observed only
Covers: REQ-AUTH-7KQ2M-003
Manual: AC-AUTH-7KQ2M-004
Verify: none

## Final verification

Report: .atipspec/tmp/junit.xml
Proof:
- AC-AUTH-7KQ2M-001: tests/auth/test_reset.py::test_registered_email_sends_link
Verify:
- `python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml`
- `ruff check .`
```

Parsed: `### Tn: title`; a `Covers:` line with REQ ids; `Tests:` and `Manual:`
lines with the criteria the task proves by a test or by a person's
observation, following each criterion's `[manual]` mark; and an optional
`## Final verification` section (also `Verificación final` or `Verificação
final`) with its `Verify:` list, which `verify` runs once for the finished
candidate. A task may carry its own `Verify:`, a development check, or
`Verify: none` when only an observation proves it. `Verify:` is followed by
list items (backticks optional) or the word `none`. An optional `Report:` line
names the JUnit XML the commands write, at a relative path inside the project
that git ignores (`check` reports any other path as an error, and a path
Windows reads as absolute or outside the project, such as `/x`, `C:\x` or
`..\x`, on every platform), and an optional `Proof:` line followed by
`- AC-...: test id` items that `check` verifies against the evidence (see
[build](../flow/build.md)); with `require_proof: true` or `risk: high`, every
criterion under `Tests:` needs one, and its verification a `Report:`. In a
plan with a final verification, `Report:` and `Proof:` go in that section.
`scope` in the frontmatter lists globs of the files the tasks may change, with
the [glob syntax of the contract rules](contract-rules.md#globs). With
`strict_scope: true`, the default, an empty or missing `scope`, or one whose
globs together match every path, is an error; touched files outside it,
deletions included, are errors too (warnings with `strict_scope: false`, where
an empty `scope` declares nothing), and the review packet lists them. Files
under `.atipspec/` never count, nor do the client skills and permission rules
AtipSpec installs while they hold only its content; removing one of those
rules counts.

A guided proposal's approval binds the plan's frontmatter, approach and final
verification, not its `## Tasks` section: tasks split or added under them need
no new approval. A plan without a final verification is bound whole.

## `review.md`

Written only by the reviewer.

```markdown
---
tree: <fingerprint from the packet>
reviewer: <client or model>
session: isolated        # or shared; a review without it counts as shared
---

## Criteria
- AC-001: PASS. tests/auth/test_reset.py::test_registered_email_sends_link
- AC-002: PASS. src/auth/reset.py:42-48
- AC-003: FAIL. precise gap

## Findings
- F1 [blocker]: text
- F2 [major]: text
- F3 [minor]: text

## Notes
```

Every criterion needs exactly one verdict. A `PASS` needs a pointer `check`
resolves: a test that passed in the current evidence's JUnit report, a
`path:line` or `path:line-line` that exists in a file of the candidate,
outside `.atipspec/` and not ignored by git (the delivery's evidence logs
count, as `evidence/logs/<file>.log:<line>`), or a `path::test` whose file
holds that name as a word; for a `[manual]` criterion, a description of three
words or more also passes. A `FAIL` needs its reason. `reviewer:` is required. `session:`
is `isolated` or `shared`: a shared review is a warning, and an error with
`risk: high` or `require_isolated_review`. With `risk: low`, a criterion whose
test named in `Proof:` passed in the current evidence may have no verdict.
Blocker and major findings block;
deferring either needs a trusted risk approval with expiry. Minor findings
inform. See [review](../flow/review.md#what-the-gate-checks-in-reviewmd).

## `deferred.md`

```markdown
- F2: reason, and where it will be handled
```

Only findings can be deferred. An `AC-` or `REQ-` entry is an error.

## `brief.md`

The explore phase's output: Problem, Today, Options, Recommendation,
Questions for the user. Not parsed; included in the context.

## `evidence/<task>-<timestamp>.json`

Generated by `atipspec verify`, one file per run: `FINAL-...` for the final
verification, `T1-...` for a task's own commands. Schema version, delivery, task, result, tree
before/after (fingerprints that leave task titles out, so a renamed task's
evidence stays current), head, timestamps, environment and exact commands with exit codes,
duration, output tail, full log path and log hash; with a `Report:`, the copied
JUnit XML with its hash, the path it was read from and `fresh: true` (the
commands wrote it after `verify` deleted it), and every test case with its
status. The latest file per task counts. Evidence with a report but no `fresh`
mark, written by 0.2.x, is a todo until `verify` runs again. Trusted CI attestation adds signer, repository, policy digest, run URL
and a detached `.json.sig` signature. Unsigned files are local evidence only.
In provider mode the file is not changed: a GitHub artifact attestation from
the trusted evidence workflow covers its hash, and its `head` must be the
commit the protected worker checked out. Log and report paths are written
with `/` on every platform.

## `review-rounds.json`

Written by `atipspec accept <slug> proposal`, which starts it, and by
`atipspec review` and `atipspec run`: the approved agreement it
counts for, how many reviews were counted (packets for another candidate, the
first included), and the tree of the last packet. `check` takes only the review of that packet.
It is left out of the fingerprint, and the Claude Code permission rules deny
editing it with the client's edit tools; they do not stop a shell command from
deleting it. In a guided delivery created since 0.3.0 a missing file was
deleted, so `review` refuses and `check` fails until the human decides; in one
approved under a trust policy, `atipspec review` counts again from the
`review.md` in the folder, as the first review, and in one created before
0.3.0, whose `review.md` names a tree of the earlier fingerprint, from the next
packet. See [review rounds](../flow/review.md#review-rounds).

## `specs/<capability>.md`

The living spec of a capability: the current truth about its behavior, one
section per requirement with its scenarios.

```markdown
# auth

## Requirements

### REQ-AUTH-7KQ2M-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

#### AC-AUTH-7KQ2M-001: Registered email
- **GIVEN** a registered user with the email "ana@example.com"
- **WHEN** the user requests a reset for "ana@example.com"
- **THEN** the system sends a reset link to "ana@example.com" within 60 seconds

#### AC-AUTH-7KQ2M-002 [manual]: The email reads well on a phone
- **WHEN** the reset email is opened on a 375 px wide screen
- **THEN** the "Reset password" button is visible without scrolling sideways

### REQ-AUTH-7KQ2M-004 [remove]: Security questions

#### AC-AUTH-7KQ2M-009: Questions page removed
- **WHEN** a user opens "/account/questions"
- **THEN** the system responds with status 404
```

Parsed: `### REQ-...[ [remove]]: title` headings (levels 2 to 4); under each,
`#### AC-...[ [manual|invariant]]: title` scenario headings with one step per
line, `GIVEN`, `WHEN`, `THEN`, `AND`, `BUT` (or `INVARIANT` in an invariant,
and the Spanish and Portuguese step words), bold or not; and `- AC-...: text`
criterion statements, the legacy form. `Why:` lines and examples are for
people and the reviewer. `deliver` updates the file by stable ID, preserving
identity on rename, and removes a requirement marked `[remove]`. Every living
requirement and acceptance criterion has an ID from the start. A guided
delivery's `requirements` lists the ones it writes; see [writing
criteria](spec-quality.md) for what `check` expects of them.

## `baseline.json`, `progress.json` and `run.json`

`baseline.json`, written by `new`: the capability's living spec when the
delivery started (`content`), the commit (`head`) and the decided sections of
the new `spec.md` (`sections`). The delivery's `base` must be that commit, and
the proposal's diff and the comparison of `specs/` read the living spec as
that commit holds it; only a delivery created before 0.3.0, without
`sections`, compares with `content`. The proposal's approval hashes it.

`progress.json`, written by `task-done`: for each task, the note, the time,
the hash of the approved agreement with its `subject_version`, and the hash
of the task without its title. A task counts as complete while both match.

`run.json`, written by `atipspec run`: the runner's checkpoint, with its
state, phase, elapsed time, correction rounds and the agreement it runs for.
`progress.json` and `run.json` are left out of the tree fingerprint.

## `contracts.json` and `sources/`

A guided delivery's `contracts.json` (`schema: 1`) lists the contracts it
pinned from other repositories, with `contract-pin` or, for the system
repository, at `new`: each with `name`, `repository`, `revision` (a full
commit id), `path` and the `sha256` of its content. The proposal's approval
hashes it.

`sources/<sha256>.md` keeps each document `spec-bind` imported, as it was;
`sources` in `spec.md` lists them and `## Import review notes` says what to
check before approving.

## `decisions/DEC-nnn-<slug>.md`

```markdown
---
id: DEC-003
title: "Use httpx for outbound HTTP"
status: accepted        # proposed, accepted, superseded, rejected; set by `accept contract` when it affects the contract
affects: [contract:dependencies, notifications]
supersedes: null
date: 2026-09-12
---

## Context
## Decision
## Alternatives
## Consequences
## Revisit when
```

`context` loads accepted decisions whose `affects` names the delivery's
capability, an impact entry, `contract` or `*`, or is empty (everything). A
decision whose `affects` names `contract`, `contract:<section>` or `*`, or is
empty, is accepted with the contract: `atipspec accept contract --code <code>`
sets its status. Such a decision counts only with the content the contract's
recorded acceptance names, so one marked `accepted` by hand is neither part of
the contract nor loaded by `context`. Without a record, `context` loads them by
their status only when the contract itself was accepted before 0.3.0.

## `initiatives/<slug>/roadmap.md`

```markdown
## Deliveries
- orders-api: Orders API
- orders-screen: Orders screen

## Interfaces
```

Parsed: `- <slug>: title` lines under `## Deliveries`. Status per delivery
is derived: pending, its current status, or delivered.

## Derived status of a delivery

| Status | Meaning |
| --- | --- |
| `draft` | the proposal (a legacy delivery: the spec) is not accepted for its current content |
| `ready` | accepted, but the plan has no task |
| `planned` | plan with tasks, none recorded; a legacy plan with `approve_plan` needs its acceptance too |
| `in_progress` | some tasks recorded with `task-done` (or, in a legacy delivery, a commit marker) |
| `implemented` | every task recorded, gate not green |
| `checked` | local checks green; the result is not accepted |
| `accepted` | local checks green and the current result's acceptance recorded; `deliver` may run |
| `verified` | trusted gate green with approved policy, signed CI evidence and human approvals |
| `delivered` | merged into the living spec and archived |

## Approvals and receipts

`approvals/local-<phase>.json` is written by `atipspec accept`: `local-proposal.json`
and `local-result.json` for guided deliveries, plus `local-spec.json` and
`local-plan.json` for legacy ones, fixes created before 0.3.0 included. Fields (schema 2):

| Field | Meaning |
| --- | --- |
| `kind`, `delivery`, `phase` | `local-acceptance`, the slug and the phase |
| `subject` | sha256 of the accepted content; `check` compares it on every run |
| `subject_version` | how the subject was hashed: 2 since 0.3.0; a record without it is version 1 |
| `code` | the approval code that was presented and passed with `--code` |
| `files` | the digest of each part of the subject, so drift names the file, or the requirement, that changed |
| `accepted_at`, `by`, `head` | when, the declared `--by` label (git's identity by default), the commit |
| `channel`, `client` | `terminal`, `client-permission` or `assistant`, and the client that ran it |

Version 2 hashes of a guided proposal's capability living spec only each
requirement the delivery lists, as `specs/<capability>.md#REQ-...`: `check`
and `merge-check` block a change of any other one, so taking main in voids no
approval (see [when main moves](../teams.md#when-main-moves)). Of
`teams.json` it hashes only the owners of the capability and `integration`,
under a trust policy too, and of `spec.md` everything but `status` and
`ticket`. The acceptance of a result also hashes, as `integrated`, the merge
base with the integration branch (the policy's under a policy) when the
delivery puts back what that branch changed: its dossier shows those files
against that commit, so taking the branch in again afterwards voids the
acceptance, even with the tree kept. Version
1 hashed both files whole; `check` compares each record with the version it
was written with. Records written by 0.2.x (schema 1, without code, files,
channel or `subject_version`) stay valid while their content does not change;
`status` shows them as `channel not recorded`. They are drift detection for
the local gate and are ignored under a policy. `progress.json`'s `task-done`
records and signed approvals carry `subject_version` the same way.

`.atipspec/approvals/contract.json` is written by `atipspec accept contract`:
kind `contract-acceptance`, the subject hash, the code, `content` (the digest of
`contract.md` and of each decision that affects the contract, without their
status lines), the decision IDs, who, when, the commit and the channel. A
decision added, edited, withdrawn or marked accepted by hand afterwards leaves
the acceptance outdated until the contract is presented and accepted again.

Signed `approvals/*.json` records phase, identity, role, approved timestamp,
subject hash, repository, policy digest and optional expiry. Each has a `.json.sig`
SSH signature. Provider records also carry PR/MR identity and source URL, and
are revalidated against the provider at acceptance time and by `merge-check`. `reports/acceptance.json`
is the archived receipt and artifact index: `accepted`, `acceptance_mode`
(`local` or `trusted`), the gate's checks, the traceability matrix, the
approvals, the artifact digests, `kind`, `risk`, `lead_time` (`created`,
`proposal_accepted_at`, `result_accepted_at`, `hours` and `complete`: the
wall-clock hours from the delivery's creation to the acceptance of its
result; under a policy, to the latest signed acceptance), `tree` (the
delivery's fingerprint),
`review` (reviewer, session and tree), `changes` (the base commit, each
changed file with its status, lines and object id, `outside_scope`, the
diff's `diff_bytes` and `diff_sha256`, the diff text staying in git history,
and `integrated`, the integration ref and the files it brought, left out of
the rest), `ticket` and `ticket_url`,
`code_tree`, the hash of everything outside `.atipspec/` when it was
delivered, `living_spec`, the digest of the living spec `deliver` wrote, and
`living_requirements`, the text of each requirement the delivery lists as
`deliver` wrote it there (`null` for one it removed).
Each row of the matrix carries `pointer`, what its PASS verdict resolved to.
Receipts written before 0.3.0 have no `review`, `changes`, `pointer`, `kind`,
`risk` or `lead_time` and still render.
`merge-check` compares `code_tree` with the branch head and `living_spec` with
the living spec there, and holds each listed requirement to the text
`living_requirements` records, as the commit that archived the delivery added
it, even when the text `deliver` wrote was never committed whole; `check`
compares the living spec of an open delivery with those texts too, for the
requirements the archived `spec.md` lists. Receipts written before 0.3.0 have
no `code_tree` and block a branch that adds them. With a trust policy,
`merge-check` does not take the receipt's word for a trusted acceptance: it
checks the delivery again at the commit before the archive commit, with the
files archived with it, and compares the living spec, and each requirement
the delivery lists, with what `deliver` writes from that commit. Of the code,
`merge-check` takes as the delivery's the files `changes` lists and those it
names as `integrated`, as they were when it was delivered (with a policy,
those its dossier shows at that commit). See
[enterprise acceptance](../enterprise.md).
