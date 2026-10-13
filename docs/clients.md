# Clients

AtipSpec runs inside the coding client you already use. `atipspec init`
installs the same skills where each client discovers them; the CLI is the same
everywhere. What differs is how you invoke a skill and how the reviewer gets an
isolated session.

## One skill per phase

Each phase has its own skill, named after the phase, plus an umbrella skill
for status and questions about the flow:

| Skill | What it does |
| --- | --- |
| `atipspec-contract` | define or change the architecture contract |
| `atipspec-explore` | brief an idea that is not clear yet |
| `atipspec-spec` | the interview and the scenarios in the living spec; with the plan, the proposal you approve at stop point 1 |
| `atipspec-fix` | a defect: the accepted requirement it breaks, corrected with a regression criterion, and a one-task plan, no interview |
| `atipspec-plan` | approach, scope, tasks and tests, presented with the proposal |
| `atipspec-build` | code and tests, each task recorded with `task-done`, then the final verification |
| `atipspec-review` | the adversarial review in an isolated session |
| `atipspec-deliver` | the result for your acceptance at stop point 2, then the archive into the living spec |
| `atipspec-curate` | keep the project's context small |
| `atipspec-ship` | run the remaining phases, stopping only where the CLI stops |
| `atipspec` | status, help, and which phase comes next |

A phase skill is a few lines: run the phase command, do what it prints, and
stop if it refuses. The CLI decides whether the phase may start, so the active
phase is never the model's interpretation of your request.

| Client | `--client` | Skills installed under |
| --- | --- | --- |
| Claude Code | `claude` | `.claude/skills/atipspec*/SKILL.md` |
| Codex | `codex` | `.agents/skills/atipspec*/SKILL.md` |
| Cursor | `cursor` | `.cursor/skills/atipspec*/SKILL.md` |
| GitHub Copilot | `github-copilot` | `.github/skills/atipspec*/SKILL.md` |
| Antigravity | `antigravity` | `.agents/skills/atipspec*/SKILL.md` |
| Gemini CLI | `gemini` | `.gemini/skills/atipspec*/SKILL.md` |

Codex and Antigravity share one folder. Some clients also discover other
clients' skill folders; if you see duplicates, install only one.

=== "Claude Code"

    **Invoke**

    ```text
    /atipspec-contract
    /atipspec-spec password-reset: users should be able to reset a forgotten password
    /atipspec-ship password-reset
    ```

    **Reviewer in an isolated session**: the model uses the Agent tool with a
    general-purpose subagent and the prompt "Read
    `.atipspec/tmp/password-reset-review-packet.md` and do what it says."
    The subagent never sees the conversation, so it writes `session:
    isolated`.

=== "Codex"

    **Invoke**

    ```text
    $atipspec-spec password-reset: users should be able to reset a forgotten password
    ```

    **Reviewer**: a sub-agent when your Codex version offers one; otherwise
    open a second Codex session in the project and paste the packet prompt.
    Either writes `session: isolated`; a review written in the same session
    writes `session: shared`.

=== "Cursor"

    **Invoke**: pick *atipspec-spec* (or the phase you need) in the skill
    picker, or ask the Agent to use it and describe the delivery.

    **Reviewer**: a background agent with the packet prompt, or a new chat
    that has not seen the work: `session: isolated`. In the same chat:
    `session: shared`.

=== "GitHub Copilot"

    **Invoke**: in agent mode, ask Copilot to use the atipspec-spec skill and
    describe the delivery.

    **Reviewer**: a new agent session with the packet prompt: `session:
    isolated`. In the same session: `session: shared`.

=== "Gemini CLI"

    **Invoke**: check `/skills list`, then ask it to use atipspec-spec.
    Project skills require a trusted workspace.

    **Reviewer**: a new session with the packet prompt: `session: isolated`.
    In the same session: `session: shared`.

=== "Antigravity"

    **Invoke**: ask the agent to use the atipspec-spec skill.

    **Reviewer**: a sub-agent or a new session with the packet prompt:
    `session: isolated`. In the same session: `session: shared`.

The reviewer declares `session:` in `review.md`; nothing in the client proves
it. A shared review is a warning, and an error with `risk: high` or
`require_isolated_review` (see [review](flow/review.md)): then ask for a new
session for the reviewer.

## What the model loads

A phase skill is a few lines. The phase command prints everything
else: the phase header with the derived status, the phase's workflow from
`.atipspec/framework/workflows/`, the shared rules from
`.atipspec/framework/rules.md`, and the output of `atipspec context <slug>`.
The model reads `specs/` only as the context selects it and writes the
living spec it changes, never reads the archive wholesale, and never reads a
workflow for a phase it may not enter.

## Approval permission rules

You approve in the conversation, and the assistant records it with
`atipspec accept ... --code <code>`. Where the client can be configured to ask
you before that command runs, `init` and `install` configure it, and the record
says so in its `channel`:

