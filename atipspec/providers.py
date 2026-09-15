"""Read-only GitHub/GitLab approval adapters. No remote writes or auto-approvals."""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from .errors import AtipSpecError
from .trust import PHASE_ROLES, approval_path, sign_document, subject, timestamp


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AtipSpecError("Approval API redirect refused")


class API:
    def __init__(self, policy):
        self.config = policy.data.get("provider", {})
        self.kind = self.config.get("kind")
        if self.kind not in ("github", "gitlab"):
            raise AtipSpecError("Configure a github or gitlab provider in the external policy")
        default = "https://api.github.com" if self.kind == "github" else "https://gitlab.com/api/v4"
        self.base = self.config.get("api_url", default).rstrip("/")
        parsed = urllib.parse.urlsplit(self.base)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
            raise AtipSpecError("Approval API must use an HTTPS origin without embedded credentials")
        token_name = "GITHUB_TOKEN" if self.kind == "github" else "GITLAB_TOKEN"
        self.token = os.environ.get(token_name)
        if not self.token:
            raise AtipSpecError(f"Set {token_name} for read-only approval verification")
        repository = self.config.get("repository")
        if not isinstance(repository, str) or not repository or repository != policy.data["repository"]:
            raise AtipSpecError("Provider repository must match the trust policy repository")
        encoded = urllib.parse.quote(repository, safe="/" if self.kind == "github" else "")
        self.prefix = ("/repos/" if self.kind == "github" else "/projects/") + encoded

    def get(self, path):
        headers = {"Accept": "application/json", "User-Agent": "atipspec"}
        if self.kind == "github":
            headers["Authorization"] = f"Bearer {self.token}"
        else:
            headers["PRIVATE-TOKEN"] = self.token
        request = urllib.request.Request(self.base + path, headers=headers)
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
                raw = response.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise AtipSpecError("Approval API response is too large")
                return json.loads(raw)
        except (urllib.error.URLError, ValueError) as exc:
            # Do not echo URLs, headers or response bodies carrying credentials.
            raise AtipSpecError("Approval API request failed; check access and connectivity") from exc

    def pages(self, path):
        items = []
        for page in range(1, 101):
            result = self.get(f"{path}?per_page=100&page={page}")
            if not isinstance(result, list):
                raise AtipSpecError("Unexpected approval API list response")
            items.extend(result)
            if len(result) < 100:
                return items
        raise AtipSpecError("Too many approval records; refusing a partial verification")


def marker(slug, phase, subject_hash, head):
    return f"ATIPSPEC-APPROVE {slug} {phase} {subject_hash} {head}"


def fetch_approvals(project, slug, phase, policy, number):
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise AtipSpecError("PR/MR number must be positive")
    api = API(policy)
    role = PHASE_ROLES.get(phase.split(":")[0])
    if not role:
        raise AtipSpecError("Unknown approval phase")
    allowed = api.config.get("roles", {}).get(role, [])
    if not isinstance(allowed, list) or not allowed:
        raise AtipSpecError(f"No provider users enrolled for role {role}")
    current_subject = subject(project, slug, phase)
    head = project.git.head()
    expected = marker(slug, phase, current_subject, head)
    records = []
    if api.kind == "github":
        prefix = f"{api.prefix}/pulls/{number}"
        pull = api.get(prefix)
        if pull.get("state") != "open" or pull.get("head", {}).get("sha") != head:
            raise AtipSpecError("PR must be open and its head must match this checkout")
        if pull.get("base", {}).get("repo", {}).get("full_name") != policy.data["repository"]:
            raise AtipSpecError("PR target repository mismatch")
        author = pull.get("user", {}).get("login")
        latest = {}
        for review in api.pages(prefix + "/reviews"):
            if review.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
                user = review.get("user", {})
                latest[user.get("login")] = review
        for login, review in latest.items():
            if (login in allowed and login != author and review.get("user", {}).get("type") == "User"
                and review.get("state") == "APPROVED" and review.get("commit_id") == head
                and expected in (review.get("body") or "").splitlines()):
                records.append({"identity": login, "approved_at": review["submitted_at"],
                                "url": review["html_url"], "provider_id": review["id"]})
    else:
        prefix = f"{api.prefix}/merge_requests/{number}"
        merge = api.get(prefix)
        if merge.get("state") != "opened" or merge.get("sha") != head:
            raise AtipSpecError("MR must be open and its head must match this checkout")
        author = merge.get("author", {}).get("username")
        state = api.get(prefix + "/approvals")
        approved = {entry.get("user", {}).get("username") for entry in state.get("approved_by", [])}
        for note in api.pages(prefix + "/notes"):
            user = note.get("author", {})
            login = user.get("username")
            if (note.get("system") is False and login in allowed and login in approved and login != author
                and expected in (note.get("body") or "").splitlines()):
                account = api.get("/users/" + str(int(user["id"])))
                if account.get("bot") is not False or account.get("state") != "active":
                    continue
                records.append({"identity": login, "approved_at": note["created_at"],
                                "url": merge["web_url"] + "#note_" + str(note["id"]), "provider_id": note["id"]})
    # Guard head movement while reading paginated responses.
    latest_change = api.get(prefix)
    latest_head = latest_change.get("head", {}).get("sha") if api.kind == "github" else latest_change.get("sha")
    if latest_head != head:
        raise AtipSpecError("PR/MR changed while approvals were read; retry")
    return [{**record, "schema": 1, "kind": "approval", "delivery": slug, "phase": phase,
             "subject": current_subject, "role": role, "source": api.kind,
             "number": number, "head": head} for record in records]


def sync_approvals(project, slug, phase, policy, number, identity, key: Path, expires=None):
    from .trust import date_time
    from datetime import datetime, timezone
    if phase.startswith("exception:") and (not expires or date_time(expires) <= datetime.now(timezone.utc)):
        raise AtipSpecError("Exception approval needs a future --expires timestamp")
    records = fetch_approvals(project, slug, phase, policy, number)
    if not records:
        raise AtipSpecError("No current human approval matches the required marker and role")
    paths = []
    for record in records:
        path = approval_path(project, slug, phase, record["identity"])
        sign_document(path, {**record, "expires": expires, "collected_at": timestamp()}, identity, key,
                      policy, "collector", project.root)
        paths.append(path)
    return paths


def refresh_approval(project, record, policy):
    try:
        fresh = fetch_approvals(project, record["delivery"], record["phase"], policy, record["number"])
        return any(all(item.get(key) == record.get(key) for key in
                       ("identity", "provider_id", "head", "subject", "approved_at", "source")) for item in fresh)
    except (AtipSpecError, KeyError, TypeError, ValueError):
        return False
