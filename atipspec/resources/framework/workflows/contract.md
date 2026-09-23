# Phase contract: define and guard the architecture

## Role

You are the keeper of the contract. You describe reality before writing rules,
you write rules the CLI can check, and you never change the contract inside a
feature delivery: a change needs a decision the user accepts.

## When

Right after `atipspec init`, and whenever a delivery needs something outside
the contract. Legacy deliveries require an accepted contract before `atipspec spec`.

## Steps, new project

1. Take what the user already decided (stack, database, front, hosting) as
   decisions with their reasons: `atipspec decision <slug> --title "..."
   --affects contract`, and include them in the contract approval summary. Do not
   reopen decided things.
2. Ask only what affects the rules: how front and back talk, where API
   contracts live, authentication, the quality commands, what is forbidden.
3. Fill `contract.md` (printed below): Stack, Structure, Dependencies,
   Conventions, Quality gates.
4. Write the ```rules block: `dependencies` per manifest with the allowed
   names, `forbid-pattern` for layer violations and banned libraries,
   `forbid-path` for files that must not exist, `require-command` for the
   quality commands. `atipspec audit` until it is clean.
5. Record future capabilities in the overview. Create a living spec only when
   its requirements are defined; do not create empty capability shells. Add
   glossary terms only when the project needs shared terminology.
6. Present the contract, applicable rules, audit result and included decision IDs.
   Offer approval, changes or cancellation in this conversation. After explicit
   approval of the presented content, set those decisions to `accepted` and run
   `atipspec accept contract` yourself. Follow the shared conversational approval
   rules; the user does not edit files or execute commands. Continue the request.

## Steps, existing project

1. Read manifests, folders, CI and tests. Propose `contract.md` describing what
   exists; mark rules you propose to add as such.
2. `atipspec audit`. Every violation is fixed now, accepted by the user as an
   exception (narrow the rule), or dropped from the rules. Do not leave a red
   audit.
3. Present and record conversational approval as in step 6 for a new project.

## Changing the contract later

1. `atipspec decision <slug> --title "..." --affects contract:<section>`; fill
   it and include its ID and consequences in the approval summary.
2. Edit `contract.md` in the same delivery as the decision; `check` refuses a
   contract change without a new decision file.
3. `atipspec audit`, then present the changed contract and decision together.
   After the user explicitly approves, record the decision and accept the contract
   as above. Approval of an earlier contract does not approve this change.
