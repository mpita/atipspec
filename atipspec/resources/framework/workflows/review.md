# Phase review: a reviewer that did not write the code writes review.md

## Role, on the driver's side

You are the author handing over. You do not argue with the reviewer inside its
context and you never edit review.md. You fix, verify, commit and ask for a new
review. The reviewer's own role is in the packet's rubric: adversarial, judging
against the spec and the contract, one verdict per criterion.

## Steps

1. The packet is at the path printed above: rubric, contract, the living
   specs and decisions the delivery declares, spec, plan, deferred items,
   evidence summary, files outside the declared scope and the diff against
   the delivery base.
2. Launch the reviewer in a context that has not seen this conversation, with
   only the packet path:
   - Claude Code: the Agent tool, general-purpose, prompt
     "Read <packet path> and do what it says."
   - Codex, Cursor, Copilot, Gemini CLI, Antigravity: a sub-agent or background
     agent when the client offers one; otherwise ask the user to open a new
     session with that prompt.
3. `atipspec check <slug>`. A FAIL on a criterion or a blocker finding: fix the
   code, verify and commit again. Findings, never criteria, may instead go to
   deferred.md with a reason, followed by an enrolled risk owner approval with
   expiry. Both blocker and major findings block without that approval. Any
   change to the tree makes the review stale: run `atipspec review <slug>` and
   the reviewer again.
4. After `review_rounds` rounds (config.yaml) without a green check, stop and
   report to the user what remains.
5. Local green is `checked`, not human acceptance. Export `atipspec report <slug>`.
   The organization collects trusted CI attestations and product/engineering/QA
   approvals using its external policy. Never access a human's signing key or
   manufacture an approval. If trust is not configured, report the local result
   and the missing organization setup; do not claim verified or delivered.
6. After `atipspec check <slug> --policy <external-policy>` is verified,
   `atipspec deliver <slug> --policy <external-policy>`, commit and ask the user
   to merge the branch. STOP POINT 2.
