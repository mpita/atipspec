# How it works

## Three truths with different lifetimes

| Truth | Where | Lives | Changes through |
| --- | --- | --- | --- |
| The **contract** | `.atipspec/contract.md` | the whole project | an accepted decision |
| The **living specs** | `.atipspec/specs/<capability>.md` | the product | `atipspec deliver` |
| A **delivery** | `.atipspec/deliveries/<slug>/` | days or weeks | the phases |

The contract says how the system is built: stack, structure, dependency
policy, conventions, quality gates, and a block of rules the CLI evaluates.
The living specs say what the product does, one file per capability. A
delivery is the unit of change: its own spec, plan, evidence, review and
deferred findings, created, verified and archived as a whole.

Around them sit the **decisions** ledger, **initiatives** that group
deliveries over months, and two curated documents, `overview.md` and
`glossary.md`, that keep the project explainable in a page.

## Who decides what

| Question | Answered by |
| --- | --- |
| What do we build? | You, approving the proposal (scenarios, approach and tests) in the conversation |
| Under which rules? | The contract you approved, recorded with `atipspec accept contract --code <code>` and enforced by `check` and `audit` |
| Is a task done? | The assistant declares it with `atipspec task-done`, bound to the approved agreement; a declaration of progress, not proof |
| Does it pass its checks? | `atipspec verify`, which runs the final verification and records exit codes and the tree hash |
| Does it meet the spec? | A reviewer in an isolated session, declared in `review.md`, one verdict per criterion with a pointer the gate resolves |
| Is the result accepted? | You, accepting the reviewed result that `atipspec report` shows; or, under a trust policy, `check --policy` with trusted CI evidence and product/engineering/QA approvals (`verified`) |
| When does it merge? | Your repository's policy; `atipspec merge-check` confirms the branch first |

The assistant presents the agreement with its approval code and offers **Approve
and continue**, **Request changes** or **Cancel**, using the client's selector or a
plain reply. After your explicit approval, it runs `atipspec accept ... --code
<code>` and continues. Claude Code, configured by `init` and opened at the
project root, asks you before that command runs; that prompt confirms the same
approval. You do not need to run
commands or edit statuses. The verifier records evidence and the reviewer records
verdicts; neither can substitute for your decision. Changed agreements need renewed
approval. External trust policies retain their authenticated procedure.

## Acceptance you can check

There are three human decisions, each presented by a view that prints an
approval code (`XXXX-XXXX`, the first 40 bits of the content's sha256 in
Crockford base32):

| Decision | Presented with | Recorded with |
| --- | --- | --- |
| The proposal: scenarios, approach and tests | `atipspec proposal <slug>` | `atipspec accept <slug> proposal --code <code>` |
| The reviewed result | `atipspec report <slug>` | `atipspec accept <slug> result --code <code>` |
| The contract and its decisions, once per project | `atipspec proposal contract` | `atipspec accept contract --code <code>` |

`accept` refuses when the code does not name the current content, so the record
binds the version you saw. It writes a hash of that content, per-file digests,
the code and the channel to `approvals/local-<phase>.json` (the contract's to
`.atipspec/approvals/contract.json`). `check` compares the hash with the files
on disk on every run; a single edited byte after your acceptance turns the
delivery back into `draft` with a `todo` that names the file that changed.
Guided deliveries, fixes included, need the proposal record; a spec and plan
pair does not replace it. Legacy deliveries approve their spec, and their plan
when `approve_plan` is on, with `accept <slug> spec|plan --code <code>`; a fix
created before 0.3.0 approves only its spec.

The channel says how the command reached you:

| Channel | Meaning |
| --- | --- |
| `terminal` | The code was typed at the CLI prompt in a terminal without agent markers |
| `client-permission` | Claude Code ran `atipspec accept` itself, and this project's rules, intact, make it ask you first in a session opened at the project root |
| `assistant` | Nothing asked you: a client without permission rules, altered rules, another agent's marker next to Claude Code's, Claude Code run through the Agent SDK or `claude -p`, or a command line the rule does not match, such as `python -m atipspec.cli` |

