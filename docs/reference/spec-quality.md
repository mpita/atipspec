# Writing criteria

A specification is only as good as its criteria, and the industry has settled
on what a good criterion looks like: ISO/IEC/IEEE 29148 asks for requirements
that are singular, unambiguous and verifiable; the INCOSE Guide for Writing
Requirements lists the words that make one unverifiable; EARS (Easy Approach
to Requirements Syntax) gives the sentence shapes; Specification by Example
asks for concrete data. AtipSpec's spec template follows them, and `check`
enforces the part a machine can check.

## The forms `check` accepts

With `criteria_syntax: ears` (the default), a criterion starts with a trigger
or carries a `shall`:

| Form | Shape | Example |
| --- | --- | --- |
| Event-driven | When *trigger*, the system *outcome* | When a registered email requests a reset, the system sends a link to that email within 60 seconds. |
| State-driven | While *state*, the system shall *outcome* | While the account is locked, the system shall reject every login with "account locked". |
| Unwanted behavior | If *condition*, then the system *outcome* | If a link is older than 30 minutes, then the system returns "link expired" and sends nothing. |
| Optional feature | Where *feature*, the system *outcome* | Where two-factor is enabled, the system asks for the code before showing the form. |
| Ubiquitous | The system shall *outcome* | The system shall reject passwords shorter than 12 characters. |
| Scenario | Given *context*, when *action*, then *outcome* | Given an order of 3 items at 10.00, when a 10% coupon is applied, then the total is 27.00. |

The triggers `check` recognizes are *when*, *whenever*, *while*, *if*,
*where*, *given* and *after* at the start of the criterion, or *shall* or
*must* in its main clause, before any comma. In Spanish: *cuando*, *mientras*, *si*,
*donde*, *dado* (and its forms), *después de*, *tras*, and *debe* or *deberá*
near the start; the English triggers count in every language, because the
templates are English. A criterion in another form gets a warning naming it; set
`criteria_syntax: free` to turn the form check off. A language without
tables gets no form check and the English vague-term list. The vague-term
check stays on in every mode. A criterion may be listed under `Tests:` in
more than one task when several tasks exercise it.

## Vague terms

The INCOSE guide's rule: no term whose meaning depends on the reader. `check`
warns when a criterion contains one of these, in English or Spanish:

`fast`, `quickly`, `user-friendly`, `easy`, `appropriate`, `adequate`,
`efficient`, `robust`, `etc.`, `and/or`, `as needed`, `if possible`,
`reasonable`, `sufficient`, `several`, `many`, `some`, `approximately`,
`seamless`, `intuitive`, `optimal`, `flexible`, `scalable`, `timely`,
`minimal`, `maximize`, `minimize`.

The fix is always the same: replace the adjective with the observable value.
"Responds quickly" becomes "responds within 300 ms at the 95th percentile".

With `strict_criteria: true`, both checks are errors and block the
acceptance; by default they are warnings the spec phase must resolve before
presenting the spec.

## Test or manual

Every criterion is proven by a test or observed by a person. Mark the second
kind in the spec, at the time it is written:

```markdown
- AC-005 [manual]: When the label prints, it shows the order code in Code 128.
```

The plan must respect the mark: a `[manual]` criterion listed under `Tests:`
is an error, and so is an unmarked one under `Manual:`. Every criterion must
appear under one of them; until it does, `check` reports a todo and `atipspec
build` refuses. The mark travels with the criterion into the living spec.

## Assumptions

The model proposes defaults when you hesitate. They are not silent: each one
is a requirement and an entry under `## Assumptions`, and the gate reminds you
to confirm them at acceptance. An assumption you reject becomes a question or
a different requirement.

## Quality attributes

Performance, capacity, availability and security use the same `REQ`/`AC`
format under `## Quality attributes`, with a number and a way to measure it,
following Gilb's Planguage and the SEI's quality attribute scenarios:

```markdown
### REQ-004: Response time of the reset request

Acceptance criteria:
- AC-006: When 100 users request a reset within one minute, the p95 response
  time measured at the API gateway is below 300 ms.
```

A quality attribute without a number is an adjective, and the vague-term
check treats it as one.

## Why and examples

A `Why:` line under a requirement records the reason, as ISO 29148 asks; it
keeps the requirement from being deleted by someone who no longer knows why it
exists. An example with real data, when the outcome involves a calculation, a
format or a date, is what Specification by Example calls a key example: the
test and the reviewer both start from it.

## References

- ISO/IEC/IEEE 29148:2018, Systems and software engineering, requirements engineering.
- INCOSE, Guide for Writing Requirements.
- Alistair Mavin et al., Easy Approach to Requirements Syntax (EARS), 2009.
- Gojko Adzic, Specification by Example, 2011.
- Karl Wiegers and Joy Beatty, Software Requirements, third edition, 2013.
- Tom Gilb, Competitive Engineering (Planguage), 2005.
