import json
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

    def test_missing_commands(self):
        contract = parse_contract(CONTRACT)
        self.assertEqual(len(missing_commands(contract, ["python  -m pytest -q"])), 0)
        self.assertEqual(len(missing_commands(contract, ["pytest"])), 1)


if __name__ == "__main__":
    unittest.main()
