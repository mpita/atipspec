# CLI reference

All commands run from anywhere inside the project; AtipSpec finds the root by
looking for `.atipspec/config.yaml`. Errors print `AtipSpec: error: ...` and
exit 1. Nothing is stored between commands: `status` and `check` compute
everything from files and git.

## Project

### `atipspec init`

```text
atipspec init [--name NAME] [--language LANG] [--client ID]...
```

Creates `.atipspec/` with `config.yaml`, `contract.md`, `overview.md`,
`glossary.md`, the folders `specs/`, `deliveries/`, `archive/`,
`decisions/`, `initiatives/`, the framework copy and the selected clients'
skills. Asks for what the flags do not provide when run in a terminal; uses
the folder name, `en` and no client otherwise.

On an initialized project: shows the state and, in a terminal, a menu to add
or remove clients, update the framework, or change name and language. With
flags it applies them directly.

### `atipspec install`

```text
atipspec install [--client ID]... [--update]
```

Installs the framework and the given clients' skills without overwriting
anything that differs. `--update` replaces framework and skill files that
differ from the installed CLI version. Without `--client` it asks in a
terminal, or targets the already installed clients with `--update`.

### `atipspec status`

```text
atipspec status [SLUG]
```

Without a slug: project name, branch, whether the contract exists, living
specs, every open delivery with its derived status, owner and next action,
overlap warnings, initiatives with progress, delivered slugs. With a slug:
the same report as `check`.

### `atipspec audit`

Checks the whole repository against the contract's rules (dependencies
always), the validity of every living spec and decision, document sizes
against their caps, overlaps between open deliveries, and initiative
roadmaps. Exit 1 on errors.

### `atipspec curate`

Regenerates the index block of `overview.md`, reports document sizes against
their caps and prints the curate workflow, which rewrites the prose.

## Phases

