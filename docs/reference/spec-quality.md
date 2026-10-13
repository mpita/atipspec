# Writing criteria

A specification is only as good as its criteria, and the industry has settled
on what a good criterion looks like: ISO/IEC/IEEE 29148 asks for requirements
that are singular, unambiguous and verifiable; the INCOSE Guide for Writing
Requirements lists the words that make one unverifiable; EARS (Easy Approach
to Requirements Syntax) gives the sentence shapes; Specification by Example
asks for concrete data; Volere asks every quality attribute for a fit
criterion. AtipSpec's workflow follows them, and `check` enforces the part a
machine can check.

## What `check` verifies

| Check | Where | Level |
| --- | --- | --- |
| Scenario structure: WHEN and THEN in order, no empty step | every scenario | error |
| EARS or scenario form | criterion statements (`- AC-001: ...`) | strict |
| No vague term | requirement titles and statements; criterion statements; scenario titles and every step | strict |
| A number in the outcome | criteria of a quality attribute | strict |
| How it is measured | criteria of a quality attribute | warning |
| A concrete value in the outcome | every other criterion | warning |
| No vague term inside quotes | wherever the vague-term check reads | warning |
| `## Intent`, `## Out of scope` and `## Quality attributes` decided | a guided delivery's `spec.md` | todo until the proposal is approved |

A strict finding is an error with `strict_criteria: true`, the default, and a
warning with `strict_criteria: false`. An error or a todo from the
specification blocks the proposal: `atipspec proposal` lists it under "Not
ready for approval" and shows no approval code, and `atipspec accept` refuses.
A warning never blocks. `proposal` lists every specification warning under its
approval code; the model resolves them or names each one it keeps when it
presents the proposal.

