"""C11: the same bytes on every platform and under any locale. Text I/O names
UTF-8 and LF, the CLI writes UTF-8 to a pipe, approvals, signatures and
evidence read CRLF as LF, an os function Windows lacks runs only behind a
platform check, the runner refuses a platform without its lock before
writing, and the suite's repositories commit and check out text as Git for
Windows does."""
import ast
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from atipspec.accept import approval_code, contract_code, is_current
from atipspec.check import check_delivery
from atipspec.cli import _utf8_output
from atipspec.errors import AtipSpecError
from atipspec.install import installed_clients
from atipspec.project import Project
from atipspec.runner import run_delivery
from atipspec.trust import TrustPolicy, subject
from tests.helpers import ProjectCase, python_command
from tests.test_approval import PLAN, GuidedCase
from tests.trust_helpers import TrustedCase
from tests.windows_text import windows_text

ROOT = Path(__file__).resolve().parents[1]
SUBPROCESS = {"run", "Popen", "check_output", "check_call", "call"}
WRITES = set("wax+")
POSIX_ONLY = {"geteuid", "getuid", "getegid", "getgid", "getgroups", "fork", "killpg", "getpgid", "setsid",
              "mkfifo", "chown", "lchown"}
PLATFORM_CHECKS = ("os.name", "sys.platform", "hasattr(os")


def _keyword(call: ast.Call, name: str):
    return next((keyword.value for keyword in call.keywords if keyword.arg == name), None)


