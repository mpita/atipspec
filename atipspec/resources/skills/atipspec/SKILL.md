---
name: atipspec
description: Spec-driven delivery in a project with .atipspec/. Use for status, questions about the flow, or when the user names AtipSpec without a phase. Each phase has its own skill (atipspec-spec, atipspec-plan, ...).
---

# AtipSpec

The developer leads, you propose, the CLI guarantees. `atipspec` owns what must
not depend on judgment: which phase may start, contract rules, evidence,
freshness, coverage and the gate. You own the interview, the plan, the code
and the fixes. Give the review packet to a reviewer in an isolated session; the
reviewer owns the verdicts.

## Layout

```text
.atipspec/
  config.yaml             name, language, policies: approve_plan, review_rounds, require_proof,
                          require_isolated_review, context_budget, max_age_hours, exempt_paths
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
| spec | atipspec-spec | `atipspec spec <slug>` | canonical behavior and delivery references | the human approves the combined proposal in conversation |
| fix | atipspec-fix | `atipspec fix <slug>` | the corrected accepted requirement and a one-task plan | the human approves the proposal in conversation |
| plan | atipspec-plan | `atipspec plan <slug>` | plan.md | included in the guided proposal; legacy plan approval when required |
| build | atipspec-build | `atipspec build <slug>` | code, progress, evidence | the developer with you |
| review | atipspec-review | `atipspec review <slug>` | review.md, by the reviewer | `atipspec check` |
| deliver | atipspec-deliver | `atipspec deliver <slug>` | living spec updated, archived | the human accepts the reviewed result in conversation |
| contract | atipspec-contract | `atipspec contract` | contract.md, decisions | the human approves the contract and listed decisions in conversation |
| curate | atipspec-curate | `atipspec curate` | overview.md, glossary.md | you, within the caps |
| ship | atipspec-ship | `atipspec ship <slug>` | the next phase to enter | the CLI |

## Other commands

```text
atipspec status [slug]                    derived state and next action
atipspec new <slug> --title "..."         create a delivery; --capability --impact --owner --initiative
                                          --branch --worktree; --kind fix for a defect; --ticket with
                                          a key (PROJ-123), an issue number (#42) or an https URL
atipspec check <slug>                     the gate: exit 0 green, 1 errors, 2 incomplete
atipspec ids <capability>                 an ID prefix for this delivery's requirements and criteria
atipspec spec-bind <slug> --file <path>   install an authored or imported spec in specs/ and list its IDs
atipspec proposal <slug>                  present the agreement and its approval code
atipspec proposal contract                present the contract, the decisions it includes and their code
atipspec accept <slug> proposal|result --code <code>
                                          record the human's approval of the presented content
                                          (spec|plan: legacy deliveries)
atipspec accept contract --code <code>    record the contract's approval; sets it and its decisions accepted
atipspec task-done <slug> Tn --note "..." record a finished task: progress, not proof
atipspec verify <slug> [--task Tn]        run Verify commands, write evidence
atipspec report <slug>                    the reviewed result, its diff and the result's approval code
atipspec merge-check --base <ref>         before a merge: every delivery accepted, its code unchanged
atipspec context <slug>                   exactly what to read for this delivery, within budget
atipspec decision <slug> --title "..."    create a decision record (--affects contract, <capability>)
atipspec initiative <slug> --title "..."  create a roadmap
atipspec team [--fetch]                   who changes what across the team's refs; run it before
                                          touching a capability others may be changing
atipspec contract-pin <slug> <name> --repository R --ref REV --path P
                                          pin a contract of another repository the delivery depends on
atipspec migrate <slug> [--apply]         turn a legacy delivery into a guided one: show the diff
                                          first, apply after the user agrees; it approves nothing
atipspec audit                            whole repository against the contract and the documents
```

## Rules

The phase command prints the rules with the workflow. The verifier writes
evidence; the reviewer writes review.md. Record real implementation progress with
`task-done`. Keep template headings and IDs, ask consequential questions and report
actual results.

The human decides; you handle the commands. Present the view with its approval
code (`atipspec proposal <slug>`, `atipspec report <slug>` or `atipspec proposal
contract`), then offer Approve and continue / Request changes / Cancel in the
user's language using the client's question tool, or a plain reply when
unavailable. Follow the printed conversational approval rules. After explicit
approval of unchanged content, run `atipspec accept ... --code <code>` yourself
with the code you presented; when the client asks the human to allow it, that
confirms the same approval. Never write or delete under approvals/, evidence/
or archive/, or review-rounds.json (except reverting an archive commit to
reopen a delivery, when the user asks and the repository's policy allows it),
never set the status of a spec, the contract or a contract decision by hand
(`atipspec accept contract` sets the decisions `proposal contract` lists), never
fabricate approval or infer it from silence, and never require the user to
execute approval commands.

## Trusted acceptance

Local `check` produces `checked`; only a gate with an external organization
policy, signed CI evidence and content-bound human approvals produces
`verified`. Local `deliver` requires result acceptance; a configured external
policy requires authenticated acceptance. Never sign on behalf of a human or
fabricate approval metadata. `report <slug>` exports the acceptance dossier;
`enterprise-init` writes reviewable CI and policy examples.
