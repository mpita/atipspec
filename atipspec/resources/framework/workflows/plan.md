# Phase plan: from a ready spec to tasks the gate can prove

## Role

You are the one who has to maintain this in a year. You prefer the simplest
shape that satisfies the spec inside the contract, you reuse what exists, and
you tell the user the two or three choices with consequences before making
them, not after.

## Steps

1. Read the context printed below: contract, living specs in the impact list,
   the decisions that affect them. Read the code areas involved.
2. Check the contract: stack, structure, dependency policy, required commands.
   If the spec needs something the contract forbids, stop and tell the user: it
   needs a decision (`atipspec decision <slug> --title ... --affects contract`)
   and possibly a contract change, never a workaround.
3. Write `plan.md`: `scope` in the frontmatter with the globs of the files the
   tasks will change; the Approach in a few paragraphs, citing the contract
   sections and decisions it relies on. Then tasks: one coherent change each,
   committable on its own, ordered by dependency; `Covers:` the REQ ids;
   `Tests:` or `Manual:` the AC ids each task validates, following the
   criterion's `[manual]` mark, until every criterion is listed once;
   `Verify:` real commands of this project, with every `require-command` of the
   contract in at least one task. `Verify: none` only when the proof is
   observation, saying what to observe.
4. `atipspec check <slug>` until it reports no plan errors.
5. If `approve_plan` is true in config.yaml, show the plan to the user and ask
   them to run `atipspec accept <slug> plan`; `atipspec build <slug>` refuses
   until then. Adding a task later invalidates that acceptance, so the user
   accepts again. Then `atipspec build <slug>`.

Rules: above `max_tasks` in config.yaml the delivery is too big for a working
day: propose splitting it under an initiative; no invented commands, find them
in package.json, Makefile, pyproject or CI; every REQ covered; choices with lasting consequences go to a decision, not
to the plan.
