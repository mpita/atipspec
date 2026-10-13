"""Initialize a project, install or update the framework and client skills,
and manage an already initialized project."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from . import __version__, frontmatter, ui
from .errors import AtipSpecError
from .gitrepo import Git
from .project import DEFAULT_POLICIES, resource_root, template


@dataclass(frozen=True)
class Client:
    label: str
    skills: str          # the client's skills directory; one subdirectory per AtipSpec skill
    hint: str

    @property
    def path(self) -> str:
        """The umbrella skill, whose presence means the client is installed."""
        return f"{self.skills}/atipspec/SKILL.md"

    def skill_path(self, name: str) -> str:
        return f"{self.skills}/{name}/SKILL.md"


CLIENTS = {
    "claude": Client("Claude Code", ".claude/skills",
                     "run /atipspec-contract to define the contract, then /atipspec-spec <slug>: what you want"),
    "codex": Client("Codex", ".agents/skills",
                    "run $atipspec-contract to define the contract, then $atipspec-spec <slug>: what you want"),
    "cursor": Client("Cursor", ".cursor/skills",
                     "pick atipspec-contract in the skill picker, then atipspec-spec for each delivery"),
    "github-copilot": Client("GitHub Copilot", ".github/skills",
                             "in agent mode, ask Copilot to use the atipspec-contract skill, then atipspec-spec"),
    "antigravity": Client("Antigravity", ".agents/skills",
                          "ask the agent to use the atipspec-contract skill, then atipspec-spec"),
    "gemini": Client("Gemini CLI", ".gemini/skills",
                     "check /skills list, then ask it to use atipspec-contract and atipspec-spec"),
}
CLIENT_PATHS = {key: client.path for key, client in CLIENTS.items()}


@dataclass(frozen=True)
class PermissionRules:
    settings: str                # the client's shared, versioned settings file
    ask: tuple[str, ...]         # commands and edits the client must ask the human about
    deny: tuple[str, ...]        # paths the client's edit tools must not write


# Only clients whose project settings make the client ask the human before a
# command are listed; the others record approvals through channel `assistant`.
# Editing the CI that runs merge-check, or the settings that hold these rules,
# also asks.
PERMISSION_RULES = {
    "claude": PermissionRules(".claude/settings.json",
                              ("Bash(*atipspec accept *)", "Edit(/.github/workflows/**)", "Edit(/.gitlab-ci.yml)",
                               "Edit(/.claude/settings*.json)"),
                              ("Edit(/.atipspec/deliveries/*/approvals/**)", "Edit(/.atipspec/deliveries/*/evidence/**)",
                               "Edit(/.atipspec/deliveries/*/review-rounds.json)", "Edit(/.atipspec/approvals/**)",
                               "Edit(/.atipspec/archive/**)")),
}
PROJECT_FOLDERS = ("specs", "deliveries", "archive", "decisions", "initiatives")
PROJECT_DOCUMENTS = ("contract.md", "overview.md", "glossary.md")
DOT_GITIGNORE = "# AtipSpec: review packets and other scratch files\ntmp/\n"
FRAMEWORK = ".atipspec/framework"


# --- files -----------------------------------------------------------------

def shipped_framework() -> dict[str, bytes]:
    """Each framework file this version installs, by its path under
    .atipspec/framework/, with its content."""
    source = resource_root() / "framework"
    files = {resource.relative_to(source).as_posix(): resource.read_bytes()
             for resource in sorted(source.rglob("*")) if resource.is_file()}
    if not files:
        raise AtipSpecError(f"Framework resources are missing from {source}.")
    return files


def shipped_skills() -> dict[str, bytes]:
    """Skill name → shipped SKILL.md content: the umbrella plus one per phase."""
    source = resource_root() / "skills"
    skills = {path.parent.name: path.read_bytes() for path in sorted(source.glob("*/SKILL.md"))}
    if "atipspec" not in skills:
        raise AtipSpecError(f"Skill resources are missing from {source}.")
    return skills


def shipped_skill() -> bytes:
    return shipped_skills()["atipspec"]


def client_files(root: Path, client: str) -> dict[Path, bytes]:
    """Every skill file of one client."""
    if client not in CLIENTS:
        raise AtipSpecError(f"Unsupported client: {client}")
    return {root / CLIENTS[client].skill_path(name): content for name, content in shipped_skills().items()}


def installation_files(root: Path, clients: list[str]) -> dict[Path, bytes]:
    """Framework files plus the skill files of each client, with shipped content."""
    files = {root / FRAMEWORK / name: content for name, content in shipped_framework().items()}
    for client in clients:
        files.update(client_files(root, client))
    return files


def holds(path: Path, content: bytes) -> bool:
    """Whether a file holds the shipped content, with CRLF read as LF: Git for
    Windows checks committed skills and framework files out with CRLF."""
    return path.is_file() and path.read_bytes().replace(b"\r\n", b"\n") == content.replace(b"\r\n", b"\n")


def classify(files: dict[Path, bytes]) -> dict[Path, str]:
    """For each target: 'missing', 'same' or 'differs' from the shipped content."""
    states = {}
    for path, content in files.items():
        if not path.exists():
            states[path] = "missing"
        elif holds(path, content):
            states[path] = "same"
        else:
            states[path] = "differs"
    return states


def write_installation(root: Path, files: dict[Path, bytes]) -> tuple[int, list[Path]]:
    """Create the missing files and keep the differing ones untouched (returned).
    Symlinked paths are refused; newly created files are removed on failure."""
    pending, kept = {}, []
    for path, content in files.items():
        for component in (path, *path.parents):
            if component == root:
                break
            if component.is_symlink():
                raise AtipSpecError(f"Installation path must not be a symlink: {component}")
            if component != path and component.exists() and not component.is_dir():
                raise AtipSpecError(f"Installation parent is not a directory: {component}")
        if not path.exists():
            pending[path] = content
        elif not holds(path, content):
            kept.append(path)
    created_files: list[Path] = []
    created_directories: list[Path] = []
    try:
        for path, content in pending.items():
            missing = []
            parent = path.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for parent in reversed(missing):
                parent.mkdir()
                created_directories.append(parent)
            with path.open("xb") as handle:
                created_files.append(path)
                handle.write(content)
    except BaseException:
        for path in reversed(created_files):
            path.unlink()
        for path in reversed(created_directories):
            path.rmdir()
        raise
    return len(created_files), kept


def overwrite_files(files: dict[Path, bytes]) -> None:
    """Replace existing files atomically (temporary file, then rename)."""
    for path, content in files.items():
        descriptor, temp = tempfile.mkstemp(prefix=".atipspec-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
            os.replace(temp, path)
        except BaseException:
            if os.path.exists(temp):
                os.unlink(temp)
            raise


def installed_clients(root: Path) -> dict[str, str]:
    """Clients whose umbrella skill exists: key → 'installed' when every skill
    matches this version and its permission rules are in place, 'outdated' otherwise."""
    found = {}
    for key, client in CLIENTS.items():
        if (root / client.path).is_file():
            states = classify(client_files(root, key))
            current = all(state == "same" for state in states.values())
            if key in PERMISSION_RULES and permission_rules_state(root, key) != "installed":
                current = False
            found[key] = "installed" if current else "outdated"
    return found


# --- client permission rules ------------------------------------------------

def _read_settings(root: Path, rules: PermissionRules) -> tuple[dict | None, str | None]:
    """The client's settings as a JSON object ({} when the file does not exist),
    or None and the reason when AtipSpec cannot merge into it safely."""
    path = root / rules.settings
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            return None, f"{_rel(root, component)} is a symlink"
    if not path.exists():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None, f"{rules.settings} is not plain JSON"
    if not isinstance(data, dict):
        return None, f"{rules.settings} is not a JSON object"
    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict) or not all(isinstance(permissions.get(name, []), list) for name in ("ask", "deny")):
        return None, f"{rules.settings} has a `permissions` value whose ask and deny are not lists"
    return data, None


def permission_rules_state(root: Path, key: str) -> str:
    """'installed', 'partial', 'missing' or 'invalid' (cannot be read or merged);
    'none' for a client without a permission mechanism AtipSpec configures."""
    rules = PERMISSION_RULES.get(key)
    if rules is None:
        return "none"
    absent = missing_permission_rules(root, key)
    if absent is None:
        return "invalid"
    return "installed" if not absent else "missing" if len(absent) == len(rules.ask) + len(rules.deny) else "partial"


def missing_permission_rules(root: Path, key: str) -> list[str] | None:
    """The client's AtipSpec rules its settings lack, as `ask Rule` or `deny
    Rule`; None when the settings cannot be read or merged."""
    rules = PERMISSION_RULES[key]
    data, _ = _read_settings(root, rules)
    if data is None:
        return None
    permissions = data.get("permissions", {})
    return [f"{name} {rule}" for name in ("ask", "deny") for rule in getattr(rules, name)
            if rule not in permissions.get(name, [])]


# Claude Code hooks that can allow a Bash command before or instead of its prompt; `ask` rules ask in
# every permission mode, so no mode is listed.
ANSWERING_HOOKS = ("PreToolUse", "PermissionRequest")
CLAUDE_SETTINGS = (".claude/settings.json", ".claude/settings.local.json")


def permission_overrides(root: Path, key: str) -> list[str]:
    """What in the project's settings files lets the client run `atipspec
    accept` without asking, despite its rules: a hook that can answer the
    prompt. User and managed settings and command-line flags are outside the
    project, and the CLI cannot see them."""
    if key != "claude":
        return []
    found = []
    for name in CLAUDE_SETTINGS:
        path = root / name
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        except (OSError, UnicodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        hooks = data.get("hooks") if isinstance(data.get("hooks"), dict) else {}
        for event in ANSWERING_HOOKS:
            entries = hooks.get(event) if isinstance(hooks.get(event), list) else []
            if any(_matches_bash(entry.get("matcher") if isinstance(entry, dict) else None) for entry in entries):
                found.append(f"{name} has a {event} hook that runs for Bash")
    return found


def _matches_bash(matcher) -> bool:
    """Whether a hook matcher selects the Bash tool: empty and `*` select every
    tool; one that is not a valid pattern counts as selecting it."""
    if matcher in (None, "", "*"):
        return True
    try:
        return re.fullmatch(str(matcher), "Bash") is not None
    except re.error:
        return True


def install_permission_rules(root: Path, key: str) -> tuple[str, str | None]:
    """Add the missing AtipSpec rules to the client's settings, keeping every
    other key and entry. Returns 'created', 'added', 'present', 'invalid' (with
    the reason; nothing is written) or 'none'. Never raises for the file."""
    rules = PERMISSION_RULES.get(key)
    if rules is None:
        return "none", None
    data, problem = _read_settings(root, rules)
    if data is None:
        return "invalid", problem
    path = root / rules.settings
    existed = path.exists()
    permissions = data.setdefault("permissions", {})
    changed = False
    for name in ("ask", "deny"):
        current = permissions.setdefault(name, [])
        for rule in getattr(rules, name):
            if rule not in current:
                current.append(rule)
                changed = True
    if not changed:
        return "present", None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        overwrite_files({path: (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")})
    except OSError as exc:
        return "invalid", f"{rules.settings} could not be written ({exc})"
    return ("added" if existed else "created"), None


def remove_permission_rules(root: Path, key: str) -> bool:
    """Remove only the AtipSpec rules; the file goes when nothing else is left."""
    rules = PERMISSION_RULES.get(key)
    if rules is None:
        return False
    data, _ = _read_settings(root, rules)
    path = root / rules.settings
    if not data or not path.is_file():
        return False
    permissions = data.get("permissions", {})
    changed = False
    for name in ("ask", "deny"):
        if name in permissions:
            kept = [rule for rule in permissions[name] if rule not in getattr(rules, name)]
            if kept != permissions[name]:
                changed = True
                if kept:
                    permissions[name] = kept
                else:
                    del permissions[name]
    if not changed:
        return False
    if not permissions:
        del data["permissions"]
    if data:
        overwrite_files({path: (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")})
    else:
        path.unlink()
    return True


def _without_rules(data, rules: PermissionRules):
    """Settings with AtipSpec's rules removed, and the lists and block they leave empty."""
    if not isinstance(data, dict) or not isinstance(data.get("permissions"), dict):
        return data
    permissions = dict(data["permissions"])
    for name in ("ask", "deny"):
        if isinstance(permissions.get(name), list):
            permissions[name] = [rule for rule in permissions[name] if rule not in getattr(rules, name)]
            if not permissions[name]:
                del permissions[name]
    data = {key: value for key, value in data.items() if key != "permissions"}
    return {**data, "permissions": permissions} if permissions else data


def _rules_in(data, rules: PermissionRules) -> set[tuple[str, str]]:
    """AtipSpec's permission rules the settings hold, as (list, rule)."""
    permissions = data.get("permissions") if isinstance(data, dict) else None
    if not isinstance(permissions, dict):
        return set()
    return {(name, rule) for name in ("ask", "deny") if isinstance(permissions.get(name), list)
            for rule in getattr(rules, name) if rule in permissions[name]}


def installed_unchanged(root: Path, name: str, before: Callable[[], str | None]) -> bool:
    """Whether a changed file (relative to root) holds only what AtipSpec
    installs: a client skill identical to this version's, or client settings
    whose only difference from their earlier text, `before()` (None when
    absent), is AtipSpec's permission rules added. A user's edit, or removing
    one of those rules, makes it count."""
    path = root / name
    folder, _, skill = name.rpartition("/")[0].rpartition("/")
    if any(folder == client.skills for client in CLIENTS.values()) and name.endswith("/SKILL.md"):
        content = shipped_skills().get(skill)
        return content is not None and not path.is_symlink() and holds(path, content)
    for rules in PERMISSION_RULES.values():
        if name == rules.settings and not path.is_symlink():
            try:
                now = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
                earlier = before()
                then = json.loads(earlier) if earlier is not None else {}
            except (OSError, UnicodeError, ValueError):
                return False
            return (_without_rules(now, rules) == _without_rules(then, rules)
                    and _rules_in(then, rules) <= _rules_in(now, rules))
    return False


def permission_rules_text(key: str) -> str:
    rules = PERMISSION_RULES[key]
    return json.dumps({"permissions": {"ask": list(rules.ask), "deny": list(rules.deny)}})


def permission_summary(root: Path) -> str:
    """One line for `status`: how an assistant's `atipspec accept` reaches the human."""
    installed = installed_clients(root)
    parts = []
    for key in installed:
        if key not in PERMISSION_RULES:
            continue
        state = permission_rules_state(root, key)
        overrides = permission_overrides(root, key)
        if state == "installed" and overrides:
            parts.append(f"{CLIENTS[key].label} may not ask before `atipspec accept`: {'; '.join(overrides)}; "
                         "its acceptances are recorded as channel assistant")
        elif state == "installed":
            parts.append(f"{CLIENTS[key].label} asks before `atipspec accept` and before editing CI workflows or its "
                         "settings, and cannot edit approval, evidence or review round records")
        else:
            parts.append(f"{CLIENTS[key].label} permission rules {state} (`atipspec install --update`); "
                         "until then its acceptances are recorded as channel assistant")
    others = [CLIENTS[key].label for key in installed if key not in PERMISSION_RULES]
    if others:
        parts.append(f"{', '.join(others)}: no permission rules, acceptances are recorded as channel assistant")
    return "; ".join(parts) or "no client permission rules: an assistant's acceptance is recorded as channel assistant"


def pending_updates(root: Path, clients: list[str]) -> dict[Path, bytes]:
    """Framework and skill files that are missing or differ from this version."""
    files = installation_files(root, clients)
    states = classify(files)
    return {path: content for path, content in files.items() if states[path] != "same"}


def framework_extras(root: Path, git: Git | None = None) -> list[Path]:
    """Files under .atipspec/framework/ that this version does not install,
    but those git ignores."""
    folder = root / FRAMEWORK
    if not folder.is_dir() or folder.is_symlink():
        return []
    shipped = shipped_framework()
    found = [path for path in sorted(folder.rglob("*"))
             if (path.is_file() or path.is_symlink()) and path.relative_to(folder).as_posix() not in shipped]
    if found:
        git = git or Git(root)
        found = [path for path in found if not (git.available and git.ignored(_rel(root, path)))]
    return found


def framework_changes(root: Path, git: Git | None = None) -> list[str]:
    """How .atipspec/framework/ differs from what this version installs: one
    `<path> changed`, `<path> missing` or `<path> added` per file."""
    found = []
    for name, content in shipped_framework().items():
        path = root / FRAMEWORK / name
        if not path.exists():
            found.append(f"{name} missing")
        elif not holds(path, content):
            found.append(f"{name} changed")
    return found + [f"{path.relative_to(root / FRAMEWORK).as_posix()} added" for path in framework_extras(root, git)]


def framework_problem(root: Path, git: Git | None = None) -> str | None:
    """The error `audit`, `check` and `merge-check` give while
    .atipspec/framework/ is not what this version installs, or None: every
    phase prints its rules and workflows to the agent, and no delivery's
    approval covers them, so only `install --update` writes them."""
    changes = framework_changes(root, git)
    if not changes:
        return None
    shown = ", ".join(changes[:10]) + (", ..." if len(changes) > 10 else "")
    return (f".atipspec/framework/ is not what AtipSpec {__version__} installs ({shown}): every phase prints these "
            "rules and workflows to the agent, and no delivery's approval covers a change to them; run `atipspec "
            "install --update` with the AtipSpec version the project and its CI use")


