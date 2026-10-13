---
title: "{{title}}"
status: draft            # draft until `atipspec accept` records the human's approval; never edit it by hand
capability: null
impact: []
owner: null
ticket: null
initiative: null
base: null
created: null
schema: 2
change_id: null
requirements: []
risk: normal
---

# {{title}}

<!--
Requirements and their scenarios live in .atipspec/specs/<capability>.md: list
their IDs under `requirements` above and keep no second definition here. There,
each requirement is a `###` heading, `REQ-...: Title`, and each scenario a `####`
heading under it, `AC-...: Title`, with GIVEN, WHEN and THEN steps; `[manual]` or
`[invariant]` follows the criterion's ID when it applies. Take the ID prefix from
`atipspec ids <capability>`; `atipspec spec-bind <slug> --file <path>` installs an
authored or imported document and lists its IDs.
-->

## Intent

<!-- Who needs this, what triggers it, what they observe when it works, and how they will know it
solved the problem. Two to five sentences, with concrete values. -->

## Out of scope

<!-- Replace `None` with what this change deliberately leaves out, one item per line. -->

- None

## Quality attributes

<!-- Replace `None` with each limit this change must hold, one line per requirement in specs/ that
states it: `- REQ-...: p95 below 300 ms`. That requirement's criterion gives the number with its
unit and how it is measured. -->

- None

## Assumptions

- None

## Open questions

- None
