# Configuration

`.atipspec/config.yaml`, written by `init`:

```yaml
name: shop
language: es
approve_plan: true
review_rounds: 3
context_budget: 800
strict_scope: true
criteria_syntax: ears
strict_criteria: true
max_requirements: 5
max_tasks: 8
max_age_hours: 8
trust: optional
require_proof: false
require_isolated_review: false
exempt_paths: []
```

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | folder name | project name, shown by `status` |
| `language` | `en` | language the model writes artifacts in; `en`, `es` and `pt` also drive the criterion lint, the section names the parser accepts and the acceptance dossier. Another code works with the English tables, and `audit` says so |
| `approve_plan` | `true` | legacy deliveries only: `atipspec build` refuses until the plan's own approval is recorded (`accept <slug> plan`). A guided delivery approves its plan with the proposal, whatever this says |
| `review_rounds` | `3` | how many reviews a delivery gets per approved agreement, the first included, whatever the reviews said; the outputs say `review N of M`. `atipspec review` and `atipspec run` count them and stop once they are used up; less one, it is also the default and the most `--max-rounds` allows. A guided proposal's approval covers it; in a legacy delivery no approval does. See [review rounds](../flow/review.md#review-rounds) |
| `context_budget` | `800` | lines; `atipspec context` warns above it |
| `strict_scope` | `true` | a plan must declare its `scope`, and globs that together match every path (`**`, `**/*`, `*` with `*/**`) declare none; a changed file outside it is an error. With `false`, a file outside a declared scope is a warning and an empty scope is allowed |
| `criteria_syntax` | `ears` | `ears` reports criterion statements that do not start with a trigger or carry a shall; `free` turns only that check off |
| `strict_criteria` | `true` | the strict specification checks are errors and block the proposal: the EARS form, vague terms in requirements, criteria and scenario steps, and the number in a quality attribute's criterion. With `false` they are warnings. The advice on concrete values and measurement methods is a warning either way; see [writing criteria](spec-quality.md) |
| `max_requirements` | `5` | `check` warns when a spec has more requirements: a delivery should fit in a working day |
| `max_tasks` | `8` | `check` warns when a plan has more tasks |
| `max_age_hours` | `8` | `check`, `status` and the dossier warn when a delivery's lead time is longer than this: wall-clock hours from its creation (`created`, written by `new`) to the acceptance of its result, or to now until then. A warning, never a block |
| `require_proof` | `false` | `true`: every criterion under `Tests:` needs a `Proof:` entry naming its test, and the verification that runs it a `Report:`; a missing one is an error that blocks the proposal. A trust policy can set it too, and then the project cannot turn it off. See [build](../flow/build.md) |
| `require_isolated_review` | `false` | `true`: a review with `session: shared`, or none, is an error instead of a warning, as it already is for `risk: high`. A trust policy can set it too |
| `trust` | `optional` | `required`: the project needs an external trust policy. Without one, `check` and `merge-check` are red, `accept` refuses every local form but `contract`, `deliver` refuses and `run` does not start; `proposal` shows no local code. `merge-check` applies it when the head, the target branch or the merge base sets it, so a branch cannot drop it for its own merge, even one forked before it |
| `exempt_paths` | `[]` | globs of files outside `.atipspec/` that a branch may change with no delivery covering them, such as `["docs/**", "*.md"]`: `**` crosses directories, `*` and `?` do not. `merge-check` reads them from the target branch's `config.yaml` (the `--base` revision), never from the branch it judges, so a branch cannot exempt its own changes, and warns on a branch that changes them. The user decides it. No approval hashes it. See [merge-check](cli.md#atipspec-merge-check) |
| `system` | unset | path to a checkout of the system repository. `atipspec new` pins its `contract.md`, and its `glossary.md` when it has one, at the checkout's current commit in the guided delivery's `contracts.json`, and that delivery's context reads them from there; legacy deliveries read the checkout as it is. See [several repositories](../teams.md#several-repositories) |

Only `name` and `language` are managed by `atipspec init`; edit the rest by
hand. `init --language en` on an existing project keeps the other keys.

Every command but `init` validates the policies first and stops with
`Invalid .atipspec/config.yaml: <key> must be ...`: booleans are `true` or
`false`, numbers are positive whole numbers (`max_age_hours` may have a
fraction, such as `7.5`), `criteria_syntax` is `ears` or `free`, `trust` is
`optional` or `required`, `exempt_paths` is a list of globs. A key left out
takes its default.

