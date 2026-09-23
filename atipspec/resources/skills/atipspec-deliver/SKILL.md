---
name: atipspec-deliver
description: Present and archive a reviewed ATIPSpec result after explicit human acceptance.
---

Run `atipspec check <slug>` and present `atipspec report <slug>` plus the observable
result. Local checked means ready to inspect. Ask for result acceptance only when
it has not already been explicitly given; use `atipspec accept <slug> result` to
record the user's instruction. Then run `atipspec deliver <slug>`.

When an external policy is configured, use its authenticated acceptance procedure.
Do not substitute a local declaration for corporate approval. Commits, push, merge
and deployment require the authorization defined for this repository.
