import contextlib
import io
import unittest
from unittest.mock import patch

from atipspec import ui

OPTIONS = [("claude", "Claude Code"), ("codex", "Codex"), ("cursor", "Cursor")]


class SelectorTests(unittest.TestCase):
    def test_keys_move_toggle_and_confirm(self):
        selector = ui.Selector(OPTIONS)
        self.assertFalse(selector.handle(" "))
        self.assertFalse(selector.handle("down"))
        self.assertFalse(selector.handle("j"))
        self.assertFalse(selector.handle(" "))
        self.assertEqual(selector.values(), ["claude", "cursor"])
        self.assertEqual(selector.labels(), ["Claude Code", "Cursor"])
        self.assertFalse(selector.handle("up"))
        self.assertEqual(selector.cursor, 1)
        self.assertTrue(selector.handle("enter"))

    def test_wraps_selects_all_and_cancels(self):
        selector = ui.Selector(OPTIONS, selected=["cursor", "unknown"])
        self.assertEqual(selector.values(), ["cursor"])
        selector.handle("up")
        self.assertEqual(selector.cursor, 2)
        selector.handle("a")
        self.assertEqual(selector.values(), ["claude", "codex", "cursor"])
        selector.handle("a")
        self.assertEqual(selector.values(), [])
        with self.assertRaises(KeyboardInterrupt):
            selector.handle("cancel")

    def test_render_marks_cursor_and_selection(self):
        selector = ui.Selector(OPTIONS, selected=["codex"])
        with patch("atipspec.ui.interactive", return_value=False):
            rows = selector.render()
        self.assertEqual(rows[0], "│  ❯ ◻ Claude Code")
        self.assertEqual(rows[1], "│    ◼ Codex")


class PromptTests(unittest.TestCase):
    def test_numbered_fallback_validates_input(self):
        with patch("atipspec.ui.interactive", return_value=True), \
             patch("atipspec.ui.key_reader", side_effect=ui.NoRawTerminal), \
             patch("builtins.input", side_effect=["4", "x", "3,1", ""]), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(ui.select_many("Which?", OPTIONS), ["claude", "cursor"])
            self.assertEqual(ui.select_many("Which?", OPTIONS, selected=["codex"]), ["codex"])
        self.assertIn("Enter numbers between 1 and 3", out.getvalue())
        self.assertIn("2. Codex (selected)", out.getvalue())

    def test_single_select_and_confirm_fallbacks(self):
        with patch("atipspec.ui.interactive", return_value=True), \
             patch("atipspec.ui.key_reader", side_effect=ui.NoRawTerminal), \
             patch("builtins.input", side_effect=["9", "2", "", "n", "sí"]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ui.select_one("Menu", OPTIONS), "codex")
            self.assertTrue(ui.confirm("Go?", default=True))
            self.assertFalse(ui.confirm("Go?", default=True))
            self.assertTrue(ui.confirm("Go?"))
        with patch("atipspec.ui.interactive", return_value=False), \
             patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
            self.assertEqual(ui.select_one("Menu", OPTIONS), "claude")
            self.assertFalse(ui.confirm("Go?"))

    def test_single_selector_state(self):
        selector = ui.Selector(OPTIONS, single=True)
        selector.handle("down")
        self.assertTrue(selector.handle(" "))
        self.assertEqual(selector.current(), "codex")
        with patch("atipspec.ui.interactive", return_value=False):
            self.assertEqual(selector.render()[1], "│  ❯ Codex")

    def test_without_terminal_prompts_use_defaults(self):
        with patch("atipspec.ui.interactive", return_value=False), \
             patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
            self.assertEqual(ui.ask_text("Name", "demo"), "demo")
            self.assertEqual(ui.select_many("Which?", OPTIONS, selected=["codex"]), ["codex"])


if __name__ == "__main__":
    unittest.main()