`check` reads the requirements the delivery defines or references, never the
rest of the living spec. In a guided delivery, a requirement of the capability
that differs from the one the living spec held at the delivery's base commit,
added, edited, deleted or marked `[remove]`, but is not listed under
`requirements` is an error at every risk level, since the approval hashes
only the listed ones and `merge-check` blocks a requirement changed outside
the deliveries that list it: list it if this change writes it, so that
`check` reads it, or undo the change. `new` refuses to start while that
living spec has changes not committed, so the base commit holds it as the
delivery starts from it; a feature created before 0.3.0 compares with its
`baseline.json` instead. A requirement changed in
another capability's living spec is an error too: the delivery does not
deliver it, and `merge-check` blocks it. What the integration branch brought
(see [when main moves](../teams.md#when-main-moves)) or a delivery archived
in the branch after the base wrote, as its receipt records, and what another
open delivery of the capability lists, is not the delivery's change; what a
merge of any other branch brings is. A receipt vouches only for the
requirements its delivery lists, as the commit that archived it added them,
or, not committed yet, while `HEAD` holds that delivery open. Text of the
living spec outside its requirements, before the first one or under a heading
that ends one, its frontmatter, and an HTML comment or fenced code in a
requirement the delivery does not list are in no approval: a change of them
is a warning, compared with the merge base where the integration branch
changed them, and only the acceptance of the result, which binds the whole
tree, covers them.

## The forms `check` accepts

With `criteria_syntax: ears` (the default), a criterion statement starts with a
trigger or carries a `shall`:

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
*must* in its main clause, before any comma. In Spanish: *cuando*,
*mientras*, *si*, *donde*, *dado* (and its forms), *después de*, *tras*, and
*debe* or *deberá* in the main clause. In Portuguese: *quando*, *enquanto*,
*se*, *onde*, *dado* (and its forms), *depois de*, *após*, and *deve* or
*deverá*. The English triggers count in every language, because the templates
are English. Set `criteria_syntax: free` to turn the form check off; the other
checks stay on. A language without tables gets no form check and the English
vague-term list. A criterion statement may continue on indented lines.

## Scenarios

A scenario is a criterion heading under its requirement, with one step per
line:

```markdown
### REQ-001: The user can request a reset link

#### AC-001: Registered email
- **GIVEN** a registered user on the "Sign in" page
- **WHEN** the user requests a reset for that email
- **THEN** the system sends a link to that email within 60 seconds
```

The parser checks the structure, whatever `strict_criteria` says: WHEN and
THEN are required, steps follow GIVEN, WHEN, THEN, AND and BUT extend the step
before them, and no step is empty. An `[invariant]` criterion asserts with
INVARIANT or THEN and needs no trigger. The lint then reads the scenario title
and every step for vague terms. Spanish and Portuguese step words (*DADO*,
*CUANDO*, *ENTONCES*, *QUANDO*, *ENTÃO*, ...) work too, and a scenario written
with them is also read with that language's vague terms, whatever the
project's language.

## Vague terms

The INCOSE guide's rule: no term whose meaning depends on the reader. `check`
reports a requirement or a criterion that contains one. English:

`fast`, `quick`, `quickly`, `slow`, `user-friendly`, `user friendly`, `easy`,
`easily`, `easy-to-use`, `appropriate`, `appropriately`, `adequate`,
`adequately`, `efficient`, `efficiently`, `effectively`, `robust`, `etc.`,
`and/or`, `and so on`, `as needed`, `if possible`, `if necessary`,
`when necessary`, `as soon as possible`, `reasonable`, `reasonably`,
`sufficient`, `sufficiently`, `several`, `a few`, `many`, `some`,
`approximately`, `seamless`, `seamlessly`, `intuitive`, `intuitively`,
`optimal`, `optimally`, `flexible`, `scalable`, `as appropriate`,
`where possible`, `timely`, `minimal`, `maximize`, `minimize`, `relevant`,
`typically`, `usually`, `correctly`, `properly`, `as expected`, `as intended`,
`works well`, `work well`.

Spanish, with the English list too:

`rápido`, `rápida`, `rápidos`, `rápidas`, `rápidamente`, `fácil`, `fáciles`,
`fácilmente`, `amigable`, `amigables`, `adecuado`, `adecuada`, `adecuados`,
`adecuadas`, `adecuadamente`, `apropiado`, `apropiada`, `apropiados`,
`apropiadas`, `apropiadamente`, `eficiente`, `eficientes`, `eficientemente`,
`robusto`, `robusta`, `robustos`, `robustas`, `etc.`, `y/o`,
`y así sucesivamente`, `según sea necesario`, `si es necesario`,
`cuando sea necesario`, `si es posible`, `lo antes posible`, `razonable`,
`razonables`, `razonablemente`, `suficiente`, `suficientes`, `suficientemente`,
`varios`, `varias`, `unos pocos`, `unas pocas`, `muchos`, `muchas`, `algunos`,
`algunas`, `aproximadamente`, `intuitivo`, `intuitiva`, `intuitivos`,
`intuitivas`, `intuitivamente`, `óptimo`, `óptima`, `óptimos`, `óptimas`,
`flexible`, `flexibles`, `escalable`, `escalables`, `cuando sea posible`,
`oportuno`, `oportuna`, `lo mínimo`, `al mínimo`, `mínimo posible`,
`maximizar`, `minimizar`, `relevante`, `relevantes`, `normalmente`,
`habitualmente`, `correctamente`, `como se espera`, `como es de esperar`,
`según lo previsto`, `funciona bien`, `funcione bien`, `sin problemas`.

Portuguese, with the English list too:

`rápido`, `rápida`, `rápidos`, `rápidas`, `rapidamente`, `fácil`, `fáceis`,
`facilmente`, `amigável`, `amigáveis`, `adequado`, `adequada`, `adequados`,
`adequadas`, `adequadamente`, `apropriado`, `apropriada`, `apropriados`,
`apropriadas`, `apropriadamente`, `eficiente`, `eficientes`, `eficientemente`,
`robusto`, `robusta`, `robustos`, `robustas`, `etc.`, `e/ou`,
`e assim por diante`, `conforme necessário`, `se necessário`,
`quando necessário`, `se possível`, `o mais rápido possível`, `o quanto antes`,
`razoável`, `razoáveis`, `razoavelmente`, `suficiente`, `suficientes`,
`suficientemente`, `vários`, `várias`, `alguns poucos`, `muitos`, `muitas`,
`alguns`, `algumas`, `aproximadamente`, `intuitivo`, `intuitiva`, `intuitivos`,
`intuitivas`, `intuitivamente`, `ótimo`, `ótima`, `ótimos`, `ótimas`,
`flexível`, `flexíveis`, `escalável`, `escaláveis`, `quando possível`,
`oportuno`, `oportuna`, `o mínimo`, `ao mínimo`, `mínimo possível`,
`maximizar`, `minimizar`, `relevante`, `relevantes`, `normalmente`,
`geralmente`, `habitualmente`, `corretamente`, `como esperado`,
`conforme esperado`, `conforme previsto`, `funciona bem`, `funcione bem`,
`sem problemas`.

A term matches whole words, also inside a hyphenated compound or Markdown
emphasis: `fast-loading` and `_quickly_` match. A token with a colon inside,
such as `theme:slow-unresponsive`, and a cardinality, such as `many-to-many`,
are identifiers and pass. Text between quotes (`"..."`, `“...”`, `«...»`) or
backticks is not read by the strict check: quote the literal text of the
interface, such as the button `"Fast checkout"`, instead of rewording it. A
quote that holds a vague term gets a warning instead, so the human sees it in
the proposal, and it is not a concrete value. Words with frequent precise uses
stay out of the lists: *correct* (the correct password), *expected*
(`Expected:`), *well* (well-formed), *significant* (significant digits),
*effective* (effective date) and *a minimum of 12*.

The fix is always the same: replace the adjective with the observable value.
"Responds quickly" becomes "responds within 300 ms at the 95th percentile".

## Concrete values

Specification by Example asks each outcome for the data a test compares. The
outcome is the THEN or INVARIANT step and the AND and BUT steps after it, or,
in a criterion statement, what follows the first comma when the trigger comes
first, and the whole statement otherwise. `check` warns when the outcome names
no concrete value:

- a number, such as `27.00`, `60 seconds` or `HTTP 404` (the 95 in `p95` names
  a percentile, not a value);
- quoted text without a vague term, such as `"link expired"`;
- a path, such as `/orders/paid`, or an address, such as `billing@example.com`;
- a name with a capital that does not open the sentence, such as the
  `Sign-in` page.

A number in GIVEN does not make THEN concrete: "Given an order of 3 items at
10.00 ... then the discount is applied" gets the warning; "then the total is
27.00" does not. This check is a heuristic, so it stays a warning in every
mode.

## Requirements

Write one requirement per behavior a user values, independent of other open
changes, small enough for the delivery and testable: the INVEST criteria for a
story. `check` reads a requirement's title and the lines that state it for
vague terms. It leaves out its criteria, the `Acceptance criteria:` label (the
text after it is read), a `Why:` paragraph (*Por qué:*, *Motivo:*, *Por
quê:*), which gives the reason, and an `Observed:` paragraph (*Observado:*),
which describes a defect, not the requirement. Each runs, with the list under
it, up to a blank line, a criterion or another label such as `Expected:`; a
label alone on its line also takes the block after it. An indented list item
under a criterion statement is not part of the criterion, so it is read as the
requirement's text. A requirement marked `[remove]` keeps the title of the
living spec, so only its criteria are read. A fix keeps the defect's story
under `## Defect` in its `spec.md`, outside any requirement, and corrects an
accepted requirement in `specs/`, which is read like any other.

## Quality attributes and fit criteria

Performance, capacity, availability and security are requirements with
criteria, like any other behavior, following Volere's fit criterion and Gilb's
Planguage: the criterion's outcome states the number with its unit, and the
criterion says how it is measured.

In a guided delivery the requirement lives in `specs/<capability>.md`, and the
delivery's `spec.md` names it under `## Quality attributes`, one line per
requirement:

```markdown
## Quality attributes

- REQ-004: p95 below 300 ms with 100 requests per minute
```

A line that names no requirement of this change is a todo while the proposal
is a draft and an error afterwards: the limit must be a requirement with a
criterion, so that a task tests it, the review gives it a verdict and the
evidence proves it. `- None` says the change has no quality attribute. In a
legacy delivery the requirement is written under `## Quality attributes` in
its `spec.md`:

```markdown
### REQ-004: Response time of the reset request

Acceptance criteria:
- AC-006: When 100 users request a reset within one minute, the p95 response
  time measured at the API gateway is below 300 ms.
```

A criterion of a quality attribute without a number in its outcome is a
strict finding. Without a word that says how it is measured (*measured*,
*medido*, *medida*, *medição*), it is a warning: name where and with what.

## Intent and scope of a guided delivery

`atipspec new` writes a guided `spec.md` with `## Intent`, `## Out of scope`
and `## Quality attributes`, and lists them under `sections` in the delivery's
`baseline.json`. Until the proposal is approved, an empty Intent, or one that
only says `TBD`, `TODO` or `...`, is a todo that blocks the proposal: state
the actor, the trigger, the observable result and how the user will know it
worked. An Out of scope or Quality attributes section with no item is
undecided, and a todo too: list the items, or write `- None`. Deleting one of
those headings is a todo as well. Approved means a local approval record of
the current content; editing the `status` line changes nothing. Under a trust
policy, whose signatures are the approval, `check` counts the `status` the
people set instead; `proposal` and `accept proposal` still count only the
local record. A delivery created before 0.3.0 without those two sections gets
a warning only, and so does a delivery whose proposal is approved for its
current content. Those warnings on an approved delivery wait for the next
change to its proposal: editing `spec.md` only for them voids the approval.

## Strictness

New projects have `strict_criteria: true`: a strict finding is an error that
blocks the proposal. Projects initialized before 0.3.0 keep the
`strict_criteria: false` that `init` wrote, where strict findings are warnings
the spec phase resolves before presenting. `proposal` shows the mode before
the approval: "Criteria check: strict" or "warnings only", and says when
`criteria_syntax: free` leaves the form unchecked. `config.yaml` is
part of what a guided proposal's approval hashes, so lowering the mode after
the approval leaves that approval outdated.

## Test or manual

Every criterion is proven by a test or observed by a person. Mark the second
kind in the spec, at the time it is written:

```markdown
#### AC-SHIP-4TQ8N-005 [manual]: Printed label
- **WHEN** the label prints
- **THEN** it shows the order code in Code 128
```

A criterion statement of a legacy delivery takes the mark the same way:
`- AC-005 [manual]: When the label prints, it shows the order code in Code 128.`

The plan must respect the mark: a `[manual]` criterion listed under `Tests:`
is an error, and so is an unmarked one under `Manual:`. Every criterion must
appear under one of them; until it does, `check` reports a todo and `atipspec
build` refuses. The mark travels with the criterion into the living spec. A
criterion may be listed under `Tests:` in more than one task when several
tasks exercise it.

## Assumptions

The model proposes defaults when you hesitate. They are not silent: each one
is a requirement and an entry under `## Assumptions`, and the gate reminds you
to confirm them at acceptance. An assumption you reject becomes a question or
a different requirement.

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
- Suzanne Robertson and James Robertson, Mastering the Requirements Process (Volere), third edition, 2012.
- Bill Wake, INVEST in Good Stories, and SMART Tasks, 2003.
- Karl Wiegers and Joy Beatty, Software Requirements, third edition, 2013.
- Tom Gilb, Competitive Engineering (Planguage), 2005.
