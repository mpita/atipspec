# Project layout

```text
.atipspec/
  config.yaml             name, language, policies
  .gitignore              ignores tmp/
  contract.md             the architecture contract; its ```rules block is machine-checked
  overview.md             what the product is and where things live; curated, with an index block
  glossary.md             the project's canonical words
  approvals/contract.json the contract's recorded acceptance, written by `atipspec accept contract`
  teams.json              optional: refs, owners, repositories, integration branch, ticket links
  adapter.json            optional: the process adapter `atipspec run` calls
  specs/
    auth.md               living spec of the auth capability: requirements and scenarios
    orders.md
  decisions/
    DEC-001-stack.md      choices with lasting consequences
  initiatives/
    orders/roadmap.md     deliveries grouped over months, with their interfaces
  deliveries/
    password-reset/
      brief.md            explore phase output, optional
      spec.md             intent, scope decisions and the requirement IDs it lists; status draft or ready
      baseline.json       the capability's living spec when the delivery started, written by `new`
      plan.md             scope, approach, tasks and final verification
      contracts.json      contracts pinned from other repositories, written by `new` and `contract-pin`
      sources/            documents `spec-bind` imported, as they were
      approvals/          local-proposal.json, local-result.json (local-spec, local-plan for legacy), written by `atipspec accept`
      progress.json       the tasks recorded with `atipspec task-done`
      evidence/           written by `atipspec verify`
        FINAL-20260913T154145.218304Z-3f9a1c2e.json
        logs/             full command output and copied JUnit reports, with hashes
      review.md           written by the reviewer
      review-rounds.json  reviews counted, started by `atipspec accept`, written by `review` and `run`
      run.json            the runner's checkpoint, written by `atipspec run`
      deferred.md         findings postponed with a reason
      reports/            report exports; on deliver, acceptance.json, the receipt
  archive/
    checkout-v2/          delivered; same files, status delivered, with reports/acceptance.json
  migrations/<digest>/    originals backed up by `atipspec migrate --apply`
  pilots/<name>/          pilot protocols and observations
  enterprise/             examples `atipspec enterprise-init` writes
  framework/
    rules.md              the rules every phase command prints
    workflows/            explore, spec, fix, plan, build, review, contract, curate
    templates/            spec, plan, fix-spec, fix-plan, brief, deferred, review, rubric, capability, contract, overview, glossary, decision, roadmap
  tmp/                    review packets and JUnit reports (`.atipspec/tmp/junit.xml`); ignored by git
.claude/skills/atipspec*/SKILL.md     per client: one skill per phase plus the umbrella
.claude/settings.json                 Claude Code: asks before `atipspec accept` and edits to CI workflows or its settings, denies edits to approval, evidence and review round records
```

## What the model reads, and when

| Moment | Reads |
| --- | --- |
| Skill invoked | that phase's `SKILL.md`, a few lines |
| The phase command runs | what it prints: the phase's workflow, `framework/rules.md` and the output of `atipspec context <slug>` |
| Writing an artifact | its template under `framework/templates/` |

It never browses `specs/` or `archive/` wholesale, and never reads a workflow
for a phase the CLI has not opened. That is what keeps the cost of a request
bounded.

## What the CLI writes

| Command | Writes |
| --- | --- |
| `init`, `install` | `config.yaml`, skeleton documents, `framework/`, client skills, the Claude Code permission rules merged into `.claude/settings.json` |
| `new`, `decision`, `initiative` | new folders and files from templates, `baseline.json`; a roadmap line; with `system` set, `contracts.json` |
| `spec-bind` | the living spec, the IDs in `spec.md`, `sources/` for an import |
| `accept` | `approvals/local-*.json` and `status: ready` in the spec, and for a guided proposal the start of `review-rounds.json`; for the contract, `.atipspec/approvals/contract.json` and `status: accepted` in the contract and the decisions it lists |
| `task-done` | `progress.json` |
| `verify` | `evidence/*.json` and `evidence/logs/` |
| `review` | `tmp/<slug>-review-packet.md` and `review-rounds.json` |
| `run` | `run.json`, `progress.json`, `review-rounds.json`, the reviewer's `review.md` and what the adapter and `verify` write |
| `contract-pin` | `contracts.json` |
| `report --out` | the dossier, outside the repository, under `tmp/` or in the delivery's `reports/` |
| `deliver` | the living spec, the receipt `reports/acceptance.json`, the delivery's status, the move to `archive/` |
| `migrate --apply` | the converted delivery and its living spec, the backups under `migrations/` |
| `curate` | the index block of `overview.md` |
| `pilot` | `pilots/<name>/` |
| `enterprise-init` | the examples under `enterprise/`, or `--out` |
| `approve`, `sync-approvals`, `attest` | signed approval and evidence records with their `.sig` files |

Everything else is written by the model or by a person.
