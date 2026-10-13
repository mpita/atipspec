# contract

**Define and guard the architecture.** The first phase of a project and the
one that keeps the fortieth delivery on the same rails as the first.

| | |
| --- | --- |
| Role | The keeper of the contract. Describes reality before rules, writes rules the CLI can check, never changes the contract inside a feature delivery. |
| Who decides | You approve the contract and the listed decisions in the conversation; the assistant records your decision with `atipspec accept contract --code <code>`. |
| Produces | `contract.md`, `decisions/DEC-nnn-*.md`, `approvals/contract.json`; living specs come later, with their first requirements |

## How to run it

```text
/atipspec-contract
```

The skill runs `atipspec contract`, which prints the workflow, the rules and
the current `contract.md`. It presents `atipspec proposal contract` (the
contract, its rules, the audit result, the decisions it includes and an approval
code), requests approval in the conversation and runs `atipspec accept contract
--code <code>` after your explicit approval. The CLI then sets the contract and
the listed decisions to `accepted` and records their hashes in
`.atipspec/approvals/contract.json`. Legacy deliveries, fixes created before
0.3.0 included, require that recorded acceptance before entering `fix` or
`spec`; for guided deliveries, fixes included, `check` warns until it exists.

## A new project

Say what you already decided: "a Django web app with PostgreSQL and a React
front". The model records those as decisions with their reasons, so they are
never reopened by accident:

```bash
atipspec decision stack --title "Django, PostgreSQL and React" --affects contract
```

Then it asks only what affects the rules: how front and back talk, where API
contracts live, authentication, the quality commands, what is forbidden. It
fills `contract.md`:

````markdown
## Stack
Python 3.12, Django 5, PostgreSQL 16; React 18 with TypeScript in web/.

## Structure
shop/domain/ has no imports from shop/infrastructure/ or Django. Views are
thin; use cases live in shop/application/.

## Dependencies
New libraries need a decision. Pin exact versions.

## Quality gates
python -m pytest -q, ruff check ., npm test in web/.

## Rules

```rules
dependencies pyproject.toml django psycopg "pytest*" ruff
dependencies web/package.json react react-dom "@types/*" typescript vite
forbid-pattern "shop/domain/**" "from shop\.infrastructure|^from django"   # DEC-001 layering
forbid-path "web/src/**/*.js"                                             # TypeScript only
require-command "python -m pytest -q"
require-command "ruff check ."
```
````

Living specs are created when their requirements are defined. The assistant runs
the audit and presents the contract and included decisions. Choose **Approve and
continue**, **Request changes** or **Cancel** using the client selector when
available, or reply in the conversation. The assistant runs these commands;
`accept` only after your explicit approval, with the code it presented:

```bash
atipspec audit
atipspec proposal contract
atipspec accept contract --code 11HN-G0QN
```

## An existing project

The model reads manifests, folders, CI and tests, and proposes a contract that
**describes what exists**; the rules it thinks you should add are marked as
proposals. Then `atipspec audit`: every violation is fixed now, accepted by
you as an exception (the rule is narrowed), or dropped. A red audit is never
left behind.

## Changing the contract

The contract changes only with a decision, and the gate enforces it: a
delivery whose diff touches `contract.md` without a new file in
`.atipspec/decisions/` is red.

```bash
atipspec decision allow-httpx --title "Use httpx for outbound HTTP" --affects contract:dependencies
```

The assistant prepares the decision and contract change in the same delivery,
runs `atipspec audit` and presents both with `atipspec proposal contract`. After
your explicit approval, it runs `atipspec accept contract --code <code>`, which
sets the decision to `accepted`. A decision whose status was set by hand is not
part of the accepted contract: the contract's acceptance becomes outdated, the
gate keeps the delivery red, legacy deliveries cannot enter `spec`, and
`atipspec context` leaves the decision out until the contract is accepted again.

!!! info "What the rules can and cannot check"
    Rules are structural on purpose: forbidden paths, forbidden patterns,
    declared dependencies per manifest, required commands. They catch the
    drift that actually happens on long projects, a new library, a layer
    crossing, a skipped test command. Design judgment stays with the reviewer,
    who receives the whole contract in the packet. See the
    [rules reference](../reference/contract-rules.md).
