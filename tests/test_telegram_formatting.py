from __future__ import annotations

import unittest

from assistant_toolkit.telegram import h, rich, split_message


class TelegramFormattingTests(unittest.TestCase):
    def test_h_escapes_html(self) -> None:
        self.assertEqual(h("<tag>&"), "&lt;tag&gt;&amp;")

    def test_rich_renders_basic_markdown(self) -> None:
        rendered = rich("# Title\nUse `code` and **bold**")
        self.assertIn("<b>Title</b>", rendered)
        self.assertIn("<code>code</code>", rendered)
        self.assertIn("<b>bold</b>", rendered)

    def test_split_message(self) -> None:
        chunks = split_message("a\nb\nc", limit=4)
        self.assertEqual(chunks, ["a\nb", "c"])


if __name__ == "__main__":
    unittest.main()
