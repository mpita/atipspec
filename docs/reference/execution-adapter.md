# Execution adapter

The guided skills work within the user's active coding assistant. For resumable
execution, `atipspec run <slug>` uses an explicitly configured process adapter.
It never accepts the proposal or the result, and never commits, pushes, merges
or deploys. It runs guided deliveries only, and refuses under an external
trust policy, selected or required.

The process runner needs a POSIX system to stop an adapter's processes: Linux,
macOS or WSL. Elsewhere `run` refuses before it reads the delivery or writes anything;
continue the delivery in the guided conversation, which has the same phases
and the same gate. The runner is a foreground process with checkpoints, not an
installed background service. A supervisor can launch it, but AtipSpec does not
claim persistence after the host process stops.

## Configuration

Create `.atipspec/adapter.json` before approving the proposal:

```json
{
  "schema": 1,
  "name": "my-agent-wrapper",
  "command": ["/absolute/path/to/wrapper"],
  "isolated_review": false
}
```

The executable runs in the project root with one JSON request on stdin. It must
write exactly one JSON response to stdout; diagnostic output goes to stderr.
The command is an argv array, not shell code. Changes to adapter configuration
invalidate guided proposal approval. The wrapper must enforce the requested
permissions and use a new model conversation for review before declaring
`isolated_review: true`. A fresh operating-system process alone cannot prove
model-context isolation. This protocol is not a sandbox for arbitrary programs.

The runner holds the review's `session:` to that declaration. A review that
says `session: isolated` from an adapter without `isolated_review: true` fails
the run. When the delivery requires an isolated review (`risk: high`, or
`require_isolated_review: true` in `config.yaml`) and the adapter does not
declare it, the run stops at `needs_decision` before calling any role, so no
work is done that only an isolated review could accept: run the delivery in
guided mode and review it in an isolated session with `atipspec review
<slug>`, or configure an adapter that isolates the reviewer.

Requests include `schema`, `delivery`, `role`, `instruction`, `agreement`,
versioned `context`, the assigned `task`, previous `findings`, a response contract
and permissions. Review requests include `review_packet`. The wrapper integrates
its chosen model and coding tools; the AtipSpec core controls verification.

Responses:

```json
{"schema": 1, "status": "done", "summary": "Implemented the approved behavior"}
```

`needs_decision`, `blocked` and `failed` are also valid statuses and must explain
the concrete issue in `summary`. Review completion additionally returns
`review_markdown` matching the packet's criterion IDs and candidate tree. The
reviewer must not modify project files. The core validates the response shape,
detects agreement drift and runs its own evidence/review gate. A `done` message
does not establish correctness or human acceptance.

## Operation and recovery

```sh
atipspec adapter
atipspec proposal my-change                       # shows the approval code
atipspec accept my-change proposal --code <code>  # after the human approves
atipspec run my-change --budget 900 --timeout 300   # --max-rounds: at most, and by default, review_rounds less one
atipspec report my-change                         # shows the result's code
atipspec accept my-change result --code <code>    # after the human accepts
atipspec deliver my-change
```

`atipspec run` prints its state as JSON and exits 0 at `ready_for_acceptance`
or `accepted`, 2 at any other state: `awaiting_approval`, `needs_decision`,
`blocked` or `failed`, with the reason. `run.json` records phase, cumulative
elapsed time, correction rounds and the agreement digest. `progress.json` records completed task definitions. Both are
operational metadata excluded from the candidate fingerprint; evidence and
approvals remain checked independently. OS locks allow one runner per checkout.

Re-running a completed candidate reuses current final evidence and review.
After resolving a reported failure use `--resume`. Interrupted or timed-out
agent mutations require inspecting partial work and explicitly selecting
`--retry-interrupted`; they are not blindly replayed. The same approved version
retains its elapsed-time and correction budget across invocations. New approved
commitments start a new budget. Increasing the time limits is an explicit CLI
choice. `--max-rounds` counts every automatic correction, whether a review or a
check asked for it; it defaults to `review_rounds` in `config.yaml` less one,
as each correction is reviewed again, and cannot exceed it, since more rounds
are the human's decision. The reviews the runner asks for count in
`review-rounds.json`, as `atipspec review` counts them: each review of another
candidate, the first included; once `review_rounds` are counted the runner
stops at `needs_decision`.

External trust policies use their protected execution/acceptance workflow;
this initial runner does not bypass them with local approval records. Token and
cost metrics are reported as unavailable, not zero.

## Validation limits

The tests use real subprocess fixtures to verify execution, refusal before
approval, shared checks, review, reuse, interruption, drift, timeouts, retries
and locking. These fixtures are deterministic programs, not live model tests.
A native coding-client wrapper and live integration validation are still needed
before claiming an end-to-end unattended model integration.