def _mode(call: ast.Call, position: int):
    """The mode of an open call, a string; None when it is not a constant."""
    value = _keyword(call, "mode")
    if value is None and len(call.args) > position:
        value = call.args[position]
    if value is None:
        return "r"
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def text_io_problems(source: str) -> list[str]:
    """Each call that reads or writes text without naming UTF-8, or writes it
    without naming LF, as `line: call`."""
    problems = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
        encoding = _keyword(node, "encoding") is not None
        if name == "read_text":
            missing = not (encoding or node.args)
        elif name == "write_text":
            missing = not (encoding or len(node.args) > 1) or _keyword(node, "newline") is None
        elif name in ("open", "fdopen"):
            # open(path, mode), os.fdopen(fd, mode) and Path.open(mode); an opener's open(request) is not a file.
            method = isinstance(node.func, ast.Attribute) and name == "open"
            if method and node.args and not (isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                continue
            mode = _mode(node, 0 if method else 1)
            missing = (mode is not None and "b" not in mode
                       and (not encoding or (WRITES & set(mode) and _keyword(node, "newline") is None)))
        elif name in SUBPROCESS:
            text = any(keyword.arg in ("text", "universal_newlines", "errors") for keyword in node.keywords)
            missing = text and not encoding
        else:
            continue
        if missing:
            problems.append(f"{node.lineno}: {ast.unparse(node.func)}(...)")
    return problems


def posix_only_calls(source: str) -> list[str]:
    """Each call to an os function Windows lacks that no platform check guards
    (an if, an `and` or a skip decorator naming the platform), as `line: call`."""
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

    def names_platform(node):
        return any(check in ast.unparse(node) for check in PLATFORM_CHECKS)

    problems = []
    for node in sorted((node for node in ast.walk(tree) if isinstance(node, ast.Call)), key=lambda call: call.lineno):
        if not (isinstance(node.func, ast.Attribute) and node.func.attr in POSIX_ONLY
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "os"):
            continue
        child, parent, guarded = node, parents.get(node), False
        while parent is not None and not guarded:
            if isinstance(parent, (ast.If, ast.IfExp, ast.While)):
                guarded = child is not parent.test and names_platform(parent.test)
            elif isinstance(parent, ast.BoolOp):
                guarded = any(names_platform(value) for value in parent.values[:parent.values.index(child)])
            elif isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                guarded = any(names_platform(decorator) for decorator in parent.decorator_list)
            child, parent = parent, parents.get(parent)
        if not guarded:
            problems.append(f"{node.lineno}: {ast.unparse(node.func)}(...)")
    return problems


class TextIOTests(unittest.TestCase):
    def test_text_io_names_encoding_and_line_ending(self):
        found = []
        for path in sorted([*(ROOT / "atipspec").rglob("*.py"), *(ROOT / "scripts").glob("*.py")]):
            found += [f"{path.relative_to(ROOT).as_posix()}:{problem}"
                      for problem in text_io_problems(path.read_text(encoding="utf-8"))]
        self.assertEqual(found, [], "name encoding='utf-8' (and newline='\\n' when writing) in each of these")

    def test_the_check_finds_each_kind_of_call(self):
        source = ("p.read_text()\np.write_text(t, encoding='utf-8')\nopen(f)\nopen(f, 'w', encoding='utf-8')\n"
                  "p.open('a+')\nsubprocess.run(a, text=True)\nsubprocess.Popen(a, errors='replace')\n"
                  "p.read_text(encoding='utf-8')\np.write_text(t, encoding='utf-8', newline='\\n')\np.read_bytes()\n"
                  "open(f, 'rb')\nopener.open(request, timeout=3)\nsubprocess.run(a, capture_output=True)\n")
        self.assertEqual([problem.split(":")[0] for problem in text_io_problems(source)],
                         ["1", "2", "3", "4", "5", "6", "7"])


class PlatformCallTests(unittest.TestCase):
    """The Windows CI jobs run the package, the scripts and the suite: a call
    Windows lacks fails there with AttributeError."""

    def test_posix_only_calls_are_guarded(self):
        found = []
        for path in sorted([*(ROOT / "atipspec").rglob("*.py"), *(ROOT / "scripts").glob("*.py"),
                            *(ROOT / "tests").glob("*.py")]):
            found += [f"{path.relative_to(ROOT).as_posix()}:{problem}"
                      for problem in posix_only_calls(path.read_text(encoding="utf-8"))]
        self.assertEqual(found, [], "check os.name before each of these")

    def test_the_check_finds_an_unguarded_call(self):
        source = ("if os.geteuid() != 0:\n    pass\nos.killpg(pid, 9)\nif os.name == 'posix':\n    os.killpg(pid, 9)\n"
                  "else:\n    process.kill()\nif os.name == 'posix' and os.geteuid() != 0:\n    pass\n"
                  "@unittest.skipIf(os.name == 'nt', 'POSIX')\ndef test():\n    os.getuid()\n"
                  "if ready and os.getuid():\n    pass\n")
        self.assertEqual([problem.split(":")[0] for problem in posix_only_calls(source)], ["1", "3", "13"])


class OutputEncodingTests(unittest.TestCase):
    def test_cli_output_to_a_pipe_is_utf8(self):
        pipe = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        with patch.object(sys, "stdout", pipe):
            _utf8_output()
            print("Navegación → paso")
            sys.stdout.flush()
        self.assertEqual(pipe.buffer.getvalue().decode("utf-8").strip(), "Navegación → paso")

    def test_a_terminal_keeps_its_encoding(self):
        console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        with patch.object(console, "isatty", return_value=True), patch.object(sys, "stdout", console):
            _utf8_output()
        self.assertEqual(console.encoding, "cp1252")


class PipedCliTests(ProjectCase):
    def test_the_command_writes_utf8_to_a_pipe_whatever_its_encoding(self):
        """`atipspec` itself switches the pipe: with an ASCII stdout a title with `→` ends `status` in an error."""
        self.new_delivery()
        spec = self.delivery() / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Password reset", "Navegación → menú"),
                        encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "atipspec", "status"], cwd=self.root, capture_output=True,
                                env={**self.env, "PYTHONIOENCODING": "ascii", "PYTHONPATH": str(ROOT)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Navegación → menú".encode("utf-8"), result.stdout)


def checkout(case, autocrlf: str = "true") -> Project:
    """A clone of the case's committed repository, checked out as Git for
    Windows does by default (core.autocrlf=true: text with CRLF) or, with
    "false", with the LF it was committed with."""
    target = tempfile.TemporaryDirectory()
    case.addCleanup(target.cleanup)
    root = Path(target.name).resolve() / "checkout"
    case.git("clone", "-q", "--no-local", "--config", f"core.autocrlf={autocrlf}", str(case.root), str(root))
    return Project.find(root)


class LineEndingTests(GuidedCase):
    """What is approved, accepted or verified on one platform holds on
    another: Git for Windows checks text out with CRLF (core.autocrlf), Git
    elsewhere with LF."""

    def test_crlf_checkout_keeps_the_approval_subjects(self):
        self.write_contract('require-command "true"')
        project = self.guided()
        code = self.presented_code("password-reset")
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal", "--code", code)[0], 0)
        self.commit("approved proposal")
        self.finish(project)
        self.commit("candidate")
        phases = ("spec", "plan", "acceptance")
        before = {phase: subject(project, "password-reset", phase) for phase in phases}
        contract = contract_code(project)
        copy = checkout(self)
        directory = copy.delivery_dir("password-reset")
        for path in (directory / "spec.md", directory / "approvals" / "local-proposal.json", copy.specs / "auth.md",
                     *directory.glob("evidence/*.json")):
            self.assertTrue(path.read_bytes().endswith(b"\r\n"), path)
        self.assertEqual({phase: subject(copy, "password-reset", phase) for phase in phases}, before)
        self.assertEqual(contract_code(copy), contract)
        self.assertTrue(is_current(copy, "password-reset", "proposal"))
        with contextlib.chdir(copy.root):
            code, out, err = self.run_cli("status", "password-reset")
        self.assertEqual(code, 0, err)
        self.assertNotIn("outdated", out)
        self.assertEqual(check_delivery(copy, "password-reset").status, "checked")

    def test_an_edit_on_a_crlf_checkout_still_voids_the_approval(self):
        self.write_contract('require-command "true"')
        self.guided()
        code = self.presented_code("password-reset")
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal", "--code", code)[0], 0)
        self.commit("approved proposal")
        copy = checkout(self)
        self.assertTrue(is_current(copy, "password-reset", "proposal"))
        living = copy.specs / "auth.md"
        living.write_bytes(living.read_bytes().replace(b"thirty minutes", b"sixty minutes"))
        self.assertFalse(is_current(copy, "password-reset", "proposal"))

    def test_an_accepted_result_holds_on_a_crlf_checkout(self):
        """The command output logs and the skills `init` installed are checked out with CRLF too."""
        project = self.guided()
        command = python_command("print('ok')")
        (self.delivery() / "plan.md").write_text(PLAN.replace("`true`", f"`{command}`"))
        code = self.presented_code("password-reset")
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal", "--code", code)[0], 0)
        self.commit("approved proposal")
        self.finish(project)
        self.commit("candidate")
        code = approval_code(project, "password-reset", "result")
        self.assertEqual(self.run_cli("accept", "password-reset", "result", "--code", code)[0], 0)
        self.commit("accepted result")
        copy = checkout(self)
        log = next(copy.delivery_dir("password-reset").glob("evidence/logs/FINAL-*.log"))
        self.assertEqual(log.read_bytes(), b"ok\r\n")
        self.assertIn(b"\r\n", (copy.root / ".claude/skills/atipspec/SKILL.md").read_bytes())
        self.assertEqual(installed_clients(copy.root), {"claude": "installed"})
        report = check_delivery(copy, "password-reset")
        self.assertEqual(report.status, "accepted", report.render())
        self.assertTrue(is_current(copy, "password-reset", "result"))
        with contextlib.chdir(copy.root):
            self.assertIn("[accepted]", self.run_cli("status", "password-reset")[1])
        # Another output still does not pass for the one recorded.
        log.write_bytes(b"ko\r\n")
        report = check_delivery(copy, "password-reset")
        self.assertIn("FINAL: command output log is missing or its hash does not match", report.errors)
        self.assertFalse(is_current(copy, "password-reset", "result"))

    def test_a_report_a_test_tool_wrote_with_crlf_holds_where_git_checks_it_out_with_lf(self):
        """A test tool on Windows writes its JUnit report with CRLF, and git commits the evidence's copy with LF."""
        project = self.guided()
        xml = '<testsuite>\n<testcase classname="tests.test_reset" name="test_expiry"/>\n</testsuite>\n'
        command = python_command("import os\nos.makedirs('.atipspec/tmp', exist_ok=True)\n"
                                 f"open('.atipspec/tmp/junit.xml', 'w', encoding='utf-8', newline='\\r\\n').write({xml!r})\n")
        (self.delivery() / "plan.md").write_text(PLAN.replace("Verify:\n- `true`", f"Report: .atipspec/tmp/junit.xml\n"
                                                              f"Verify:\n- `{command}`"))
        code = self.presented_code("password-reset")
        self.assertEqual(self.run_cli("accept", "password-reset", "proposal", "--code", code)[0], 0)
        self.commit("approved proposal")
        self.finish(project)
        self.assertIn(b"\r\n", next(self.delivery().glob("evidence/logs/FINAL-*-report.xml")).read_bytes())
        self.commit("candidate")
        self.assertEqual(check_delivery(project, "password-reset").status, "checked")
        for autocrlf in ("false", "true"):
            copy = checkout(self, autocrlf)
            report = check_delivery(copy, "password-reset")
            self.assertEqual(report.status, "checked", f"core.autocrlf={autocrlf}: {report.render()}")


class SignedLineEndingTests(TrustedCase):
    def test_signed_records_hold_on_a_crlf_checkout(self):
        """Approvals, attested evidence and their signatures are checked out with CRLF."""
        self.prepare()
        self.commit("approvals, evidence and review")
        copy = checkout(self)
        directory = copy.delivery_dir("password-reset")
        records = [*directory.glob("approvals/*.json*"), *directory.glob("evidence/*.json*")]
        self.assertTrue(records and all(path.read_bytes().endswith(b"\r\n") for path in records))
        report = check_delivery(copy, "password-reset", policy=TrustPolicy.load(self.policy_path, copy.root))
        self.assertEqual((report.exit_code, report.status), (0, "verified"), report.render())


class WindowsTextTests(ProjectCase):
    """On Windows a test that names no newline writes CRLF, and AtipSpec
    rewrites with LF. The suite's repositories commit text with LF and check
    it out with CRLF, as Git for Windows does by default, so a rewrite changes
    no line and a merge does not conflict. CI runs the whole suite this way on
    Linux."""

    def setUp(self):
        self.enterContext(windows_text())
        super().setUp()

    def test_text_written_with_crlf_is_committed_with_lf(self):
        living = self.root / ".atipspec/specs/auth.md"
        living.write_text("# Auth\n")
        self.assertEqual(living.read_bytes(), b"# Auth\r\n")
        self.commit("living spec")
        blob = subprocess.check_output(["git", "cat-file", "blob", "HEAD:.atipspec/specs/auth.md"], cwd=self.root,
                                       env=self.env)
        self.assertEqual(blob, b"# Auth\n")
        living.write_text("# Auth\n", encoding="utf-8", newline="\n")
        self.assertEqual(self.git("diff", "--name-only", "HEAD"), "")

    def test_deliveries_and_merges_hold_with_windows_text(self):
        names = ["tests.test_fix_and_risk.GuidedFixTests.test_a_requirement_a_delivery_left_as_it_was_stays_as_it_wrote_it",
                 "tests.test_teams.IntegrationTests.test_without_integration_ref_behaviour_is_strict"]
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromNames(names))
        self.assertEqual((result.testsRun, len(result.skipped)), (2, 0))
        self.assertTrue(result.wasSuccessful(), stream.getvalue())


