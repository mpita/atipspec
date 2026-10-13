"""Project discovery, layout, configuration and policies."""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
import math
from pathlib import Path
import re

from . import frontmatter
from .errors import AtipSpecError
from .gitrepo import Git

SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
# Files a delivery produces about itself must not change the tree they describe.
FINGERPRINT_EXCLUDES = ("evidence", "review.md", "deferred.md", "approvals", "reports", "progress.json", "run.json",
                        "review-rounds.json")
# Every delivery plan, whose task titles may change without changing what was verified.
PLANS = ":(glob).atipspec/deliveries/*/plan.md"
DEFAULT_POLICIES = {"approve_plan": True, "review_rounds": 3, "context_budget": 800, "strict_scope": True,
                    "criteria_syntax": "ears", "strict_criteria": True,
                    "max_requirements": 5, "max_tasks": 8, "max_age_hours": 8, "trust": "optional",
                    "require_proof": False, "require_isolated_review": False, "exempt_paths": []}
# The values a text policy accepts; the others take their default's type, and
# numbers must be positive. Hours may be fractional, as 0.2.x read them. A list
# holds globs.
POLICY_CHOICES = {"criteria_syntax": ("ears", "free"), "trust": ("optional", "required")}
FRACTIONAL = ("max_age_hours",)


def globs(value) -> bool:
    """Whether a configured value is a list of path globs."""
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def resource_root() -> Path:
    return Path(str(resources.files("atipspec") / "resources"))


def template(name: str) -> str:
    return (resource_root() / "framework" / "templates" / name).read_text(encoding="utf-8")


def validate_slug(slug: str, what: str = "slug") -> str:
    if not SLUG.match(slug):
        raise AtipSpecError(f"Invalid {what} {slug!r}: use lowercase letters, digits and hyphens.")
    return slug


