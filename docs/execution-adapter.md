# Process execution adapter (development)

The guided skills work within the user's active coding assistant. For resumable
execution, `atipspec run <change>` uses an explicitly configured process adapter.
It never accepts the proposal/result or commits, pushes, merges or deploys.

The process runner currently supports POSIX systems. Guided mode is available
on other platforms. The runner is a foreground process with checkpoints, not an
installed background service. A supervisor can launch it, but ATIPSpec does not
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

Requests include `schema`, `delivery`, `role`, `instruction`, `agreement`,
versioned `context`, the assigned `task`, previous `findings`, a response contract
and permissions. Review requests include `review_packet`. The wrapper integrates
its chosen model and coding tools; the ATIPSpec core controls verification.

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
atipspec proposal my-change
atipspec accept my-change proposal
atipspec run my-change --budget 900 --timeout 300 --max-rounds 2
atipspec report my-change
atipspec accept my-change result
atipspec deliver my-change
```

`run.json` records phase, cumulative elapsed time, correction rounds and the
agreement digest. `progress.json` records completed task definitions. Both are
operational metadata excluded from the candidate fingerprint; evidence and
approvals remain checked independently. OS locks allow one runner per checkout.

Re-running a completed candidate reuses current final evidence and review.
After resolving a reported failure use `--resume`. Interrupted or timed-out
agent mutations require inspecting partial work and explicitly selecting
`--retry-interrupted`; they are not blindly replayed. The same approved version
retains its elapsed-time and correction budget across invocations. New approved
commitments start a new budget. Increasing limits is an explicit CLI choice.

External trust policies use their protected execution/acceptance workflow;
this initial runner does not bypass them with local approval records. Token and
cost metrics are reported as unavailable, not zero.

## Validation limits

The tests use real subprocess fixtures to verify execution, refusal before
approval, shared checks, review, reuse, interruption, drift, timeouts, retries
and locking. These fixtures are deterministic programs, not live model tests.
A native coding-client wrapper and live integration validation are still needed
before claiming an end-to-end unattended model integration.
