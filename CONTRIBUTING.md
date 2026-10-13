# Contributing to AtipSpec

## Development setup

Python 3.11+, Git and OpenSSH with `ssh-keygen -Y` support, from a clone:

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -e .
```

The runtime has no third-party dependencies. Framework resources ship inside
the package (`atipspec/resources/`), so both editable and regular installs work.

## Repository layout

- `atipspec/`: the CLI package.
  - `cli.py`: the commands and their options. `phases.py`: the phase commands: prerequisites, then
    workflow, rules and context.
  - `frontmatter.py`: the YAML subset used by artifacts and config. `project.py`: the project, its
    policies and the tree fingerprint.
  - `delivery.py`: parsers for spec, plan, review, deferred, evidence and roadmaps. `specs.py`: guided
    deliveries' canonical requirements in `specs/`, `baseline.json` and `spec-bind`.
    `migration.py`: imports for `spec-bind` and `atipspec migrate`.
  - `creators.py`: `new`, `decision` and `initiative` from the templates.
  - `proposal.py`: the proposal and contract views with their approval codes. `accept.py`: local
    acceptance records (proposal, result, spec, plan, contract), approval codes and the channel.
  - `progress.py`: `task-done` records. `verify.py`: Verify commands and evidence. `junit.py`: JUnit
    XML reports for evidence per criterion.
  - `review.py`: the review packet. `rounds.py`: review rounds. `pointers.py`: what a PASS verdict
    points to.
  - `check.py`: the gate and derived status. `risk.py`: what each risk level asks. `lint.py`: the form,
    vague-term and fit-criterion checks on requirements and criteria. `locale.py`: the language tables.
  - `contract.py`: the contract's rules: parsing, globs, manifests, evaluation. `audit.py`: the
    repository-wide check.
  - `deliver.py`: the living spec merge and the archive. `merge.py`: `merge-check`.
  - `teams.py`: `teams.json`, the board, dependencies and contract pins. `integration.py`: what the
    integration branch brought. `tickets.py`: ticket keys and links. `traceability.py`: durable IDs.
  - `runner.py`, `adapter.py`, `roles.py`: the process runner, its adapter protocol and the guided roles.
  - `trust.py`, `assurance.py`, `providers.py`, `attestation.py`: external trust, approval subjects,
    signed evidence, read-only provider approvals and artifact attestations.
  - `reporting.py`, `pilot.py`: acceptance dossiers and measured pilots.
  - `context.py`, `curate.py`: computed context and the living documents' upkeep.
  - `gitrepo.py`: git wrapper, tree fingerprint, task markers, worktrees.
  - `status.py`, `install.py`, `ui.py`, `enterprise.py`: status, installation, the terminal UI and the
    enterprise examples.
  - `resources/skills/<name>/SKILL.md`: the umbrella skill and one skill per phase, installed in each client.
  - `resources/framework/rules.md`: the rules every phase command prints.
  - `resources/framework/workflows/`: one file per phase; explore, fix, contract and curate open with
    the role the model adopts.
  - `resources/framework/templates/`: spec, plan, fix-spec, fix-plan, brief, deferred, review, rubric,
    capability, contract, overview, glossary, decision, roadmap.
  - `resources/enterprise/`: the examples `enterprise-init` writes.
- `docs/`: the MkDocs Material site (`mkdocs.yml` at the root); `docs/design.md` is the reasoning. Not installed, not read by the model.
- `tests/`: standard-library tests in temporary git repositories.
- `scripts/smoke_test.py`: the installed CLI through a whole change.

## Making changes

Keep the skill, the workflows, the templates and the parsers consistent: a
heading or line shape the skill tells the model to write must be one `check`
parses, and the other way round. Every line installed into a project is loaded
by a model on every use, so add text only when it changes behavior.

AtipSpec runs on Linux, macOS and Windows, and CI runs the tests on Windows
with its own code page. Name the encoding of every text read and write,
`encoding="utf-8"`, add `newline="\n"` when writing, and give `subprocess`
calls with `text=True` an `encoding`; `tests/test_portability.py` checks the
package and `scripts/` for it. A Verify command in a test runs in `cmd.exe`
on Windows: use `true`, `false` or `tests.helpers.python_command`. A test that
names no newline writes CRLF there; `python -m tests.windows_text` runs the
suite that way on any platform, as CI does on Linux. The suite's repositories
use the Git for Windows default, `core.autocrlf=true`, on every platform: git
commits text with LF and checks it out with CRLF.

The documentation is part of the change. Every behavior, command, option or
message a change adds or alters is described in the English pages of `docs/`
and in `README.md` in the same change, and in their Spanish (`.es.md`) and
Portuguese (`.pt.md`) translations. English is the source: a translation keeps
its code blocks, its ``### `atipspec ...` `` headings, IDs and file names as
the English page has them. `tests/test_docs.py` checks that every command and
option the documentation cites exists, that the CLI reference covers every
command and option in the three languages, that every page is in the
navigation and translated, and that the translations cite the same commands.

Before proposing a change, run:

```bash
python -m unittest discover -s tests -t . -v
python scripts/smoke_test.py
git diff --check
mkdocs build --strict
```

Describe the behavior changed, why, and the validation performed. Keep
unrelated refactoring out of focused changes.
