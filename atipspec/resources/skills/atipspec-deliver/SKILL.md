---
name: atipspec-deliver
description: Present and archive a reviewed ATIPSpec result after explicit human acceptance.
---

Run `atipspec check <slug>` and present `atipspec report <slug>` plus the observable
result. Local checked means ready to inspect. Ask for result acceptance only when
it has not already been explicitly given; record the user's approval with
`atipspec accept <slug> result --code <code>`, using the code from the report you
presented. Then run `atipspec deliver <slug>`.

When the repository's policy lets you commit, commit the accepted code before
`deliver` and what `deliver` changed in a commit of its own. After `deliver`,
change nothing outside `.atipspec/` on this branch and do not merge the target
branch into it; if a change is needed, ask the user to reopen the delivery:
with their consent and when the repository's policy allows it, revert the commit
that archived it (the one exception to never deleting under `archive/`), then
verify, review and request result acceptance again. Before
asking for the merge, run `atipspec merge-check --base <target branch>` and
report its result. When the user asks you to open a pull request, include the
delivery's ticket and the output of `atipspec report <slug> --format markdown`
in its description.

When an external policy is configured, use its authenticated acceptance procedure.
Do not substitute a local declaration for corporate approval. Commits, push, merge
and deployment require the authorization defined for this repository.
