import unittest

from atipspec import frontmatter


class FrontmatterTests(unittest.TestCase):
    def test_split_and_parse_scalars_and_lists(self):
        meta, body = frontmatter.split('---\ntitle: "A: b"\nstatus: draft\nbase: null\ncount: 3\nflag: true\n'
                                       "tags:\n  - one\n  - two\ninline: [a, b]\nempty: []\n---\n\n# A\n")
        self.assertEqual(meta, {"title": "A: b", "status": "draft", "base": None, "count": 3, "flag": True,
                                "tags": ["one", "two"], "inline": ["a", "b"], "empty": []})
        self.assertEqual(body, "\n# A\n")

    def test_no_frontmatter_and_errors(self):
        self.assertEqual(frontmatter.split("# A\n"), ({}, "# A\n"))
        with self.assertRaises(ValueError):
            frontmatter.split("---\ntitle: x\n")
        with self.assertRaises(ValueError):
            frontmatter.parse("title x\n")

    def test_comments_and_quotes(self):
        self.assertEqual(frontmatter.parse("a: b # note\nb: 'it''s'\nc: \"x #y\"\n"),
                         {"a": "b", "b": "it's", "c": "x #y"})

    def test_dump_round_trip(self):
        meta = {"title": "Recuperación: sí", "status": "draft", "base": None, "n": 2, "ok": False,
                "tags": ["a b", "c"], "none": []}
        self.assertEqual(frontmatter.parse(frontmatter.dump(meta)[4:-4]), meta)
        self.assertIn('title: "Recuperación: sí"', frontmatter.dump(meta))
        self.assertIn("status: draft", frontmatter.dump(meta))


if __name__ == "__main__":
    unittest.main()
