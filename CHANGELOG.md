# Release history

## 0.3.0 — Human approval, a gate that fails closed and coherent documentation

- Human approval without self-approval. `atipspec proposal <slug>`,
  `atipspec report <slug>` (for a checked result) and the new
  `atipspec proposal contract` print an approval code, `XXXX-XXXX`: the first
  40 bits of the presented content's sha256 in Crockford base32. `atipspec
  accept` needs it (`--code`) and refuses, without revealing the current code,
  when the content changed after it was presented. In an interactive terminal
  with no agent marker, the CLI always asks to type the code.
- Every local approval record states its channel: `terminal` (the code was
  typed at the CLI prompt in a terminal without agent markers),
  `client-permission` (Claude Code ran `atipspec accept` itself with this
  project's rules intact and no hook in its project settings that can answer
  the prompt for Bash) or `assistant` (nothing asked the human; recorded with
  a warning). Agent
  markers (`CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`, `COPILOT_CLI`,
  `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT`) only lower the channel: another
  agent's marker next to Claude Code's, Claude Code run through the Agent SDK
  or `claude -p`, or a command line its rule does not match (`python -m
  atipspec.cli`, `python -m atipspec.__main__`, `python -c`), records
  `assistant`. The CLI sees only its own process, so a script, or an agent
  without a marker, that Claude Code starts and that runs `atipspec accept`
  still records `client-permission`; so does a session opened outside the
  project root that enters it with `cd`, which loads no project rules
  (`accept` prints a note with the root); and an agent can unset its markers
  and answer the prompt from a pseudo-terminal, which records `terminal`. A
  channel describes how the command ran, not who approved. `status`,
  `report`, the archived receipt and `merge-check` show it.
- `init` and `install` merge Claude Code permission rules into the shared
  `.claude/settings.json`: ask before `Bash(*atipspec accept *)` and before
  `Edit` on `.github/workflows/**`, `.gitlab-ci.yml` and
  `.claude/settings*.json`, and deny `Edit` on approval, evidence and archive
  records. The merge keeps every other entry;
  a file that is not plain JSON is left alone and the rules are printed. `audit`
  warns when they are missing, `install --update` repairs them, and removing the
  client removes only them. Other clients get no rules yet; their channel is
  `assistant`.
- Guided deliveries require the current proposal record: `accept <slug> spec`
  and `accept <slug> plan` are refused for them, and a spec and plan pair no
  longer substitutes for the proposal. `check`, `build`, `deliver` and `run`
  messages point to `atipspec proposal <slug>` and `accept <slug> proposal
  --code <code>`.
- The contract's acceptance is recorded in `.atipspec/approvals/contract.json`
  with the hash of `contract.md` and of each decision that affects it. `accept
  contract --code <code>` sets the contract and those decisions to `accepted`.
  A decision added, edited or marked accepted by hand afterwards leaves the
  acceptance outdated: legacy deliveries, fixes created before 0.3.0 included,
  cannot start, a contract change
  inside a delivery stays red, and `context` leaves that decision out. A
  decision without `affects` affects everything and is accepted with the
  contract too. Guided deliveries only get a warning while the contract is not
  accepted. Delivery approvals hash `contract.md` whole, so the status lines
  `accept contract` writes leave them outdated: `proposal contract` names them
  before the human decides, and `accept contract` names them again. A decision
  whose Context or Decision is still the template's is not ready for approval.
  The slug `contract` is reserved.
- Approval records also store per-file digests, so drift messages name the
  file that changed instead of "spec.md or the contract".
- Rules, workflows, skills and templates describe the protocol: present the
  view with its code, wait for explicit approval, run `accept --code` with that
  code, treat the client's permission prompt as the same approval, report the
  channel, and never write approval, evidence or archive records or a status by
  hand. The templates no longer say a person runs `accept`.
- The gate fails closed. Without git, `check` is an error instead of a warning,
  so the gate stays red (before, only fabricated evidence turned it green), and
  a result acceptance never binds a missing tree. `forbid-pattern` reads a file
  that is not UTF-8 as Latin-1 instead of skipping it, ignores a UTF-8 byte
  order mark, and a file it cannot read is a violation.
- New projects are strict: `strict_scope` and `strict_criteria` default to
  `true`. A plan must declare a `scope`, and globs that together match every
  path (`**`, `**/*`, `*` with `*/**`) declare none; that is an error that blocks the proposal, and
  a file outside the scope is an error. The skills and permission rules
  AtipSpec installs do not count as outside the scope while they hold only its
  content. Criteria outside the EARS or scenario form, or with vague terms,
  are errors.
- `config.yaml` is validated before every command but `init`: booleans,
  positive whole numbers, `criteria_syntax: ears|free` and the new `trust:
  optional|required`; `max_age_hours` may have a fraction, as before.
  `strict_scope: no` used to read as true; it now stops with a message naming
  the key. `init` writes every key, `trust: optional` included.
- `trust: required` makes the external trust policy mandatory: without
  `--policy` or `ATIPSPEC_TRUST_POLICY`, `check` is red, local `accept` is
  disabled except for the contract, `deliver` refuses and `run` does not start.
- `deliver` stores `code_tree` in the receipt: the hash of everything outside
  `.atipspec/`, which later AtipSpec bookkeeping never changes.
- New `atipspec merge-check --base <ref> [--format text|markdown]`: before the
  merge, every delivery the branch touches must be `accepted` (or `verified`
  under a policy), and every delivery the branch archived must have a receipt
  whose `code_tree` is the head's code, so a change after `deliver` blocks the
  merge and the message names the files. It also blocks a branch that rewrites
  or removes an earlier archive, changes a living spec outside `deliver` (the
  receipt records the digest of the one it wrote in `living_spec`) or changes
  the accepted contract without its new acceptance, a dirty working tree, a
  project below the repository root, and a missing policy when the head, the
  target branch or the merge base sets `trust: required`. With a policy, even
  without `trust: required`, a locally accepted receipt blocks, and a trusted
  one counts only when the delivery passes its trusted check again at the
  commit before the archive commit, with the files archived with it (in
  provider mode, the pull request's reviews of that commit or of the head
  with the same marker lines), that commit holds the code at the head and the
  living spec is what `deliver` writes from it; `contract.md` and the
  decisions that affect it change only in such a delivery (`contract.md`
  through a decision engineering approves), and a draft contract is accepted
  only with one checked with it. It runs no candidate command.
- `github-local.yml` and `gitlab-local.yml` from `enterprise-init` now run
  `merge-check` on the branch head with full history, as the pull request's
  check: a draft delivery fails the job. They no longer run `verify`; the
  project's tests belong in their own job. They install the pinned verifier
  from outside the checkout with `python -I -m pip`, so a `pip/` package or a
  wheel the candidate commits is never loaded, and the GitLab job compares with
  the target branch's tip. The GitHub job writes the result to the job summary.
- `install --update` lists the policies in `config.yaml` that differ from this
  version's defaults, without editing it; `audit` notes a `strict_scope: false`
  or `strict_criteria: false` kept from an older project.
- The lint reads requirements and scenarios, not only criterion statements. A
  requirement's title and the lines that state it, and a scenario's title and
  every step, get the vague-term check; 0.2.0 let every scenario through. `Why:`
  and `Observed:` paragraphs (and their Spanish and Portuguese labels), with the
  list under them up to a blank line, a criterion or another label, and the
  title of a `[remove]` requirement are not read; the text after an `Acceptance
  criteria:` label and an indented list item under a criterion are. The strict
  check does not read text in quotes or backticks, so quoting the literal
  interface text is the way out of a false positive; a quote that holds a vague
  term gets a warning instead and is not a concrete value. A token with a colon
  inside (`theme:slow-unresponsive`) and a cardinality (`many-to-many`) no
  longer match; a hyphenated compound (`fast-loading`) and Markdown emphasis
  (`_quickly_`) do. A scenario with Spanish or Portuguese step words is also
  read with that language's terms.
- In a guided delivery, a requirement that differs in `specs/` from the living
  spec at the delivery's base commit, added, edited, deleted or marked `[remove]`, but is not
  listed under `requirements` is an error at every risk level: `check` reads
  only the listed ones, the approval hashes only them, and `merge-check`
  blocks it. The same goes for a requirement changed in another capability's
  living spec, which the proposal shows as a diff. What the integration
  branch brought or a delivery archived in the branch after the base wrote,
  as its receipt records, and what another open delivery lists, is not the
  delivery's change; what a merge of any other branch brings is. A committed
  change gets a message that does not assume the delivery made it. A change
  of the living spec's text outside its requirements, before the first one
  or under a heading that ends one, of its frontmatter, or of an HTML comment
  or fenced code in a requirement the delivery does not list, is a warning:
  no approval of the proposal covers it, only the acceptance of the result,
  which binds the whole tree. Where the integration branch changed that
  text, it is compared with the merge base.
- `base` in `spec.md` must be the full id of a commit in the history of
  `HEAD`, the head `new` recorded in `baseline.json`: a name such as `HEAD` or
  a later commit is an error, since it hid committed work from the scope
  check, the comparison of `specs/` and the dossier's diff, and so is an
  earlier one, which compared a fix with requirements not yet accepted. A
  delivery migrated from a legacy one keeps its earlier base, not later than
  that head. When a rebase rewrote the base, the error says to restore that
  history and take in the target branch with a merge.
- `merge-check` compares living specs requirement by requirement: each one is
  at the head as the merge base had it, as the last delivery archived in the
  branch that lists it wrote it, or as an open guided delivery lists it. A
  receipt no longer vouches for a requirement its delivery did not list, such
  as one deleted or rewritten in a commit before the delivery started. The
  receipt records `living_requirements`, the text of each requirement the
  delivery lists as `deliver` wrote it, so a later edit shows in `check` and
  `merge-check` even when the delivery left the living spec as it was or its
  text was never committed whole (two deliveries before one commit). Both
  read the receipt and the archived `spec.md` as the commit that archived the
  delivery added them, so an edit of the receipt afterwards vouches for
  nothing; one not committed yet counts while `HEAD` holds that delivery
  open. Locally a receipt is a file that could be written by hand and
  committed; with a trust policy, `merge-check` takes each requirement's text
  from what `deliver` writes at the commit the delivery was delivered from,
  and only for the deliveries it authenticates. An archive folder whose name
  is not a slug is no delivery: neither `check` nor `merge-check` reads it.
- The vague-term tables grow in English, Spanish and Portuguese: `correctly`,
  `properly`, `as expected`, `as intended`, `works well`, `appropriately`,
  `relevant`, `usually`, `correctamente`, `adecuadamente`, `funciona bien`,
  `lo antes posible`, `corretamente`, `funciona bem`, `sem problemas`, the
  missing plural and feminine forms, and more. `mínimo` alone left the Spanish
  and Portuguese lists, since "a minimum of 12" is precise; `lo mínimo`, `al
  mínimo`, `mínimo posible` and their Portuguese forms replace it.
- Quality attributes need a fit criterion. Each criterion of a quality
  attribute states a number in its outcome (a strict finding; the 95 of `p95`
  does not count) and says how it is measured (a warning). In a guided
  delivery, `## Quality attributes` names the requirements of the change that
  state a limit, one `- REQ-...: limit` line each; a line that names none is a
  todo before the proposal is approved and an error afterwards. A legacy
  delivery keeps them under its `## Quality attributes` heading.
- Every other criterion whose outcome names no concrete value (a number,
  quoted text, a path, an address or a capitalized name) gets a warning: "then
  the discount is applied" does, "then the total is 27.00" does not. It is a
  heuristic, so it never becomes an error.
- A criterion statement may continue on indented lines; 0.2.0 read only its
  first line.
- `atipspec new` writes `## Intent`, `## Out of scope` and `## Quality
  attributes` into a guided `spec.md`, the last two with `- None`, with
  instructions in comments, and lists them in `baseline.json`. Until the
  proposal is approved, an empty Intent (`TBD`, `TODO` or `...` count as empty),
  an Out of scope or Quality attributes section with no item, or one of those
  sections deleted, is a todo that blocks `proposal` and `accept proposal`; once
  the proposal is approved for its current content it is a warning. Approved
  means a local record of that content: writing `status: ready` by hand lifts
  nothing, and selecting a trust policy does not change that for `proposal` and
  `accept proposal`. A delivery created without those sections only gets a
  warning.
- `proposal` shows how strictly the criteria are checked, `Criteria check:
  strict` or `warnings only (strict_criteria: false in config.yaml)`, notes
  when `criteria_syntax: free` leaves the form unchecked, and lists the
  specification warnings below the approval code.
- The spec workflow asks at most three questions per round, with another
  round while a consequential decision is open; 0.2.0 said "a short round"
  and its documentation five. It recovers the 0.1.0 interview list (actor and
  trigger, happy path, failure paths, data, out of scope, quality attributes
  with a number and how it is measured, conflicts) and asks for requirements
  that meet INVEST, a concrete value in each THEN and a fit criterion for each
  quality attribute. The documentation examples follow the lint, and the
  "Writing criteria" reference lists every check with its scope and level.

- A JUnit report counts only when the run wrote it. `verify` deletes the file
  named in `Report:` before the commands run; afterwards it must exist and be
  modified after that deletion (two seconds of tolerance), or the evidence
  fails with `test report not found` or `predates this verification`. In 0.2.0
  a report planted at that path, or left by an earlier run, passed. The path
  must be one git ignores, such as `.atipspec/tmp/junit.xml`: anything else
  fails `verify` and is a plan error in `check` that blocks the proposal. The
  evidence records the report's path and `fresh: true`; evidence with a report
  but no such mark asks to verify again, and `attest` refuses it.
- New `require_proof` policy, `false` by default and written by `init`: with
  `true` in `config.yaml` or in the trust policy, every criterion under
  `Tests:` needs a `Proof:` entry and its verification a `Report:`, an error
  that blocks the proposal. The trust policy's value cannot be lifted by the
  project. A Proof entry that names several test cases counts as passed only
  when all of them passed; 0.2.0 took the first.
- Review pointers must resolve. A PASS names a test that passed in the current
  evidence's report, a `path:line` or `path:line-line` that exists in a file
  of the candidate, outside `.atipspec/` and `.git` (whatever the case of the
  name where the file system ignores it) and not ignored by git, or in the
  delivery's evidence logs, ignored or not, as
  `evidence/logs/<file>.log:<line>`, or a `path::test` whose file holds that
  name as a word; a `[manual]` criterion may instead describe what was done
  and observed in three words or more.
  `PASS. ok` is an error, and so is a `review.md` without `reviewer:`. While
  the review is stale its pointers are not judged, and while the evidence is
  not current an unresolved one is a todo, since the test it names may be in
  the next run. The dossier shows what each pointer resolved to, a
  `path::test` as a name found in a file. A pointer keeps its leading dot:
  0.2.0 read `PASS. .atipspec/...` as `atipspec/...`.
- `review.md` declares `session: isolated|shared`; a review without it counts
  as shared. A shared review is a warning, and an error with `risk: high` or
  the new `require_isolated_review: true` (in `config.yaml` or the trust
  policy); another value is an error. `atipspec run` stops at
  `needs_decision` before the review when isolation is required and the
  adapter does not declare `isolated_review`, and fails a review that claims
  `isolated` from such an adapter. Rules, workflows, skills and templates say
  "a reviewer in an isolated session" instead of "a fresh context", and tell
  the reviewer to write `shared` when it saw the author's conversation.
- `review_rounds` is applied; 0.2.0 documented it, but nothing read it. It is
  how many reviews a delivery gets per approved agreement, the first included
  (default 3). `atipspec review` counts a review each time it writes a packet
  for another candidate than the last packet's, whatever `review.md` says,
  since the CLI cannot tell a reviewer's verdicts from ones edited
  afterwards; a packet that cannot be built counts nothing. Once
  `review_rounds` reviews are counted and the candidate changed again, it
  refuses, counting nothing, and asks to present `atipspec check` to the
  user. `check` reports the used-up reviews as an error, and takes only the
  review of the last packet `review` counted: a review written without
  running `review` is a todo that asks for it, so skipping the command counts
  no review less. The dossier shows the count. The
  count lives in `review-rounds.json`, written by the CLI, left out of the
  fingerprint and covered by a new Claude Code `deny` rule for its edit tools,
  not for a shell command; without the file, `review` starts again from the
  `review.md` in the folder, as the first review, in a delivery approved
  under a trust policy, and from the next packet in one created before 0.3.0,
  whose `review.md` names a tree of the earlier fingerprint. It starts again
  with a new approved proposal (or spec, for legacy deliveries, where no
  approval covers `review_rounds`). `review`, `status <slug>` and the dossier say `review N of
  M`. `atipspec run` counts its reviews too and stops at `needs_decision`
  once they are used up; `run --max-rounds` now defaults to `review_rounds`
  less one, as each correction is reviewed again, instead of 2, and cannot
  exceed it.
- The dossier shows the code: `report` lists every file changed since the
  base commit (the delivery's own folder aside) with its status, lines and
  whether it is outside the plan's scope, and the diff of those files, so a
  change to `config.yaml`, the contract or a decision shows too, computed on
  the candidate tree that the evidence, the review and the result acceptance
  are bound to. The diff, there and in the review packet, shows the stored
  content: no textconv filter, and a text file that a local attribute marks as
  binary, or UTF-8 text with a NUL byte, which git alone shows as binary, is
  shown as text, each NUL as `␀`; a byte that is not UTF-8 shows as `�`
  instead of stopping `report`, `deliver` and `review` with an error. The
  dossier names the binary files the candidate adds or changes, to inspect
  before accepting. JSON and HTML keep up to 200 KB of diff,
  markdown up to 50 KB, with the full diff's size and sha256 when cut. It also
  shows the reviewer and the session, with a warning when shared. The archived
  receipt keeps the files and the diff's size and sha256, not its text;
  receipts written before keep rendering.
- Renaming a task no longer invalidates its work. Task completion is bound to
  the task without its title, and the fingerprint that evidence, reviews,
  attestation, the result acceptance and the runner compare reads each task
  heading of a delivery plan reduced to its id (`### T1:`), so a renamed task
  leaves them current, in a fresh clone such as CI too. Records keep one
  tree.
- A test report tracked by git fails with a message that says so and how to
  untrack it.
- `proposal` shows an `Evidence check:` line: whether Proof is required and
  whether the review must come from an isolated session.

- `risk` in a guided delivery's `spec.md` now changes the gate; in 0.2.0 it
  only chose the runner's roles, so its "checks scaled to risk" did not reach
  `check` or the review. `low`: a criterion whose test named in `Proof:` passed
  in the current evidence needs no reviewer verdict (`review.md` is still
  required, a `FAIL` still blocks and a criterion that is not under `Tests:`,
  such as a `[manual]` one, still needs its verdict), and removing a
  requirement (marked `[remove]` or deleted from `specs/`), even a listed one,
  or changing `contract.md` is an error; the
  requirements compared are those `specs/` held at the delivery's base
  commit. `normal`: as before. `high`: the plan declares a
  `scope` and a file outside it is an error even with `strict_scope: false`,
  every criterion under `Tests:` names its test in `Proof:` with a `Report:`
  (an error that blocks the proposal), and the review comes from an isolated
  session. The level is part of what the proposal's approval hashes, so the
  human approves it with the proposal and changing it voids that approval; no
  approval is added. `proposal` shows `Kind: ... · Risk: ...` with what the
  level asks, `check` notes it, the review packet states it and the dossier
  shows it, with `NOT NEEDED` and the reason for each criterion `low` takes
  from its named test. A value other than the three is an error.
- `atipspec new --kind fix` creates a guided fix (`schema: 2`), approved with
  one proposal and without an accepted contract, like a feature. Its
  `spec.md` states the defect under `## Defect` (`Observed:` and `Expected:`
  required, `Reproduction:` advised) and lists under `requirements` the
  accepted requirement it corrects in `specs/<capability>.md`, where the model
  adds the regression criterion or rewrites the one that let the defect
  through. A requirement that `specs/<capability>.md` did not hold at the
  delivery's base commit, nor received since through the integration branch
  or a delivery archived in the branch after the base, is an error, unless no living spec
  held a requirement (an info); neither the working file nor `baseline.json`
  changes that list, and the capability is the one `spec.md` names. A fix
  removes no requirement and adds, changes or deletes none it does not list,
  in its capability or in another one's living spec, and at least one
  criterion of the corrected requirements goes under `Tests:`. `merge-check`
  blocks a fix whose requirement was not in the living spec at the merge base
  nor written by an earlier delivery of the branch. Its plan has one task and
  a `## Final verification` with the contract's commands and a placeholder for
  the command that runs the regression test. The living spec gets only the corrected behavior; in 0.2.0 a fix
  added a new requirement with the defect's story to it. `proposal` shows
  `Corrects: REQ-... (accepted requirement)`. The flow takes about ten
  commands: `new`, `fix`, `proposal`, `accept proposal`, `task-done`,
  `verify`, `review`, `report`, `accept result`, `deliver`. The fix workflow
  no longer asks for a `[<slug>:T1]` commit or a trust policy to deliver.
- Lead time: wall-clock hours from a delivery's creation (`created`, written
  by `new`) to the acceptance of its result, or to now until then.
  `max_age_hours` defaults to 8 instead of 48, and its warning, which only
  `status` showed, is now in `check`, and so in the dossier's checks, from the
  draft on; below the limit `check` shows the lead time as an info. The clock
  stops when the result is accepted. `status` shows each
  open delivery's lead time and each delivered one's. The dossier and the
  receipt carry `kind`, `risk` and `lead_time`; under a policy, the lead time
  in `check`, `status`, the dossier and the receipt ends at the latest signed
  acceptance. `pilot record` no longer requires
  `--lead-hours` for the `atipspec` cohort: it reads them from the archived
  receipt, or from the records archived with a 0.2.x delivery, records
  `lead_hours_origin`, and refuses rather than estimate. The `baseline`
  cohort still needs them measured.
- `atipspec run` with `risk: high` or `require_isolated_review` and an adapter
  without `isolated_review` stops at `needs_decision` before calling any role,
  instead of after the implementation.
- The working-tree fingerprint keeps the git index's time on the temporary
  copy it hashes from, so a file rewritten with the same size in the second
  the index was written is read again instead of taken from the index: before,
  evidence or a review could be bound to the file's previous content, and
  `verify` could call its own run stale.
- A path with characters git quotes, such as `src/reset/café.py`, is read as
  written: before, the scope check took it for a file outside every glob, and
  the contract check and the audit left it out.

- Integrating another delivery no longer voids an open one's approval. A
  guided proposal's approval (subject version 2) hashes of its capability's
  living spec only each requirement the delivery lists, apart; of
  `teams.json` only the capability's owners and `integration`, under a trust
  policy too; and of `spec.md` everything but `status` and `ticket`. A
  requirement it does not list is not part of the approval: `check` and
  `merge-check` block a change of one. In 0.2.0 a merge of main voided every
  open approval of the capability. The same holds for `task-done` records,
  signed approvals and review round counts; drift messages name the part that
  changed, such as `.atipspec/specs/auth.md REQ-001`. What the integration
  branch brought is not the delivery's change, as in the diff of a pull
  request: the files and the requirements that changed between the commit
  where the delivery's base meets that branch and the merge base of `HEAD`
  with it, a file only while the delivery has not changed it since, whether
  main merged, squashed or rebased the other deliveries. Changing a file
  main brought since, putting it back as the base had it included, in the
  index or not, is the delivery's change: it counts in the scope, the review
  packet and the dossier show it against that merge base, as a pull
  request's diff does, and `check` warns when the delivery undoes there, in
  whole or in part, what main changed, read from the two diffs: a line main
  added that the delivery takes out or rewrites, or one main took out that
  the delivery puts back where it was, or anywhere when main left no such
  line in the file. The integration branch is `integration` in
  `teams.json`, or the first of `refs/remotes/origin/HEAD`, `origin/main` and
  `origin/master` that resolves; under a trust policy only the policy's new
  `integration` key.
  Without a ref nothing is attributed, nor when main holds the delivery's own
  folder. `check` and the proposal's diff compare the living spec with what
  main holds, and the files the integration branch brought are neither
  outside the plan's scope nor in the review packet's or the dossier's diff,
  which list them apart. A change main made outside a delivery, such as a
  hotfix, counts as brought too, as in a pull request's diff.
- Records carry `subject_version`: local approvals, `task-done` records,
  signed approvals, review round counts and runner checkpoints. One without it
  is compared with the version 1 subject it was made for, and a provider
  review that carries a version 1 marker still counts.
- `atipspec ids <capability>` prints a short prefix, `REQ-AUTH-7KQ2M-001`: a
  five-character Crockford base32 token, shared by the requirement and its
  criterion, that no ID in the living spec, the deliveries, the archive or
  the refs of `teams.json` uses, and asks to number the delivery's further IDs
  with it (`-002`, `-003`). 0.2.0 printed a 32-character token. Its IDs stay
  valid. The spec workflow and template say to run it once per delivery.
- `new --ticket` takes a key (`SHOP-12`), an issue number (`#42`) or an https
  URL and refuses free text. With `ticket_url` in `teams.json` (`{ticket}`
  where the key goes) the ticket is a link in `status`, `team`, the proposal,
  the dossier (`ticket_url` in its JSON; an HTML link only to https) and
  `merge-check`. It is not part of the proposal's approval.
- `merge-check` lists each delivery the branch touches with its state and
  ticket, a table in `--format markdown`, so the pull request's check shows
  them. The deliver skill tells the agent, when the user asks for a pull
  request, to put the ticket and `atipspec report <slug> --format markdown`
  in its description.
- `status --format json|markdown`: the project's state as data, or tables for
  a pull request; `status` still exits 0.
- `system:` in `config.yaml` works with guided deliveries: `new` pins the
  system repository's `contract.md`, and its `glossary.md`, with
  `contract-pin`, and their context reads them from that commit. 0.2.0
  refused every guided proposal while `system` was set. Without the pin,
  `check` names the `contract-pin` command; `contract-pin --repository system`
  needs no `teams.json` entry. The proposal lists the pinned contracts.
- `teams.json` accepts `refs` ending in `*` (`refs/remotes/origin/delivery/*`),
  `integration` and `ticket_url`; `atipspec team --fetch` fetches the remotes
  those refs name without prompting for credentials, and the board says when
  the repository last fetched. Reading the refs never fetches. `teams.json`,
  `team`, `contract-pin` and `ids` are now documented.
- Correction of 0.2.0, whose migration tooling no command reached:
  `spec-bind` now imports a document with an `Acceptance Criteria` section,
  keeps the original in the delivery's `sources/`, adds
  `## Import review notes` and refuses a generated ID that names another
  requirement. The new `atipspec migrate <slug> [--apply]` shows how a legacy
  delivery becomes a guided one and writes it with backups; it approves
  nothing and refuses legacy fixes.

- Provider mode attests evidence only from a trusted workflow outside the
  candidate repository. In a pull request GitHub runs the workflows the pull
  request carries, so 0.2.0's evidence workflow, which had to live in the
  candidate repository, could be rewritten by the change it attested. The
  policy's `[attestation] signer_workflow` must now name a workflow of another
  repository of the same organization, compared without case, and
  `signer_digest` pins its commit; `owner` becomes optional and must match the
  repository's organization when set, and `[provider] kind` must be `github`.
  A policy that breaks any of these does not load, and says why. The worker
  runs `gh attestation verify` with `--repo`, `--signer-workflow`,
  `--signer-digest`, `--source-ref refs/pull/<number>/merge` and
  `--deny-self-hosted-runners` (`allow_self_hosted_runners = true` lifts the
  last one), fails closed without the PR number, and requires each evidence
  record's `head` to be the commit it checked out.
- `enterprise-init` replaces `github-evidence.yml` with
  `github-evidence-trusted.yml`, the reusable workflow for the trusted
  repository, and `github-evidence-caller.yml`, which each candidate
  repository runs on `pull_request` at the pinned commit. 0.2.0's workflow
  checked out the merge commit, kept the evidence committed to the branch and
  attested every `evidence/*.json`, so a committed record could be attested.
  The trusted workflow checks out the pull request's head and deletes the
  committed evidence (`atipspec.verify.clear_evidence`); a `produce` job runs
  the Verify commands without an OIDC token or attestation permission, and an
  `attest` job, which runs no candidate command, attests only the records
  `atipspec.attestation.records_to_attest` accepts: one passing record per
  verified task of each active delivery, written on that head and tree. It
  downloads them by the artifact's ID, since a job the pull request adds to
  the caller can replace an artifact of the same name in the run.
  `ADOPTION.md` gives the worker's commands, which take only the `evidence/`
  folders of the run attempt's artifact, `atipspec-evidence-<attempt>`, since
  the caller can upload others to the same run, and says what an attestation
  does not prove: code under test can fake its own results while it runs. For
  ssh mode it says to clear the committed evidence before the producer
  verifies and before the collector restores its records, since `attest`
  signs the record that finished last.
- In ssh mode the product approver confirms the delivery owner:
  `atipspec approve <slug> spec` needs `--owner`, the `owner` `spec.md`
  declares, and signs it with the approval; `--owner` is refused in other
  phases. A spec approval that confirms no owner, or another one, does not
  count, and `check` and `verify --policy` name the command. 0.2.0 excluded
  from the later phases whatever owner the author wrote. In both modes the
  later phases exclude the owner whatever the case: an owner written
  `Engineering` is the identity or account `engineering`. Under a policy the
  owner is written in ASCII letters, digits, `_`, `.`, `@` and `-`, as
  identities are: `check` and `approve` refuse one that only reads as an
  identity, with a Cyrillic letter or an invisible character in it.
- Windows. AtipSpec reads CRLF line endings as LF wherever it hashes a file or
  checks a signature: an approval's subject, signed approvals and evidence
  records, command output logs, test report copies and the installed skills it
  compares with its own. What is approved, accepted or verified in a checkout
  with `core.autocrlf` (the Git for Windows default) no longer looks changed
  on Linux or macOS, nor the other way round, and neither does the copy of a
  report a test tool on Windows wrote with CRLF, which git commits with LF.
  Every text file AtipSpec reads or writes, and the output of `git`, `gh` and
  the Verify commands, is UTF-8, and what it writes uses LF;
  `tests/test_portability.py` checks the package for it. On a pipe the CLI
  writes UTF-8 whatever the code page, so a spec with `→` no longer ends in an
  encoding error. Evidence and the receipt record paths with `/`. A plan's
  `Report` is refused on every platform when Windows reads it as absolute or
  outside the project (`/x`, `C:\x`, `..\x`). The checkout lock that
  `migrate --apply` takes works on Windows too. Outside POSIX, `atipspec run`,
  which stops an adapter by its process group, refuses before it reads the
  delivery or writes anything and says to use Linux, macOS or WSL, or the
  guided conversation. CI runs the suite (one process per test module, as each
  git and Python process starts slowly there) and the smoke test on
  `windows-latest` with Python 3.11 and 3.13, and on Linux the
  suite again with text written as Windows writes it, CRLF where no newline is
  named (`python -m tests.windows_text`). On every platform the suite's
  repositories check text out with CRLF, as Git for Windows does by default.

- The documentation describes the guided flow the code runs. The new page
  "Guided delivery, end to end" (`flow/guided.md`, in the navigation) follows
  one change through the three human decisions, every command the assistant
  runs, what the CLI checks and which files each step writes. The quick start,
  the spec, plan, build, review and deliver pages, how it works, the home
  page, clients, teams, design and the artifacts, configuration and layout
  references teach the guided format: requirements and scenarios in
  `specs/<capability>.md`, the proposal, `task-done`, the final verification
  and the result's acceptance. The embedded `spec.md` format, `accept
  spec|plan`, `approve_plan`, commit markers, `ids --legacy` and `migrate`
  moved to the new "Legacy deliveries" reference, and the execution adapter
  page into Reference. The CLI reference has a section for each of the 38
  commands with every option, who runs it, what it writes, when it refuses
  and its exit codes, and an environment table.
- Corrected claims of the 0.2.0 documentation that the code did not hold: a
  task is done when a commit carries `[slug:Tn]` (only in a legacy delivery;
  guided deliveries record it with `task-done`), "git is the state machine",
  `deliver` requires a trust policy (without one it requires the recorded
  acceptance of the result), stop point 2 is the merge (it is the result's
  acceptance; the merge follows the repository's policy), a person runs
  `accept` and the model never does (the assistant records the human's
  decision), the contract is required to start every delivery (only legacy
  ones), and the quick start's `### REQ-001` in a guided `spec.md`, which
  `check` rejects.
- `tests/test_docs.py` keeps the documentation with the code: every command
  and option that the English pages, README, CONTRIBUTING, the installed
  framework and skills and the CLI's own messages cite exists; the CLI
  reference covers every command and option; every page is in the navigation;
  the versions in `pyproject.toml`, the package, README, the CHANGELOG and the
  installation banner agree; `config.yaml`'s reference lists every key; a list
  of retired claims stays out of the English pages and the installed text;
  and the Spanish and Portuguese pages translate every page, and only
  those, with the same commands and options and the same CLI reference.
- `atipspec new` writes a guided `spec.md` from the installed
  `templates/spec.md`, which now is the guided spec (`schema: 2`,
  `requirements`, `risk`) with a comment on the format of `specs/`; the
  template taught the embedded format, which `new` no longer creates. Its
  `plan.md` says where the IDs of `Covers:` and `Tests:` come from instead of
  showing `REQ-001` and `AC-001`.
- CLI messages name what the guided flow needs. A guided draft without
  requirements asks to write them in `.atipspec/specs/<capability>.md` and
  list their IDs, or to run `spec-bind`, instead of `### REQ-001` in
  `spec.md`, and one that lists IDs the living spec lacks gets only the
  error that names them; a requirement without criteria asks for a scenario there; a
  guided plan without tasks asks for Tests or Manual and a final
  verification. A problem in a living spec names that file and line, in
  `check` and `audit`, instead of `spec.md line N`. The final verification's
  evidence is judged once, after the tasks, so a task still to record comes
  first in `Next:` and a missing or stale run is reported once. `ship` names
  the real stop points: the proposal's approval before building and the
  result's acceptance before `deliver`. `task-done` prints the record it
  wrote, relative to the project, and the next action. `deliver`'s help says
  it archives an accepted delivery; `team --json` and `contract-pin`'s
  arguments have help, and `review`'s says that each changed candidate counts
  a round, whether its review passed or not. Without git, `check` and `init`
  say the base commit, contract rules and evidence freshness need it.
- The installed rules and spec workflow say to leave a legacy delivery's
  embedded requirements in place and convert one only with `atipspec migrate`
  when the user asks; the build workflow says commit markers count only in
  legacy deliveries; the umbrella skill lists `ids`, `spec-bind`,
  `task-done`, `report` and `merge-check`.
- Closing review. `check --json` works again (a set in the report broke it).
  `merge-check` reads paths with `-z`, so a decision or living spec whose name
  git quotes is judged; locally it also blocks a receipt changed after its
  archive commit, one removed and added again, unless a revert of the archive
  commit reopened the delivery in between or an earlier archive added that
  receipt, and one whose code neither its archive commit nor that commit's
  parent holds. A local receipt is still not authenticated: a history
  rewritten coherently, or a reopening faked by hand, passes, and only a trust
  policy checks the delivery again. `merge-check` shows the channel `accept`
  declared for each approval, which is not who approved, and blocks code a
  branch changes that no delivery it archives or leaves open changed after
  its base commit, also when it only removes deliveries, unless
  `exempt_paths` on the target branch exempts it (see the closing decisions
  below). Without `integration` in `teams.json`, the
  integration branch is the first of `origin/HEAD`, `origin/main` and
  `origin/master` that resolves, so a CI checkout without `origin/HEAD` hashes
  approvals as the developer's clone does when that branch is main or master;
  for another name, set `integration`, and `status` and `audit` warn when
  `origin/HEAD` names one and `integration` is not set.
  `accept <slug> proposal` starts the review round count, and a count deleted
  afterwards makes `review` refuse and `check` fail until the human decides.
  `ship` stops when the rounds are used up. A guided draft's `check` lists
  what the plan and the contract still lack, and the proposal shows the plan's
  and the contract's warnings, the policies `config.yaml` changes since the
  base and the capability decisions the implementation follows. Without git, a
  guided draft's `check` is red and `new` warns. `require-command` accepts the
  command followed by more arguments, but not by a control operator, a
  redirection or a command substitution, such as `|| true` or `| tail -1`,
  that can hide its failure, nor, on Windows, by a `cmd.exe` metacharacter;
  arguments that narrow the run still count. Verify
  commands no longer get the SSH agent, CI job tokens or OIDC request tokens.
  A blocker finding's message no longer suggests a deferral that only a trust
  policy allows; a guided spec without `schema: 2` is an error; a hook in the
  project's Claude Code settings that can answer the prompt lowers the channel
  to `assistant`; build and explore print the rules without the approval
  protocol, and the rules on approval records, statuses and commits are now
  among those every phase prints.
- Closing simplification. What the integration branch brought is attributed
  with the merge base alone, as a pull request's diff does: the receipts of
  the deliveries main integrated no longer have to vouch for it, so a merge, a
  squash or a rebase on main, a fresh clone or a CI checkout attribute alike,
  and a hotfix main made outside a delivery is accepted with the rest of main.
  The proposal's approval hashes only the requirements the delivery lists,
  and a requirement changed without being listed is an error at every risk
  level instead of a warning, as `merge-check` blocks it. A receipt records
  the text of each requirement `deliver` wrote, which `check` and
  `merge-check` compare with, and only the deliveries archived in the branch
  count; the proposal no longer asks the human to check merges or the commit
  that last changed the living spec. `merge-check` follows the full history
  when it looks for the commits that added a receipt, so a receipt a merge
  takes from another branch is judged like one removed and added again. The
  warning about an integration branch a CI checkout would not find also asks
  to declare it in the trust policy that judges the merge.
- Closing decisions. `merge-check` blocks a branch that changes files outside
  `.atipspec/` that no delivery archived in it or open at its head covers,
  instead of warning. A delivery covers the files its dossier shows: those
  that changed between its base commit and the head, and those the
  integration branch changed that the branch holds otherwise, but not those
  the branch had changed before that base, so code committed before `atipspec
  new` is outside it, in a file the delivery changes again too, and so is a
  change of a target branch other than the integration branch that the
  branch puts back as the base had it. The dossier is the one the human
  accepted: when a delivery puts back what the integration branch changed,
  the acceptance of its result also hashes the merge base its dossier shows
  those files against, so taking that branch in again afterwards voids it,
  even with the tree kept (`git merge -s ours`); an archived delivery covers
  the files its receipt lists (under a policy, those its dossier shows at the
  commit it was delivered from), less those the target branch changed after
  the commit that archived it, which the branch takes back, whatever
  `integration` the branch names afterwards. A delivery archived in the branch
  whose base commit is not in the history of `HEAD`, as after a squash of the
  branch, blocks with that commit named, and the result says it did not look
  for code outside the deliveries. Only the files
  that `exempt_paths`, a new list of globs in `config.yaml` (empty by default,
  written by `init` and validated by every command), matches pass, and client
  files that hold only what AtipSpec installs. It reads the list from the
  target branch (`--base`), never from the branch it judges, so a branch
  cannot exempt itself; the result lists the files it let through, and warns
  when the branch changes `exempt_paths`. Which files need no delivery is the
  user's decision: the rules tell the agent to change `exempt_paths` only when
  the user asks, and no approval hashes it, so setting it on main sends no
  open delivery's proposal back to draft. The Claude
  Code rules also ask before `Edit` on `.github/workflows/**`, `.gitlab-ci.yml`
  and `.claude/settings*.json`, so the agent does not change the CI that runs
  `merge-check`, or the rules themselves, without the human; `audit` and the
  rules' state check them, and `audit` names the rules missing.
  `review_rounds` counts every review, the first included (default 3), and
  every output says `review N of M`. One fingerprint, with the task titles of
  every delivery plan reduced to their ids, replaces the pair of trees
  (`tree_without_titles`, `packet_tree_without_titles`), so a recorded tree
  holds exactly while the fingerprint is the same. `check` and the proposal
  compare a delivery's living spec with the one its base commit holds, at
  every kind and risk, and `new` refuses to start while that living spec has
  changes not committed; a delivery created before 0.3.0 still compares with
  its `baseline.json`. `require-command` does not count, on Windows, a line
  with a `cmd.exe` metacharacter (`&`, `|`, `<`, `>`, `^`, `%`, a double
  quote) after the command, as `cmd.exe` reads quotes otherwise than sh.
- Closing trial. The framework in `.atipspec/framework/`, whose rules and
  workflows every phase prints to the agent, must hold what the installed
  version installs, as the client skills do: a file changed, missing, or
  added and not ignored by git is an error in `audit`, in `check`, where it
  blocks the proposal, the tasks, the build and the review, and in
  `merge-check`, until `atipspec install --update`, which now also removes
  the framework files the version does not install; the rules tell the agent
  never to edit it. `merge-check` shows more without blocking more: it warns
  when the branch relaxes a policy of `config.yaml` against the target branch
  (`strict_scope`, `strict_criteria`, `criteria_syntax`, `review_rounds`,
  `max_tasks`, `max_requirements`, `max_age_hours`, `require_proof`,
  `require_isolated_review`, `trust`),
  listed as the proposal lists its policy changes, and when it adds, changes
  or removes `overview.md`, `glossary.md` or a decision, with each decision's
  status, since the agent reads them as context and no delivery's approval
  covers them, and when it changes `adapter.json` (the program `atipspec run`
  executes, and whether its reviews count as isolated) or `teams.json`; when the branch changes the contract or a decision that
  affects it, the result shows the contract's acceptance and its channel. A
  delivered branch that takes the target branch in is told to reopen the
  delivery (revert its archive commit, then verify, review, accept and
  deliver it again) and to take the target branch in before `deliver`,
  instead of reverting the files, which blocked again; the error for code
  outside any delivery is two sentences; `new`, with the living spec changed
  and not committed, says to discard the changes or make them in the
  delivery, no longer to commit them, which `merge-check` blocks; `status
  <slug>` shows the recorded approvals with their channel; and a guided
  draft with nothing missing asks only to present the proposal. The client
  page no longer says that the `ask` rules for the CI and the settings stop
  redirections: with Claude Code 2.1.296 in `acceptEdits` mode, a Bash command
  the settings allow wrote to `.github/workflows/` with a redirection without
  asking, so the protection that holds is `merge-check`. `enterprise.md` and
  `ADOPTION.md` suggest an `exempt_paths` list to start from, and say that
  each entry is code no human approves in a delivery.

### Updating to 0.3.0

Install the new package and run `atipspec install --update` in each project: it
refreshes the framework and skills and merges the Claude Code permission rules
into `.claude/settings.json`. Until then, local approvals are recorded with
channel `assistant`, `audit` warns, and `audit`, `check` and `merge-check`
fail on the framework, which must be the installed version's; pin the same
version in the CI that runs `merge-check`. Customized framework files are
replaced, and files added to the framework are removed. Scripts that ran `atipspec accept`
without a terminal must pass `--code` with the code `proposal` or `report`
shows. Guided deliveries approved only with `accept spec` and `accept plan`
return to draft: present `atipspec proposal <slug>` and approve once. Records
written by 0.2.x stay valid while their content does not change and show
`channel not recorded`. A contract accepted in 0.2.x by its status alone shows
as accepted without a record: present `atipspec proposal contract` once and
record `accept contract --code <code>`; until then legacy deliveries, fixes
created before 0.3.0 included, cannot enter `spec` or `fix`, `merge-check` blocks a branch that changes the
contract or a decision that affects it, and `context` loads contract decisions
by their status as before. A contract still in draft has no accepted decisions:
`context` leaves out those that affect it, or that have no `affects`, until
its acceptance is recorded. `install --update` rewrites the framework files and
`.claude/settings.json`, which are part of the tree hash: as after any change
to the tree, the evidence and review of a delivery in progress become stale,
and a result accepted but not yet delivered must be presented again. Deliver
accepted results before updating.

Guided drafts created with 0.2.0 have an empty `## Intent`, which now blocks
their proposal: fill it before presenting them, and add `## Out of scope` and
`## Quality attributes` (`- None` when nothing applies) to clear the warnings.
For a delivery whose proposal is already approved, and not changed since,
an empty Intent and those sections are only warnings, and no approval becomes
outdated: the lint reads the files, it changes none. Settle them the next time
that proposal changes; editing `spec.md` only for them voids its approval.
Projects that keep `strict_criteria: false` see the new lint findings as
warnings.

For each open delivery: run `atipspec verify <slug>` again if its plan uses a
`Report:`, after moving that report to a path git ignores, such as
`.atipspec/tmp/junit.xml` (in a guided delivery that edits the approved plan,
so the proposal is presented again). Run `atipspec review <slug>` again if its
`review.md` has pointers that are not a test of the report, a `path:line` or a
`path::test`, or has no `reviewer:`; the reviewer now also declares
`session: isolated|shared`, and a review without it is a warning (an error
with `risk: high`). `require_proof` and `require_isolated_review` are `false`
unless set, so they change nothing until a project or its trust policy turns
them on; `install --update` lists them as not set. `install --update` also
adds the `deny` rule for `review-rounds.json` and the `ask` rules for the CI
workflows and the Claude Code settings; until then `audit` reports the Claude
Code rules as partial, naming the missing ones, and approvals record channel
`assistant`. The fingerprint now leaves the task titles of every plan out, so
the trees 0.2.x recorded no longer match: a delivery in progress runs
`atipspec verify <slug>` and `atipspec review <slug>` again and, if its result
was accepted, presents `atipspec report <slug>` for the result's acceptance
again. Its reviews are counted from the first packet `atipspec review` writes
after the update: the `review.md` written before names a tree of the earlier
fingerprint, never this candidate, so it is not counted. `review_rounds` now counts
every review, the first included: a `config.yaml` that 0.2.x wrote with
`review_rounds: 2` allows two reviews, one fewer than the default 3, and
`install --update` lists it; raise it when no guided delivery is between its
proposal and its result. A `run --max-rounds` above `review_rounds` less one
is now an error. A guided proposal's
approval is hashed in version 2 from now on; records written before keep
their version 1 hash and stay valid until their content changes, as before.

A fix created before 0.3.0 (no `schema: 2` in its `spec.md`) keeps its legacy
flow until it is archived: the contract's acceptance to start, its embedded
requirement, `accept <slug> spec` and no plan acceptance; the new fix workflow
says so. Fixes already archived keep the requirement they added to the living
spec; clean it with a delivery when it matters. A delivery, legacy ones
included, that set `risk: high` by hand now needs a declared scope, a `Report:`
and a `Proof:` entry for every criterion under `Tests:` (configure the test
command to write JUnit XML, such as
`pytest --junitxml .atipspec/tmp/junit.xml`) and an isolated review; one with
`risk: low` stops needing verdicts for criteria its named tests prove, and
cannot remove a requirement. `check` notes the level. Projects keep the `max_age_hours: 48`
that `init` wrote, and `install --update` lists it; to adopt 8, edit
`config.yaml` when no guided delivery is between its proposal and its result,
since the proposal's approval hashes that file. Receipts written before keep
rendering without kind, risk or lead time.

Every command but `init` now stops on a `config.yaml` value 0.2.x ignored or
misread: a boolean written as `no` or `yes`, `review_rounds: 0`, or a word
where a number goes. The message names the key; set a valid value.

Existing projects keep `strict_scope: false` and `strict_criteria: false`,
which `init` wrote out. To adopt the strict values, set both to `true` when no
guided delivery is between its proposal and its result: `config.yaml` is part
of what a proposal's approval hashes. A plan with `scope: []` in a strict
project needs its scope, and its approval again. Replace a copied
`github-local.yml` or `gitlab-local.yml` with the new examples
(`atipspec enterprise-init --out <new directory>`) and run the project's tests
in their own job. `merge-check` blocks a branch that changes code with no
delivery, or with code it committed before `atipspec new`: before you
require its job, list in `exempt_paths`, in the target branch's
`config.yaml`, the files no delivery needs to govern, such as `"docs/**"`
(`install --update` lists the key as not set). The pull request that adds or
replaces the workflow file is such a change: merge it before you require the
job, and make a later change to that file, such as a new pin, in a delivery,
or list that file alone in `exempt_paths` first if the user decides it needs
none; `.github/**` would let a branch change every workflow with no delivery.
No approval hashes
`exempt_paths`, so setting it voids no open proposal; a branch that takes the
change in verifies and reviews again, as after any change main brings. `atipspec new`
refuses while the capability's living spec has changes not committed: discard
them, or set them aside and write them back in the new delivery; committed on
their own, outside a delivery, `merge-check` blocks them. Before relying on `merge-check`, merge the branches that
already archive a delivery with 0.2.x, or revert their archive commit and
deliver again: their receipts have no `code_tree`. After `deliver`, change no
code on the branch and do not bring the target branch into it; bring it in
before the final verification. Organizations with a trust policy add `trust:
required` to `.atipspec/config.yaml`, protect it with CODEOWNERS, and run
`merge-check --policy` on the protected worker; commit the archive on its own
right after `deliver`, since `merge-check` checks the delivery again at the
commit before the archive commit. A worker that already passes a policy to
`merge-check` without `trust: required` now blocks locally accepted receipts.

So that integrating another delivery does not void open approvals, work with
one branch per delivery and, when the integration branch is neither main nor
master, set `integration` in `teams.json`, such as
`"refs/remotes/origin/develop"`: a CI checkout has no `origin/HEAD`, so
without it CI finds another branch, or none, and `status` and `audit` warn
about it; under a trust policy add `integration` to the policy. Approvals made
before the update still hash the living spec whole:
taking main in voids them once, and the next approval uses version 2. In an
open guided delivery, a requirement changed in `specs/` without being listed
is an error at every risk level: list it under `requirements` in the delivery
that writes it, or restore it, before presenting the proposal. With
`system:` set, pin the system contract in each open guided delivery once:
`atipspec contract-pin <slug> system-contract --repository system --ref HEAD
--path contract.md` (and `system-glossary` with `--path glossary.md`), which
voids its proposal's approval. Scripts that passed free text to `new
--ticket` pass a key, an issue number or an https URL; tickets already in
`spec.md` are shown as they are.

Organizations in provider mode: create a repository of the organization for
the evidence workflow, protect it, and, if it is private or internal, open its
Actions access to the organization's repositories; copy
`github-evidence-trusted.yml` there as `.github/workflows/atipspec-evidence.yml`
with `ATIPSPEC_PACKAGE` and the actions pinned; set `signer_workflow` to it and
`signer_digest` to that commit in the policy, drop `owner` or leave it as the
organization, and pin the policy's new SHA-256. Until then the policy does not
load and the gate fails closed. In each candidate repository replace
`.github/workflows/atipspec-evidence.yml` with `github-evidence-caller.yml`
calling the same commit, and on the protected worker delete the committed
evidence and download the latest successful run's artifact before `check` or
`deliver` (`ADOPTION.md`). Organizations in ssh mode: for each open delivery
the product approver signs the spec again with `atipspec approve <slug> spec
--owner <owner> ...`. On Windows nothing needs doing; an approval made there
with CRLF files before the update shows as changed once and is approved
again.

Run `atipspec install --update` also to get the guided `templates/spec.md`,
the updated rules, spec and build workflows and the umbrella skill; deliveries
already created keep their `spec.md`. Scripts that read the path `task-done`
printed now get `AtipSpec: T1 of <slug> recorded as implemented (progress, not
verification) in <path relative to the project>` and a `Next:` line. Two
pages of the site moved: `/execution-adapter/` is now
`/reference/execution-adapter/`, and the Spanish guided page `/es/guided-flow/`
becomes `/es/flow/guided/`.

## 0.2.0 — Guided workflow and conversational approval

- Human approval stays in the assistant conversation. The agent presents the
  agreement and offers approval, changes or cancellation using the client's
  selector when available, or a plain reply. After explicit confirmation, it
  records acceptance and continues; the user need not run approval commands or
  edit statuses. Contract approval can include the listed architecture decisions.
- Guided deliveries combine behavior, implementation approach and test strategy
  in one reviewable proposal. `atipspec proposal <slug>` presents the agreement
  and specification diff; `accept <slug> proposal` records approval of its content.
  The reviewed result requires separate human acceptance with `accept <slug> result`.
  Changed agreements require renewed approval.
- New feature deliveries reference canonical requirements in `.atipspec/specs/`.
  `spec-bind` installs complete requirements and their delivery references without
  creating empty capability documents. Scenarios support GIVEN/WHEN/THEN, AND/BUT,
  manual criteria and invariants, including Spanish and Portuguese step words.
- `task-done` records implementation progress without requiring a commit per task.
  Shared final verification runs against the finished candidate; targeted task
  checks remain available during development. Local result acceptance permits
  archiving without signatures. External trust policies retain their authenticated
  acceptance requirements; commit, push, merge and deployment follow repository policy.
- Guided skills define responsibilities for the guide, analyst, designer, tester,
  implementer and reviewer, with checks scaled to risk and explicit disclosure
  when independent review is unavailable. (Corrected in 0.3.0: in 0.2.0 `risk`
  only chose the roles and instructions of `context --role` and `run`; no gate
  check depended on it until 0.3.0.)
- An optional POSIX process runner supports configured execution adapters,
  checkpoints, budgets, bounded correction rounds and explicit recovery after
  interruption. It requires proposal approval and does not approve results itself.
  It is a foreground runner, not an installed background service; live coding-client
  integration still requires a wrapper and validation.
- Team coordination adds capability ownership, concurrent identifiers and
  integration checks. Migration tooling converts legacy embedded deliveries,
  which remain supported. (Corrected in 0.3.0: no command reached the
  migration code in 0.2.0; 0.3.0 adds `spec-bind` imports and
  `atipspec migrate`.)
- Updated workflows, skills, CLI guidance and documentation to consistently
  distinguish the human's decision from the agent's recording of that decision.
  (Corrected in 0.3.0: the spec templates still said a person runs `accept`,
  several pages that the model never runs it, and most pages taught the 0.1.0
  flow; see the 0.3.0 notes.)

### Updating existing projects

Install the new package, then run `atipspec install --update` in each project to
refresh its framework and installed skills. The agent can perform this update.
Inspect customizations first: the update replaces framework and skill files that
differ from the package. Reload cached client skills or start a fresh session.
Local acceptance detects content drift; it does not authenticate human identity.

## 0.1.0 — First release

Initial version of AtipSpec, prepared for new projects.

- One command, one skill and one workflow per phase. `atipspec explore|spec|plan|build <slug>`
  check what the phase requires and refuse with one line while a step is missing;
  otherwise they print the workflow, the shared rules (`framework/rules.md`) and the
  context. `review` refuses until every task is committed with fresh evidence;
  `contract` and `curate` print their workflow; `ship` names the next phase.
- `atipspec accept <slug> spec|plan` and `atipspec accept contract`: a person
  accepts, the command sets the status and records a hash of the accepted content,
  and `check` sends the delivery back to draft when the spec or the contract changes
  afterwards. The model never sets `ready` or `accepted` and never runs `accept`.
  `atipspec build` refuses until the plan is accepted when `approve_plan` is on.
- `init` warns when the repository has no `.gitignore`, because untracked build
  caches change the working tree and make evidence stale.
- Trusted acceptance in two modes: an SSH mode using an external organization
  policy, signed CI evidence and content-bound human approvals by role; and a
  provider mode (`schema = 2`, `mode = "provider"`) where the protected worker
  reads product, engineering and QA approvals live from the PR or MR and verifies
  each CI evidence record with a GitHub artifact attestation through a pinned
  `gh` — no human, CI or collector key to enroll. `check`, `deliver` and `report`
  take `--number` or `ATIPSPEC_PR_NUMBER`. `enterprise-init` writes the provider
  policy example and the evidence workflow.
- Read-only GitHub and GitLab approval adapters, including revocation checks.
- Stable requirement and acceptance-criterion IDs with test/evidence mapping.
- Acceptance dossiers in JSON, Markdown and HTML.
- Languages: English primary, Spanish and Portuguese supported. `language` in
  `config.yaml` drives the criterion lint, the section names and empty markers the
  parser accepts, and the acceptance dossier's labels; `init` offers the three;
  `audit` warns about a language without tables. The documentation site builds in
  the three languages with a switcher and English fallback for untranslated pages.
- Evidence per criterion: a task can name the JUnit XML its commands write
  (`Report:`) and the test that proves each criterion (`Proof:`). `verify` copies
  the report with its hash and records every test case; `check` fails when a named
  test did not run or did not pass; altering the copy is detected; the packet and
  the dossier show the tests per criterion.
- `atipspec new --kind fix` and the `fix` phase: a defect gets a spec with one
  regression criterion, a one-task plan with the contract's required commands
  prefilled, no interview and no plan acceptance; evidence, review and the gate
  are unchanged. `status` marks such deliveries `[fix]`.
- Deliveries are sized for a working day: `check` warns above `max_requirements`
  (5) and `max_tasks` (8), `status` shows how long each delivery has been open and
  warns above `max_age_hours` (48), and `new` records `created` with the time.
- Specs follow the industry's shape: criteria in EARS or scenario form with
  concrete values (`check` warns about other forms and about vague terms, in
  English and Spanish; `criteria_syntax` and `strict_criteria` tune it), a
  `[manual]` mark for criteria a person observes that the plan must respect,
  `## Assumptions` the user confirms at acceptance, `## Quality attributes`
  with numbers, and `Why:` lines. Every criterion must be mapped under `Tests:`
  or `Manual:` before `atipspec build` starts.
- The review packet includes the living specs in the impact list and the accepted
  decisions affecting them, so a reviewer can see conflicts with existing behavior;
  the diff is capped at 200 KB with a `--stat` summary when truncated.
- Plans declare `scope`, the globs of files their tasks may change. `check` warns
  about touched files outside it, deletions included (`strict_scope: true` makes
  it an error) and the packet lists them for the reviewer.
- Enterprise policy and CI examples, an adoption guide, and MIT licensing.
- Pilot protocols and sourced measurements for comparing real deliveries.

Organization trust, protected CI and real-world pilots require configuration
in the adopting organization. This entry describes the initial codebase;
publication to a package registry is a separate release operation.
