import json
import os
from pathlib import Path
import tempfile
import unittest

from atipspec.contract import (evaluate, glob_to_regex, manifest_dependencies, matches,
                               missing_commands, parse_contract)

CONTRACT = """# Contract

## Rules

```rules
# comment line
forbid-path "src/**/*.js"                       # TypeScript only
forbid-pattern "src/domain/**" "from app\\\\.infra"   # layering (DEC-002)
dependencies pyproject.toml django psycopg "pytest*"
require-command "python -m pytest -q"
bogus-rule x
forbid-pattern "src/**" "("
```
"""


class RuleParsingTests(unittest.TestCase):
    def test_rules_reasons_and_problems(self):
        contract = parse_contract(CONTRACT)
        self.assertEqual([rule.kind for rule in contract.rules],
                         ["forbid-path", "forbid-pattern", "dependencies", "require-command"])
        self.assertEqual(contract.rules[0].reason, "TypeScript only")
        self.assertEqual(contract.rules[1].args, ["src/domain/**", "from app\\.infra"])
        self.assertEqual(contract.rules[2].args, ["pyproject.toml", "django", "psycopg", "pytest*"])
        self.assertEqual(len(contract.problems), 2)
        self.assertIn("unknown rule", contract.problems[0])
        self.assertIn("invalid regex", contract.problems[1])
        self.assertEqual(parse_contract("# no block\n").rules, [])

    def test_globs(self):
        self.assertTrue(matches("src/**/*.js", "src/a/b/c.js"))
        self.assertTrue(matches("src/**/*.js", "src/c.js"))
        self.assertFalse(matches("src/*.js", "src/a/c.js"))
        self.assertTrue(matches("@types/*", "@types/node"))
        self.assertFalse(matches("pytest*", "django"))
        self.assertEqual(glob_to_regex("a?c").pattern, "^a[^/]c$")


class ManifestTests(unittest.TestCase):
    def test_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text('[project]\ndependencies = ["Django>=5", "psycopg[binary]"]\n'
                                                 '[project.optional-dependencies]\ndev = ["pytest-cov"]\n')
            (root / "requirements.txt").write_text("django==5.0  # web\n-r base.txt\nrequests\n")
            (root / "package.json").write_text(json.dumps({"dependencies": {"react": "1"}, "devDependencies": {"@types/node": "1"}}))
            (root / "Cargo.toml").write_text('[dependencies]\nserde = "1"\n[dev-dependencies]\ninsta = "1"\n')
            (root / "go.mod").write_text("module x\n\nrequire (\n\tgithub.com/a/b v1.0.0 // indirect\n)\nrequire golang.org/x/y v0.1.0\n")
            self.assertEqual(manifest_dependencies(root / "pyproject.toml"), ["django", "psycopg", "pytest-cov"])
            self.assertEqual(manifest_dependencies(root / "requirements.txt"), ["django", "requests"])
            self.assertEqual(manifest_dependencies(root / "package.json"), ["react", "@types/node"])
            self.assertEqual(manifest_dependencies(root / "Cargo.toml"), ["serde", "insta"])
            self.assertEqual(manifest_dependencies(root / "go.mod"), ["github.com/a/b", "golang.org/x/y"])
            with self.assertRaises(ValueError):
                manifest_dependencies(root / "unknown.lock")


