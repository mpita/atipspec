"""Project discovery, layout, configuration and policies."""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
import re

from . import frontmatter
from .errors import AtipSpecError
from .gitrepo import Git

SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
# Files a delivery produces about itself must not change the tree they describe.
FINGERPRINT_EXCLUDES = ("evidence", "review.md", "deferred.md", "approvals", "reports")
DEFAULT_POLICIES = {"approve_plan": True, "review_rounds": 2, "context_budget": 800, "strict_scope": False,
                    "criteria_syntax": "ears", "strict_criteria": False,
                    "max_requirements": 5, "max_tasks": 8, "max_age_hours": 48}


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
                return cls(candidate, data)
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
        return DEFAULT_POLICIES[key] if value is None else value

    @property
    def system(self) -> Path | None:
        """Optional checkout of the system-level repository (multi-repo projects)."""
        value = self.config.get("system")
        if not value:
            return None
        path = Path(str(value))
        return path if path.is_absolute() else self.root / path

    # Git --------------------------------------------------------------------
    @property
    def git(self) -> Git:
        if self._git is None:
            self._git = Git(self.root)
        return self._git

    def fingerprint(self) -> str | None:
        return self.fingerprint_at()

    def fingerprint_at(self, rev: str | None = None) -> str | None:
        """Working-tree hash with every delivery's own evidence, review and deferred
        files left out, so writing them never makes them stale. None without git."""
        if not self.git.available:
            return None
        exclude = [".atipspec/tmp"]
        for slug in self.list_deliveries():
            exclude.extend(f".atipspec/deliveries/{slug}/{name}" for name in FINGERPRINT_EXCLUDES)
        return self.git.fingerprint(exclude, rev)

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
