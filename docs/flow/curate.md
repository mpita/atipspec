# curate

**Keep the context small as the project grows.** The cost of a request must
depend on the delivery, not on the age of the project.

| | |
| --- | --- |
| Role | The editor of the project's memory. Removes, merges and shortens; never adds history. |
| Who decides | The model, within the caps. |
| Produces | `overview.md`, `glossary.md`, split proposals for living specs |

## When

After a delivery, when `atipspec audit` or `atipspec context` report a size
over its cap, or whenever you ask.

## How to run it

```text
/atipspec-curate
```

The skill runs the CLI:

```bash
atipspec curate
```

```text
curate  [done]
  info    overview.md index regenerated
  info    overview.md: 58 lines (cap 150)
  warning glossary.md: 312 lines (cap 300)
  info    contract.md: 96 lines (cap 400)

Phase curate
...
```

`curate` regenerates the index block of `overview.md` (capabilities with their
requirement counts, accepted decisions, initiatives with progress, deliveries
in progress), reports every size against its cap and prints the workflow.
Then the model:

1. Rewrites the prose of `overview.md` above the index in under 60 lines:
   what the product is, for whom, the map of the repository, how to run and
   test it. Nothing that lives in a spec or a decision.
2. Rewrites `glossary.md`: one line per canonical term with the spec or
   decision that fixed it; merges synonyms; removes terms no spec uses.
3. Proposes splitting a living spec that is over its cap by capability, done
   through a delivery with `[remove]` and a new capability, never by editing
   history by hand.
4. Marks superseded decisions; never deletes one.
5. Leaves `atipspec audit` clean.

## Caps

| Document | Cap |
| --- | --- |
| `overview.md` | 150 lines |
| `glossary.md` | 300 lines |
| `contract.md` | 400 lines |
| each living spec | 400 lines |

`context_budget` in `config.yaml` (default 800 lines) is what `atipspec
context` measures a delivery's material against.
