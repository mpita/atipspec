"""C12: the documentation matches the CLI it documents. Every command and
option the documentation, the installed text and the CLI's own messages cite
exists; the CLI reference covers every command and option; every page is in
the navigation; the versions agree; retired claims stay retired; and the
Spanish and Portuguese pages translate every English page, and only those,
with the same commands and options."""
import argparse
from collections import Counter
from pathlib import Path
import re
import unittest

from atipspec import __version__
from atipspec.cli import build_parser
from atipspec.project import DEFAULT_POLICIES

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INSTALLATION = DOCS / "getting-started" / "installation.md"
TRANSLATIONS = ("es", "pt")
FENCE = re.compile(r"^\s*(```+|~~~+)")
INLINE = re.compile(r"(`+)(.+?)\1")
CITED = re.compile(r"(?<![\w./-])atipspec\s+([a-z][a-z-]*)(.*?)(?=(?<![\w./-])atipspec\s+[a-z]|$)")
OPTION = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]*)")
# Where a shell line goes on to another command or a comment.
COMMAND_END = re.compile(r"\s(?:#|\|\s|&&|;)|\s\|$")
SECTION = re.compile(r"^###\s+`atipspec ([a-z-]+)`\s*$", re.M)
# Claims the code no longer makes; each was in the documentation or the
# installed text, and the CHANGELOG keeps them as history.
RETIRED = ("run by a person", "never runs it", "with the trusted policy", "commit with `[",
           "A task is done when a commit says so", "requires a policy and full trusted acceptance",
           "state machine", "one commit per task", "merges the branch", "Stop point 2: the merge",
           "migrate it explicitly", "until migrated", "Migration tooling", "fresh context",
           "every task committed", "task without a commit", "nothing to resume", "Nothing is stored",
           "git for task completion", "run `/atipspec-review <slug>` there", "waits at that prompt",
           "configured to ask the human first", "defer it in deferred.md with a reason",
           "set status: accepted when approved", "No status is written by hand", "Already integrated",
           "brought by merge")


def commands() -> dict[str, argparse.ArgumentParser]:
    parser = build_parser()
    action = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    return dict(action.choices)


def options(parser: argparse.ArgumentParser) -> set[str]:
    """Every long option of a command, its subcommands' included."""
    found = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                found |= options(child)
        found.update(option for option in action.option_strings if option.startswith("--"))
    return found - {"--help"}


def english_pages() -> list[Path]:
    """The English pages of the site: docs/ without the translations."""
    return sorted(path for path in DOCS.rglob("*.md") if not translated(path))


def translated(path: Path) -> bool:
    return any(path.name.endswith(f".{language}.md") for language in TRANSLATIONS)


def translation(page: Path, language: str) -> Path:
    return page.with_name(f"{page.stem}.{language}.md")


def nav_pages() -> list[str]:
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    nav = text[text.index("\nnav:"):]
    return re.findall(r"^\s*-\s+(?:[^:\n]+:\s+)?(\S+\.md)\s*$", nav, re.M)


def code(text: str, inline: bool = True) -> list[str]:
    """The code of a Markdown text: each line of its fenced blocks, a line
    that ends in a backslash joined with the next, and its inline code spans."""
    found, fenced, pending = [], False, ""
    for line in text.splitlines():
        if FENCE.match(line):
            fenced, pending = not fenced, ""
            continue
        if fenced:
            pending += line
            if pending.endswith("\\"):
                pending = pending[:-1] + " "
                continue
            found.append(pending)
            pending = ""
        elif inline:
            found += [match.group(2) for match in INLINE.finditer(line)]
    return found


def citations(snippets: list[str]) -> list[tuple[str, list[str]]]:
    """Each `atipspec <command>` the snippets cite, with the options after it."""
    cited = []
    for snippet in snippets:
        for match in CITED.finditer(snippet):
            rest = COMMAND_END.split(match.group(2), maxsplit=1)[0]
            cited.append((match.group(1), OPTION.findall(rest)))
    return cited


