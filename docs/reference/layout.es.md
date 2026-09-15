# Estructura del proyecto

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

## Qué lee el modelo, y cuándo

| Momento | Lee |
| --- | --- |
| Se invoca el skill | el `SKILL.md` de esa fase, unas pocas líneas |
| Se ejecuta el comando de la fase | lo que imprime: el workflow de la fase, `framework/rules.md` y la salida de `atipspec context <slug>` |
| Se escribe un artefacto | su plantilla bajo `framework/templates/` |

Nunca explora `specs/` ni `archive/` en su totalidad, y nunca lee el
workflow de una fase que el CLI no ha abierto. Eso es lo que mantiene
acotado el coste de una petición.

## Qué escribe el CLI

| Comando | Escribe |
| --- | --- |
| `init`, `install` | `config.yaml`, documentos esqueleto, `framework/`, los skills de los clientes |
| `new`, `decision`, `initiative` | carpetas y ficheros nuevos a partir de plantillas; una línea de roadmap |
| `accept` | `approvals/local-*.json`, `status: ready` en la spec, `status: accepted` en el contrato |
| `verify` | `evidence/*.json` y `evidence/logs/` |
| `review` | `tmp/<slug>-review-packet.md` |
| `deliver` | la spec viva, el status de la entrega, el traslado a `archive/` |
| `curate` | el bloque de índice de `overview.md` |

Todo lo demás lo escribe el modelo o una persona.
