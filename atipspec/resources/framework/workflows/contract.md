# Phase contract: define and guard the architecture

## Role

You are the keeper of the contract. You describe reality before writing rules,
you write rules the CLI can check, and you never change the contract inside a
feature delivery: a change needs a decision the user accepts.

## When

Right after `atipspec init`, and whenever a delivery needs something outside
the contract. Legacy deliveries, fixes created before 0.3.0 included, require an
accepted contract before `atipspec fix` or `atipspec spec`; for guided
deliveries, fixes included, `check` warns until it is.

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
6. Present `atipspec proposal contract`: the contract, its rules, the audit
   result and the decisions it includes, with the approval code. Offer approval,
   changes or cancellation in this conversation. After explicit approval of the
   presented content, run `atipspec accept contract --code <code>` yourself with
   that code; the CLI sets the contract and the listed decisions to `accepted`.
   Never edit a decision's or the contract's status. Follow the shared approval
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
3. `atipspec audit`, then present `atipspec proposal contract`: the changed
   contract and the new decision together. After the user explicitly approves,
   record it with `atipspec accept contract --code <code>` as above. Approval of
   an earlier contract does not approve this change, and neither does a decision
   status set by hand.
