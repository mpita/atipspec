---
title: "{{name}} architecture contract"
status: draft
---

# {{name}}: architecture contract

The rules every delivery follows. Changing this file requires an accepted
decision in `.atipspec/decisions/` in the same delivery.

## Stack

<!-- Languages, frameworks and their versions, database, runtime, hosting. -->

## Structure

<!-- Folders and layers, and who may depend on whom. -->

## Dependencies

<!-- Policy: who approves a new library, allowed sources, how versions are pinned. -->

## Conventions

<!-- Naming, error handling, logging, API style, tests, commits. -->

## Quality gates

<!-- The commands every delivery must pass, and where they run (local, CI). -->

## Rules

Machine-checked by `atipspec check` on every delivery and by `atipspec audit`
on the whole repository. One rule per line, shell quoting, `#` starts a comment.

```rules
# forbid-path <glob>                         no file may match       e.g. forbid-path "src/**/*.js"
# forbid-pattern <glob> <regex>              no matching file may contain the pattern
#                                            e.g. forbid-pattern "src/domain/**" "from app\.infrastructure"
# dependencies <manifest> <name-or-glob>...  the manifest may only declare these
#                                            e.g. dependencies package.json react react-dom "@types/*"
# require-command <command>                 every plan verifies with it, e.g. require-command "npm test"
```
