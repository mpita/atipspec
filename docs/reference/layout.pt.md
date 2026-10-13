# Estrutura do projeto

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

## O que o modelo lê, e quando

| Momento | Lê |
| --- | --- |
| Skill invocada | o `SKILL.md` daquela fase, poucas linhas |
| O comando de fase roda | o que ele imprime: o workflow da fase, `framework/rules.md` e a saída de `atipspec context <slug>` |
| Escrevendo um artefato | seu template sob `framework/templates/` |

Ele nunca navega por `specs/` ou `archive/` por inteiro, e nunca lê o
workflow de uma fase que a CLI não abriu. É isso que mantém limitado o custo
de uma requisição.

## O que a CLI escreve

| Comando | Escreve |
| --- | --- |
| `init`, `install` | `config.yaml`, documentos esqueleto, `framework/`, skills do cliente, as regras de permissão do Claude Code mescladas em `.claude/settings.json` |
| `new`, `decision`, `initiative` | novas pastas e arquivos a partir de templates, `baseline.json`; uma linha no roadmap; com `system` definido, `contracts.json` |
| `spec-bind` | a spec viva, os IDs em `spec.md`, `sources/` para uma importação |
| `accept` | `approvals/local-*.json` e `status: ready` na spec, e para uma proposta guiada o início de `review-rounds.json`; para o contrato, `.atipspec/approvals/contract.json` e `status: accepted` no contrato e nas decisões que ele lista |
| `task-done` | `progress.json` |
| `verify` | `evidence/*.json` e `evidence/logs/` |
| `review` | `tmp/<slug>-review-packet.md` e `review-rounds.json` |
| `run` | `run.json`, `progress.json`, `review-rounds.json`, o `review.md` do revisor e o que o adaptador e `verify` escrevem |
| `contract-pin` | `contracts.json` |
| `report --out` | o dossiê, fora do repositório, sob `tmp/` ou em `reports/` da entrega |
| `deliver` | a spec viva, o recibo `reports/acceptance.json`, o status da entrega, a movimentação para `archive/` |
| `migrate --apply` | a entrega convertida e sua spec viva, os backups sob `migrations/` |
| `curate` | o bloco de índice de `overview.md` |
| `pilot` | `pilots/<name>/` |
| `enterprise-init` | os exemplos sob `enterprise/`, ou em `--out` |
| `approve`, `sync-approvals`, `attest` | registros assinados de aprovação e de evidência com seus arquivos `.sig` |

Todo o resto é escrito pelo modelo ou por uma pessoa.
