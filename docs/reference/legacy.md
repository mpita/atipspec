# Legacy deliveries

A legacy delivery keeps its requirements inside its own `spec.md`, with no
`schema: 2`. `atipspec new` has created guided deliveries since 0.2.0, and
guided fixes since 0.3.0, so the legacy ones in a project are:

- deliveries created with AtipSpec 0.1.x;
- fixes created with `new --kind fix` before 0.3.0.

AtipSpec reads them as they are, with the same gate for evidence, review and
the result, until they are archived. Nothing converts them on its own. This
page describes what differs; the [guided delivery](../flow/guided.md) is the
flow for everything new.

## `spec.md` with embedded requirements

```markdown
---
title: "Password reset"
status: draft          # draft or ready; `atipspec accept` sets ready when it records the human's approval
kind: feature          # or fix: a fix created before 0.3.0, one regression criterion, no plan acceptance
capability: auth       # living spec that receives the requirements on deliver
impact: [notifications]  # other living specs or contract sections touched
owner: ana
ticket: SHOP-12
initiative: null
base: 9f2c1e...        # commit the delivery started from; diff and rules use it
created: 2026-09-12T15:41:45Z   # the lead time counts from here
---

# Password reset

## Intent

Let a user who forgot the password recover access without support.

## Requirements

### REQ-001: The user can request a reset link

From the sign-in screen the user enters an email and receives a link.

Why: support tickets for forgotten passwords are 40% of the queue.

Acceptance criteria:
- AC-001: When a registered email requests a reset, the system sends a link to that email within 60 seconds.
- AC-002 [manual]: When the reset email is opened on a 375 px wide screen, a person sees the "Reset password" button without scrolling sideways.

### REQ-002 [remove]: Security questions
- AC-003: If a user opens "/account/questions", then the system responds with status 404.

## Quality attributes

### REQ-003: Reset requests under load

Acceptance criteria:
- AC-004: When 100 users request a reset within one minute, the p95 response time measured at the API gateway is below 300 ms.

## Assumptions
- The link is single-use.

## Out of scope
- Password policy changes.

## Open questions
- None
```

Parsed: `### REQ-nnn[ [remove]]: title` headings (levels 2 to 4), `- AC-nnn[
[test|manual]]: text` lines under a requirement, which may continue on
indented lines, scenario headings as in a guided living spec, and the list
items under `## Assumptions` and `## Open questions` (`- None` counts as
empty). `deliver` merges the requirements into
`specs/<capability>.md` by ID and removes those marked `[remove]`. See
[writing criteria](spec-quality.md) for the checks; they are the same.

## Approvals

| | Legacy delivery | Guided delivery |
| --- | --- | --- |
| To start `spec` or `fix` | the contract's acceptance, recorded for its current content | nothing; `check` warns while the contract is not accepted |
| Before `plan` | `accept <slug> spec --code <code>` | the scenarios complete, no open question |
| Before `build` | with `approve_plan: true` (the default), `accept <slug> plan --code <code>`; a fix created before 0.3.0 has no plan acceptance | `accept <slug> proposal --code <code>` |
| The result | `accept <slug> result --code <code>` | the same |

`atipspec proposal <slug>` on a legacy delivery presents the approval still
pending, with its code and the `accept` command that records it, or says none
is: the spec until it is accepted, then the plan when `approve_plan` asks for
it. A feature whose spec and plan are both ready is presented as one proposal,
and `accept <slug> proposal` with that code records the spec and the plan with
it; a fix presents only its spec. A code records only the phase the view
showed it with, so run the command the view prints. The spec approval hashes
`spec.md` and `contract.md`; the plan approval adds `plan.md` whole, so any
edit to the plan, a new task included, asks for it again. `review_rounds`
restarts with each new spec approval; no approval covers `config.yaml`.
`accept <slug> spec` and `accept <slug> plan` are refused on guided
deliveries.

## Task completion

A task is complete when `atipspec task-done <slug> Tn --note "..."` records
it, or when a commit in the branch since the base carries the marker
`[<slug>:Tn]` (several ids may share one, `[password-reset:T1,T2]`). Guided
deliveries ignore commit markers. A legacy plan has no `## Final
verification` unless someone adds one: `verify` runs each task's Verify
commands, and every `require-command` of the contract must appear in one of
them.

## IDs

Legacy requirements and criteria are numbered per capability, `REQ-001`,
`AC-001`, above the highest number in the living spec, the open deliveries
and the archive. `atipspec ids <capability> --legacy` prints the next pair.
Two people numbering at the same time can collide; the guided flow's `atipspec
ids <capability>` draws a prefix no visible ID uses. Numbered IDs stay valid in
every flow and are never renumbered.

## Several repositories

With `system:` in `config.yaml`, a legacy delivery reads the system
repository's contract and glossary from the checkout as it is; a guided one
reads them from the commit `new` pinned (see [several
repositories](../teams.md#several-repositories)).

## Converting a legacy feature

`atipspec migrate <slug>` shows, as a diff, how a legacy feature becomes a
guided delivery, and writes nothing: its requirements move to
`specs/<capability>.md`, `spec.md` lists their IDs under `requirements` and
gets `schema: 2`, `status: draft`, `risk: normal` and a new `baseline.json`.
`atipspec migrate <slug> --apply` writes it after backing up the originals and
the approval records in `.atipspec/migrations/<digest>/`. It approves nothing:
the delivery returns to draft and its proposal is presented for approval. The
existing plan is kept; move shared checks into a `## Final verification` when
you review it. A legacy fix keeps its flow until it is delivered, and
`migrate` refuses it.