One command per phase. Each checks what the phase requires and exits 1 with
one line naming the missing step; otherwise it prints `Phase <name>: <title>`,
the derived status, the phase's workflow from `.atipspec/framework/workflows/`,
the shared rules and, for `explore`, `spec`, `plan` and `build`, the output of
`atipspec context`.
See [the flow](../flow/index.md#what-each-phase-requires) for the
prerequisites.

```text
atipspec explore SLUG [--no-context]
atipspec spec SLUG [--no-context]
atipspec fix SLUG [--no-context]        only for a delivery created with --kind fix
atipspec plan SLUG [--no-context]
atipspec build SLUG [--no-context]      also names the next task without a commit
atipspec review SLUG [--out FILE]       writes the reviewer packet when the prerequisites hold
atipspec deliver SLUG --policy PATH     see below
atipspec contract                       prints the workflow and the current contract.md
atipspec curate                         regenerates the overview index, reports sizes, prints the workflow
atipspec ship SLUG                      prints the next phase the delivery can enter
```

`--no-context` prints the workflow without the context material, for
re-entering a phase in the same session.

## Acceptance

### `atipspec accept`

```text
atipspec accept SLUG spec [--by WHO]
atipspec accept SLUG plan [--by WHO]
atipspec accept contract
```

Run by a person, never by the model. `spec` refuses while a requirement has
no criterion or a question is open; otherwise it sets `status: ready` and
writes `approvals/local-spec.json` with a hash of `spec.md` and the contract.
`plan` requires an accepted spec and a plan without errors, and records the
hash of spec, plan and contract. `contract` sets `status: accepted` in
`contract.md`. `--by` defaults to git's `user.email`.

`check` compares the recorded hash with the files: after any edit the
delivery is a draft again (or the plan is unaccepted) until the person runs
the command again. With `--policy`, signed approvals rule and these records
are ignored.

## Deliveries

### `atipspec new`

```text
atipspec new SLUG --title TITLE [--capability NAME] [--impact NAME]...
                  [--owner WHO] [--ticket ID] [--initiative SLUG]
                  [--branch | --worktree] [--kind feature|fix]
```

Creates `deliveries/SLUG/` with `spec.md` (status draft, base = current
commit), `plan.md` and `deferred.md`. `--kind fix` creates a defect repair:
a spec with one regression criterion to fill, a one-task plan whose `Verify:`
lists the contract's required commands, no plan acceptance, and `atipspec fix`
as its phase (see [fix](../flow/fix.md)). `--branch` creates and switches to
`delivery/SLUG`; `--worktree` creates that branch in `../<repo>-SLUG` and
writes the delivery there. `--initiative` registers the delivery in the
roadmap.

### `atipspec check`

```text
atipspec check SLUG
```

The gate. Exit 0 green, 1 errors, 2 incomplete. See
[how it works](../getting-started/how-it-works.md#the-gate) for the levels.

### `atipspec context`

```text
atipspec context SLUG [--out FILE] [--summary]
```

Prints the material for the delivery with a size summary against
`context_budget`. `--out` writes it to a file; `--summary` prints only the
sizes.

### `atipspec verify`

```text
atipspec verify SLUG [--task Tn]... [--timeout SECONDS]
```

Runs each task's Verify commands from the project root through the shell,
prints their output tail, and writes `evidence/Tn-<timestamp>.json`. Exit 1
if any command fails. Requires git.

### `atipspec review`

```text
atipspec review SLUG [--out FILE]
```

Refuses, without writing anything, while a task has no commit, evidence is
missing or stale, or the contract is violated. Otherwise writes the reviewer
packet to `.atipspec/tmp/SLUG-review-packet.md`: rubric, contract, the living
specs in the impact list, the accepted decisions affecting them, spec, plan,
deferred, evidence summary, files outside the plan's `scope`, the diff against
the base (capped at 200 KB, with `--stat` when truncated) and untracked files;
then prints the review workflow.

### `atipspec deliver`

```text
atipspec deliver SLUG --policy /secure/company.toml
```

Requires a green trusted check, authenticated evidence and human approvals. Merges the requirements into the capability's living
spec, sets `status: delivered`, moves the folder to `archive/`.

## Decisions and initiatives

### `atipspec decision`

```text
atipspec decision SLUG --title TITLE [--affects NAME]...
```

Creates `decisions/DEC-nnn-SLUG.md` with status `proposed`. `--affects`
takes capability names, `contract`, `contract:<section>` or `*`.

### `atipspec initiative`

```text
atipspec initiative SLUG --title TITLE
```

Creates `initiatives/SLUG/roadmap.md`.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | done; for `check`, green |
| 1 | error, or for `check` and `audit`, red |
| 2 | `check`: incomplete, work remains |
| 130 | cancelled from the keyboard |

## Trusted acceptance

| Command | Purpose |
| --- | --- |
| `enterprise-init [--out directory]` | Write policy, CI and adoption examples without activating them |
| `approval-subject <slug> <phase>` | Print the content/head-bound approval marker |
| `approve <slug> <phase> --identity id --key path --policy path` | Sign from an enrolled human identity |
| `sync-approvals <slug> <phase> --number n --identity id --key path --policy path` | Collect existing GitHub/GitLab human approval, read-only |
| `attest <slug> --identity id --key path --run-url url --policy path` | Protected collector signs CI evidence |
| `check <slug> --policy path [--policy-sha256 hash] [--number n] [--json]` | Trusted gate; default without policy is only a local check; `--number` names the PR or MR in provider mode |
| `report <slug> --format json\|markdown\|html [--out path] [--policy path]` | Dossier and traceability matrix |
| `ids <capability>` | Show next requirement/criterion IDs |
| `pilot init <name>` | Create an empty real-world evaluation protocol |
| `pilot record <name> ...` | Record one sourced complete observation; see `--help` |
| `pilot report <name>` | Compare recorded cohorts, with sample sizes and limitations |

Phases: `spec`, `plan`, `acceptance`, `decision:DEC-nnn`, `exception:Fn`.
Exceptions require `--expires` with a future timezone-aware ISO timestamp.
`verify` accepts `--policy` and requires spec/plan approval before executing.
`deliver` requires a policy and full trusted acceptance.
`ATIPSPEC_TRUST_POLICY`, `ATIPSPEC_POLICY_SHA256` and `ATIPSPEC_PR_NUMBER` are
protected environment alternatives to the command flags. Never derive them
from candidate documents.

See [enterprise adoption](../enterprise.md) for the trust boundary, CI isolation,
key custody and read-only provider integration.
