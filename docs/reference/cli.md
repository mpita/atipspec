# CLI reference

All commands run from anywhere inside the project; AtipSpec finds the root by
looking for `.atipspec/config.yaml`. Every command but `init` first validates
that file (see [configuration](configuration.md)). Errors print `AtipSpec:
error: ...` and exit 1 (see [exit codes](#exit-codes)). The state of a
delivery is derived: `status` and `check` compute it from the files and git on
every run. What the CLI records, it writes as files in the repository:
approval records, `progress.json`, evidence, `review-rounds.json`, the runner's
`run.json` and the archive's receipt (see [artifacts](artifacts.md)).

**Who runs what.** In the guided conversation the assistant runs the commands;
you approve in the conversation, and the assistant records your decision with
`accept` (see [three human decisions](../flow/guided.md#three-human-decisions)).
Each section says when a command is the human's, CI's or a protected
worker's. `atipspec <command> --help` prints the options.

## Project

### `atipspec init`

```text
atipspec init [--name NAME] [--language LANG] [--client ID]...
```

Creates `.atipspec/` with `config.yaml`, `contract.md`, `overview.md`,
`glossary.md`, the folders `specs/`, `deliveries/`, `archive/`,
`decisions/`, `initiatives/`, the framework copy and the selected clients'
skills. For Claude Code it also merges the AtipSpec permission rules into
`.claude/settings.json` (see [approval permission rules](../clients.md#approval-permission-rules)).
Asks for what the flags do not provide when run in a terminal; uses
the folder name, `en` and no client otherwise. `--client` takes `claude`,
`codex`, `cursor`, `github-copilot`, `antigravity` or `gemini` and repeats.
`config.yaml` gets every policy written out, `trust: optional` included.
Outside a git repository it warns: the gate needs git and stays red without
it. It also warns when the repository has no `.gitignore`.

On an initialized project: shows the state and, in a terminal, a menu to add
or remove clients, update the framework, or change name and language. With
flags it applies them directly. You run it once per project.

### `atipspec install`

```text
atipspec install [--client ID]... [--update]
```

Installs the framework and the given clients' skills without overwriting
anything that differs, and merges the Claude Code permission rules. `--update`
replaces framework and skill files that differ from the installed CLI version,
removes the files under `.atipspec/framework/` that version does not install
(but those git ignores), and repairs missing permission rules. It also lists the policies in
`config.yaml` that differ from this version's defaults or are not set, and
never edits them. Without `--client` it asks in a terminal, or targets the
already installed clients with `--update`. Run it after upgrading AtipSpec.

### `atipspec status`

```text
atipspec status [SLUG] [--format text|json|markdown]
```

Without a slug: project name, branch, the contract's acceptance (who, when,
channel, code and decisions, or what changed since), an `approvals:` line with
the state of the client permission rules, living specs, every open delivery
with its derived status, owner, ticket (with its link, see
[tickets](../teams.md#tickets)), lead time (`open 5h`, or `accepted after 5h`
once its result is accepted), recorded approvals with their channel and next
action, a warning above `max_age_hours`, overlap warnings, initiatives with
progress, delivered slugs with their lead time, a `trust:` line when
`config.yaml` sets `trust: required`, and a warning when `origin/HEAD` names
an integration branch other than main or master and `teams.json` declares
none, since a CI checkout would not find it: the warning asks to declare it in
`teams.json`, and in the trust policy when one judges the merge (see [when
main moves](../teams.md#when-main-moves)). With a slug: the same
report as `check`, then the ticket, the recorded approvals with their channel,
as the project's status shows them, `review N of M` once `atipspec review`
has written a packet, and the next action.

`--format json` prints the same state as data (`schema: 1`): each open
delivery with its slug, title, kind, state, the exit code `check` would give,
owner, ticket and `ticket_url`, tasks, lead time, recorded approvals and next
action, the initiatives, each archived delivery with its owner, ticket and
whether its receipt records an accepted result, and `integration_warning`
(that warning, or `null`); with a slug, that delivery's
entry and its checks. `--format markdown` prints the deliveries as tables
(Delivery, Ticket, Owner, State, Next), for a pull request or a job summary.
`status` always exits 0; `check` and `merge-check` are the gates.

### `atipspec audit`

```text
atipspec audit
```

Checks the whole repository against the contract's rules (dependencies
always), the validity of every living spec and decision, document sizes
against their caps, overlaps between open deliveries, and initiative
roadmaps. Fails while `.atipspec/framework/` is not what the installed
version installs (a file changed, missing, or added and not ignored by git):
every phase prints those rules and workflows to the agent, and no delivery's
approval covers them, so `atipspec install --update` restores them. Warns
when the contract's acceptance is unrecorded or outdated,
when the Claude Code permission rules are missing or incomplete, naming the
ones missing, and, as
`status` does, when `origin/HEAD` names an integration branch other than main
or master and `teams.json` declares none, and notes a
`strict_scope: false` or `strict_criteria: false` kept from an older project.
Exit 1 on errors.

### `atipspec curate`

```text
atipspec curate
```

Regenerates the index block of `overview.md`, reports document sizes against
their caps and prints the curate workflow, which rewrites the prose (see
[curate](../flow/curate.md)).

## Guided delivery

The commands of a delivery in the order the [guided
flow](../flow/guided.md) uses them. The phase commands (`spec`, `plan`,
`build`, and `explore` and `fix` below) check what the phase requires and exit
1 with one line naming the missing step; otherwise they print `Phase <name>:
<title> (<slug>)`, the derived status, the phase's workflow from
`.atipspec/framework/workflows/`, the shared rules and the output of
`atipspec context`. `--no-context` leaves the context out, for re-entering a
phase in the same session. See [what each phase
requires](../flow/index.md#what-each-phase-requires).

### `atipspec new`

```text
atipspec new SLUG --title TITLE [--capability NAME] [--impact NAME]...
                  [--owner WHO] [--ticket TICKET] [--initiative SLUG]
                  [--depends-on SLUG]... [--kind feature|fix]
                  [--branch | --worktree] [--branch-name NAME] [--reuse-branch]
```

Creates a guided delivery in `deliveries/SLUG/`: `spec.md` (`schema: 2`,
`status: draft`, `base` the full id of the current commit, `created`,
`change_id`, `requirements: []`, `risk: normal`), `plan.md`, `deferred.md` and
`baseline.json`, which records that commit. `check` and the proposal compare
the capability's living spec with the one that commit holds, so `new`
refuses while `specs/<capability>.md` has changes not committed: discard them,
or, to make them in the delivery, set them aside and write them back once
`new` has run; committed on their own, outside a delivery, `merge-check`
blocks them. A feature's
`spec.md` has `## Intent`, `## Out of scope` and `## Quality attributes`, the
last two with `- None`; its requirements go to `specs/<capability>.md` (see
[artifacts](artifacts.md#specmd)). `--capability` names that living spec and
defaults to the slug; `--impact` lists other living specs or contract
sections it touches. `--kind fix` creates a guided defect repair: a `spec.md`
with `## Defect` to fill and `requirements` to point at the accepted
requirement it corrects in the `--capability` living spec, a one-task plan
whose `## Final verification` lists the contract's required commands and a
placeholder for the regression test's, and `atipspec fix` as its phase (see
[fix](../flow/fix.md)).

`--owner` names who owns it (required when `teams.json` lists owners for the
capability). `--ticket` takes a key such as `PROJ-123`, an issue number such
as `#42`, or an https URL, and refuses anything else (see
[tickets](../teams.md#tickets)). `--initiative` registers the delivery in that
roadmap. `--depends-on` names a delivery whose accepted receipt must be in the
archive before this one's check turns green. `--branch` creates and switches
to `delivery/SLUG`; `--worktree` creates that branch in `../<repo>-SLUG` and
writes the delivery there. `--branch-name` uses another branch name with
either, and `--reuse-branch` switches to that existing local branch instead of
creating it; both need `--branch` or `--worktree`, and `--reuse-branch` needs
`--branch-name`.

With `system` in `config.yaml`, `new` pins the system repository's
`contract.md`, and its `glossary.md` when it has one, in the delivery's
`contracts.json`, and prints each pin; when that checkout is not available it
warns and names the `contract-pin` command the proposal then needs. It
refuses an existing slug and the slug `contract`, reserved for `proposal
contract` and `accept contract`.

### `atipspec spec`

```text
atipspec spec SLUG [--no-context]
```

Opens the spec phase: the interview, the requirements and scenarios in the
living spec, and the delivery's intent. Refuses for a fix delivery (use
`atipspec fix`), and for a legacy delivery while the contract's acceptance is
not recorded for its current content. A guided delivery needs nothing else;
`check` warns while the contract is not accepted. See [spec](../flow/spec.md).

### `atipspec ids`

```text
atipspec ids CAPABILITY [--legacy]
```

Prints a requirement and criterion ID prefix for one delivery, such as
`REQ-PRICING-7KQ2M-001` and `AC-PRICING-7KQ2M-001`: a random five-character
token no ID this checkout can see uses (the living spec, every delivery and
archive, and the living spec at each ref `teams.json` lists), and asks to
number the delivery's further requirements and criteria with it, `-002`,
`-003`. The assistant runs it once per delivery. Two branches that drew the
same token before either was published get duplicate IDs, which `check`
reports. Longer IDs from earlier versions stay valid. `--legacy` prints the
next numeric IDs from the local history, which is not safe for concurrent
work (see [legacy deliveries](legacy.md#ids)).

### `atipspec spec-bind`

```text
atipspec spec-bind SLUG --file PATH
```

Installs requirements in the guided delivery's living spec,
`specs/<capability>.md`, keeping the others there, lists their IDs under
`requirements` in `spec.md` and sets it back to draft; it approves nothing. A
document with requirement IDs is bound as it is. One without them is imported
when it has an `Acceptance Criteria` section: its title becomes a requirement
and each numbered or bulleted item one of its criteria, a scenario when the
item has `**When**` and `**Then**` steps. Imported IDs are short and derived
from the capability and the title, so importing the same document again gives
the same IDs; one that already names a requirement with another title in the
living spec is refused. The original is kept in the delivery's
`sources/<sha256>.md`, listed under `sources` in `spec.md`, and
`## Import review notes` in `spec.md` lists what the human checks before
approving. A document in any other form is refused, with nothing written. A
removal is never inferred from an import. It refuses a legacy delivery.

### `atipspec plan`

```text
atipspec plan SLUG [--no-context]
```

Opens the plan phase: approach, scope, tasks and final verification. A guided
delivery may plan before its approval, once its scenarios are complete without
a blocking specification finding, its intent is stated, its out-of-scope and
quality sections are decided (for a fix, its defect stated and the
requirements it corrects listed) and no question is open. A legacy delivery
needs its spec accepted for its current content. See [plan](../flow/plan.md).

### `atipspec proposal`

```text
atipspec proposal SLUG
atipspec proposal contract
```

Presents what the human approves, with its approval code. `proposal SLUG`
shows the scope, scenarios, approach, tests and specification diff of a
delivery, with its ticket and link, a `Kind: ... · Risk: ...` line that says what the risk level
asks of the gate, for a fix a `Corrects:` line that says whether each
requirement it lists is an accepted one, a `Pinned contracts:` line with each
contract pinned from another repository (name, repository, commit and path),
a `Capability decisions` line with the accepted decisions about a capability
that `context` and the review packet load (they are marked accepted in the
conversation, with no code or record); the specification diff leaves out the
requirements the integration branch brought (see [when main
moves](../teams.md#when-main-moves)). For a legacy delivery, a fix
created before 0.3.0 included, the approval still pending (the spec, the spec
and plan together as one proposal when a feature has both ready, or the plan),
or that none is (a legacy fix's plan, a plan with `approve_plan: false` or one
already accepted). `proposal contract` shows the contract, its rules, the
audit findings and the decisions whose `affects` names `contract`,
`contract:<section>` or `*`, or is empty (one whose Context or Decision is
still the template's is not ready for approval), and names the current delivery
approvals that recording it would leave outdated, because the status lines it
writes are part of what they hash. The code and the exact `accept` command
appear only when `accept` would record that content; otherwise the view lists
what is missing under "Not ready for approval". Below them, a delivery's view says how strictly the criteria
are checked (`Criteria check: strict` or `warnings only`, noting when
`criteria_syntax: free` turns the form check off), what the evidence and the
review need (`Evidence check:` with `require_proof` or `risk: high` and
whether the review must come from an isolated session), a `Policy changes
since the base commit` line with each policy `config.yaml` changes since the
delivery's base, and lists the warnings of the spec, the plan (such as its
size against `max_tasks`) and the contract (such as an acceptance that is not
current) that the model resolves or names when presenting. Presenting
grants nothing; with `trust: required` it shows no local code.

### `atipspec accept`

```text
atipspec accept SLUG proposal [--code CODE] [--by WHO]
atipspec accept SLUG result [--code CODE] [--by WHO]
atipspec accept SLUG spec [--code CODE] [--by WHO]     legacy deliveries
atipspec accept SLUG plan [--code CODE] [--by WHO]     legacy deliveries
atipspec accept contract [--code CODE] [--by WHO]
```

The human approves in the conversation; the assistant then runs this command
with the code of the content it presented. The code is `XXXX-XXXX`: the first
40 bits of the content's sha256 in Crockford base32 (digits and letters without
I, L, O and U). Typing ignores case, spaces and the hyphen, and reads O, I and L
as 0, 1 and 1. When the code does not name the current content, the command
records nothing and says the content changed, without revealing the current
code. Without a phase for a delivery it refuses and names the forms.

In an interactive terminal with no agent marker in the environment, the CLI
always asks to type the code at its prompt; when `--code` is also given, both
must match. Everywhere else `--code` is required. The record states the
channel:

| Channel | When |
| --- | --- |
| `terminal` | the code was typed at the CLI prompt in an interactive terminal, with no agent marker |
| `client-permission` | Claude Code is the only agent marker (`CLAUDECODE`, or `AI_AGENT` naming Claude Code), outside the Agent SDK and `claude -p` (`CLAUDE_CODE_ENTRYPOINT` not `sdk-*`), the interpreter received the command line its ask rule matches (the installed `atipspec accept` or `python -m atipspec accept`), `.claude/settings.json` holds the AtipSpec rules intact, and no hook in `.claude/settings.json` or `.claude/settings.local.json` can answer the prompt for Bash, so Claude Code, in a session opened at the project root, asks the human first |
| `assistant` | anything else: an agent without those rules, altered rules, a client without a permission mechanism, another agent's marker next to Claude Code's (Claude Code passes its marker to the agents it starts), Claude Code run through the Agent SDK or `claude -p`, `python -m atipspec.cli`, `python -m atipspec.__main__` or `python -c`, CI. Recorded, with a warning |

The channel is what the command's own process declares, not proof of who
approved; the CLI sees only that process:

- `client-permission` says the rules are in this project, not that the
  session loaded them or that the CLI saw the human confirm. Claude Code reads
  them only in a session opened at the project root, the folder that holds
  `.claude/settings.json`: a session opened in a parent folder or another
  repository that enters the project with `cd`, as some workflow and
  subagent sessions do, is not asked and still records `client-permission`.
  So does a script or program that Claude Code starts and that runs
  `atipspec accept` itself, including an agent that sets none of the
  markers, although Claude Code's rule asked only about the script. After
  recording it, `accept` prints a note with the root.
- `terminal` says the code was typed in a terminal without agent markers. An
  agent can unset its markers and answer the prompt from a pseudo-terminal it
  creates, so this channel is not stronger than the others.
- A record written by hand under `approvals/` reads like one the CLI wrote.

Agent markers (`CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`,
`COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT`) only lower the
channel. Only an external trust policy (`trust: required`) authenticates who
approved.

What each form does:

- `proposal` validates scenarios, plan, contract, base and coordination and
  refuses open questions; it sets `status: ready` and writes
  `approvals/local-proposal.json` (legacy deliveries: also
  `local-spec.json` and `local-plan.json`, with the code of a view that
  presented the proposal, not the spec or the plan alone).
- `result` requires a green local check and no trust policy, and writes
  `approvals/local-result.json`; `deliver` requires it without a policy.
- `spec` refuses on guided deliveries, while a requirement has no criterion or
  a question is open; otherwise it sets `status: ready` and records the hash of
  `spec.md` and the contract.
- `plan` refuses on guided deliveries; it requires an accepted spec and a plan
  without errors, and records the hash of spec, plan and contract.
- `contract` validates the rules, sets `status: accepted` in `contract.md` and
  in each decision `proposal contract` listed, and writes
  `.atipspec/approvals/contract.json` with their hashes. Delivery approvals
  that hashed the previous status lines become outdated; it names them.

With `trust: required` in `config.yaml`, every form but `contract` refuses:
local acceptance is disabled and approvers sign with `atipspec approve`.

`--by` is a declared label that defaults to git's `user.email`; the assistant
passes it only with the name the user gave. Records store the hash and its
`subject_version`, the digest of each part, the code, who, when, the commit
and the channel.

`check` compares the recorded hash with the files: after any edit the
delivery is a draft again (or the plan is unaccepted), with a todo that names
the files, or the requirements of the living spec, that changed, until the
human approves the changed content and it is recorded again. Taking in the
integration branch is not such an edit (see [when main
moves](../teams.md#when-main-moves)). With a trust policy, signed approvals rule and these records are
ignored. `approval-subject` prints the digest the trust modes sign; it is not
a local approval code.

### `atipspec build`

```text
atipspec build SLUG [--no-context]
```

Opens the build phase and names the next task: the first one not recorded
with `task-done` (or, in a legacy delivery, without a commit marker), or that
every task is complete. A guided delivery needs its proposal accepted for its
current content; a legacy one a plan with tasks, accepted when `approve_plan`
is on. It refuses while the plan, the spec, the base, the contract's
definition or the coordination with other deliveries has an error or a
pending step; a file that breaks a contract rule is what the build fixes, so
it does not refuse for it. See [build](../flow/build.md).

### `atipspec task-done`

```text
atipspec task-done SLUG TASK --note TEXT
```

Records that a task of the plan is implemented, with the note: what changed.
It writes `progress.json` in the delivery folder, with the time, the hash of
the approved agreement and of the task without its title, and prints the next
action. It refuses before the approval, or while the plan, the spec, the
contract's definition, the base or the coordination has an error, for an
unknown task and for an empty note. A record is progress, not verification:
`verify` and the review check the work. It stays valid while the approved
agreement and the task, its title aside, are unchanged. No commit is needed.

### `atipspec verify`

```text
atipspec verify SLUG [--task Tn]... [--timeout SECONDS]
                [--policy PATH] [--policy-sha256 HASH] [--number N]
```

Runs, from the project root through the shell, the plan's `## Final
verification` commands once for the finished candidate, or, in a plan without
one, each task's Verify commands; `--task` runs only the named tasks' own
commands, a development check. It prints each command's output tail and
writes `evidence/<task or FINAL>-<time>.json` with the commands, exit codes,
full output logs and the fingerprint of the working tree. `--timeout` limits
each command (default 1800 seconds). Exit 1 when a command fails or the
commands changed the tree, which makes that evidence stale at once. Requires
git. Without a policy it needs no approval; run it on the finished candidate,
after the proposal's approval.

With a `Report:`, the path must be one git ignores, such as
`.atipspec/tmp/junit.xml`. `verify` deletes that file before the commands run
and reads it afterwards: a missing report (`test report not found`) or one
modified before the deletion (`predates this verification`, with two seconds
of tolerance) fails the evidence, as does a failed test in it. The evidence
records the report's copy with `fresh: true`.

With `--policy` (or `ATIPSPEC_TRUST_POLICY`), it first requires the spec
ready and its trusted spec and plan approvals, and the protected producer
runs it (see [trusted acceptance](#trusted-acceptance)).

### `atipspec review`

```text
atipspec review SLUG [--out FILE]
```

Refuses, without writing anything, while a task is not complete, evidence is
missing or stale, or the contract is violated. Otherwise counts the review
and writes the reviewer packet to `.atipspec/tmp/SLUG-review-packet.md`
(or `--out`): rubric, contract, the living specs in the impact list, the
accepted decisions affecting them, spec, plan, deferred, evidence summary,
files outside the plan's `scope`, the diff against the base (capped at 200 KB,
with `--stat` when truncated) and untracked files; then prints `review N of M`
and the review workflow. A review is counted each time the packet is for
another candidate than the previous packet's, the first included, whatever
`review.md` says: a review that passed counts too, since the CLI cannot tell a
reviewer's verdicts from ones edited afterwards. Once `review_rounds` reviews
are counted for the current approved agreement and the candidate changed again,
it refuses, counting nothing, and asks to present `atipspec check SLUG` to the
user: change the proposal, raise `review_rounds` or stop; `check` reports it as
an error until then. A packet that cannot be built counts nothing.
`check` takes only the review of the last packet counted: a `review.md`
written without running `review` waits for it. The count is in
`review-rounds.json`, which the CLI writes from `accept <slug> proposal` on;
without it, `review` refuses in a guided delivery created since 0.3.0, counts
again from the `review.md` in the folder, as the first review, in one approved
under a trust policy, and starts at the next packet in one created before
0.3.0, whose `review.md` names a tree of the earlier fingerprint. The diff
shows the stored content: no
textconv filter, and a text file that a local attribute marks as binary, or
UTF-8 text with a NUL byte, is shown as text, each NUL as `␀`; a byte that is
not UTF-8 shows as `�`. A reviewer in an isolated session reads the packet
and writes `review.md` (see [review](../flow/review.md)).

### `atipspec check`

```text
atipspec check SLUG [--json] [--policy PATH] [--policy-sha256 HASH] [--number N]
```

The gate. Exit 0 green, 1 errors, 2 incomplete. See
[how it works](../getting-started/how-it-works.md#the-gate) for the levels.
It prints the derived status, each finding and the next action; `--json`
prints the same report as data. It fails closed: without git it is an error
(the base commit, contract rules and evidence freshness come from git), and
with `trust: required` and no policy it is an error too, and so is a
`.atipspec/framework/` that is not what the installed version installs (see
[`audit`](#atipspec-audit)), which blocks the proposal, the tasks, the build
and the review until `atipspec install --update`. It never runs the
tests: it judges the evidence `verify` wrote and the review the reviewer wrote.
A PASS verdict needs a pointer it can resolve, and `review.md` needs
`reviewer:` and declares its `session:` (see
[review](../flow/review.md#what-the-gate-checks-in-reviewmd)). The `risk` level
in a delivery's `spec.md` changes what it asks (see [risk](../flow/spec.md#risk)).
It shows the delivery's lead time, from its creation to the acceptance of its
result, and warns, without blocking, when it is above `max_age_hours`. In a
guided draft it also lists what the proposal still lacks in the plan and the
contract, and their warnings; when nothing is missing, its one todo is to
present the proposal for approval. Without
a policy, green is `checked`, and `accepted` once the current result's
acceptance is recorded; with `--policy`, the trusted gate's green is
`verified`.

### `atipspec report`

```text
atipspec report SLUG [--format json|markdown|html] [--out FILE]
                [--policy PATH] [--policy-sha256 HASH] [--number N]
```

The acceptance dossier the assistant presents for the result's acceptance:
status, the result's approval code while the delivery is `checked` and no
policy is set, the kind, the risk and the lead time, the traceability matrix with each
verdict and what its pointer resolved to, the reviewer and the review's
session (with a warning when shared), `Review N of M` once `atipspec review`
has counted a review, approvals, checks, evidence, and the changes from the
base commit: every changed file but the delivery's own folder, with its
status, lines added and removed and whether it is outside the plan's `scope`,
and the diff of those files, `config.yaml`, the contract and decisions
included, as stored, like the packet's. It compares the base with the
candidate tree the evidence, review and result acceptance are bound to,
untracked files included. A file listed as `binary` has no text in the diff,
and the dossier names the binary files the candidate adds or changes: inspect
them in the repository before you accept. It also names, as the review packet
does, the changed files that configure how the tests run and report
(`conftest.py`, `pytest.ini`, `pyproject.toml`, `package.json`, `jest.config.*`
and the like), whose change can alter what the evidence says. The JSON and HTML formats keep up to
200 KB of diff, markdown (the default) up to 50 KB; a longer diff is cut, with
its full size and sha256 and the base to inspect the rest from. The archived
receipt keeps the files and the diff's size and sha256, not its text. `--out`
writes outside the repository, under `.atipspec/tmp/` or in the delivery's
`reports/`, so an export changes nothing the acceptance binds. An archived
delivery's report reads its receipt. With `--policy`, it shows the trusted
approvals QA signs for.

### `atipspec deliver`

```text
atipspec deliver SLUG [--policy PATH] [--policy-sha256 HASH] [--number N]
```

Requires a green check and the human's acceptance of the current result:
without a policy, the record `accept SLUG result` writes; with one, a green
trusted check with authenticated evidence and approvals. Merges the
requirements into the capability's living spec by ID, writes the receipt
`reports/acceptance.json` with `code_tree`, the hash of everything outside
`.atipspec/`, `living_spec`, the digest of the living spec it wrote, and
`living_requirements`, the text of each requirement it lists as written
there, sets `status: delivered`, moves the folder to `archive/` and names
`merge-check` as the step before merging. It does not commit, push or merge.

### `atipspec merge-check`

```text
atipspec merge-check --base REF [--format text|markdown] [--policy PATH] [--policy-sha256 HASH] [--number N]
```

The gate for a branch before it merges into `REF` (a branch or commit, such
as `origin/main`), run by the assistant before asking for the merge and by
the pull request's CI job. It finds the deliveries the branch changes since its merge
base with `REF`, in the folders under `deliveries/` and `archive/` named as
a slug, lists each with its state and ticket (a table in Markdown, with the
ticket's link), and blocks when:

- an open delivery is not `accepted` (locally) or `verified` (with a policy);
- a delivery archived in the branch has a receipt without an accepted result
  or without `code_tree` (delivered before 0.3.0), or its `code_tree` differs
  from the code at the head: any change outside `.atipspec/` after `deliver`,
  taking the target branch in (merge or rebase) included. It names the changed
  files when the accepted tree or the archiving commit is available, and says
  how to go on: reopen the delivery by reverting the commit that archived it,
  then verify, review, accept and deliver it again (reverting the files helps
  only with a change of the branch itself), and take the target branch in
  before `deliver` next time. Locally it also blocks a receipt that changed after the commit
  that archived it; one removed and added again, unless the commit before
  holds the delivery open, as after reverting the archive commit to reopen
  it, or an earlier archive added that same receipt; and one whose
  `code_tree` neither the archiving commit nor the one before it holds. So
  rewriting `code_tree` after a change of the code shows, but a receipt is not
  authenticated: a history rewritten coherently, or a reopening faked by hand
  (the archive removed and the delivery restored in one commit, then archived
  again with a receipt written by hand), still passes; only a trust policy
  checks the delivery again;
- the branch changes or removes a delivery archived before it;
- the branch changes a living spec in `specs/` other than through `deliver`
  (the receipt's `living_spec`; with a policy, what `deliver` writes from the
  commit it was delivered from) or an open guided delivery's approved
  proposal. It compares each requirement too: the head holds it as the merge
  base had it, as the last delivery archived in the branch that lists it wrote
  it (the text its receipt's `living_requirements` records, as the commit
  that archived it added it; with a policy, what `deliver` writes from the
  commit it was delivered from, and only for a delivery the policy
  authenticates), or as an open guided delivery lists it, so a
  receipt does not vouch for a requirement its delivery did not list, nor for
  a later edit of one it did, nor for a later edit of the receipt;
- a guided fix archived in the branch, or open in it, lists a requirement that
  the living spec did not hold at the merge base and that no earlier delivery
  of the branch wrote: a fix corrects an accepted requirement;
- the branch changes the contract, or a decision that affects it, and the
  contract's acceptance is not current; with a policy, the branch changes
  `contract.md` or such a decision outside a delivery checked under the
  policy (`contract.md` with a new decision that affects the contract, which
  engineering approved), or accepts a draft contract that no such delivery
  was checked with;
- the branch changes a file outside `.atipspec/` that no delivery it archives
  or leaves open covers, and that `exempt_paths` does not match. A delivery
  covers the files its dossier shows: those that changed between its base
  commit and the head, and those the integration branch changed that the
  branch holds otherwise, put back as the base had them included (see [when
  main moves](../teams.md#when-main-moves)), except those the branch had
  changed before that base. An open delivery's dossier is the one at the
  head, which the acceptance of its result binds: when the delivery puts back
  what the integration branch changed, that acceptance names the merge base,
  so taking the branch in again voids it. An archived delivery's is the one it
  was delivered with, as its receipt lists it (with a policy, as at the commit
  it was delivered from), less the files the target branch changed after the
  commit that archived it, which the branch takes back. Code committed before
  `atipspec new`, or changed in a file the delivery changes again, is outside
  it, and so is a change of a
  target branch that is not the integration branch, or of any branch without
  an integration ref, that the branch puts back as the base had it, and any
  code in a branch that touches no delivery or only removes one. A delivery
  archived in the branch whose base commit is not in the history of `HEAD`,
  as in a shallow clone or after a squash or a rebase of the branch, blocks
  too: without it, `merge-check` cannot tell which files the delivery covers,
  and it says that it did not look for code outside the deliveries.
  `exempt_paths`, a list of globs, is read from
  `config.yaml` at `REF`, never from the branch, so a branch cannot exempt its
  own changes: the user decides which files need no delivery, and adds the
  globs on the target branch first. Client files that hold only what AtipSpec
  installs, such as a skill of this version or `.claude/settings.json` with
  only its rules added, do not count;
- the working tree differs from `HEAD`: it judges the committed head;
- `.atipspec/framework/` is not what the AtipSpec version running
  `merge-check` installs (see [`audit`](#atipspec-audit));
- `.atipspec/` is not at the top of the git repository;
- `trust: required` is set at the head, on `REF` or at the merge base and no
  policy is given. With a policy, with or without `trust: required`, a
  locally accepted receipt blocks, and so does a trusted one whose delivery
  does not pass its trusted check again: at the commit before the archive
  commit, checked out in a temporary clone with the repository's refs and the
  evidence, review, deferral terms and approvals archived with it, the check
  must be `verified`
  (approvals and attested evidence; in provider mode the pull request's
  reviews of that commit, or of the head with the same marker lines, read
  with `--number`), and that commit must hold the code at the head. Commit
  the archive on its own right after `deliver`.

Each delivered or accepted delivery's line names the channel `accept`
declared for each local approval: how the command ran, not who approved. A
branch that touches no delivery is ready unless it changes a living spec, the
contract or a file outside `.atipspec/` that `exempt_paths` does not match;
the result lists the files `exempt_paths` let through, and warns when the
branch changes `exempt_paths`, which no approval hashes. It also warns,
without blocking, when the branch relaxes against `REF` a policy of
`config.yaml` among `strict_scope`, `strict_criteria`, `criteria_syntax`,
`review_rounds`, `max_tasks`, `max_requirements`, `max_age_hours`,
`require_proof`, `require_isolated_review` and `trust`, listed as the proposal lists its policy changes, such as
`review_rounds 3 → 99`, since every delivery started after the merge takes
them and no proposal lists them; and when it adds, changes or removes `overview.md`,
`glossary.md` or a decision, named with each decision's status, since the
agent reads them as context in every phase and no delivery's approval covers
them; and when it changes `adapter.json`, which names the program `atipspec
run` executes and whether its reviews count as isolated, or `teams.json`. When the branch changes the contract or a decision that affects it, the
result shows the contract's acceptance with the channel `accept contract`
declared. It runs no command
from the candidate, only git and file reads,
so a pull-request job runs it without credentials. `--format markdown` prints
the result for a CI job summary. Exit 0 ready, 1 blocked. The CI examples from
`enterprise-init` run it (see [enterprise](../enterprise.md#ci-before-the-merge)).

### `atipspec ship`

```text
atipspec ship SLUG
```

Ship mode's guide: names the next phase the delivery can enter, why, the stop
point that follows (the proposal's approval, or the spec's for a legacy
delivery, before building; the result's acceptance before `deliver`) and the
command to run. The phase it names always passes its own prerequisites. See
[ship mode](../flow/index.md#ship-mode).

### `atipspec context`

```text
atipspec context SLUG [--out FILE] [--summary]
                 [--role guide|analyst|designer|tester|implementer|reviewer] [--task Tn]
```

Prints the material for the delivery with a size summary against
`context_budget`: the contract, the overview, the glossary, the living specs
in the impact list, the accepted decisions that affect them and the
delivery's own files, never the archive. `--out` writes it to a file;
`--summary` prints only the sizes. `--role` adds that role's instruction,
adjusted to the delivery's `risk`, as the runner sends it; `--task` limits the
material to that task and the requirements it covers. The phase commands print
its output.

## Other deliveries

### `atipspec explore`

```text
atipspec explore SLUG [--no-context]
```

Opens the explore phase for a delivery that exists: the model writes a
one-page `brief.md` with the problem, what exists, options and a
recommendation, and stops. See [explore](../flow/explore.md).

### `atipspec fix`

```text
atipspec fix SLUG [--no-context]
```

Opens the fix phase of a delivery created with `--kind fix`: reproduce the
defect, correct the accepted requirement it breaks with a regression
criterion, plan one task, present the proposal. Refuses on a delivery that is
not a fix, and on a fix created before 0.3.0 while the contract's acceptance is
not recorded for its current content. See [fix](../flow/fix.md).

### `atipspec migrate`

```text
atipspec migrate SLUG [--apply]
```

Shows how a legacy delivery becomes a guided one, as a diff, and writes
nothing: its requirements move to `specs/<capability>.md`, `spec.md` lists
them under `requirements` without its empty `## Requirements` heading, and
gets `schema: 2`, `status: draft` and a new `baseline.json`. `--apply` writes
it after backing up the originals and the approval records in
`.atipspec/migrations/<digest>/`. It is not an approval: the delivery returns
to draft and needs its proposal approved. A legacy fix keeps its flow until
it is delivered: `migrate` refuses it. See [legacy deliveries](legacy.md).

## Contract and decisions

### `atipspec contract`

```text
atipspec contract
```

Opens the contract phase: prints the workflow, the rules and the current
`contract.md`. It never refuses. The assistant then presents `atipspec proposal
contract` and records your approval with `atipspec accept contract --code
<code>`. See [contract](../flow/contract.md).

### `atipspec decision`

```text
atipspec decision SLUG --title TITLE [--affects NAME]...
```

Creates `decisions/DEC-nnn-SLUG.md` with status `proposed`. `--affects`
takes capability names, `contract`, `contract:<section>` or `*`; without it the
decision affects everything. A decision that affects the contract or
everything is accepted with the contract: `atipspec accept contract` sets its
status; never edit it by hand.

### `atipspec initiative`

```text
atipspec initiative SLUG --title TITLE
```

Creates `initiatives/SLUG/roadmap.md`; `new --initiative SLUG` lists a
delivery in it.

## Automation

### `atipspec run`

```text
atipspec run SLUG [--resume] [--retry-interrupted] [--budget SECONDS] [--timeout SECONDS] [--max-rounds N]
```

Executes an approved guided delivery through the configured process adapter
and prints its state as JSON; see [the execution
adapter](execution-adapter.md). It needs the proposal accepted for its
current content, otherwise it records `awaiting_approval` and stops; it never
accepts anything. `--budget` limits the elapsed seconds for this approved
version (default 900), `--timeout` each adapter call or verification command
(default 300). `--max-rounds` limits the automatic corrections; it defaults to
`review_rounds` in `config.yaml` less one, as each correction is reviewed
again, and cannot exceed it. The reviews the runner asks for count as
`atipspec review` counts them, and it stops at
`needs_decision` once they are used up. `--resume` continues after you
resolved a reported decision or failure; `--retry-interrupted` retries after
you inspected an interrupted agent mutation. Exit 0 when the state is
`ready_for_acceptance` or `accepted`, 2 for any other state. It refuses a
legacy delivery, and with a trust policy, selected or required. The runner
needs a POSIX system (Linux, macOS or WSL) for its checkout lock; elsewhere it
refuses before it reads the delivery or writes anything, and the delivery
continues in the guided conversation, which has the same phases and the same
gate.

### `atipspec adapter`

```text
atipspec adapter
```

Prints, as JSON, what the adapter in `.atipspec/adapter.json` declares and
what the runner provides: whether the review runs isolated, checkpoints, that
it is no background service, and that token and cost metrics are unavailable.
Refuses when no adapter is configured.

## Teams

### `atipspec team`

```text
atipspec team [--fetch] [--json]
```

The board: every open delivery of the working checkout and of each ref
`teams.json` lists (a `*` at the end takes every ref it matches), with its
status, owner, ticket, ref, capability, requirements and dependencies. It
reads local refs only; its first line says when the repository last fetched.
`--fetch` first fetches each remote a `refs/remotes/<remote>/...` entry names,
without prompting for credentials (git and ssh run without a terminal or an
askpass program); a remote that fails gets a warning and the board shows what
it fetched last. `--json` prints the board as data, with each ticket's
`ticket_url`. See [the board](../teams.md#the-board-atipspec-team).

### `atipspec contract-pin`

```text
atipspec contract-pin SLUG NAME --repository NAME --ref REV --path PATH
```

Pins the file `PATH` of another repository's checkout, named in `teams.json`
`repositories` (`system` defaults to `system` in `config.yaml`), at the commit
`REV` resolves to, in the delivery's `contracts.json` under `NAME` with its
digest, and prints that commit. The delivery's context reads the file from
that commit; `check` refuses a pin that names a branch or a tag, or whose
content differs from its digest. `contracts.json` is part of what the
proposal's approval hashes, so pinning again voids it. See [several
repositories](../teams.md#several-repositories).

## Trusted acceptance

These commands serve an external trust policy (see [enterprise
acceptance](../enterprise.md)). People with enrolled keys, a protected CI
worker and a collector run them; the assistant never signs. `check`,
`verify`, `report`, `deliver` and `merge-check` take the policy with:

- `--policy PATH`: the organization's trust policy TOML, outside the
  candidate repository (or `ATIPSPEC_TRUST_POLICY`);
- `--policy-sha256 HASH`: the digest the policy must have, pinned in protected
  configuration (or `ATIPSPEC_POLICY_SHA256`);
- `--number N`: the pull request, for a policy in provider mode (or
  `ATIPSPEC_PR_NUMBER`).

With a policy, `check` requires the signed approvals and attested evidence
and its green is `verified`; `verify` requires the spec and plan approvals
before it runs; `deliver` requires the trusted gate green; local `accept`
records are ignored. With `trust: required` in `config.yaml`, `check`,
`accept` (but `accept contract`), `deliver` and `run` refuse to work without
one. Never derive these values from candidate documents.

### `atipspec enterprise-init`

```text
atipspec enterprise-init [--out DIRECTORY]
```

Writes the trust policy examples (`policy.example.toml` for ssh mode,
`policy.provider.example.toml` for provider mode), the CI jobs that run
`merge-check` (`github-local.yml`, `gitlab-local.yml`), the provider-mode
evidence workflows (`github-evidence-trusted.yml`,
`github-evidence-caller.yml`), a protected acceptance script and
`ADOPTION.md` into `DIRECTORY` (default `.atipspec/enterprise`). It activates
nothing, and refuses when the files already exist there.

### `atipspec approval-subject`

```text
atipspec approval-subject SLUG PHASE
```

Prints the marker an approver puts in a pull request review, `ATIPSPEC-APPROVE
<slug> <phase> <subject> <head>`: the digest of the phase's content and the
head commit. It reads the policy from `ATIPSPEC_TRUST_POLICY`. It is not a
local approval code.

### `atipspec approve`

```text
atipspec approve SLUG PHASE --identity ID --key PATH --policy PATH
                 [--policy-sha256 HASH] [--expires TIME] [--owner ID]
```

Signs a human approval from an enrolled identity, on that person's trusted
machine. `PHASE` is `spec`, `plan`, `acceptance`, `decision:DEC-nnn` or
`exception:Fn`. `--key` is the private key outside the repository. Exceptions
require `--expires` with a future timezone-aware ISO timestamp. The spec
approval confirms the delivery owner: `--owner` must be the `owner` `spec.md`
declares, and is signed with it; it is required for `spec` and refused for
every other phase. That owner cannot approve the later phases, and a spec
approval that confirms no owner, or another one, does not count; one signed
before 0.3.0 is signed again with `--owner`. `approve` refuses an owner that is
not written in ASCII letters, digits, `_`, `.`, `@` and `-`, as identities are.

### `atipspec sync-approvals`

```text
atipspec sync-approvals SLUG PHASE --number N --identity ID --key PATH --policy PATH
                        [--policy-sha256 HASH] [--expires TIME]
```

Collects the human approvals of pull or merge request `N` that carry the
phase's `approval-subject` marker, read-only through the GitHub or GitLab API,
and signs the normalized record with the enrolled collector identity.
An `exception:Fn` phase needs `--expires` with a future timestamp. The gate reads the provider again on every
run, so a revoked review fails.

### `atipspec attest`

```text
atipspec attest SLUG --identity ID --key PATH --run-url URL --policy PATH [--policy-sha256 HASH]
```

The protected collector signs the evidence of each task, the record in
`evidence/` that finished last, with the CI run's URL. It does not
authenticate that run: the orchestrator verifies the producer, the head and
the artifact before calling it, and deletes the evidence the branch committed
first (`atipspec.verify.clear_evidence`). It refuses evidence whose test
report has no `fresh` mark.

## Pilots

### `atipspec pilot`

```text
atipspec pilot init NAME
atipspec pilot record NAME --delivery SLUG --cohort baseline|atipspec --source SOURCE --collector WHO
                      [--lead-hours H] --human-review-minutes M --rework-minutes M
                      --escaped-defects N --criteria-total N --criteria-tested N --observation-days N
atipspec pilot report NAME
```

`pilot init` creates an empty real-world evaluation protocol in
`.atipspec/pilots/NAME/`. `pilot record` adds one sourced, complete
observation; unknown values are not entered as zero. For the `atipspec`
cohort, `--lead-hours` may be omitted: it is read from the delivery's archived
receipt, or from the records archived with it, and the observation says so in
`lead_hours_origin`; it is never estimated. The `baseline` cohort needs it
measured. `pilot report` compares the recorded cohorts, with sample sizes,
medians and limitations, and flags unequal observation windows.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | done; for `check`, green; for `merge-check`, ready; for `run`, `ready_for_acceptance` or `accepted` |
| 1 | error; for `check` and `audit`, red; for `merge-check`, blocked; for `verify`, a command failed or changed the tree |
| 2 | `check`: incomplete, work remains; `run`: any state but `ready_for_acceptance` and `accepted` |
| 130 | cancelled from the keyboard |

## Environment

| Variable | Effect |
| --- | --- |
| `ATIPSPEC_TRUST_POLICY` | selects the external trust policy for every command, as `--policy` does |
| `ATIPSPEC_POLICY_SHA256` | the digest the policy must have, as `--policy-sha256` |
| `ATIPSPEC_PR_NUMBER` | the pull request in provider mode, as `--number` |
| `GITHUB_TOKEN`, `GITLAB_TOKEN` | read-only tokens for the provider adapters on the protected worker; `verify` removes them from the commands it runs, with every `ATIPSPEC_` variable, `SSH_AUTH_SOCK`, `GIT_ASKPASS`, the CI job tokens (`CI_JOB_TOKEN`, `ACTIONS_RUNTIME_TOKEN`) and the OIDC request token (`ACTIONS_ID_TOKEN_REQUEST_TOKEN`) |
| `NO_COLOR`, `TERM=dumb` | turn off colors in the terminal output |
| agent markers and `CLAUDE_CODE_ENTRYPOINT` | decide the channel `accept` records; see [environment](configuration.md#environment) |

Set the trust variables in protected organization configuration, never from
values the candidate repository provides.
