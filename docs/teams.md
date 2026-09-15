# Teams and scale

AtipSpec is built for projects that run for months with several people and
their agents. Two ideas carry the weight: the unit of assignment is the
delivery, and the cost of a request is bounded by the delivery, not by the
project.

## Deliveries, not tasks

| Jira | AtipSpec | Unit of |
| --- | --- | --- |
| Epic | initiative | months of work, several people |
| Story | delivery | assignment to one person, one branch |
| Sub-task | task | one agent run with a clean context |

Tasks inside a delivery share a spec and a branch and run in sequence. A
delivery is sized to close within a working day: `check` warns above
`max_requirements` and `max_tasks`, and `status` shows how long each
delivery has been open and warns above `max_age_hours`. Bigger work becomes
several deliveries under an initiative. Work that two people should do in
parallel becomes two deliveries, split by ownership, with the interface
between them fixed in the initiative:

```bash
atipspec initiative orders --title "Orders"
atipspec new orders-api    --title "Orders API"    --capability orders    --owner ana  --initiative orders --worktree
atipspec new orders-screen --title "Orders screen" --capability orders-ui --owner luis --initiative orders --worktree --impact orders
```

Creating a delivery with `--initiative` lists it in the roadmap. The roadmap
has an *Interfaces* section for what both sides agree on (an API shape, an
event, a schema) and the file that is its source of truth.

```bash
atipspec status
```

```text
- orders-screen [in_progress]  tasks 1/3 @luis, open 1d 3h: Orders screen
    next: T2 is not committed: build it, run `atipspec verify orders-screen --task T2` and commit with [orders-screen:T2]
initiatives:
- orders 1/2: orders-api delivered; orders-screen in_progress
```

Tickets: `--ticket SHOP-12` records the external id in the spec; the commit
markers `[orders-api:T1]` are yours to combine with any convention.

## One delivery, one branch, one worktree

```bash
atipspec new orders-api --title "Orders API" --worktree
```

creates the branch `delivery/orders-api` in a sibling folder
`../<repo>-orders-api`. Each person, and each agent, works in its own tree;
nothing is shared until the pull request. `--branch` does the same in the
current folder.

Rebasing onto main changes the tree, which makes the evidence and the review
stale. The gate makes you verify and review again after integrating, so
there is no "it worked on my branch".

## Overlaps

`status` and `audit` warn when two open deliveries declare the same living
spec in their `impact`:

```text
  warning: orders-api and orders-screen both touch orders
```

That is the conflict worth catching before code exists. Git conflicts stay
git's business.

## Several repositories

Each repository has its own `.atipspec/`, because git is the state machine
and evidence is per tree. For the shared parts, a small **system**
repository holds the system contract, the shared glossary, the API contracts
and schemas, and the initiatives that span repositories. Point each project
at a checkout of it:

```yaml
# .atipspec/config.yaml
system: ../shop-system
```

`atipspec context` then includes the system's `contract.md` and
`glossary.md` in every delivery's material.

## Keeping the context small

Every phase command prints the output of `atipspec context <slug>`, which
loads the contract, overview, glossary, the living specs in the impact list,
the accepted decisions that affect them, and the delivery's own files. It
prints the size:

```text
Context for orders-api: 184 lines (budget 800)
     43  contract (.atipspec/contract.md)
     22  overview (.atipspec/overview.md)
     10  glossary (.atipspec/glossary.md)
     37  decision DEC-001
     48  spec (.atipspec/deliveries/orders-api/spec.md)
     24  plan (.atipspec/deliveries/orders-api/plan.md)
```

Two things keep it bounded over time: the [curate](flow/curate.md) phase
with its caps, and the impact list, which is why a spec declares what it
touches instead of the model guessing.

## Policies per project

Ceremony is a dial in `config.yaml`, not a property of the tool:

```yaml
approve_plan: true      # build refuses until a person runs `atipspec accept <slug> plan`
review_rounds: 2        # rounds before the model stops and reports
context_budget: 800     # lines; context warns above it
max_requirements: 5     # check warns above it: split the delivery
max_tasks: 8            # same, for the plan
max_age_hours: 48       # status warns when a delivery has been open longer
```

A small project sets `approve_plan: false` and ships in one go. A regulated
one keeps both stop points, plan approval, and a low budget.
