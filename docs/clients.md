# Clients

AtipSpec runs inside the coding client you already use. `atipspec init`
installs the same skills where each client discovers them; the CLI is the same
everywhere. What differs is how you invoke a skill and how the reviewer gets a
fresh context.

## One skill per phase

Each phase has its own skill, named after the phase, plus an umbrella skill
for status and questions about the flow:

| Skill | What it does |
| --- | --- |
| `atipspec-contract` | define or change the architecture contract |
| `atipspec-explore` | brief an idea that is not clear yet |
| `atipspec-spec` | requirements and acceptance criteria; ends at stop point 1 |
| `atipspec-fix` | a defect: one regression criterion and a one-task plan, no interview |
| `atipspec-plan` | tasks the gate can prove |
| `atipspec-build` | code, evidence and one commit per task |
| `atipspec-review` | the adversarial review in a fresh context |
| `atipspec-deliver` | merge into the living spec and archive; ends at stop point 2 |
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

    **Reviewer in a fresh context**: the model uses the Agent tool with a
    general-purpose subagent and the prompt "Read
    `.atipspec/tmp/password-reset-review-packet.md` and do what it says."
    The subagent never sees the conversation.

=== "Codex"

    **Invoke**

    ```text
    $atipspec-spec password-reset: users should be able to reset a forgotten password
    ```

    **Reviewer**: a sub-agent when your Codex version offers one; otherwise
    open a second Codex session in the project and paste the packet prompt.

=== "Cursor"

    **Invoke**: pick *atipspec-spec* (or the phase you need) in the skill
    picker, or ask the Agent to use it and describe the delivery.

    **Reviewer**: a background agent with the packet prompt, or a new chat
    that has not seen the work.

=== "GitHub Copilot"

    **Invoke**: in agent mode, ask Copilot to use the atipspec-spec skill and
    describe the delivery.

    **Reviewer**: a new agent session with the packet prompt.

=== "Gemini CLI"

    **Invoke**: check `/skills list`, then ask it to use atipspec-spec.
    Project skills require a trusted workspace.

    **Reviewer**: a new session with the packet prompt.

=== "Antigravity"

    **Invoke**: ask the agent to use the atipspec-spec skill.

    **Reviewer**: a sub-agent or a new session with the packet prompt.

## What the model loads

A phase skill is under fifteen lines. The phase command prints everything
else: the phase header with the derived status, the phase's workflow from
`.atipspec/framework/workflows/`, the shared rules from
`.atipspec/framework/rules.md`, and the output of `atipspec context <slug>`.
The model never browses `specs/` or `archive/`, and never reads a workflow
for a phase it may not enter.

## Language

English is the primary language; Spanish and Portuguese are supported.
Framework files, skills and the CLI output stay in English: one source, read
by a model that follows English instructions and answers you in yours. What a
person reads follows `language` in `config.yaml`: the acceptance dossier from
`atipspec report`, and this site, which exists in the three languages with a
switcher. What the model writes in your language is understood by the CLI:
section names such as `Preguntas abiertas` or `Questões em aberto`, empty
markers such as `Ninguna` or `Nenhuma`, and the criterion lint's triggers and
vague terms. IDs, template headings and statuses stay as the templates define
them, because the CLI parses them.

## Upgrading

After upgrading the CLI, run in each project:

```bash
atipspec install --update
```

It replaces the framework and skill files that differ from the installed
version and never touches anything else. An installation from before 0.1.0
had a single `atipspec` skill; the update replaces its content and adds the
phase skills next to it.
