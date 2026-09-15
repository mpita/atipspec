"""Disposable test identities. Never install these keys as organization trust."""
import json
from pathlib import Path
import subprocess
import tempfile

from atipspec.assurance import attest
from atipspec.project import Project
from atipspec.trust import TrustPolicy, approve
from tests.helpers import ProjectCase


class TrustedCase(ProjectCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="atipspec-test-trust-")
        self.addCleanup(temporary.cleanup)
        self.trust_root = Path(temporary.name).resolve()
        self.keys = {}
        text = 'schema = 1\nversion = "test-1"\nrepository = "example/demo"\ncontract_rules = [\'require-command "true"\']\n'
        for role in ("product", "engineering", "qa", "risk", "ci", "collector"):
            key = self.trust_root / role
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
            self.keys[role] = key
            public = key.with_suffix(".pub").read_text().strip()
            text += f'\n[[signers]]\nidentity = "{role}"\nroles = ["{role}"]\npublic_key = {json.dumps(public)}\n'
        self.policy_path = self.trust_root / "policy.toml"
        self.policy_path.write_text(text)
        self.project = Project.find(self.root)
        self.policy = TrustPolicy.load(self.policy_path, self.root)

    def prepare(self):
        self.write_contract('require-command "true"')
        self.commit("accepted architecture")
        self.new_delivery()
        self.write_spec()
        path = self.delivery() / "spec.md"
        path.write_text(path.read_text().replace("capability: auth", "owner: author\ncapability: auth"))
        self.write_plan()
        # The local acceptance follows the edited content, as the person would redo it.
        self.accept("password-reset", "spec")
        self.accept("password-reset", "plan")
        self.commit("implementation [password-reset:T1,T2]")
        self.approve("spec", "product")
        self.approve("plan", "engineering")
        code, out, err = self.run_cli("verify", "password-reset", "--policy", str(self.policy_path))
        self.assertEqual(code, 0, out + err)
        attest(self.project, "password-reset", self.policy, "ci", self.keys["ci"], "https://ci.example/runs/1")
        self.write_review(self.project.fingerprint())
        self.approve("acceptance", "qa")

    def approve(self, phase, role, expires=None):
        return approve(self.project, "password-reset", phase, role, self.keys[role], self.policy, expires=expires)
