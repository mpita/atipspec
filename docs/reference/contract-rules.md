# Contract rules

`contract.md` is prose for the model plus one fenced block the CLI evaluates:

````markdown
```rules
dependencies pyproject.toml django psycopg "pytest*"
forbid-pattern "shop/domain/**" "from shop\.infrastructure"   # DEC-002 layering
forbid-path "web/src/**/*.js"                                 # TypeScript only
require-command "python -m pytest -q"
```
````

One rule per line, shell-style quoting, `#` starts a comment that is shown
as the reason in reports.

## Rules

### `forbid-path <glob>`

No file may match the glob. `check` looks at the files the delivery touched;
`audit` at every tracked and untracked file outside `.atipspec/`.

### `forbid-pattern <glob> <regex>`

No file matching the glob may contain a line matching the regular expression
(Python syntax). The first matching line is reported with its number. Use it
for layering (`"from shop\.infrastructure|^from django"` in the domain), for
banned libraries, or for patterns your conventions forbid.

### `dependencies <manifest> <name-or-glob>...`

The manifest may only declare the listed dependencies. Names are compared in
lowercase; globs like `"@types/*"` or `"pytest*"` are allowed. In `check` the
rule runs when the manifest is among the files the delivery touched; in
`audit` it always runs. Supported manifests:

| File | Read from |
| --- | --- |
| `pyproject.toml` | `project.dependencies`, `project.optional-dependencies`, `dependency-groups`, Poetry dependencies and groups |
| `requirements*.txt` | one requirement per line, `-r`/`-e` lines skipped |
| `package.json` | dependencies, devDependencies, peerDependencies, optionalDependencies |
| `Cargo.toml` | dependencies, dev-dependencies, build-dependencies |
| `go.mod` | `require` lines and blocks |

### `require-command <command>`

Every delivery's plan must include the command, verbatim modulo whitespace and
shell quoting, in at least one task's `Verify:`, alone or followed by more
arguments: with `require-command "python -m pytest"`, the line
`python -m pytest -q --junitxml .atipspec/tmp/junit.xml` that writes a
`Report:` counts. A line that follows the command with a control operator
(`|`, `||`, `&&`, `;`, `&`), a redirection (`>`, `<`, `2>&1`) or a command
substitution (`$(...)`, backquotes) does not count: `python -m pytest || true`
and `python -m pytest | tail -1` pass whether the tests do or not. On
Windows, where `verify` runs the line with `cmd.exe`, which reads neither
single quotes nor backslashes as quotes, a line with `&`, `|`, `<`, `>`, `^`,
`%` or a double quote anywhere after the command does not count either, even
inside quotes sh would honor. The
arguments are not judged: one that narrows the run, such as `-k smoke` or a
single test file, still counts, since telling it from `--junitxml` depends on
the tool; the human sees each `Verify:` line in the proposal. This is how the
quality gates of the contract become evidence on every delivery.

## Globs

`**` crosses directories, `*` and `?` do not. Patterns are anchored to the
whole path relative to the project root: `src/**/*.js` matches `src/c.js`
and `src/a/b/c.js`; `src/*.js` matches only the first.

## Where the rules apply

| | `atipspec check <slug>` | `atipspec audit` |
| --- | --- | --- |
| Files | changed since the delivery's base, plus untracked | all tracked and untracked, outside `.atipspec/` |
| `dependencies` | when the manifest changed | always |
| `require-command` | the delivery's plan | not applicable |
| Result | errors in the delivery's gate | errors, exit 1 |

## Changing the contract

A delivery whose diff touches `.atipspec/contract.md` is red unless a new
file under `.atipspec/decisions/` is part of the same diff and the contract's
recorded acceptance includes it. Create it with `atipspec decision <slug>
--title ... --affects contract:<section>`; the assistant presents `atipspec
proposal contract` and, after your explicit approval, records it with
`atipspec accept contract --code <code>`, which sets the decision's status. A status set to
`accepted` by hand does not count. With an external trust policy, the decision
needs its signed engineering approval instead.
