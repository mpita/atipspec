# Estructura del proyecto

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

## Qué lee el modelo, y cuándo

| Momento | Lee |
| --- | --- |
| Se invoca el skill | el `SKILL.md` de esa fase, unas pocas líneas |
| Se ejecuta el comando de la fase | lo que imprime: el workflow de la fase, `framework/rules.md` y la salida de `atipspec context <slug>` |
| Se escribe un artefacto | su plantilla bajo `framework/templates/` |

Nunca recorre `specs/` ni `archive/` en su totalidad, y nunca lee el
workflow de una fase que el CLI no ha abierto. Eso es lo que mantiene
acotado el coste de una petición.

## Qué escribe el CLI

| Comando | Escribe |
| --- | --- |
| `init`, `install` | `config.yaml`, documentos esqueleto, `framework/`, los skills de los clientes, las reglas de permisos de Claude Code fusionadas en `.claude/settings.json` |
| `new`, `decision`, `initiative` | carpetas y ficheros nuevos a partir de plantillas, `baseline.json`; una línea de roadmap; con `system` definido, `contracts.json` |
| `spec-bind` | la spec viva, los IDs en `spec.md`, `sources/` en una importación |
| `accept` | `approvals/local-*.json` y `status: ready` en la spec, y para una propuesta guiada el inicio de `review-rounds.json`; para el contrato, `.atipspec/approvals/contract.json` y `status: accepted` en el contrato y en las decisiones que lista |
| `task-done` | `progress.json` |
| `verify` | `evidence/*.json` y `evidence/logs/` |
| `review` | `tmp/<slug>-review-packet.md` y `review-rounds.json` |
| `run` | `run.json`, `progress.json`, `review-rounds.json`, el `review.md` del revisor y lo que escriben el adaptador y `verify` |
| `contract-pin` | `contracts.json` |
| `report --out` | el dosier, fuera del repositorio, bajo `tmp/` o en `reports/` de la entrega |
| `deliver` | la spec viva, el recibo `reports/acceptance.json`, el status de la entrega, el traslado a `archive/` |
| `migrate --apply` | la entrega convertida y su spec viva, las copias de seguridad bajo `migrations/` |
| `curate` | el bloque de índice de `overview.md` |
| `pilot` | `pilots/<name>/` |
| `enterprise-init` | los ejemplos bajo `enterprise/`, o en `--out` |
| `approve`, `sync-approvals`, `attest` | registros firmados de aprobación y de evidencia con sus ficheros `.sig` |

Todo lo demás lo escribe el modelo o una persona.