def documentation() -> dict[Path, list[str]]:
    """The code each English source cites commands in: the site, README,
    CONTRIBUTING, the installed resources and the CLI's own messages."""
    sources = {path: code(path.read_text(encoding="utf-8"))
               for path in [*english_pages(), ROOT / "README.md", ROOT / "CONTRIBUTING.md"]}
    for path in sorted((ROOT / "atipspec" / "resources").rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            sources[path] = code(text) if path.suffix == ".md" else text.splitlines()
    for path in sorted((ROOT / "atipspec").glob("*.py")):
        sources[path] = path.read_text(encoding="utf-8").splitlines()
    return sources


def miscited(sources: dict[Path, list[str]]) -> list[str]:
    """Each command, or option of a command, the sources cite and the CLI lacks."""
    known = commands()
    wrong = []
    for path, snippets in sources.items():
        for command, cited in citations(snippets):
            if command not in known:
                wrong.append(f"{path.relative_to(ROOT)}: atipspec {command} is not a command")
                continue
            wrong += [f"{path.relative_to(ROOT)}: atipspec {command} has no option {option}"
                      for option in cited if option not in options(known[command])]
    return sorted(set(wrong))


def commands_cited(path: Path) -> list[str]:
    """Each command a page's code blocks cite, with its options."""
    return [" ".join([command, *sorted(cited)])
            for command, cited in citations(code(path.read_text(encoding="utf-8"), False))]


def reference_sections(text: str) -> dict[str, str]:
    """Each `### \\`atipspec <command>\\`` section of the CLI reference, up to
    the next heading of its level or above."""
    sections = {}
    for match in SECTION.finditer(text):
        end = re.compile(r"^#{1,3}\s", re.M).search(text, match.end())
        sections[match.group(1)] = text[match.end():end.start() if end else len(text)]
    return sections


def reference_gaps(path: Path) -> list[str]:
    """What the CLI reference at `path` leaves out: a command without its
    section, or an option its section never names."""
    sections = reference_sections(path.read_text(encoding="utf-8"))
    gaps = []
    for name, parser in commands().items():
        if name not in sections:
            gaps.append(f"no section for atipspec {name}")
            continue
        gaps += [f"atipspec {name} {option}" for option in sorted(options(parser))
                 if not re.search(re.escape(option) + r"(?![\w-])", sections[name])]
    return gaps


class DocumentationTests(unittest.TestCase):
    def test_every_command_and_option_cited_exists(self):
        self.assertEqual(miscited(documentation()), [])

    def test_the_check_reads_commands_options_and_where_they_end(self):
        cited = citations(code("Run `atipspec verify reset --task T1` and `python -m atipspec accept reset "
                               "proposal|result --code K7M2`; Update: atipspec install --update. Add: atipspec "
                               "init --client <id>.\n\n```bash\natipspec report reset \\\n  --format json"
                               "  # --not-an-option\natipspec status | grep --count draft\n```\n"
                               "`.atipspec/specs/` and `atipspec.verify` and `uv tool install atipspec`\n"))
        self.assertEqual(cited, [("verify", ["--task"]), ("accept", ["--code"]), ("report", ["--format"]),
                                 ("status", [])])
        self.assertEqual(citations(["Update: atipspec install --update. Add: atipspec init --client <id>."]),
                         [("install", ["--update"]), ("init", ["--client"])])

    def test_cli_reference_documents_every_command_and_option(self):
        self.assertEqual(reference_gaps(DOCS / "reference" / "cli.md"), [])

    def test_every_page_is_in_the_navigation(self):
        nav = nav_pages()
        pages = [path.relative_to(DOCS).as_posix() for path in english_pages()]
        self.assertEqual(sorted(set(pages) - set(nav)), [], "pages missing from the nav in mkdocs.yml")
        self.assertEqual(sorted(set(nav) - set(pages)), [], "nav entries without a page")

    def test_versions_agree(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(f'\nversion = "{__version__}"\n', pyproject)
        self.assertIn(f"**Current version: {__version__}.**", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn(f"## {__version__} — ", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn(f"· v{__version__}\n", INSTALLATION.read_text(encoding="utf-8"))

    def test_configuration_reference_lists_every_key(self):
        text = (DOCS / "reference" / "configuration.md").read_text(encoding="utf-8")
        missing = [key for key in [*DEFAULT_POLICIES, "name", "language", "system"]
                   if not re.search(rf"^\| `{key}` \|", text, re.M)]
        self.assertEqual(missing, [])

    def test_installed_text_and_english_docs_drop_retired_claims(self):
        paths = [*english_pages(), ROOT / "README.md", ROOT / "CONTRIBUTING.md",
                 *(path for path in (ROOT / "atipspec").rglob("*") if path.is_file() and path.suffix in (".md", ".py"))]
        found = [f"{path.relative_to(ROOT)}: {phrase}" for path in paths
                 for phrase in RETIRED if phrase in path.read_text(encoding="utf-8")]
        self.assertEqual(found, [])


class TranslationTests(unittest.TestCase):
    """English is the source: each page in the navigation has a Spanish and a
    Portuguese translation that keeps its commands and options, and each
    translation translates an English page."""

    def test_every_command_and_option_the_translations_cite_exists(self):
        pages = sorted(path for path in DOCS.rglob("*.md") if translated(path))
        self.assertEqual(miscited({path: code(path.read_text(encoding="utf-8")) for path in pages}), [])

    def test_every_page_is_translated(self):
        missing = [translation(DOCS / page, language).relative_to(ROOT).as_posix()
                   for page in nav_pages() for language in TRANSLATIONS
                   if not translation(DOCS / page, language).is_file()]
        self.assertEqual(missing, [])

    def test_every_translation_has_an_english_page(self):
        orphans = [path.relative_to(ROOT).as_posix() for path in DOCS.rglob("*.md")
                   if translated(path) and not path.with_name(f"{path.name.split('.')[0]}.md").is_file()]
        self.assertEqual(orphans, [], "translations of no English page; mkdocs publishes them outside the nav")

    def test_translations_cite_the_same_commands(self):
        different = []
        for page in english_pages():
            source = Counter(commands_cited(page))
            for language in TRANSLATIONS:
                path = translation(page, language)
                if not path.is_file():
                    continue
                cited = Counter(commands_cited(path))
                if cited != source:
                    different.append(f"{path.relative_to(ROOT)}: missing {sorted((source - cited).elements())}, "
                                     f"extra {sorted((cited - source).elements())}")
        self.assertEqual(different, [])

    def test_installation_banners_show_the_version(self):
        for language in TRANSLATIONS:
            page = translation(INSTALLATION, language)
            self.assertIn(f"· v{__version__}\n", page.read_text(encoding="utf-8"), page.name)

    def test_cli_reference_is_complete_in_every_language(self):
        for language in TRANSLATIONS:
            with self.subTest(language=language):
                self.assertEqual(reference_gaps(translation(DOCS / "reference" / "cli.md", language)), [])


if __name__ == "__main__":
    unittest.main()
