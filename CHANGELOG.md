# Release history

## 0.1.0 — First release

Initial version of AtipSpec, prepared for new projects.

- One command, one skill and one workflow per phase. `atipspec explore|spec|plan|build <slug>`
  check what the phase requires and refuse with one line while a step is missing;
  otherwise they print the workflow, the shared rules (`framework/rules.md`) and the
  context. `review` refuses until every task is committed with fresh evidence;
  `contract` and `curate` print their workflow; `ship` names the next phase.
- `atipspec accept <slug> spec|plan` and `atipspec accept contract`: a person
  accepts, the command sets the status and records a hash of the accepted content,
  and `check` sends the delivery back to draft when the spec or the contract changes
  afterwards. The model never sets `ready` or `accepted` and never runs `accept`.
  `atipspec build` refuses until the plan is accepted when `approve_plan` is on.
- `init` warns when the repository has no `.gitignore`, because untracked build
  caches change the working tree and make evidence stale.
- Trusted acceptance in two modes: an SSH mode using an external organization
  policy, signed CI evidence and content-bound human approvals by role; and a
  provider mode (`schema = 2`, `mode = "provider"`) where the protected worker
  reads product, engineering and QA approvals live from the PR or MR and verifies
  each CI evidence record with a GitHub artifact attestation through a pinned
  `gh` — no human, CI or collector key to enroll. `check`, `deliver` and `report`
  take `--number` or `ATIPSPEC_PR_NUMBER`. `enterprise-init` writes the provider
  policy example and the evidence workflow.
- Read-only GitHub and GitLab approval adapters, including revocation checks.
- Stable requirement and acceptance-criterion IDs with test/evidence mapping.
- Acceptance dossiers in JSON, Markdown and HTML.
- Languages: English primary, Spanish and Portuguese supported. `language` in
  `config.yaml` drives the criterion lint, the section names and empty markers the
  parser accepts, and the acceptance dossier's labels; `init` offers the three;
  `audit` warns about a language without tables. The documentation site builds in
  the three languages with a switcher and English fallback for untranslated pages.
- Evidence per criterion: a task can name the JUnit XML its commands write
  (`Report:`) and the test that proves each criterion (`Proof:`). `verify` copies
  the report with its hash and records every test case; `check` fails when a named
  test did not run or did not pass; altering the copy is detected; the packet and
  the dossier show the tests per criterion.
- `atipspec new --kind fix` and the `fix` phase: a defect gets a spec with one
  regression criterion, a one-task plan with the contract's required commands
  prefilled, no interview and no plan acceptance; evidence, review and the gate
  are unchanged. `status` marks such deliveries `[fix]`.
- Deliveries are sized for a working day: `check` warns above `max_requirements`
  (5) and `max_tasks` (8), `status` shows how long each delivery has been open and
  warns above `max_age_hours` (48), and `new` records `created` with the time.
- Specs follow the industry's shape: criteria in EARS or scenario form with
  concrete values (`check` warns about other forms and about vague terms, in
  English and Spanish; `criteria_syntax` and `strict_criteria` tune it), a
  `[manual]` mark for criteria a person observes that the plan must respect,
  `## Assumptions` the user confirms at acceptance, `## Quality attributes`
  with numbers, and `Why:` lines. Every criterion must be mapped under `Tests:`
  or `Manual:` before `atipspec build` starts.
- The review packet includes the living specs in the impact list and the accepted
  decisions affecting them, so a reviewer can see conflicts with existing behavior;
  the diff is capped at 200 KB with a `--stat` summary when truncated.
- Plans declare `scope`, the globs of files their tasks may change. `check` warns
  about touched files outside it, deletions included (`strict_scope: true` makes
  it an error) and the packet lists them for the reviewer.
- Enterprise policy and CI examples, an adoption guide, and MIT licensing.
- Pilot protocols and sourced measurements for comparing real deliveries.

Organization trust, protected CI and real-world pilots require configuration
in the adopting organization. This entry describes the initial codebase;
publication to a package registry is a separate release operation.
