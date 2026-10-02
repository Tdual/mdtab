"""Unit tests for path safety and link rewriting (no network, no pandoc needed)."""
import unittest
from pathlib import Path

from mdtab.server import HOME, rewrite_links, safe


class SafeTest(unittest.TestCase):
    def test_home_ok(self):
        self.assertEqual(safe(str(HOME / "x.md")), HOME / "x.md")

    def test_outside_home_rejected(self):
        self.assertIsNone(safe("/etc/hosts"))
        self.assertIsNone(safe(str(HOME / ".." / ".." / "etc" / "hosts")))


class RewriteTest(unittest.TestCase):
    base = HOME / "docs"

    def test_relative_image(self):
        out = rewrite_links('<img src="img/a.png">', self.base)
        self.assertIn('src="/api/raw?path=', out)
        self.assertIn("docs/img/a.png", out)

    def test_local_md_same_tab(self):
        out = rewrite_links('<a href="other.md">x</a>', self.base)
        self.assertIn('href="/view?path=', out)
        self.assertNotIn("_blank", out)

    def test_external_new_tab(self):
        out = rewrite_links('<a href="https://example.com">x</a>', self.base)
        self.assertIn('target="_blank"', out)

    def test_anchor_untouched(self):
        self.assertEqual(rewrite_links('<a href="#top">x</a>', self.base), '<a href="#top">x</a>')

    def test_outside_home_untouched(self):
        out = rewrite_links('<img src="/etc/hosts">', self.base)
        self.assertIn('src="/etc/hosts"', out)


if __name__ == "__main__":
    unittest.main()
