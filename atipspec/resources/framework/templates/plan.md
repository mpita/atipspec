---
title: "{{title}}"
scope: []
---

# Plan: {{title}}

<!--
scope: globs of the files the tasks will change, e.g. ["shop/auth/**", "tests/auth/**"];
`**` crosses directories, `*` does not. `check` warns about touched files outside them,
deletions included (error with strict_scope: true), and the reviewer sees them.
-->

## Approach

<!-- What changes where and why this shape. Name the living specs and decisions you rely on. -->

## Tasks

<!--
Small, ordered tasks. Each one:
  Covers: the REQ ids it implements (every REQ must be covered by at least one task)
  Tests: AC ids verified by the commands; Manual: AC ids requiring human observation
  Verify: commands that prove it, run from the project root by `atipspec verify`
  Report: optional, the JUnit XML a Verify command writes (pytest --junitxml, jest-junit, surefire...)
  Proof: optional, `- AC-001: test id` per criterion; `check` requires that test to have run and passed
A task is done only when a commit carries [{{slug}}:Tn] in its message.
-->

### T1: <!-- what changes -->

Covers: REQ-001
Tests: AC-001
Report: <!-- e.g. .atipspec/tmp/junit.xml -->
Proof:
- AC-001: <!-- e.g. tests/auth/test_reset.py::test_link_sent -->
Verify:
- `<!-- e.g. python -m pytest -q tests/auth --junitxml .atipspec/tmp/junit.xml -->`
