# Contributing to AtipSpec

## Development setup

Python 3.11+, Git and OpenSSH with `ssh-keygen -Y` support, from a clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The runtime has no third-party dependencies. Framework resources ship inside
the package (`atipspec/resources/`), so both editable and regular installs work.

## Repository layout

- `atipspec/`: the CLI package.
  - `frontmatter.py`: the YAML subset used by artifacts and config.
  - `accept.py`: local acceptance records for spec, plan and contract.
  - `lint.py`: the form and vague-term checks on criteria. `junit.py`: JUnit XML reports for evidence per criterion.
  - `gitrepo.py`: git wrapper, tree fingerprint, task markers, worktrees.
  - `delivery.py`: parsers for spec, plan, review, deferred, evidence and roadmaps.
  - `contract.py`: the contract's rules: parsing, globs, manifests, evaluation.
  - `trust.py`, `assurance.py`, `providers.py`: external trust, signed evidence and read-only approvals.
  - `traceability.py`, `reporting.py`, `pilot.py`: durable IDs, acceptance dossiers and measured pilots.
  - `check.py`: the gate and derived status. `audit.py`: the repository-wide check.
  - `context.py`, `curate.py`: computed context and the living documents' upkeep.
  - `verify.py`, `review.py`, `deliver.py`, `creators.py`, `status.py`, `install.py`, `ui.py`.
  - `phases.py`: the phase commands: prerequisites, then workflow, rules and context.
  - `resources/skills/<name>/SKILL.md`: the umbrella skill and one skill per phase, installed in each client.
  - `resources/framework/rules.md`: the rules every phase command prints.
  - `resources/framework/workflows/`: one file per phase, each starting with its role.
  - `resources/framework/templates/`: spec, plan, fix-spec, fix-plan, brief, deferred, review, rubric,
    capability, contract, overview, glossary, decision, roadmap.
- `docs/`: the MkDocs Material site (`mkdocs.yml` at the root); `docs/design.md` is the reasoning. Not installed, not read by the model.
- `tests/`: standard-library tests in temporary git repositories.
- `scripts/smoke_test.py`: the installed CLI through a whole change.

## Making changes

Keep the skill, the workflows, the templates and the parsers consistent: a
heading or line shape the skill tells the model to write must be one `check`
parses, and the other way round. Every line installed into a project is loaded
by a model on every use, so add text only when it changes behavior.

Before proposing a change, run:

```bash
python -m unittest discover -s tests -t . -v
python scripts/smoke_test.py
git diff --check
```

Describe the behavior changed, why, and the validation performed. Keep
unrelated refactoring out of focused changes.
