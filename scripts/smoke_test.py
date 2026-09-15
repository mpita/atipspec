"""Exercise a non-editable installed CLI, including disposable trusted acceptance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


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
        (outer / ".empty").write_text("")

        def run(*args, expect=0):
            result = subprocess.run(list(args), cwd=project, env=env, capture_output=True, text=True,
                                    timeout=120, stdin=subprocess.DEVNULL)
            if result.returncode != expect:
                raise SystemExit(f"{' '.join(args)} exited {result.returncode} (expected {expect})\n{result.stdout}{result.stderr}")
            return result.stdout

        def git(*args):
            return run("git", *args)

        git("init", "-q", "-b", "main", ".")
        (project / "README.md").write_text("smoke\n")
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
        (project / ".atipspec/contract.md").write_text('---\nstatus: draft\n---\n# Contract\n\n```rules\nrequire-command "atipspec --version"\n```\n')
        run(executable, "spec", "smoke", expect=1)   # refused: the contract is not accepted
        run(executable, "accept", "contract")
        if "status: accepted" not in (project / ".atipspec/contract.md").read_text():
            raise SystemExit("accept contract must set the contract's status")
        git("add", "-A")
        git("commit", "-q", "-m", "contract")
        policy = outer / "policy.toml"
        policy_text = 'schema = 1\nversion = "smoke"\nrepository = "example/smoke"\n'
        keys = {}
        for role in ("product", "engineering", "qa", "ci"):
            keys[role] = outer / role
            run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(keys[role]))
            public = keys[role].with_suffix(".pub").read_text().strip()
            policy_text += f'\n[[signers]]\nidentity = "{role}"\nroles = ["{role}"]\npublic_key = {json.dumps(public)}\n'
        policy.write_text(policy_text)
        run(executable, "initiative", "launch", "--title", "Launch")
        run(executable, "new", "smoke", "--title", "Smoke", "--capability", "smoke", "--owner", "author", "--initiative", "launch")
        change = project / ".atipspec/deliveries/smoke"
        run(executable, "check", "smoke", expect=2)
        if "# Phase spec" not in run(executable, "spec", "smoke"):
            raise SystemExit("The spec phase must print its workflow")
        run(executable, "plan", "smoke", expect=1)
        if "next phase is spec" not in run(executable, "ship", "smoke"):
            raise SystemExit("Ship mode must name the spec phase for a draft")
        base = git("rev-parse", "HEAD").strip()
        (change / "spec.md").write_text(f'''---
status: draft
capability: smoke
owner: author
base: {base}
---
# Smoke

### REQ-001: The CLI runs
- AC-001: The CLI reports its version.

## Open questions
- None
''')
        (change / "plan.md").write_text('''# Plan

### T1: Run the CLI
Covers: REQ-001
Tests: AC-001
Verify:
- `atipspec --version`
''')
        run(executable, "plan", "smoke", expect=1)     # refused: the spec is not accepted
        run(executable, "accept", "smoke", "spec", "--by", "product@example.com")
        if "status: ready" not in (change / "spec.md").read_text():
            raise SystemExit("accept spec must set status: ready")
        run(executable, "build", "smoke", expect=1)    # refused: approve_plan is on and the plan is not accepted
        run(executable, "accept", "smoke", "plan", "--by", "architect@example.com")
        run(executable, "review", "smoke", expect=1)   # nothing committed yet: refused, no packet
        git("add", "-A")
        git("commit", "-q", "-m", "smoke [smoke:T1]")
        if "Next task: all tasks are committed" not in run(executable, "build", "smoke", "--no-context"):
            raise SystemExit("The build phase must report that every task is committed")
        for phase, identity in (("spec", "product"), ("plan", "engineering")):
            run(executable, "approve", "smoke", phase, "--identity", identity, "--key", str(keys[identity]), "--policy", str(policy))
        run(executable, "verify", "smoke", "--policy", str(policy))
        run(executable, "attest", "smoke", "--identity", "ci", "--key", str(keys["ci"]), "--policy", str(policy), "--run-url", "https://ci.example/runs/smoke")
        run(executable, "review", "smoke")
        packet = (project / ".atipspec/tmp/smoke-review-packet.md").read_text()
        tree = next(line for line in packet.splitlines() if line.startswith("tree: ")).split(" ", 1)[1]
        (change / "review.md").write_text(f'---\ntree: {tree}\nreviewer: smoke-reviewer\n---\n# Review\n\n- AC-001: PASS. observed installed CLI version in CI evidence\n')
        if "[checked]" not in run(executable, "check", "smoke"):
            raise SystemExit("Local check must not claim trusted verification")
        run(executable, "deliver", "smoke", expect=1)
        run(executable, "approve", "smoke", "acceptance", "--identity", "qa", "--key", str(keys["qa"]), "--policy", str(policy))
        if "[verified]" not in run(executable, "check", "smoke", "--policy", str(policy)):
            raise SystemExit("Expected verified signed delivery")
        run(executable, "report", "smoke", "--format", "html", "--out", str(outer / "report.html"), "--policy", str(policy))
        run(executable, "deliver", "smoke", "--policy", str(policy))
        living = (project / ".atipspec/specs/smoke.md").read_text()
        if "### REQ-001: The CLI runs" not in living or "AC-001:" not in living:
            raise SystemExit("Living IDs must survive delivery")
        run(executable, "report", "smoke", "--format", "json")
        run(executable, "curate")
        run(executable, "audit")
        if "launch 1/1" not in run(executable, "status"):
            raise SystemExit("Expected completed initiative")
        run(executable, "enterprise-init")
        for resource in ("policy.example.toml", "github-local.yml", "gitlab-local.yml", "ADOPTION.md"):
            if not (project / ".atipspec/enterprise" / resource).is_file():
                raise SystemExit(f"Missing installed enterprise resource {resource}")
        run(executable, "pilot", "init", "quality")
        if json.loads(run(executable, "pilot", "report", "quality"))["observations"] != 0:
            raise SystemExit("Pilot must start without fabricated observations")
    print("Installed CLI smoke test passed (signed approvals, CI evidence, dossier, stable IDs and pilot).")


if __name__ == "__main__":
    main()