The CLI sees only its own process, so each channel is what that process
declares. It cannot see whether the session loaded the rules: a session opened
in another folder that enters the project with `cd` is not asked and records
`client-permission`. A script, or an agent that sets none of the markers
listed under [environment](../reference/configuration.md#environment), that
Claude Code runs and that calls `atipspec accept` inside it records
`client-permission` too, although Claude Code asked you only about the script
or the agent. And an agent can remove its markers and answer the CLI prompt
from a terminal it creates, which records `terminal`.

This is drift detection, not authentication: the record proves what was
accepted and how the command ran, not who you are. Signed approvals under an
external policy are the authenticated form, and when a policy is set the gate
ignores the local records. See [enterprise acceptance](../enterprise.md).

## Phases the CLI opens

A phase starts with its command: `atipspec spec <slug>`, `atipspec plan
<slug>`, and so on. The command checks what the phase requires and refuses
with one line when something is missing: the scenarios incomplete, the
proposal not approved, a task not recorded. Otherwise it prints the workflow, the
rules and the context, so the model works from what the CLI opened and not
from its reading of the request. `atipspec ship <slug>` names the next phase
a delivery can enter. See [the flow](../flow/index.md#what-each-phase-requires).

## The gate

`atipspec check <slug>` checks local consistency. Trusted acceptance additionally needs `--policy`. It reads the files
and git, and reports three kinds of things:

- **error**: something is wrong or failed. The gate is red.
- **todo**: something has not happened yet. The gate is not green yet.
- **warning** and **info**: worth attention, do not block.

```text
password-reset  [implemented]  tasks 2/2
  error   AC-003 FAIL: the link never expires
  error   F1 [blocker] contract: shop/domain/order.py:3 contains forbidden pattern 'from shop\.infrastructure'
  todo    review.md is stale (the working tree changed since the review); run `atipspec review password-reset` and review again
  info    F2 [minor] Missing docstring
Next: Fix: AC-003 FAIL: the link never expires
```

Exit code 0 means the selected checks passed, 1 means errors, 2 means incomplete.
The gate fails closed: without git it is red, because the base commit, the
contract rules and the freshness of the evidence come from git. Without a policy, green is only
`checked`, and `deliver` also requires your recorded acceptance of the result;
with the [external policy](../enterprise.md), it requires a green trusted gate.
Before the merge, `atipspec merge-check --base <target>` checks the whole
branch: every delivery it touches is accepted, and the code is still the code
each receipt accepted.

## Evidence bound to the tree

`atipspec verify` runs the commands a task declares and writes a JSON file
with the commands, exit codes, output tails, duration and the **fingerprint
of the working tree**: a content hash computed through a temporary git index,
identical before and after committing the same content. The review records
the same fingerprint. When the tree changes, both go stale and the gate asks
for them again; renaming a task in the plan is the one change they survive.
Taking main in changes the tree too, which is the point: there is no "it
worked on my branch". A JUnit report counts only when that run wrote it:
`verify` deletes it first, and `check` never runs the tests itself.

## Derived status

The status is never stored: `status` and `check` compute where a delivery
is from its files and git on every run. What they read are records in the
repository: the approvals, `progress.json`, the evidence, `review.md` and the
receipt.

`draft` → `planned` → `in_progress` → `implemented` → `checked` → `accepted` → `delivered`

`checked` is the local gate green; `accepted` adds your recorded acceptance of
that result; under a trust policy, `verified` is the trusted gate green. A
legacy delivery also passes `ready`, its spec accepted before a plan exists.
`atipspec accept` moves a spec to `ready` and the contract and its decisions to
`accepted`. The gate treats a hand-written `ready` without a matching
acceptance record as a draft, and a contract, or a decision that affects it,
marked `accepted` by hand without a matching record as not accepted. A
decision about a capability is the one status the assistant writes: it marks
it `accepted` after you approve it in the conversation, with no code or
record, and the next `atipspec proposal` lists it so you see what the
implementation and the review will follow.

## Context that does not grow with the project

`atipspec context <slug>` assembles exactly what a phase needs: the contract,
the overview, the glossary, the living specs the delivery's `impact` list
names, the accepted decisions that affect them, and the delivery's own
files. Never the archive. It prints the size against `context_budget`, and
`audit` warns when a document outgrows its cap so the **curate** phase can
shrink it.

Next: [the flow](../flow/index.md).