class RunnerPlatformTests(ProjectCase):
    def test_runner_refuses_non_posix_before_writing(self):
        self.new_delivery()
        project = Project.find(self.root)
        with patch("atipspec.runner.POSIX", False), self.assertRaises(AtipSpecError) as caught:
            run_delivery(project, "password-reset")
        self.assertIn("Linux, macOS or WSL", str(caught.exception))
        self.assertIn("guided conversation", str(caught.exception))
        self.assertFalse((self.delivery() / "run.json").exists())
        self.assertFalse((project.tmp / "runner.lock").exists())
        with patch("atipspec.runner.POSIX", False):
            code, _, err = self.run_cli("run", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("guided conversation", err)

    def test_required_trust_is_named_before_the_platform(self):
        """Under a trust policy the runner is never the way, on any platform."""
        config = self.root / ".atipspec/config.yaml"
        config.write_text(config.read_text(encoding="utf-8").replace("trust: optional", "trust: required"),
                          encoding="utf-8")
        self.new_delivery()
        with patch("atipspec.runner.POSIX", False):
            code, _, err = self.run_cli("run", "password-reset")
        self.assertEqual(code, 1)
        self.assertIn("external trust policy", err)
        self.assertNotIn("POSIX", err)


if __name__ == "__main__":
    unittest.main()
