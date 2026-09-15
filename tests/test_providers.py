from unittest.mock import patch

from atipspec.providers import fetch_approvals, marker, sync_approvals
from atipspec.trust import subject, valid_approvals
from tests.trust_helpers import TrustedCase


class ProviderTests(TrustedCase):
    def setup_provider(self, kind="github"):
        self.prepare()
        self.policy.data["provider"] = {"kind": kind, "repository": "example/demo", "roles": {"qa": ["reviewer"]}}
        self.head = self.project.git.head()
        self.text = marker("password-reset", "acceptance", subject(self.project, "password-reset", "acceptance"), self.head)

    def test_github_accepts_human_current_head_and_detects_revocation(self):
        self.setup_provider()
        pull = {"state": "open", "head": {"sha": self.head}, "base": {"repo": {"full_name": "example/demo"}}, "user": {"login": "author"}}
        review = {"id": 7, "state": "APPROVED", "commit_id": self.head, "user": {"login": "reviewer", "type": "User"},
                  "body": self.text, "submitted_at": "2026-01-01T00:00:00Z", "html_url": "https://github.com/example/demo/pull/1#review-7"}
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-only"}), patch("atipspec.providers.API.get", return_value=pull), patch("atipspec.providers.API.pages", return_value=[review]) as pages:
            records = fetch_approvals(self.project, "password-reset", "acceptance", self.policy, 1)
            self.assertEqual(len(records), 1)
            sync_approvals(self.project, "password-reset", "acceptance", self.policy, 1, "collector", self.keys["collector"])
            self.assertTrue(any(a["source"] == "github" for a in valid_approvals(self.project, "password-reset", "acceptance", self.policy, "author")))
            pages.return_value = [review, {**review, "id": 8, "state": "CHANGES_REQUESTED"}]
            self.assertFalse(any(a["source"] == "github" for a in valid_approvals(self.project, "password-reset", "acceptance", self.policy, "author")))
            for invalid in ({"commit_id": "old"}, {"user": {"login": "reviewer", "type": "Bot"}}, {"user": {"login": "author", "type": "User"}}, {"body": self.text + "changed"}):
                pages.return_value = [{**review, **invalid}]
                self.assertEqual(fetch_approvals(self.project, "password-reset", "acceptance", self.policy, 1), [])

    def test_gitlab_needs_approval_note_current_head_and_non_bot(self):
        self.setup_provider("gitlab")
        merge = {"state": "opened", "sha": self.head, "author": {"username": "author"}, "web_url": "https://gitlab.com/example/demo/-/merge_requests/1"}
        state = {"approved_by": [{"user": {"username": "reviewer"}}]}
        account = {"bot": False, "state": "active"}
        note = {"id": 9, "system": False, "author": {"username": "reviewer", "id": 3}, "body": self.text, "created_at": "2026-01-01T00:00:00Z"}
        def get(path):
            if path.endswith("/approvals"):
                return state
            if path.startswith("/users/"):
                return account
            return merge
        with patch.dict("os.environ", {"GITLAB_TOKEN": "test-only"}), patch("atipspec.providers.API.get", side_effect=get), patch("atipspec.providers.API.pages", return_value=[note]):
            self.assertEqual(len(fetch_approvals(self.project, "password-reset", "acceptance", self.policy, 1)), 1)
            account["bot"] = True
            self.assertEqual(fetch_approvals(self.project, "password-reset", "acceptance", self.policy, 1), [])
            account["bot"] = False
            state["approved_by"] = []
            self.assertEqual(fetch_approvals(self.project, "password-reset", "acceptance", self.policy, 1), [])
