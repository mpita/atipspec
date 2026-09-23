# Configuration

`.atipspec/config.yaml`, written by `init`:

```yaml
name: shop
language: es
approve_plan: true
review_rounds: 2
context_budget: 800
strict_scope: false
criteria_syntax: ears
strict_criteria: false
max_requirements: 5
max_tasks: 8
max_age_hours: 48
```

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | folder name | project name, shown by `status` |
| `language` | `en` | language the model writes artifacts in; `en`, `es` and `pt` also drive the criterion lint, the section names the parser accepts and the acceptance dossier. Another code works with the English tables, and `audit` says so |
| `approve_plan` | `true` | `atipspec build` refuses until explicit human plan approval is recorded (included in guided proposal approval) |
| `review_rounds` | `2` | review rounds without a green check before the model stops and reports |
| `context_budget` | `800` | lines; `atipspec context` warns above it |
| `strict_scope` | `false` | when true, a changed file outside the plan's `scope` is an error instead of a warning |
| `criteria_syntax` | `ears` | `ears` warns about criteria that do not start with a trigger or carry a shall; `free` turns that check off |
| `strict_criteria` | `false` | when true, the form and vague-term checks on criteria are errors and block the acceptance |
| `max_requirements` | `5` | `check` warns when a spec has more requirements: a delivery should fit in a working day |
| `max_tasks` | `8` | `check` warns when a plan has more tasks |
| `max_age_hours` | `48` | `status` warns when a delivery has been open longer than this, in wall-clock hours |
| `system` | unset | path to a checkout of the system repository; its `contract.md` and `glossary.md` join every context |

Only `name` and `language` are managed by `atipspec init`; edit the rest by
hand. `init --language en` on an existing project keeps the other keys.

## `.atipspec/.gitignore`

Created by `init`; ignores `tmp/`, where review packets are written.
Everything else under `.atipspec/` is meant to be committed: the contract,
the living specs, the deliveries with their evidence and reviews, the
archive.

## Environment

| Variable | Effect |
| --- | --- |
| `NO_COLOR` | disables colors in the terminal output |
| `TERM=dumb` | same |

## Organization trust

Local project settings guide the assistant; they cannot relax trusted acceptance.
`approve_plan: false` skips conversational ceremony, not the trusted engineering
approval requirement. The external TOML policy controls roles, public keys,
corporate rules and provider identities. It must live outside the candidate.

`ATIPSPEC_TRUST_POLICY` selects that policy; `ATIPSPEC_POLICY_SHA256` pins its
contents. Use protected organization configuration, not project-provided values.
GitHub/GitLab adapters use read-only `GITHUB_TOKEN` / `GITLAB_TOKEN` in the trusted
collector. The verification runner removes those credentials from command
environments. See [enterprise acceptance](../enterprise.md).
