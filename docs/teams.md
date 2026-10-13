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
`max_requirements` and `max_tasks`, `status` shows each delivery's lead time,
from its creation to the acceptance of its result, and `check`, `status` and
the dossier warn above `max_age_hours` (8 by default). Bigger work becomes
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
- orders-screen [in_progress] tasks 1/3 @luis SHOP-12 (https://example.atlassian.net/browse/SHOP-12), open 1d 3h: Orders screen
    accepted: proposal accepted by luis@example.com at 2026-10-02T09:12:00Z via client-permission (Claude Code) (current)
    next: T2 is not complete: implement it and record `atipspec task-done orders-screen T2 --note <summary>`
initiatives:
- orders 1/2: orders-api delivered; orders-screen in_progress
```

`atipspec status --format json` gives the same state to scripts and
`--format markdown` as tables for a pull request or a job summary; with a
slug, the delivery's entry and its checks.

## One delivery, one branch, one worktree

```bash
atipspec new orders-api --title "Orders API" --worktree
```

creates the branch `delivery/orders-api` in a sibling folder
`../<repo>-orders-api`. Each person, and each agent, works in its own tree;
nothing is shared until the pull request. `--branch` does the same in the
current folder. A team with its own branch names passes `--branch-name
feature/SHOP-12-orders-api` with either, and `--reuse-branch` with
`--branch-name` to start the delivery on a local branch that already exists.

A delivery that needs another one first names it with `--depends-on`:

```bash
atipspec new orders-screen --title "Orders screen" --capability orders-ui --depends-on orders-api --worktree
```

Until `orders-api` is archived with an accepted receipt in this checkout,
`check orders-screen` keeps a todo `Waiting for accepted dependency
orders-api`, so its gate is not green and its result cannot be accepted.

Integrating main changes the tree, which makes the evidence and the review
stale. The gate makes you verify and review again after integrating, so
there is no "it worked on my branch". Integrate before the final verification:
after `deliver`, `merge-check` blocks any change to the branch's code,
integration included, until the delivery is reopened and accepted again. One
delivery per branch keeps that cheap; delivering another delivery on the same
branch also makes the open ones stale.

Start a delivery from an up-to-date main, and take main in with a merge only
when the branch needs it. What main brings does not void the approved
proposal, nor count as the delivery's change in `check`, the review packet and
the dossier, once AtipSpec knows which branch is main: see [when main
moves](#when-main-moves). A rebase onto main rewrites the branch: when
`new` ran after commits of the branch's own, it rewrites the commit the
delivery started from, and `check` then stops until you restore the history
from before the rebase (`git reflog` lists it) and merge instead.

## When main moves

Several deliveries often change the same capability, each on its branch. When
one is integrated into main and another branch takes main in, the second
delivery's living spec now holds the first one's requirements too. AtipSpec
attributes them to the **integration branch**:

- `integration` in `teams.json`, such as `"refs/remotes/origin/main"`;
- without it, the first of `refs/remotes/origin/HEAD`, which `git clone` sets,
  `refs/remotes/origin/main` and `refs/remotes/origin/master` that resolves,
  so a CI checkout without `origin/HEAD` finds the same branch; declare
  `integration` when main has another name, since a CI checkout has no
  `origin/HEAD`; `status` and `audit` warn when `origin/HEAD` names such a
  branch and `integration` is not set;
- under a trust policy, only the policy's `integration`: `teams.json` is part
  of the candidate and names nothing there.

What main brought is what changed between the commit where the delivery's
base meets main and the merge base of `HEAD` with main, as in the diff of a
pull request: each file the delivery has not changed since, and each
requirement as that merge base holds it. It does not matter whether main
merged, squashed or rebased the other deliveries. Then:

- The proposal's approval stays current, and so do the `task-done` records:
  it hashes the requirements the delivery lists, not the rest of the living
  spec. Text outside the requirements, before the first one or under a
  heading between them, the frontmatter, and an HTML comment or fenced code
  in a requirement the delivery does not list are in no approval: `check`
  warns when they change, compared with what main holds where main changed
  them, and only the acceptance of the result, which binds the whole tree,
  covers them.
- `check` and the proposal's diff compare the living spec with what main
  holds, so a requirement main brought is not the delivery's change. Editing
  it, removing it or putting it back as it was is: a requirement the delivery
  changes without listing it is an error, at every risk level, and
  `merge-check` blocks it too.
- The files main brought are not outside the plan's `scope`, and the review
  packet and the dossier list them apart instead of in the diff. A file the
  delivery changes too stays its own, in the index or not, and so does one it
  puts back as the base had it, such as a file main deleted: the review packet
  and the dossier show it against the merge base, as a pull request's diff
  does, and `check` warns when the delivery undoes there, in whole or in part,
  what main changed: a line main added that the delivery takes out or
  rewrites, or one main took out that the delivery puts back where it was, or
  anywhere when main left no such line in the file.
- The evidence and the review are stale, as after any change of the tree:
  verify and review again.

Nothing is attributed without a ref that resolves, nor when main holds the
delivery's own folder, as when it was committed on main itself. `merge-check`
covers what the dossier shows, so without a ref, or when the pull request
targets a branch other than the integration branch, such as a release branch,
a change of that branch that the branch puts back as the base had it is code
outside any delivery. The dossier the human accepted is what counts. When
an open delivery puts back what the integration branch changed, the
acceptance of its result names the merge base its dossier shows those files
against, so taking that branch in again afterwards voids it, even with the
tree kept, as `git merge -s ours` keeps it. An archived delivery covers the
files its dossier showed when it was delivered, as its receipt lists them
(under a trust policy, as its dossier shows them at the commit it was
delivered from), not what a dossier would show at the head, nor a file the
target branch changed after the commit that archived it: keeping the
delivered code, the branch takes that change back. The accepted
risk: a change main made outside a delivery, such as a hotfix, counts as
brought too, as it does in the diff of a pull request: it is judged where it
entered main, in its own pull request, whose `merge-check` blocks code
outside any delivery unless `exempt_paths` on main exempts it. A file that a delivery archived earlier in the same
branch changed, and main changed too, no longer matches what main holds once
the branch takes main in, so it counts as the open delivery's change, outside
its scope included: one delivery per branch avoids it. In local mode the ref
and the receipts of the deliveries archived in the branch are local files
that could be moved or written, and a receipt written by hand and committed
vouches for the requirements its spec lists, and covers the files it lists,
as one `deliver` wrote would: this detects drift. A trust policy authenticates in `merge-check`, whose ref
the protected worker fetches: it checks each delivery archived in the branch
again where it was delivered from and takes the requirements only of those
it authenticates; `check` reads the receipts as committed.

A merge with conflicts that is not committed yet counts as the delivery's
change until the merge commit: the attribution reads `HEAD`. Two deliveries
that add requirements to the same capability conflict in git where both
append; keep both blocks when resolving.

## Team configuration

`.atipspec/teams.json` is optional and written by hand:

```json
{
  "schema": 1,
  "refs": ["refs/remotes/origin/delivery/*", "refs/heads/release"],
  "owners": {"orders": ["ana"], "orders-ui": ["luis", "marta"]},
  "repositories": {"api": "../shop-api"},
  "integration": "refs/remotes/origin/main",
  "ticket_url": "https://example.atlassian.net/browse/{ticket}"
}
```

| Key | Meaning |
| --- | --- |
| `refs` | full ref names the board and `check` read; a `*` at the end takes every ref it matches in that last segment |
| `owners` | capability to its human owners: a guided delivery of an owned capability needs an `owner` in `spec.md` |
| `repositories` | name to a local checkout, for `contract-pin`; `system` defaults to `system` in `config.yaml` |
| `integration` | the integration branch, as a full ref name; see [when main moves](#when-main-moves) |
| `ticket_url` | an https address with `{ticket}` where a ticket key or issue number goes |

A guided proposal's approval hashes only the owners of its capability and
`integration`, under a trust policy too; editing the other keys voids no
approval.

## The board: `atipspec team`

```bash
atipspec team [--fetch] [--json]
```

lists every open delivery of the working checkout and of each ref in
`refs`: its status, owner, ticket, ref, capability, requirements and
dependencies. Run it before you touch a capability others may be changing.
`check` reports a requirement two deliveries declare differently. It reads
only local refs and never fetches; the first line says when the repository
last fetched. `--fetch` first fetches, without prompting for credentials,
each remote a `refs/remotes/<remote>/...` entry names: git and ssh run
without a terminal or an askpass program, so a remote that needs a password
or a passphrase the credential helper or ssh-agent does not hold fails. A
remote that fails gets a warning and the board shows what was fetched last.
It is the only command that uses the network.

## Tickets

`atipspec new --ticket` takes a key such as `SHOP-12` (Jira, Linear), an
issue number such as `#42`, or an https URL; anything else is refused. With
`ticket_url` in `teams.json`, a key or a number becomes a link in `status`,
`team`, the proposal, the dossier (`ticket_url` in its JSON, a link in
Markdown and HTML) and `merge-check`. The ticket is not part of what the
proposal's approval hashes: add or correct it in `spec.md` at any time.
AtipSpec links the ticket; it never writes to the tracker. A free-text
ticket written before 0.3.0 is shown as it is, without a link.

## Pull requests

`github-local.yml` and `gitlab-local.yml` from `atipspec enterprise-init` run
`merge-check` as the pull request's check; its job summary lists each delivery
the branch touches with its state and ticket. When the user asks the agent to
open a pull request, the agent puts the delivery's ticket and the output of
`atipspec report <slug> --format markdown` in its description. In local mode
an accepted receipt is not authenticated: the check confirms that the branch
matches what was accepted, not who accepted it.

## Overlaps

`status` and `audit` warn when two open deliveries declare the same living
spec in their `impact`:

```text
  warning: orders-api and orders-screen both touch orders
```

That is the conflict worth catching before code exists. Git conflicts stay
git's business.

## Several repositories

Each repository has its own `.atipspec/`, because approvals and evidence are
bound to the tree of their repository. For the shared parts, a small **system**
repository holds the system contract, the shared glossary, the API contracts
and schemas, and the initiatives that span repositories. Point each project
at a checkout of it:

```yaml
# .atipspec/config.yaml
system: ../shop-system
```

`atipspec new` then pins the system's `contract.md`, and its `glossary.md`
when it has one, at the checkout's current commit, in the delivery's
`contracts.json`:

```text
Pinned system contract.md at 3f2a9c41d0e7 as system-contract (contracts.json)
```

The delivery's context reads them from that commit, so the system moving on
changes neither what the agent reads nor the approved proposal. When the
checkout is not available, `new` warns and the proposal cannot be approved
until the pin exists:

```bash
atipspec contract-pin <slug> system-contract --repository system --ref HEAD --path contract.md
```

Any other contract, such as an API schema in another repository, is pinned
the same way after naming its checkout in `teams.json` `repositories`:

```bash
atipspec contract-pin orders-screen orders-api --repository api --ref main --path openapi.yaml
```

`--ref` is resolved once to a full commit id; `check` refuses a pin that names
a branch or a tag, or whose content no longer has the recorded digest.
Pinning again changes `contracts.json`, which voids the proposal's approval:
a shared contract changed, and the human approves the delivery against the
new one. Legacy deliveries keep reading the checkout as it is.

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

Ceremony is a dial in `config.yaml`, and in each delivery's
[`risk`](flow/spec.md#risk), not a property of the tool:

```yaml
approve_plan: true      # legacy deliveries: build waits for the plan's own approval
review_rounds: 3        # reviews per approved proposal, the first included, before `review` refuses and you decide
context_budget: 800     # lines; context warns above it
max_requirements: 5     # check warns above it: split the delivery
max_tasks: 8            # same, for the plan
max_age_hours: 8        # check and status warn when a delivery has been open longer
```

The two stop points, the proposal and the result, stay in every project: the
dials change what the gate asks between them. A regulated project adds
`require_proof: true`, `require_isolated_review: true`, a low budget and, for
authenticated approvals, `trust: required` with an external policy.