def write_config(root: Path, name: str, language: str) -> None:
    """Write name and language, keeping any other configured policy."""
    path = root / ".atipspec" / "config.yaml"
    current = {}
    if path.is_file():
        try:
            current = frontmatter.parse(path.read_text(encoding="utf-8"))
        except ValueError:
            current = {}
    config = {"name": name, "language": language, **{k: v for k, v in DEFAULT_POLICIES.items()}}
    config.update({key: value for key, value in current.items() if key not in ("name", "language")})
    path.write_text(frontmatter.dump(config)[4:-4], encoding="utf-8", newline="\n")


def config_differences(root: Path) -> list[str]:
    """The policies config.yaml sets differently from this version's defaults,
    or leaves unset, for `install --update` to report without editing."""
    try:
        config = frontmatter.parse((root / ".atipspec" / "config.yaml").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    def written(value) -> str:
        if isinstance(value, list):
            return "[" + ", ".join(written(item) for item in value) + "]"
        return frontmatter.dump({"v": value})[len("---\nv: "):-len("\n---\n")]
    found = []
    for key, default in DEFAULT_POLICIES.items():
        value = config.get(key)
        if value is None:
            found.append(f"{key} is not set (default {written(default)} applies)")
        elif value != default or type(value) is not type(default):
            found.append(f"{key}: {written(value)} (default {written(default)})")
    return found


# --- presentation ----------------------------------------------------------

def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _labels(clients) -> str:
    return ", ".join(CLIENTS[key].label for key in dict.fromkeys(clients)) or "none"


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def choose_clients(preselected=()) -> list[str]:
    """Ask which clients to configure; without a terminal, keep the preselection."""
    return ui.select_many("Which clients do you use?",
                          [(key, client.label) for key, client in CLIENTS.items()], preselected)


LANGUAGE_OPTIONS = [("en", "English"), ("es", "Español"), ("pt", "Português"), ("other", "Other (type a code)")]


def choose_language(current: str = "en") -> str:
    """Ask for the output language among the supported ones; without a terminal, keep the current one."""
    if not ui.interactive():
        return current
    chosen = ui.select_one("Output language", LANGUAGE_OPTIONS)
    if chosen == "other":
        return ui.ask_text("Language code", current)
    return chosen


def next_steps(clients) -> None:
    print()
    print(ui.paint("Next steps", ui.BOLD))
    number = 1
    for key in dict.fromkeys(clients):
        client = CLIENTS[key]
        print(f"  {number}. Open a new {client.label} session in this project and {client.hint}.")
        number += 1
    if not clients:
        print(f"  {number}. Configure a client: atipspec install --client claude")
        number += 1
    print(f"  {number}. `atipspec status` shows the state and the next action at any time.")


def _install(root: Path, clients: list[str]) -> list[Path]:
    """Install what is missing, never overwrite; report and return kept files."""
    files = installation_files(root, clients)
    states = classify(files)
    _, kept = write_installation(root, files)
    framework = [path for path in files if ".atipspec" in path.parts]
    if all(states[path] == "same" for path in framework):
        ui.step("Framework in .atipspec/framework/ (already up to date)")
    else:
        ui.step(f"Framework in .atipspec/framework/ ({len(framework)} files)")
    outdated = [path for path in framework if path in kept]
    if outdated:
        ui.warn(f"{_plural(len(outdated), 'framework file')} differ from v{__version__} and were kept; "
                "run `atipspec install --update` to replace them")
    for key in dict.fromkeys(clients):
        paths = list(client_files(root, key))
        if all(states[path] == "missing" for path in paths):
            state = "installed"
        elif all(states[path] == "same" for path in paths):
            state = "already installed"
        elif any(path in kept for path in paths):
            state = f"{_plural(sum(1 for path in paths if path in kept), 'file')} differ, kept"
        else:
            state = "completed"
        ui.step(f"{CLIENTS[key].label}: {CLIENTS[key].skills}/atipspec*/ ({len(paths)} skills) "
                f"{ui.paint(f'({state})', ui.DIM)}")
    outdated_skills = [path for path in kept if ".atipspec" not in path.parts]
    if outdated_skills:
        ui.warn(f"{_plural(len(outdated_skills), 'skill file')} differ from v{__version__} and were kept; "
                "run `atipspec install --update` to replace them")
    for key in dict.fromkeys(clients):
        _apply_permission_rules(root, key)
    return kept


def _apply_permission_rules(root: Path, key: str) -> bool:
    """Merge the client's permission rules and report it; True when the file changed."""
    state, problem = install_permission_rules(root, key)
    if state == "none":
        return False
    label, settings = CLIENTS[key].label, PERMISSION_RULES[key].settings
    if state == "invalid":
        ui.warn(f"{label}: {problem}, so it was left unchanged and acceptances are recorded as channel assistant. "
                f"Add these rules to {settings} by hand: {permission_rules_text(key)}")
        return False
    note = {"created": "created", "added": "rules added", "present": "already present"}[state]
    ui.step(f"{label}: {settings} asks before `atipspec accept` and before edits to CI workflows or its settings, "
            f"and denies edits to approval, evidence and review round records {ui.paint(f'({note})', ui.DIM)}")
    return state != "present"


def _update(root: Path, clients: list[str], ask: bool) -> bool:
    """Bring framework and the given clients' skills to this version, and repair
    their permission rules."""
    updates = pending_updates(root, clients)
    extras = framework_extras(root)
    changed = False
    if not updates and not extras:
        ui.step(f"Framework and skills already match v{__version__}")
    else:
        for path in updates:
            ui.line(f"{_rel(root, path)} {ui.paint('(missing)' if not path.exists() else '(differs)', ui.DIM)}")
        for path in extras:
            ui.line(f"{_rel(root, path)} {ui.paint(f'(not in v{__version__})', ui.DIM)}")
        if ask and not ui.confirm(f"Update {_plural(len(updates) + len(extras), 'file')} to v{__version__}?",
                                  default=True):
            ui.step("Framework and skill files kept")
        else:
            missing = {path: content for path, content in updates.items() if not path.exists()}
            existing = {path: content for path, content in updates.items() if path.exists()}
            write_installation(root, missing)
            overwrite_files(existing)
            for path in extras:
                path.unlink()
                for parent in path.parents:
                    if parent == root / FRAMEWORK or any(parent.iterdir()):
                        break
                    parent.rmdir()
            ui.step(f"Updated to v{__version__}: {_plural(len(existing), 'file')} replaced, {len(missing)} created"
                    + (f", {len(extras)} removed" if extras else ""))
            changed = True
    for key in dict.fromkeys(clients):
        changed = _apply_permission_rules(root, key) or changed
    differences = config_differences(root)
    if differences:
        ui.step("Configuration kept: .atipspec/config.yaml differs from this version's defaults "
                f"{ui.paint('(' + '; '.join(differences) + ')', ui.DIM)}")
    return changed


def _remove_client(root: Path, key: str, keep_paths: set[str]) -> None:
    client = CLIENTS[key]
    if client.path in keep_paths:
        ui.step(f"{client.label}: shares {client.skills}/ with a selected client, kept")
        return
    paths = [path for path in client_files(root, key) if path.is_file()]
    if not paths:
        return
    if not ui.confirm(f"Remove the {len(paths)} AtipSpec skills under {client.skills}/?", default=False):
        ui.step(f"{client.label}: kept")
        return
    for path in paths:
        path.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass
    ui.step(f"{client.label}: removed {len(paths)} skills under {client.skills}/")
    if remove_permission_rules(root, key):
        ui.step(f"{client.label}: removed the AtipSpec permission rules from {PERMISSION_RULES[key].settings}")


# --- commands --------------------------------------------------------------

TAGLINE = "spec-driven delivery with a deterministic gate"


def install_clients(root: Path, clients: list[str] | None, update: bool = False) -> None:
    ui.banner(__version__, TAGLINE)
    ui.intro("Update installation" if update else "Install clients")
    installed = installed_clients(root)
    if clients is None:
        clients = choose_clients(preselected=list(installed)) if ui.interactive() else list(installed)
        if not clients:
            raise AtipSpecError("No client selected. Pass --client <id> to choose one.")
    else:
        ui.answered("Clients", _labels(clients))
    if update:
        _update(root, clients, ask=False)
        for key in dict.fromkeys(clients):
            ui.step(f"{CLIENTS[key].label}: {CLIENTS[key].skills}/atipspec*/")
    else:
        _install(root, clients)
    ui.line()
    ui.outro("AtipSpec installed.")
    next_steps(clients)


def init_project(root: Path, *, clients: list[str] | None = None, name: str | None = None,
                 language: str | None = None) -> None:
    destination = root / ".atipspec"
    if destination.is_symlink():
        raise AtipSpecError(".atipspec must not be a symlink.")
    if destination.exists():
        if not (destination / "config.yaml").is_file():
            raise AtipSpecError(".atipspec exists but has no config.yaml. Remove it or restore the file.")
        manage_project(root, clients=clients, name=name, language=language)
        return
    ui.banner(__version__, TAGLINE)
    ui.intro("New project")
    if not ui.interactive() and (name is None or language is None or clients is None):
        ui.warn("No terminal detected: using defaults" + (" and configuring no client" if clients is None else "")
                + ". Run this from a terminal, or pass --name, --language and --client.")
        ui.line()
    name = (name or "").strip() or ui.ask_text("Project name", root.name)
    language = (language or "").strip() or choose_language()
    if clients is None:
        clients = choose_clients()
    elif clients:
        ui.answered("Clients", _labels(clients))
    try:
        destination.mkdir()
    except FileExistsError as exc:
        raise AtipSpecError(".atipspec already exists. Nothing was overwritten.") from exc
    try:
        for folder in PROJECT_FOLDERS:
            (destination / folder).mkdir()
        write_config(root, name, language)
        (destination / ".gitignore").write_text(DOT_GITIGNORE, encoding="utf-8", newline="\n")
        for document in PROJECT_DOCUMENTS:
            (destination / document).write_text(template(document).replace("{{name}}", name), encoding="utf-8",
                                                newline="\n")
        ui.step(f"Project {ui.paint(name, ui.BOLD)}, output language {ui.paint(language, ui.BOLD)}")
        ui.step("Created .atipspec/ with specs/, deliveries/, archive/, decisions/, initiatives/")
        ui.step("Contract, overview and glossary skeletons ready for the contract phase")
        _install(root, clients)
    except BaseException:
        shutil.rmtree(destination)
        raise
    if not Git(root).available:
        ui.warn("Not a git repository. Run `git init` and commit: the gate needs git for the base commit, "
                "contract rules and evidence freshness, and stays red without it.")
    elif not (root / ".gitignore").is_file():
        ui.warn("No .gitignore: build caches such as __pycache__/ or node_modules/ change the working tree "
                "and make evidence stale; commit one before `atipspec new`, since one added in a delivery is a "
                "file outside its scope.")
    ui.line()
    ui.outro("AtipSpec is ready.")
    next_steps(clients)


def manage_project(root: Path, *, clients: list[str] | None, name: str | None, language: str | None) -> None:
    """`atipspec init` on an initialized project: show the state, apply flags,
    and in a terminal offer to add or remove clients, update, or reconfigure."""
    try:
        config = frontmatter.parse((root / ".atipspec" / "config.yaml").read_text(encoding="utf-8"))
    except ValueError as exc:
        raise AtipSpecError(f"Invalid .atipspec/config.yaml: {exc}") from exc
    current_name = str(config.get("name") or root.name)
    current_language = str(config.get("language") or "en")
    ui.banner(__version__, TAGLINE)
    ui.intro("Existing project")
    ui.step(f"Already initialized: {ui.paint(current_name, ui.BOLD)}, output language {ui.paint(current_language, ui.BOLD)}")
    _summary(root)
    ui.line()
    changed = False
    if name or language:
        current_name = (name or "").strip() or current_name
        current_language = (language or "").strip() or current_language
        write_config(root, current_name, current_language)
        ui.step(f"Configuration: {current_name}, output language {current_language}")
        changed = True
    if clients:
        ui.answered("Clients", _labels(clients))
        _install(root, clients)
        changed = True
    if not changed and ui.interactive():
        _menu(root, current_name, current_language)
    else:
        if not changed:
            ui.line(ui.paint("Add clients: atipspec init --client <id>. Update: atipspec install --update. "
                             "State: atipspec status", ui.DIM))
        ui.line()
    ui.outro("AtipSpec is ready.")
    next_steps(list(installed_clients(root)))


def _summary(root: Path) -> None:
    installed = installed_clients(root)
    labels = [CLIENTS[key].label + (" (outdated)" if state == "outdated" else "")
              for key, state in installed.items()]
    ui.line(f"Clients: {', '.join(labels) or 'none'}")
    changes = framework_changes(root)
    ui.line("Framework: " + ("up to date" if not changes else f"{_plural(len(changes), 'file')} differ from v{__version__}"))


def _menu(root: Path, name: str, language: str) -> None:
    while True:
        installed = installed_clients(root)
        count = len(pending_updates(root, list(installed))) + len(framework_extras(root))
        label = f"Update framework and skills to v{__version__}"
        label += f" ({_plural(count, 'file')})" if count else " (already up to date)"
        choice = ui.select_one("What do you want to do?", [
            ("clients", "Add or remove clients"),
            ("update", label),
            ("config", "Change project name or language"),
            ("done", "Done"),
        ])
        if choice == "done":
            return
        if choice == "clients":
            chosen = choose_clients(preselected=list(installed))
            to_add = [key for key in chosen if key not in installed]
            to_remove = [key for key in installed if key not in chosen]
            if to_add:
                _install(root, to_add)
            for key in to_remove:
                _remove_client(root, key, {CLIENTS[key].path for key in chosen})
            if not to_add and not to_remove:
                ui.step("Clients unchanged")
        elif choice == "update":
            _update(root, list(installed), ask=True)
        elif choice == "config":
            name = ui.ask_text("Project name", name)
            language = choose_language(language)
            write_config(root, name, language)
            ui.step(f"Configuration: {name}, output language {language}")
        ui.line()
