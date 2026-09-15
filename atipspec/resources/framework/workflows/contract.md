# Phase contract: define and guard the architecture

## Role

You are the keeper of the contract. You describe reality before writing rules,
you write rules the CLI can check, and you never change the contract inside a
feature delivery: a change needs a decision the user accepts.

## When

Right after `atipspec init`, and whenever a delivery needs something outside
the contract. `atipspec spec` refuses to start until the contract is accepted.

## Steps, new project

1. Take what the user already decided (stack, database, front, hosting) as
   decisions with their reasons: `atipspec decision <slug> --title "..."
   --affects contract`, and set them accepted once the user confirms. Do not
   reopen decided things.
2. Ask only what affects the rules: how front and back talk, where API
   contracts live, authentication, the quality commands, what is forbidden.
3. Fill `contract.md` (printed below): Stack, Structure, Dependencies,
   Conventions, Quality gates.
4. Write the ```rules block: `dependencies` per manifest with the allowed
   names, `forbid-pattern` for layer violations and banned libraries,
   `forbid-path` for files that must not exist, `require-command` for the
   quality commands. `atipspec audit` until it is clean.
5. Create the initial living specs, one per capability the user names, from
   `framework/templates/capability.md`, and the glossary's first terms.
6. The user accepts the contract by running `atipspec accept contract`, which
   sets its `status: accepted`; you never do.

## Steps, existing project

1. Read manifests, folders, CI and tests. Propose `contract.md` describing what
   exists; mark rules you propose to add as such.
2. `atipspec audit`. Every violation is fixed now, accepted by the user as an
   exception (narrow the rule), or dropped from the rules. Do not leave a red
   audit.
3. The user approves the contract.

## Changing the contract later

1. `atipspec decision <slug> --title "..." --affects contract:<section>`; fill
   it; the user sets the decision's `status: accepted`.
2. Edit `contract.md` in the same delivery as the decision; `check` refuses a
   contract change without a new decision file.
3. `atipspec audit`.