class EvaluationTests(unittest.TestCase):
    def test_violations_and_manifest_scope(self):
        contract = parse_contract(CONTRACT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src/domain").mkdir(parents=True)
            (root / "src/domain/order.py").write_text("from app.infra import db\n")
            (root / "src/domain/ok.py").write_text("x = 1\n")
            (root / "src/legacy.js").write_text("")
            (root / "pyproject.toml").write_text('[project]\ndependencies = ["django", "requests"]\n')
            files = ["src/domain/order.py", "src/domain/ok.py", "src/legacy.js"]
            found = evaluate(contract, root, files, manifests_always=False)
            self.assertEqual([v.path for v in found], ["src/legacy.js", "src/domain/order.py:1"])
            self.assertIn("TypeScript only", found[0].render())
            found = evaluate(contract, root, files + ["pyproject.toml"], manifests_always=False)
            self.assertTrue(any("'requests' is not in the contract" in v.render() for v in found))
            found = evaluate(contract, root, [], manifests_always=True)
            self.assertEqual(len(found), 1)

    def test_forbid_pattern_reads_files_in_any_encoding_and_fails_closed(self):
        contract = parse_contract('```rules\nforbid-pattern "**/*.py" "^import os"\n```\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "legacy.py").write_bytes("# café\nimport os\n".encode("latin-1"))
            (root / "package.py").mkdir()
            found = evaluate(contract, root, ["legacy.py", "package.py"], manifests_always=False)
            self.assertEqual([v.path for v in found], ["legacy.py:2"], "a file that is not UTF-8 is still searched")
            (root / "marked.py").write_bytes(b"\xef\xbb\xbfimport os\n")
            found = evaluate(contract, root, ["marked.py"], manifests_always=False)
            self.assertEqual([v.path for v in found], ["marked.py:1"], "a byte order mark does not hide line 1")
            if os.name == "posix" and os.geteuid() != 0:   # Windows has no mode that denies reading
                locked = root / "locked.py"
                locked.write_text("x = 1\n")
                locked.chmod(0)
                found = evaluate(contract, root, ["locked.py"], manifests_always=False)
                self.assertEqual([v.path for v in found], ["locked.py"])
                self.assertIn("cannot be read", found[0].detail)

    def test_missing_commands(self):
        from unittest import mock
        contract = parse_contract(CONTRACT)
        both = parse_contract('```rules\nrequire-command "make test && make lint"\n```\n')
        # As sh reads them; on Windows cmd.exe runs Verify (see the next test).
        with mock.patch("atipspec.contract.os.name", "posix"):
            self.assertEqual(len(missing_commands(contract, ["python  -m pytest -q"])), 0)
            self.assertEqual(len(missing_commands(contract, ["pytest"])), 1)
            self.assertEqual(len(missing_commands(contract, ["python -m pytest -q --junitxml .atipspec/tmp/junit.xml"])),
                             0, "more arguments, such as a JUnit report, still run the required command")
            self.assertEqual(len(missing_commands(contract, ["python -m pytest"])), 1, "fewer arguments do not")
            self.assertEqual(len(missing_commands(contract, ["python -m pytest -qq"])), 1, "nor another argument")
            for hidden in ("python -m pytest -q || true", "python -m pytest -q | tail -1",
                           "python -m pytest -q; true", "python -m pytest -q && echo ok", "python -m pytest -q &",
                           "python -m pytest -q > out.txt", "python -m pytest -q 2>&1",
                           "python -m pytest -q $(cat args)", 'python -m pytest -q "$(true)"',
                           "python -m pytest -q `true`", "python -m pytest -q||true", "python -m pytest -q 'open"):
                self.assertEqual(len(missing_commands(contract, [hidden])), 1,
                                 f"{hidden!r}: what follows may hide the command's failure")
            self.assertEqual(len(missing_commands(contract, ['python -m pytest -q -k "a or b|c" tests/'])), 0,
                             "quoted text is an argument; arguments that narrow the run are not judged")
            self.assertEqual(len(missing_commands(contract, ["python -m 'pytest' -q"])), 0, "the shell's words count")
            self.assertEqual(len(missing_commands(both, ["make test && make lint"])), 0,
                             "an operator the rule requires")

    def test_on_windows_a_cmd_metacharacter_after_the_command_does_not_count(self):
        from unittest import mock
        contract = parse_contract(CONTRACT)
        hidden = ("python -m pytest -q -k 'x || ver '", "python -m pytest -q -k x\\|\\|ver",
                  'python -m pytest -q -k "a or b|c" tests/', "python -m pytest -q -k %COMSPEC%",
                  "python -m pytest -q -k '^x'", "python -m pytest -q -k 'a\" & ver & \"'",
                  "python -m pytest -q -k 'a\"b'", "python -m pytest -q -k 'a<b'", "python -m pytest -q -k 'a>b'")
        with mock.patch("atipspec.contract.os.name", "posix"):
            for line in hidden:
                self.assertEqual(len(missing_commands(contract, [line])), 0, f"sh reads {line!r} as arguments")
        with mock.patch("atipspec.contract.os.name", "nt"):
            for line in hidden:
                self.assertEqual(len(missing_commands(contract, [line])), 1,
                                 f"cmd.exe, which takes no single quote or backslash as a quote, may run what "
                                 f"follows in {line!r}")
            self.assertEqual(len(missing_commands(contract, ["python -m pytest -q --junitxml .atipspec/tmp/junit.xml"])),
                             0, "arguments without a metacharacter still count")
            self.assertEqual(len(missing_commands(parse_contract('```rules\nrequire-command "make test && make lint"'
                                                                 '\n```\n'), ["make test && make lint"])), 0,
                             "an operator the rule requires")


if __name__ == "__main__":
    unittest.main()
