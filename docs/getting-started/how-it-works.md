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
| What do we build? | You, approving the presented agreement in the conversation |
| Under which rules? | The contract you accepted with `atipspec accept contract`, enforced by `check` and `audit` |
| Is a task done? | git: a commit carrying `[slug:Tn]` |
| Does it pass its checks? | `atipspec verify`, which records exit codes and the tree hash |
| Does it meet the spec? | A reviewer in a fresh context, one verdict per criterion |
| Is it verified? | `check --policy` with trusted CI evidence and product/engineering/QA approvals |
| Does it ship? | You, by merging |

The assistant presents the agreement and offers **Approve and continue**, **Request
changes** or **Cancel**, using the client's selector or a plain reply. After your
explicit approval, it runs `atipspec accept` and continues. You do not need to run
commands or edit statuses. The verifier records evidence and the reviewer records
verdicts; neither can substitute for your decision. Changed agreements need renewed
approval. External trust policies retain their authenticated procedure.

## Acceptance you can check

`atipspec accept <slug> spec` is how you approve a spec: it sets `status:
ready` and records a hash of the spec and the contract in
`approvals/local-spec.json`. `check` compares that hash with the files on
disk on every run; a single edited byte after your acceptance turns the
delivery back into `draft` with a `todo` that names you. The same holds for
`atipspec accept <slug> plan` when `approve_plan` is on, and `atipspec accept
contract` sets the contract's `status: accepted`.

This is drift detection, not authentication: the record proves what was
accepted, not who ran the command. Signed approvals under an external policy
are the authenticated form, and when a policy is set the gate ignores the
local records. See [enterprise acceptance](../enterprise.md).

## Phases the CLI opens

A phase starts with its command: `atipspec spec <slug>`, `atipspec plan
<slug>`, and so on. The command checks what the phase requires and refuses
with one line when something is missing: the contract not accepted, the spec
not ready, a task without a commit. Otherwise it prints the workflow, the
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
Without a policy, green is only `checked`. `deliver` requires a green trusted
gate and the [external policy](../enterprise.md).

## Evidence bound to the tree

`atipspec verify` runs the commands a task declares and writes a JSON file
with the commands, exit codes, output tails, duration and the **fingerprint
of the working tree**: a content hash computed through a temporary git index,
identical before and after committing the same content. The review records
the same fingerprint. When the tree changes, both go stale and the gate asks
for them again. Rebasing onto main changes the tree too, which is the point:
there is no "it worked on my branch".

## Derived status

Nothing is stored. `status` and `check` compute where a delivery is:

`draft` → `ready` → `planned` → `in_progress` → `implemented` → `checked` (local) / `verified` (trusted) → `delivered`

No status is written by hand: `atipspec accept` moves a spec to `ready` and
a contract to `accepted`, and the gate treats a hand-written `ready` without a
matching acceptance record as a draft.

## Context that does not grow with the project

`atipspec context <slug>` assembles exactly what a phase needs: the contract,
the overview, the glossary, the living specs the delivery's `impact` list
names, the accepted decisions that affect them, and the delivery's own
files. Never the archive. It prints the size against `context_budget`, and
`audit` warns when a document outgrows its cap so the **curate** phase can
shrink it.

Next: [the flow](../flow/index.md).
