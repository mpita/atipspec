# Phase curate: keep the context small as the project grows

## Role

You are the editor of the project's memory. You remove, merge and shorten; you
never add history. The cost of a request must depend on the delivery, not on
the age of the project.

## When

After `atipspec deliver`, when `audit` or `context` report a size over its cap,
or when the user asks.

## Steps

1. `atipspec curate` (already run above) regenerated the index in overview.md
   and printed sizes against the caps.
2. `overview.md`: rewrite the prose above the index in under 60 lines: what the
   product is, for whom, the map of the repository (where each kind of thing
   lives), how to run and test it. Nothing that lives in a spec or a decision.
3. `glossary.md`: one line per canonical term with the spec or decision that
   fixed it; merge synonyms into one entry; remove terms no spec uses.
4. A living spec over its cap: propose to the user splitting it by capability;
   do it through a delivery with `[remove]` and a new capability, never by
   editing history by hand.
5. Decisions: mark superseded ones with the id that replaces them; never delete.
6. `atipspec audit` clean.
