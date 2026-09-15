---
title: "{{title}}"
status: draft            # only `atipspec accept <slug> spec`, run by a person, moves it to ready
capability: null
impact: []
owner: null
ticket: null
initiative: null
base: null
created: null
---

# {{title}}

<!--
Frontmatter: `capability` is the living spec that receives these requirements on
deliver; `impact` lists every other living spec or contract section this delivery
touches (`atipspec context` loads them; `status` warns about overlaps).
-->

## Intent

<!-- Who needs this, what problem it solves, how we will know it worked. Two to five sentences. -->

## Requirements

<!--
One requirement per observable behavior, with a `Why:` line when the reason is
not obvious. Each needs at least one acceptance criterion a test or a reviewer
can check without interpretation, in EARS or scenario form with concrete values:
  - AC-001: When <trigger>, the system <observable outcome with values>.
  - AC-002: While <state>, the system shall <outcome>.
  - AC-003: If <unwanted condition>, then the system <outcome>.
  - AC-004: Given <context>, when <action>, then <outcome>.
Add an example with real data when the outcome involves a calculation, a format
or a date. Mark a criterion a person must observe with `[manual]`:
  - AC-005 [manual]: When ..., the printed label shows ...
IDs are stable within the capability. Preserve IDs when editing or renaming.
Use `atipspec ids <capability>` for new IDs; never reuse retired IDs.
To delete a requirement on deliver: ### REQ-003 [remove]: Title
-->

### REQ-001: <!-- short behavior statement -->

<!-- What the system does, from the user's point of view. -->

Why: <!-- the reason this behavior exists, one line -->

Acceptance criteria:
- AC-001: <!-- When <trigger>, the system <observable outcome with concrete values> -->

## Quality attributes

<!--
Performance, capacity, availability, security, usability: quantified, never
adjectives. Same REQ/AC format, one number per criterion, with how it is
measured:
### REQ-002: Response time of the reset request
- AC-002: When 100 users request a reset within one minute, the p95 response
  time measured at the API gateway is below 300 ms.
Delete this section when the delivery has no quality attribute.
-->

## Assumptions

<!--
Every default you proposed because the user did not decide it. The user
confirms them when accepting the spec; an assumption they reject becomes a
question or a requirement.
-->

- None

## Out of scope

- <!-- what this delivery deliberately does not do -->

## Open questions

- None