@dataclass
class Project:
    root: Path
    config: dict = field(default_factory=dict)
    _git: Git | None = field(default=None, repr=False)
    cloned_from: Path | None = field(default=None, repr=False)  # the checkout a temporary clone was made from

    @classmethod
    def find(cls, start: Path | None = None) -> "Project":
        current = (start or Path.cwd()).resolve()
        for candidate in (current, *current.parents):
            config = candidate / ".atipspec" / "config.yaml"
            if config.is_file():
                try:
                    data = frontmatter.parse(config.read_text(encoding="utf-8"))
                except ValueError as exc:
                    raise AtipSpecError(f"Invalid {config}: {exc}") from exc
                project = cls(candidate, data)
                project.validate()
                return project
        raise AtipSpecError("AtipSpec is not initialized here. Run: atipspec init")

    # Layout ---------------------------------------------------------------
    @property
    def dot(self) -> Path:
        return self.root / ".atipspec"

    @property
    def specs(self) -> Path:
        return self.dot / "specs"

    @property
    def deliveries(self) -> Path:
        return self.dot / "deliveries"

    @property
    def archive(self) -> Path:
        return self.dot / "archive"

    @property
    def decisions(self) -> Path:
        return self.dot / "decisions"

    @property
    def initiatives(self) -> Path:
        return self.dot / "initiatives"

    @property
    def framework(self) -> Path:
        return self.dot / "framework"

    @property
    def tmp(self) -> Path:
        return self.dot / "tmp"

    @property
    def approvals(self) -> Path:
        return self.dot / "approvals"

    @property
    def contract(self) -> Path:
        return self.dot / "contract.md"

    @property
    def overview(self) -> Path:
        return self.dot / "overview.md"

    @property
    def glossary(self) -> Path:
        return self.dot / "glossary.md"

    # Configuration ----------------------------------------------------------
    @property
    def name(self) -> str:
        return str(self.config.get("name") or self.root.name)

    @property
    def language(self) -> str:
        return str(self.config.get("language") or "en")

    def policy(self, key: str):
        value = self.config.get(key)
        if value is None:
            return DEFAULT_POLICIES[key]
        default = DEFAULT_POLICIES[key]
        if key in POLICY_CHOICES:
            valid, expected = value in POLICY_CHOICES[key], " or ".join(POLICY_CHOICES[key])
        elif isinstance(default, bool):
            valid, expected = isinstance(value, bool), "true or false"
        elif isinstance(default, list):
            valid, expected = globs(value), "a list of globs, such as [\"docs/**\"]"
        elif key in FRACTIONAL:
            try:
                number = float(value) if not isinstance(value, bool) else 0.0
            except (TypeError, ValueError):
                number = 0.0
            valid, expected = math.isfinite(number) and number > 0, "a positive number"
            value = value if type(value) is int else number
        else:
            valid, expected = type(value) is int and value > 0, "a positive whole number"
        if not valid:
            raise AtipSpecError(f"Invalid .atipspec/config.yaml: {key} must be {expected}, found {value!r}")
        return value

    def validate(self) -> None:
        """Reject any policy value the CLI would misread, before a command runs."""
        for key in DEFAULT_POLICIES:
            self.policy(key)

    def requirement(self, key: str, policy=None) -> bool:
        """A boolean requirement, on when config.yaml or the selected trust
        policy sets it: the organization's policy cannot be relaxed here."""
        return bool(self.policy(key)) or (policy is not None and policy.data.get(key) is True)

    @property
    def trust_required(self) -> bool:
        """`trust: required`: the gate, acceptance and delivery need an external trust policy."""
        return self.policy("trust") == "required"

    @property
    def system(self) -> Path | None:
        """Optional checkout of the system-level repository (multi-repo projects)."""
        value = self.config.get("system")
        if not value:
            return None
        return self.local_path(value)

    def local_path(self, value) -> Path:
        """A local checkout that config.yaml or teams.json names: a relative path
        starts at the project root, or at the checkout a temporary clone was made from."""
        path = Path(str(value))
        return path if path.is_absolute() else (self.cloned_from or self.root) / path

    # Git --------------------------------------------------------------------
    @property
    def git(self) -> Git:
        if self._git is None:
            self._git = Git(self.root)
        return self._git

    def fingerprint(self) -> str | None:
        return self.fingerprint_at()

    def _excluded(self, slugs: list[str] | None = None) -> list[str]:
        exclude = [".atipspec/tmp", ".atipspec/approvals"]
        for slug in self.list_deliveries() if slugs is None else slugs:
            exclude.extend(f".atipspec/deliveries/{slug}/{name}" for name in FINGERPRINT_EXCLUDES)
        return exclude

    def fingerprint_at(self, rev: str | None = None, slugs: list[str] | None = None) -> str | None:
        """Working-tree hash with every delivery's own evidence, review and deferred
        files, and the project's approval records, left out, so writing them never
        makes them stale, and the task headings of every delivery plan reduced to
        their ids (`### T1:`), so renaming a task does not change what was
        verified. `slugs` names the deliveries to leave those files out for (the
        working tree's by default). None without git."""
        if not self.git.available:
            return None
        from .delivery import without_task_titles
        return self.git.fingerprint(self._excluded(slugs), rev, rewrite=(PLANS, without_task_titles))

    def same_candidate(self, recorded: str | None, current: str | None) -> bool:
        """Whether evidence or a review recorded for the tree `recorded` still
        holds for `current`: the same fingerprint."""
        return bool(recorded) and recorded == current

    def code_fingerprint(self, rev: str | None = None) -> str:
        """Hash of everything outside .atipspec/: the code a delivery receipt
        vouches for. `deliver` and later AtipSpec bookkeeping never change it."""
        if not self.git.available:
            raise AtipSpecError("git is required: a delivery receipt binds the code tree")
        return self.git.fingerprint([".atipspec"], rev)

    # Collections ------------------------------------------------------------
    def list_deliveries(self) -> list[str]:
        if not self.deliveries.is_dir():
            return []
        return sorted(path.name for path in self.deliveries.iterdir() if (path / "spec.md").is_file())

    def list_archived(self) -> list[str]:
        if not self.archive.is_dir():
            return []
        return sorted(path.name for path in self.archive.iterdir() if (path / "spec.md").is_file())

    def list_capabilities(self) -> list[str]:
        return sorted(path.stem for path in self.specs.glob("*.md")) if self.specs.is_dir() else []

    def list_decisions(self) -> list[Path]:
        return sorted(self.decisions.glob("DEC-*.md")) if self.decisions.is_dir() else []

    def list_initiatives(self) -> list[str]:
        if not self.initiatives.is_dir():
            return []
        return sorted(path.name for path in self.initiatives.iterdir() if (path / "roadmap.md").is_file())

    def delivery_dir(self, slug: str, must_exist: bool = True) -> Path:
        validate_slug(slug)
        path = self.deliveries / slug
        if must_exist and not (path / "spec.md").is_file():
            raise AtipSpecError(f"Delivery not found: {slug}. Run `atipspec status` to list deliveries.")
        return path

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)
