# Phase plan: prepare implementation and verification together

Act as technical designer and test specialist. Reuse the architecture and test
facilities of the project. Inspect actual commands in its scripts, build files
and CI. Name affected paths in scope, explain the approach briefly and surface
consequential choices. Scale detail to risk rather than a fixed document count.

Tasks list Covers (REQ IDs), Tests (automated AC IDs) and Manual (observed AC IDs).
Use a shared `## Final verification` section with Verify commands for the finished
candidate. Add Report and Proof there to link scenarios to actual JUnit tests.
Task-level Verify commands are optional development checks. Manual-only tasks can
use Verify: none and describe the observation. Contract-required commands belong
in final verification. Plan for recovery when migrations or destructive changes
make it necessary; include isolation negatives for permissions/multitenancy.

Run `atipspec proposal <slug>` to inspect completeness and the combined agreement.
Resolve contradictions before presenting it. The human accepts the proposal once;
implementation can then continue through tests and review without phase approvals.
Scope, approach and final verification remain bound to approval. In guided plans
with final verification, operational task decomposition may evolve within those
commitments without another approval; coverage and scope are still checked.
Changes to the approved commitments need an explicit decision before execution.