| Client | What AtipSpec installs | Channel of an assistant's `accept` |
| --- | --- | --- |
| Claude Code | `.claude/settings.json`: `ask` for `Bash(*atipspec accept *)`, and for `Edit` on `.github/workflows/**`, `.gitlab-ci.yml` and `.claude/settings*.json`; `deny` of `Edit` on `.atipspec/deliveries/*/approvals/**`, `.atipspec/deliveries/*/evidence/**`, `.atipspec/deliveries/*/review-rounds.json`, `.atipspec/approvals/**` and `.atipspec/archive/**` | `client-permission` while those rules are intact and no project hook answers the prompt, `assistant` otherwise |
| Codex | nothing yet: project rules in `.codex/rules/*.rules` can ask before a command prefix, but they load only for a trusted project layer and their behavior with `approval_policy = never` is not verified | `assistant` |
| Cursor | nothing: `.cursor/cli.json` has allow and deny lists, no ask, and only for its CLI | `assistant` |
| GitHub Copilot | nothing: VS Code's terminal auto-approve setting is best effort, not a security boundary | `assistant` |
| Gemini CLI | nothing: its policy engine can ask, but workspace policies do not load today | `assistant` |
| Antigravity | nothing: its permission rules are global or set in the IDE | `assistant` |

How the Claude Code rules behave:

- Claude Code evaluates `deny`, then `ask`, then `allow`; an `allow` rule never
  overrides them, and `ask` rules ask in every permission mode. In modes that
  cannot ask, the command is denied, so nothing is recorded.
- The prompt asks you to allow the exact command, with the code of the content
  you approved; it confirms that same approval, it is not a second one.
- The `deny` rules cover Claude Code's edit tools, the file commands it
  recognizes and redirections; versions before 2.1.210 treat `Edit` rules and
  redirections differently. They do not cover arbitrary programs, such as a
  script that writes a file.
- The `ask` rules for `Edit` on `.github/workflows/**`, `.gitlab-ci.yml` and
  `.claude/settings*.json` make Claude Code's edit tools ask you before they
  change the CI that runs `merge-check`, or the settings that hold these rules.
  Unlike the `deny` rules, they do not stop a redirection: with Claude Code
  2.1.296 in `acceptEdits` mode, a Bash command the settings allow, such as
  `echo`, `printf` or `python3 -c`, wrote to `.github/workflows/` with a
  redirection without asking, and any program the session may run can write
  there. The protection that holds is `merge-check`: it blocks a branch that
  changes the CI, the client settings or the skills outside a delivery, and
  the CI itself is protected on the provider (see [CI before the
  merge](enterprise.md#ci-before-the-merge)).
- The rules load from the project's `.claude/settings.json`: open the session at
  the project root. A session opened in a subdirectory, or in a parent folder
  or another repository that enters the project with `cd` (some workflow and
  subagent sessions do), `--setting-sources` without `project`, user or
  managed settings, and hooks there that answer permission requests bypass
  them without the CLI being able to tell. A `PreToolUse` or
  `PermissionRequest` hook for Bash in the project's `.claude/settings.json`
  or `.claude/settings.local.json` is visible: `status` and `audit` name it
  and the channel is `assistant`. Sessions run through the Agent SDK, which
  loads no project settings unless its program asks and hands the prompts to
  that program, and `claude -p` record `assistant`.
- The merge keeps every other key and entry, adds only the missing rules, and
  writes nothing when they are all present. A file that is not plain JSON (with
  comments, say) or a symlink is left alone, and the rules are printed to add by
  hand. Removing Claude Code from the `init` menu removes only these rules.
- `audit` warns when the rules are missing or incomplete, naming the ones
  missing, and `status` prints an `approvals:` line with their state. Until
  every rule is there, acceptances are recorded as channel `assistant`.
  `atipspec install --update` repairs them.

`client-permission` means the rules that make Claude Code ask you are in this
project, not that the session loaded them or that the CLI saw you confirm. In
a terminal without an agent marker, `accept` asks you to type the code
(channel `terminal`); an agent can remove its markers and answer that prompt
from a terminal it creates, so neither channel identifies who approved: they
describe how the command ran. For authenticated approvals, use an
[external trust policy](enterprise.md).

## Language

English is the primary language; Spanish and Portuguese are supported.
Framework files, skills and the CLI output stay in English: one source, read
by a model that follows English instructions and answers you in yours. What a
person reads follows `language` in `config.yaml`: the acceptance dossier from
`atipspec report`, and this site, which exists in the three languages with a
switcher. What the model writes in your language is understood by the CLI:
section names such as `Intención` or `Intenção`, `Fuera de alcance` or `Fora do
escopo`, `Atributos de calidad` or `Atributos de qualidade`, `Preguntas
abiertas` or `Questões em aberto`; empty markers such as `Ninguna` or
`Nenhuma`; labels such as `Por qué:` or `Observado:`; and the lint's triggers,
vague terms and measurement words. IDs, template headings and statuses stay as
the templates define them, because the CLI parses them.

## Upgrading

After upgrading the CLI, run in each project:

```bash
atipspec install --update
```

It replaces the framework and skill files that differ from the installed
version, removes the files under `.atipspec/framework/` that version does not
install, merges the missing Claude Code permission rules into
`.claude/settings.json` without removing anything, and never touches anything
else. Until it runs, `audit`, `check` and `merge-check` fail: every phase
prints the framework's rules and workflows to the agent, so they must be the
ones the installed version ships, as the skills are. Pin the same version in
the CI that runs `merge-check`. An installation from before 0.1.0
had a single `atipspec` skill; the update replaces its content and adds the
phase skills next to it.
