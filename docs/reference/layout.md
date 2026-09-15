# Project layout

```text
.atipspec/
  config.yaml             name, language, policies
  .gitignore              ignores tmp/
  contract.md             the architecture contract; its ```rules block is machine-checked
  overview.md             what the product is and where things live; curated, with an index block
  glossary.md             the project's canonical words
  specs/
    auth.md               living spec of the auth capability
    orders.md
  decisions/
    DEC-001-stack.md      choices with lasting consequences
  initiatives/
    orders/roadmap.md     deliveries grouped over months, with their interfaces
  deliveries/
    password-reset/
      brief.md            explore phase output, optional
      spec.md             requirements and criteria; status draft or ready
      plan.md             approach and tasks
      approvals/          local-spec.json, local-plan.json, written by `atipspec accept`
      evidence/           written by `atipspec verify`
        T1-20260913T154145Z-3f9a1c2e.json
        logs/             full command output and copied JUnit reports, with hashes
      review.md           written by the reviewer
      deferred.md         findings postponed with a reason
  archive/
    checkout-v2/          delivered; same files, status delivered
  framework/
    rules.md              the rules every phase command prints
    workflows/            explore, spec, fix, plan, build, review, contract, curate
    templates/            spec, plan, fix-spec, fix-plan, brief, deferred, review, rubric, capability, contract, overview, glossary, decision, roadmap
  tmp/                    review packets; ignored by git
.claude/skills/atipspec*/SKILL.md     per client: one skill per phase plus the umbrella
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
| `init`, `install` | `config.yaml`, skeleton documents, `framework/`, client skills |
| `new`, `decision`, `initiative` | new folders and files from templates; a roadmap line |
| `accept` | `approvals/local-*.json`, `status: ready` in the spec, `status: accepted` in the contract |
| `verify` | `evidence/*.json` and `evidence/logs/` |
| `review` | `tmp/<slug>-review-packet.md` |
| `deliver` | the living spec, the delivery's status, the move to `archive/` |
| `curate` | the index block of `overview.md` |

Everything else is written by the model or by a person.
