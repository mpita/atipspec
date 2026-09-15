# Layout do projeto

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

## O que o modelo lê, e quando

| Momento | Lê |
| --- | --- |
| Skill invocada | o `SKILL.md` daquela fase, poucas linhas |
| O comando de fase roda | o que ele imprime: o workflow da fase, `framework/rules.md` e a saída de `atipspec context <slug>` |
| Escrevendo um artefato | seu template sob `framework/templates/` |

Ele nunca navega por `specs/` ou `archive/` por inteiro, e nunca lê um
workflow de uma fase que a CLI não abriu. É isso que mantém o custo de uma
requisição limitado.

## O que a CLI escreve

| Comando | Escreve |
| --- | --- |
| `init`, `install` | `config.yaml`, documentos esqueleto, `framework/`, skills do cliente |
| `new`, `decision`, `initiative` | novas pastas e arquivos a partir de templates; uma linha no roadmap |
| `accept` | `approvals/local-*.json`, `status: ready` na spec, `status: accepted` no contrato |
| `verify` | `evidence/*.json` e `evidence/logs/` |
| `review` | `tmp/<slug>-review-packet.md` |
| `deliver` | a spec viva, o status da entrega, a movimentação para `archive/` |
| `curate` | o bloco de índice de `overview.md` |

Todo o resto é escrito pelo modelo ou por uma pessoa.
