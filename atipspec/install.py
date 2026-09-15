"""Initialize a project, install or update the framework and client skills,
and manage an already initialized project."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
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
PROJECT_FOLDERS = ("specs", "deliveries", "archive", "decisions", "initiatives")
PROJECT_DOCUMENTS = ("contract.md", "overview.md", "glossary.md")
DOT_GITIGNORE = "# AtipSpec: review packets and other scratch files\ntmp/\n"


# --- files -----------------------------------------------------------------

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
    source = resource_root() / "framework"
    files: dict[Path, bytes] = {}
    for resource in sorted(source.rglob("*")):
        if resource.is_file():
            files[root / ".atipspec" / "framework" / resource.relative_to(source)] = resource.read_bytes()
    if not files:
        raise AtipSpecError(f"Framework resources are missing from {source}.")
    for client in clients:
        files.update(client_files(root, client))
    return files


def classify(files: dict[Path, bytes]) -> dict[Path, str]:
    """For each target: 'missing', 'same' or 'differs' from the shipped content."""
    states = {}
    for path, content in files.items():
        if not path.exists():
            states[path] = "missing"
        elif path.is_file() and path.read_bytes() == content:
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
        elif not path.is_file() or path.read_bytes() != content:
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
    matches this version, 'outdated' otherwise."""
    found = {}
    for key, client in CLIENTS.items():
        if (root / client.path).is_file():
            states = classify(client_files(root, key))
            found[key] = "installed" if all(state == "same" for state in states.values()) else "outdated"
    return found


def pending_updates(root: Path, clients: list[str]) -> dict[Path, bytes]:
    """Framework and skill files that are missing or differ from this version."""
    files = installation_files(root, clients)
    states = classify(files)
    return {path: content for path, content in files.items() if states[path] != "same"}


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
    path.write_text(frontmatter.dump(config)[4:-4], encoding="utf-8")


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
    return kept


def _update(root: Path, clients: list[str], ask: bool) -> bool:
    """Bring framework and the given clients' skills to this version."""
    updates = pending_updates(root, clients)
    if not updates:
        ui.step(f"Framework and skills already match v{__version__}")
        return False
    for path in updates:
        ui.line(f"{_rel(root, path)} {ui.paint('(missing)' if not path.exists() else '(differs)', ui.DIM)}")
    if ask and not ui.confirm(f"Replace {_plural(len(updates), 'file')} with v{__version__}?", default=True):
        ui.step("Nothing changed")
        return False
    missing = {path: content for path, content in updates.items() if not path.exists()}
    existing = {path: content for path, content in updates.items() if path.exists()}
    write_installation(root, missing)
    overwrite_files(existing)
    ui.step(f"Updated to v{__version__}: {_plural(len(existing), 'file')} replaced, {len(missing)} created")
    return True


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
        (destination / ".gitignore").write_text(DOT_GITIGNORE, encoding="utf-8")
        for document in PROJECT_DOCUMENTS:
            (destination / document).write_text(template(document).replace("{{name}}", name), encoding="utf-8")
        ui.step(f"Project {ui.paint(name, ui.BOLD)}, output language {ui.paint(language, ui.BOLD)}")
        ui.step("Created .atipspec/ with specs/, deliveries/, archive/, decisions/, initiatives/")
        ui.step("Contract, overview and glossary skeletons ready for the contract phase")
        _install(root, clients)
    except BaseException:
        shutil.rmtree(destination)
        raise
    if not Git(root).available:
        ui.warn("Not a git repository. Run `git init`: task completion and evidence freshness come from git.")
    elif not (root / ".gitignore").is_file():
        ui.warn("No .gitignore: build caches such as __pycache__/ or node_modules/ change the working tree "
                "and make evidence stale; add one before the first `atipspec verify`.")
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
    updates = pending_updates(root, [])
    ui.line("Framework: " + ("up to date" if not updates else f"{_plural(len(updates), 'file')} differ from v{__version__}"))


def _menu(root: Path, name: str, language: str) -> None:
    while True:
        installed = installed_clients(root)
        updates = pending_updates(root, list(installed))
        label = f"Update framework and skills to v{__version__}"
        label += f" ({_plural(len(updates), 'file')})" if updates else " (already up to date)"
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
