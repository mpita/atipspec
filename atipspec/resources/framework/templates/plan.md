---
title: "{{title}}"
scope: []
---

# Plan: {{title}}

## Approach

<!-- Brief solution, affected components, relevant risks and recovery if needed. -->

## Tasks

### T1: <!-- what changes -->

Covers: <!-- the IDs listed under `requirements` in spec.md that this task implements -->
Tests: <!-- the criteria of those requirements that this task's tests verify -->

## Final verification

<!-- Commands run once on the finished candidate, shared across mapped scenarios.
Add Report: .atipspec/tmp/junit.xml, a path git ignores that the Verify command
itself writes (verify deletes it first), and Proof entries naming real tests.
With require_proof: true or risk: high, name in Proof the test of every criterion under Tests.
Omit this section for manual-only changes and declare Manual + Verify: none per task.
A task-level Verify command is optional for focused development checks.
Task completion uses atipspec task-done, independently of the repository commit policy.
-->
Verify:
- `<!-- the project's relevant final checks -->`
