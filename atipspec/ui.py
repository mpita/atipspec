"""Terminal presentation: a step log in the style of clack/OpenSpec and a
dependency-free multi-select. Falls back to plain prompts without a terminal."""
from __future__ import annotations

import contextlib
import os
import sys

CYAN, GREEN, YELLOW, DIM, BOLD = "36", "32", "33", "2", "1"


def interactive() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def paint(text: str, code: str) -> str:
    if not interactive() or os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


LOGO = (
    "▄▀█ ▀█▀ █ █▀█ █▀ █▀█ █▀▀ █▀▀",
    "█▀█  █  █ █▀▀ ▄█ █▀▀ ██▄ █▄▄",
)
GRADIENT = ("51", "50", "44", "38", "39", "33")  # 256-color teal to blue, left to right


def banner(version: str, tagline: str) -> None:
    """The AtipSpec wordmark with a color gradient in a terminal, plain otherwise."""
    width = len(LOGO[0])
    for row in LOGO:
        if interactive() and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb":
            cells = []
            for index, char in enumerate(row):
                shade = GRADIENT[min(len(GRADIENT) - 1, index * len(GRADIENT) // width)]
                cells.append(f"\x1b[38;5;{shade}m{char}" if char != " " else char)
            print("  " + "".join(cells) + "\x1b[0m")
        else:
            print("  " + row)
    print("  " + paint(f"{tagline} · v{version}", DIM))
    print()


def intro(title: str) -> None:
    print(f"{paint('┌', CYAN)}  {paint(title, BOLD)}")
    line()


def line(text: str = "") -> None:
    print(paint("│", CYAN) + (f"  {text}" if text else ""))


def step(text: str) -> None:
    print(f"{paint('◇', CYAN)}  {text}")


def warn(text: str) -> None:
    print(f"{paint('▲', YELLOW)}  {text}")


def outro(text: str) -> None:
    print(f"{paint('└', CYAN)}  {paint(text, GREEN)}")


def answered(label: str, value: str) -> None:
    step(label)
    line(paint(value, DIM))
    line()


def ask_text(label: str, default: str) -> str:
    """Prompt for one line; without a terminal the default is used silently."""
    if not interactive():
        return default
    print(f"{paint('◆', CYAN)}  {label} {paint(f'({default})', DIM)}")
    value = input(f"{paint('│', CYAN)}  ").strip() or default
    sys.stdout.write("\x1b[2A\r\x1b[J")
    answered(label, value)
    return value


class Selector:
    """State of a selector: a cursor and, for multi-select, a set of selected values."""

    def __init__(self, options: list[tuple[str, str]], selected=(), single: bool = False):
        self.options = options
        self.cursor = 0
        self.single = single
        self.selected = {value for value in selected if value in dict(options)}

    def handle(self, key: str) -> bool:
        """Apply one key. Returns True when the selection is confirmed."""
        count = len(self.options)
        if key in ("up", "k"):
            self.cursor = (self.cursor - 1) % count
        elif key in ("down", "j"):
            self.cursor = (self.cursor + 1) % count
        elif key == " ":
            if self.single:
                return True
            self.selected ^= {self.options[self.cursor][0]}
        elif key == "a":
            everything = {value for value, _ in self.options}
            self.selected = set() if self.selected == everything else everything
        elif key == "enter":
            return True
        elif key == "cancel":
            raise KeyboardInterrupt
        return False

    def values(self) -> list[str]:
        return [value for value, _ in self.options if value in self.selected]

    def labels(self) -> list[str]:
        return [label for value, label in self.options if value in self.selected]

    def current(self) -> str:
        return self.options[self.cursor][0]

    def render(self) -> list[str]:
        rows = []
        for index, (value, label) in enumerate(self.options):
            box = "" if self.single else ("◼ " if value in self.selected else "◻ ")
            text = f"{'❯' if index == self.cursor else ' '} {box}{label}"
            rows.append(f"{paint('│', CYAN)}  {paint(text, BOLD) if index == self.cursor else text}")
        return rows


class NoRawTerminal(Exception):
    """Raw key reading is not available; use the numbered prompt instead."""


@contextlib.contextmanager
def key_reader():
    """Yield a function that returns one key: a character, 'up', 'down', 'enter' or 'cancel'."""
    if os.name == "nt":
        try:
            import msvcrt
        except ImportError as exc:
            raise NoRawTerminal from exc
        os.system("")  # lets the Windows console interpret ANSI sequences

        def read_windows() -> str:
            char = msvcrt.getwch()
            if char in ("\x00", "\xe0"):
                return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
            if char in ("\x03", "\x1b"):
                return "cancel"
            if char == "\r":
                return "enter"
            return char.lower()

        yield read_windows
        return
    try:
        import select
        import termios
        import tty
        descriptor = sys.stdin.fileno()
        saved = termios.tcgetattr(descriptor)
        tty.setcbreak(descriptor)
    except (ImportError, ValueError, OSError, AttributeError) as exc:
        raise NoRawTerminal from exc
    except Exception as exc:  # termios.error is not an OSError subclass everywhere
        raise NoRawTerminal from exc

    def read_posix() -> str:
        char = os.read(descriptor, 1)
        if char == b"\x03":
            return "cancel"
        if char in (b"\r", b"\n"):
            return "enter"
        if char == b"\x1b":
            if select.select([descriptor], [], [], 0.1)[0]:
                sequence = os.read(descriptor, 2)
                return {b"[A": "up", b"[B": "down"}.get(sequence, "")
            return "cancel"
        return char.decode("utf-8", "replace").lower()

    try:
        yield read_posix
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, saved)


def select_many(label: str, options: list[tuple[str, str]], selected=()) -> list[str]:
    """Return the chosen values in option order. Arrow keys and space in a
    terminal; a numbered prompt otherwise; the preselection without a terminal."""
    if interactive():
        try:
            selector = _drive(label, options, selected, single=False)
            answered(label, ", ".join(selector.labels()) or "none")
            return selector.values()
        except NoRawTerminal:
            pass
    return _select_numbered(label, options, selected)


def select_one(label: str, options: list[tuple[str, str]]) -> str:
    """Return one value. Arrow keys and enter in a terminal; a numbered prompt
    otherwise; the first option without a terminal."""
    if interactive():
        try:
            selector = _drive(label, options, (), single=True)
            answered(label, dict(options)[selector.current()])
            return selector.current()
        except NoRawTerminal:
            pass
    return _select_one_numbered(label, options)


def confirm(label: str, default: bool = False) -> bool:
    """Yes/no question; the default without a terminal."""
    if not interactive():
        return default
    print(f"{paint('◆', CYAN)}  {label} {paint('(Y/n)' if default else '(y/N)', DIM)}")
    raw = input(f"{paint('│', CYAN)}  ").strip().lower()
    value = default if not raw else raw in ("y", "yes", "s", "si", "sí")
    sys.stdout.write("\x1b[2A\r\x1b[J")
    answered(label, "yes" if value else "no")
    return value


def _drive(label: str, options: list[tuple[str, str]], selected, single: bool) -> Selector:
    selector = Selector(options, selected, single=single)
    hint = "enter confirms" if single else "space selects, a selects all, enter confirms"
    with key_reader() as read_key:
        print(f"{paint('◆', CYAN)}  {label} {paint(hint, DIM)}")
        print("\n".join(selector.render()))
        sys.stdout.write("\x1b[?25l")
        sys.stdout.flush()
        try:
            while not selector.handle(read_key()):
                sys.stdout.write(f"\x1b[{len(options)}A")
                for row in selector.render():
                    sys.stdout.write(f"\r\x1b[K{row}\n")
                sys.stdout.flush()
        finally:
            sys.stdout.write("\x1b[?25h")
            sys.stdout.flush()
    sys.stdout.write(f"\x1b[{len(options) + 1}A\r\x1b[J")
    return selector


def _print_numbered(label: str, options: list[tuple[str, str]], selected=()) -> None:
    print(f"{paint('◆', CYAN)}  {label}")
    for number, (value, text) in enumerate(options, 1):
        line(f"{number}. {text}{' (selected)' if value in selected else ''}")


def _select_numbered(label: str, options: list[tuple[str, str]], selected) -> list[str]:
    current = [value for value, _ in options if value in set(selected)]
    if not interactive():
        return current
    _print_numbered(label, options, selected)
    while True:
        raw = input(f"{paint('│', CYAN)}  numbers separated by commas, empty keeps the current selection: ").strip()
        chosen = [part.strip() for part in raw.split(",") if part.strip()]
        if not chosen:
            return current
        if all(part.isdigit() and 1 <= int(part) <= len(options) for part in chosen):
            picked = {options[int(part) - 1][0] for part in chosen}
            return [value for value, _ in options if value in picked]
        line(f"Enter numbers between 1 and {len(options)}.")


def _select_one_numbered(label: str, options: list[tuple[str, str]]) -> str:
    if not interactive():
        return options[0][0]
    _print_numbered(label, options)
    while True:
        raw = input(f"{paint('│', CYAN)}  number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        line(f"Enter a number between 1 and {len(options)}.")
