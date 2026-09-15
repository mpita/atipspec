---
name: atipspec
description: Spec-driven delivery in a project with .atipspec/. Use for status, questions about the flow, or when the user names AtipSpec without a phase. Each phase has its own skill (atipspec-spec, atipspec-plan, ...).
---

# AtipSpec

The developer leads, you propose, the CLI guarantees. `atipspec` owns what must
not depend on judgment: which phase may start, contract rules, evidence,
freshness, coverage and the gate. You own the interview, the plan, the code
and the fixes. A reviewer in a fresh context owns the verdicts.

## Layout

```text
.atipspec/
  config.yaml             name, language, policies: approve_plan, review_rounds, context_budget
  contract.md             the architecture contract; its ```rules block is machine-checked
  overview.md, glossary.md   curated, small
  specs/<capability>.md   living specs: the current truth about behavior
  decisions/DEC-nnn-*.md  choices with lasting consequences; a contract change needs one
  initiatives/<slug>/     roadmap.md grouping deliveries
  deliveries/<slug>/      one delivery: brief, spec, plan, evidence/, review, deferred
  archive/<slug>/         delivered
  framework/              workflows, templates and rules the CLI prints when a phase starts
```

## Phases

One verb per phase; the same verb is the CLI command, the workflow file and the
skill. A phase command checks what the phase requires; when something is
missing it refuses with one line that says what to do first. Never work around
a refusal: tell the user.

| Phase | Skill | Command | Produces | Who decides |
| --- | --- | --- | --- | --- |
| explore | atipspec-explore | `atipspec explore <slug>` | brief.md | the user |
| spec | atipspec-spec | `atipspec spec <slug>` | spec.md | the user runs `atipspec accept <slug> spec`. STOP POINT 1 |
| fix | atipspec-fix | `atipspec fix <slug>` | spec.md with one regression criterion, a one-task plan | the user accepts the spec; no plan acceptance |
| plan | atipspec-plan | `atipspec plan <slug>` | plan.md | the user runs `atipspec accept <slug> plan` when `approve_plan` is true |
| build | atipspec-build | `atipspec build <slug>` | code, evidence, commits | the developer with you |
| review | atipspec-review | `atipspec review <slug>` | review.md, by the reviewer | `atipspec check` |
| deliver | atipspec-deliver | `atipspec deliver <slug> --policy ...` | living spec updated, archived | the user merges. STOP POINT 2 |
| contract | atipspec-contract | `atipspec contract` | contract.md, decisions | the user runs `atipspec accept contract` |
| curate | atipspec-curate | `atipspec curate` | overview.md, glossary.md | you, within the caps |
| ship | atipspec-ship | `atipspec ship <slug>` | the next phase to enter | the CLI |

## Other commands

```text
atipspec status [slug]                    derived state and next action; nothing is stored
atipspec new <slug> --title "..."         create a delivery; --capability --impact --owner --ticket
                                          --initiative --branch --worktree; --kind fix for a defect
atipspec check <slug>                     the gate: exit 0 green, 1 errors, 2 incomplete
atipspec accept <slug> spec|plan          run by the person, never by you; also `accept contract`
atipspec verify <slug> [--task Tn]        run Verify commands, write evidence
atipspec context <slug>                   exactly what to read for this delivery, within budget
atipspec decision <slug> --title "..."    create a decision record (--affects contract, <capability>)
atipspec initiative <slug> --title "..."  create a roadmap
atipspec audit                            whole repository against the contract and the documents
```

## Rules

The phase command prints the rules with the workflow. In short: never write
evidence/ or review.md, never mark work done, keep the template headings and
IDs (`- AC-001 [manual]: ...` marks a criterion a person observes), ask only
what changes the spec or the contract, report real output.

## Trusted acceptance

Local `check` produces `checked`; only a gate with an external organization
policy, signed CI evidence and content-bound human approvals produces
`verified`, and `deliver` requires it. Never sign on behalf of a human or
fabricate approval metadata. `report <slug>` exports the acceptance dossier;
`enterprise-init` writes reviewable CI and policy examples.
