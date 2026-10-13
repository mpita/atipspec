"""Exercise a non-editable installed CLI, including disposable trusted acceptance."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def approval_code(output):
    """The code a presentation view (`proposal`, `proposal contract`) shows."""
    for line in output.splitlines():
        if line.startswith("Approval code: "):
            return line.split()[2]
    raise SystemExit("Expected an approval code in:\n" + output)


def template_step(path, step):
    """The shell script of the `run: |` block that follows the line naming `step` in a CI template."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(index for index, line in enumerate(lines) if step in line)
    run = next(index for index in range(start, len(lines)) if lines[index].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body = []
    for line in lines[run + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    margin = min(len(line) - len(line.lstrip()) for line in body if line.strip())
    return "\n".join(line[margin:] for line in body) + "\n"


def main():
    executable = shutil.which("atipspec")
    if executable is None:
        raise SystemExit("Install AtipSpec first: python -m pip install .")
    with tempfile.TemporaryDirectory(prefix="atipspec-smoke-") as temporary:
        outer = Path(temporary).resolve()
        project = outer / "project"
        project.mkdir()
        env = {**os.environ, "GIT_CONFIG_GLOBAL": str(outer / ".empty"), "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "smoke", "GIT_AUTHOR_EMAIL": "smoke@example.com",
               "GIT_COMMITTER_NAME": "smoke", "GIT_COMMITTER_EMAIL": "smoke@example.com"}
        env.pop("ATIPSPEC_TRUST_POLICY", None)
        env.pop("ATIPSPEC_POLICY_SHA256", None)
        for marker in ("CLAUDECODE", "CODEX_SANDBOX", "CODEX_THREAD_ID", "COPILOT_CLI", "CURSOR_AGENT", "GEMINI_CLI",
                       "AI_AGENT", "CLAUDE_CODE_ENTRYPOINT"):
            env.pop(marker, None)
        (outer / ".empty").write_text("", encoding="utf-8", newline="\n")

        def run(*args, expect=0, extra=None):
            result = subprocess.run(list(args), cwd=project, env={**env, **(extra or {})}, capture_output=True,
                                    text=True, encoding="utf-8", timeout=120, stdin=subprocess.DEVNULL)
            if result.returncode != expect:
                raise SystemExit(f"{' '.join(args)} exited {result.returncode} (expected {expect})\n{result.stdout}{result.stderr}")
            return result.stdout

        def git(*args):
            return run("git", *args)

        git("init", "-q", "-b", "main", ".")
        (project / "README.md").write_text("smoke\n", encoding="utf-8", newline="\n")
        git("add", "-A")
        git("commit", "-q", "-m", "init")
        run(executable, "--version")
        run(executable, "init", "--name", "Smoke", "--language", "es", "--client", "codex", "--client", "claude",
            "--client", "cursor", "--client", "github-copilot", "--client", "antigravity", "--client", "gemini")
        for skill in ("atipspec", "atipspec-spec", "atipspec-ship"):
            for folder in (".claude/skills", ".agents/skills", ".cursor/skills", ".github/skills", ".gemini/skills"):
                if not (project / folder / skill / "SKILL.md").is_file():
                    raise SystemExit(f"Missing installed skill {folder}/{skill}")
        run(executable, "contract")
        (project / ".atipspec/contract.md").write_text(
            '---\nstatus: draft\n---\n# Contract\n\n```rules\nrequire-command "atipspec --version"\n```\n',
            encoding="utf-8", newline="\n")
        run(executable, "spec", "smoke", expect=1)   # refused: there is no delivery named smoke yet
        run(executable, "accept", "contract", expect=1)   # refused: no approval code
        contract_code = approval_code(run(executable, "proposal", "contract"))
        run(executable, "accept", "contract", "--code", contract_code)
        if "status: accepted" not in (project / ".atipspec/contract.md").read_text(encoding="utf-8"):
            raise SystemExit("accept contract must set the contract's status")
        if not (project / ".atipspec/approvals/contract.json").is_file():
            raise SystemExit("accept contract must record the acceptance")
        if json.loads((project / ".claude/settings.json").read_text(encoding="utf-8"))["permissions"]["ask"] != [
                "Bash(*atipspec accept *)", "Edit(/.github/workflows/**)", "Edit(/.gitlab-ci.yml)",
                "Edit(/.claude/settings*.json)"]:
            raise SystemExit("init must configure Claude Code to ask before atipspec accept and before editing the CI "
                             "or its settings")
        # With the rules intact, only the command line Claude Code's ask rule matches counts as client-permission.
        for command, channel in (([sys.executable, "-m", "atipspec.cli"], "assistant"),
                                 ([sys.executable, "-m", "atipspec.__main__"], "assistant"),
                                 ([sys.executable, "-m", "atipspec"], "client-permission"),
                                 ([executable], "client-permission")):
            run(*command, "accept", "contract", "--code", contract_code, extra={"CLAUDECODE": "1"})
            if json.loads((project / ".atipspec/approvals/contract.json").read_text(encoding="utf-8"))["channel"] != channel:
                raise SystemExit(f"{' '.join(command)} accept under Claude Code must record channel {channel}")
        git("add", "-A")
        git("commit", "-q", "-m", "contract")
        # A remote target branch and a delivery branch, as a pull request sees them.
        run("git", "init", "-q", "--bare", str(outer / "origin.git"))
        git("remote", "add", "origin", str(outer / "origin.git"))
        git("push", "-q", "origin", "main")
        git("switch", "-q", "-c", "delivery/smoke")
        run(executable, "enterprise-init", "--out", str(outer / "enterprise"))
        ci_step = template_step(outer / "enterprise/github-local.yml", "- name: Gate the deliveries")
        ci_env = {"BASE": "main", "RUNNER_TEMP": str(outer), "GITHUB_STEP_SUMMARY": str(outer / "summary.md")}

        def gate(expect=0):
            """The merge-check step of github-local.yml, run with bash as its ubuntu runner does; its command on Windows."""
            if os.name != "nt":
                return run("bash", "-eo", "pipefail", "-c", ci_step, expect=expect, extra=ci_env)
            output = run(sys.executable, "-I", "-m", "atipspec", "merge-check", "--base", "origin/main", "--format",
                         "markdown", expect=expect)
            (outer / "summary.md").write_text(output, encoding="utf-8", newline="\n")
            return output
        policy = outer / "policy.toml"
        policy_text = 'schema = 1\nversion = "smoke"\nrepository = "example/smoke"\n'
        keys = {}
        for role in ("product", "engineering", "qa", "ci"):
            keys[role] = outer / role
            run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(keys[role]))
            public = keys[role].with_suffix(".pub").read_text(encoding="utf-8").strip()
            policy_text += f'\n[[signers]]\nidentity = "{role}"\nroles = ["{role}"]\npublic_key = {json.dumps(public)}\n'
        policy.write_text(policy_text, encoding="utf-8", newline="\n")
        run(executable, "initiative", "launch", "--title", "Launch")
        # A title no Windows code page encodes: the CLI writes UTF-8 to a pipe whatever the locale.
        run(executable, "new", "smoke", "--title", "Smoke → navegación", "--capability", "smoke", "--owner", "author",
            "--initiative", "launch")
        change = project / ".atipspec/deliveries/smoke"
        run(executable, "check", "smoke", expect=2)
        if "# Phase spec" not in run(executable, "spec", "smoke"):
            raise SystemExit("The spec phase must print its workflow")
        run(executable, "plan", "smoke", expect=1)
        if "next phase is spec" not in run(executable, "ship", "smoke"):
            raise SystemExit("Ship mode must name the spec phase for a draft")
        base = git("rev-parse", "HEAD").strip()
        (change / "spec.md").write_text(f'''---
title: "Smoke → navegación"
status: draft
capability: smoke
owner: author
ticket: SMOKE-1
base: {base}
---
# Smoke → navegación

### REQ-001: The CLI runs
- AC-001: When a user runs `atipspec --version`, the CLI prints its version.

## Open questions
- None
''', encoding="utf-8", newline="\n")
        (change / "plan.md").write_text('''---
scope: ["*"]
---
# Plan

### T1: Run the CLI
Covers: REQ-001
Tests: AC-001
Verify:
- `atipspec --version`
''', encoding="utf-8", newline="\n")
        git("add", "-A")
        git("commit", "-q", "-m", "smoke draft")
        gate(expect=1)   # the local CI template blocks a draft
        if "smoke [draft]" not in (outer / "summary.md").read_text(encoding="utf-8"):
            raise SystemExit("The merge-check job summary must name the draft delivery")
        if "| smoke | SMOKE-1 | draft |" not in (outer / "summary.md").read_text(encoding="utf-8"):
            raise SystemExit("The merge-check job summary must list each delivery with its ticket")
        if json.loads(run(executable, "status", "--format", "json"))["deliveries"][0]["ticket"] != "SMOKE-1":
            raise SystemExit("status --format json must give each delivery's ticket")
        ids = run(executable, "ids", "smoke").splitlines()
        if (not re.fullmatch(r"smoke/REQ-SMOKE-([0-9A-HJKMNP-TV-Z]{5})-001 smoke/AC-SMOKE-\1-001", ids[0])
                or "-002, -003" not in ids[1]):
            raise SystemExit("ids must print a short shared prefix and how to number further IDs")
        run(executable, "plan", "smoke", expect=1)     # refused: the spec is not accepted
        run(executable, "build", "smoke", expect=1)    # refused: nothing is approved yet
        run(executable, "accept", "smoke", "proposal", "--code", "0000-0000", expect=1)   # not the presented content
        code = approval_code(run(executable, "proposal", "smoke"))
        run(executable, "accept", "smoke", "proposal", "--code", code, "--by", "product@example.com")
        if "status: ready" not in (change / "spec.md").read_text(encoding="utf-8"):
            raise SystemExit("accept proposal must set status: ready")
        status = run(executable, "status")
        if "proposal accepted by product@example.com" not in status or "via assistant" not in status:
            raise SystemExit("status must show who accepted and through which channel")
        if "Smoke → navegación" not in status:
            raise SystemExit("status must print a non-ASCII title to a pipe as UTF-8")
        run(executable, "review", "smoke", expect=1)   # nothing committed yet: refused, no packet
        git("add", "-A")
        git("commit", "-q", "-m", "smoke [smoke:T1]")
        if "Next task: all tasks are complete" not in run(executable, "build", "smoke", "--no-context"):
            raise SystemExit("The build phase must report that every task is complete")
        run(executable, "approve", "smoke", "spec", "--identity", "product", "--key", str(keys["product"]), "--policy",
            str(policy), expect=1)   # refused: the product approver confirms the owner
        run(executable, "approve", "smoke", "spec", "--identity", "product", "--key", str(keys["product"]), "--policy",
            str(policy), "--owner", "author")
        run(executable, "approve", "smoke", "plan", "--identity", "engineering", "--key", str(keys["engineering"]),
            "--policy", str(policy))
        run(executable, "verify", "smoke", "--policy", str(policy))
        run(executable, "attest", "smoke", "--identity", "ci", "--key", str(keys["ci"]), "--policy", str(policy), "--run-url", "https://ci.example/runs/smoke")
        run(executable, "review", "smoke")
        packet = (project / ".atipspec/tmp/smoke-review-packet.md").read_text(encoding="utf-8")
        tree = next(line for line in packet.splitlines() if line.startswith("tree: ")).split(" ", 1)[1]
        log = next((change / "evidence/logs").glob("T1-*-1.log")).relative_to(project).as_posix()
        (change / "review.md").write_text(f'---\ntree: {tree}\nreviewer: smoke-reviewer\nsession: isolated\n---\n'
                                          f'# Review\n\n- AC-001: PASS. {log}:1\n', encoding="utf-8", newline="\n")
        if "[checked]" not in run(executable, "check", "smoke"):
            raise SystemExit("Local check must not claim trusted verification")
        dossier = run(executable, "report", "smoke")
        if "Cambios respecto al commit base" not in dossier or f"remite a: file {log}:1" not in dossier:
            raise SystemExit("The dossier must show the changes and what each review pointer resolved to")
        run(executable, "deliver", "smoke", expect=1)
        run(executable, "approve", "smoke", "acceptance", "--identity", "qa", "--key", str(keys["qa"]), "--policy", str(policy))
        if "[verified]" not in run(executable, "check", "smoke", "--policy", str(policy)):
            raise SystemExit("Expected verified signed delivery")
        run(executable, "report", "smoke", "--format", "html", "--out", str(outer / "report.html"), "--policy", str(policy))
        run(executable, "deliver", "smoke", "--policy", str(policy))
        git("add", "-A")
        git("commit", "-q", "-m", "deliver smoke")
        gate()
        if "smoke: delivered; the head matches the accepted code" not in (outer / "summary.md").read_text(encoding="utf-8"):
            raise SystemExit("merge-check must accept a delivered branch whose code is the accepted code")
        if "smoke: delivered; its trusted check passes at" not in run(
                executable, "merge-check", "--base", "origin/main", "--policy", str(policy)):
            raise SystemExit("merge-check --policy must check the archived delivery where it was delivered from")
        (project / "late.py").write_text("print('unreviewed')\n", encoding="utf-8", newline="\n")
        git("add", "-A")
        git("commit", "-q", "-m", "late change")
        if "the code changed after `atipspec deliver` (late.py)" not in run(
                executable, "merge-check", "--base", "origin/main", "--policy", str(policy), expect=1):
            raise SystemExit("merge-check must block code changed after delivery")
        git("revert", "--no-edit", "HEAD")
        living = (project / ".atipspec/specs/smoke.md").read_text(encoding="utf-8")
        if "### REQ-001: The CLI runs" not in living or "AC-001:" not in living:
            raise SystemExit("Living IDs must survive delivery")
        run(executable, "report", "smoke", "--format", "json")
        run(executable, "curate")
        run(executable, "audit")
        if "launch 1/1" not in run(executable, "status"):
            raise SystemExit("Expected completed initiative")
        run(executable, "enterprise-init")
        for resource in ("policy.example.toml", "policy.provider.example.toml", "github-local.yml", "gitlab-local.yml",
                         "github-evidence-trusted.yml", "github-evidence-caller.yml", "ADOPTION.md"):
            if not (project / ".atipspec/enterprise" / resource).is_file():
                raise SystemExit(f"Missing installed enterprise resource {resource}")
        run(executable, "pilot", "init", "quality")
        if json.loads(run(executable, "pilot", "report", "quality"))["observations"] != 0:
            raise SystemExit("Pilot must start without fabricated observations")
    print("Installed CLI smoke test passed (signed approvals, CI evidence, merge check, dossier, stable IDs and pilot).")


if __name__ == "__main__":
    main()