Defaults apply only where a key is missing. Projects created before 0.3.0 have
`strict_scope: false`, `strict_criteria: false` and `max_age_hours: 48`
written out and keep them; `audit` notes the first two, and `install --update`
lists every policy that differs from this version's defaults without editing
the file. `config.yaml`, all but `exempt_paths`, is part of what
a guided proposal's approval hashes: change it when no guided delivery is
between its proposal and its result, or present those proposals again.

## `.atipspec/teams.json`

Optional, written by hand: the refs the team board reads, the owners of each
capability, the other repositories contracts are pinned from, the integration
branch and the address of the ticket tracker. See [team
configuration](../teams.md#team-configuration). A guided proposal's approval
hashes only the owners of its capability and `integration`, so adding refs,
repositories or `ticket_url` voids no approval.

## `.atipspec/adapter.json`

Optional, written by hand: the process adapter `atipspec run` calls, as
`{"schema": 1, "name": ..., "command": [...], "isolated_review": false}`. The
command is an argv array, not shell code. A guided proposal's approval hashes
the file. See [the execution adapter](execution-adapter.md).

## `.atipspec/.gitignore`

Created by `init`; ignores `tmp/`, where review packets are written and where
a plan's JUnit `Report:` belongs, such as `.atipspec/tmp/junit.xml`.
Everything else under `.atipspec/` is meant to be committed: the contract,
the living specs, the deliveries with their evidence and reviews, the
archive.

## `.claude/settings.json`

Written or merged by `init` and `install` when Claude Code is a client: `ask`
rules for `Bash(*atipspec accept *)` and for `Edit` on `.github/workflows/**`,
`.gitlab-ci.yml` and `.claude/settings*.json`, and `deny` rules for `Edit` on
the approval, evidence, review round (`review-rounds.json`) and archive
records. Every other key and entry is kept.
See [approval permission rules](../clients.md#approval-permission-rules).

## Environment

| Variable | Effect |
| --- | --- |
| `NO_COLOR` | disables colors in the terminal output |
| `TERM=dumb` | same |
| `ATIPSPEC_TRUST_POLICY` | path of the external trust policy; every command uses it, as `--policy` does (see [organization trust](#organization-trust)) |
| `ATIPSPEC_POLICY_SHA256` | the SHA-256 the policy must have, as `--policy-sha256` |
| `ATIPSPEC_PR_NUMBER` | the pull request a policy in provider mode reads, as `--number` |
| `GITHUB_TOKEN`, `GITLAB_TOKEN` | read-only tokens of the provider adapters, on the protected worker only; `verify` removes them, the SSH agent and the CI job and OIDC tokens from the commands it runs |
| `CLAUDECODE`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`, `COPILOT_CLI`, `CURSOR_AGENT`, `GEMINI_CLI`, `AI_AGENT` | set by coding agents; `accept` never records channel `terminal` while one is set, nor `client-permission` while one names an agent other than Claude Code (values `0`, `false`, `no` and `off` are ignored) |
| `CLAUDE_CODE_ENTRYPOINT` | set by Claude Code; `sdk-ts` and `sdk-py` (the Agent SDK) and `sdk-cli` (`claude -p`) make `accept` record channel `assistant` |

## Organization trust

Local project settings guide the assistant; they cannot relax trusted acceptance.
`approve_plan: false` skips a legacy delivery's plan approval, not the trusted
engineering approval requirement. The external TOML policy controls roles, public keys,
corporate rules and provider identities. It must live outside the candidate.
Its `require_proof` and `require_isolated_review` add to the project's: the
gate applies a requirement when either sets it to `true`. Its optional
`integration`, a full ref name such as `refs/remotes/origin/main`, names the
branch whose history counts as integrated, so that what a delivery takes in
from it is not the delivery's change in `check`, the review packet and the
dossier; under a policy, teams.json's `integration` names no branch, though
approvals still hash it. See [when main
moves](../teams.md#when-main-moves). In provider mode (GitHub only), its
`[attestation]` block names the trusted evidence workflow, `signer_workflow`,
in another repository of the same organization, and pins its commit,
`signer_digest`; a policy without them does not load. See [two trust
modes](../enterprise.md#two-trust-modes).

`ATIPSPEC_TRUST_POLICY` selects that policy; `ATIPSPEC_POLICY_SHA256` pins its
contents. Use protected organization configuration, not project-provided values.
GitHub/GitLab adapters use read-only `GITHUB_TOKEN` / `GITLAB_TOKEN` in the trusted
collector. The verification runner removes those credentials from command
environments. See [enterprise acceptance](../enterprise.md).
