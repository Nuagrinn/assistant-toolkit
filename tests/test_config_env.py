from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from assistant_toolkit.config import (
    load_env_file,
    parse_bool,
    parse_float,
    parse_hhmm,
    parse_int,
    resolve_path,
)


class ConfigEnvTests(unittest.TestCase):
    def test_load_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                """
                # comment
                TOKEN="abc"
                EMPTY=
                NAME='bot'
                """,
                encoding="utf-8",
            )

            self.assertEqual(load_env_file(path), {"TOKEN": "abc", "EMPTY": "", "NAME": "bot"})

    def test_parsers(self) -> None:
        self.assertTrue(parse_bool("yes"))
        self.assertFalse(parse_bool("off", default=True))
        self.assertEqual(parse_int("1_200", min_value=0), 1200)
        self.assertEqual(parse_int("bad", default=7), 7)
        self.assertEqual(parse_float("1,5"), 1.5)
        self.assertEqual(parse_hhmm("09:30", default=(1, 2)), (9, 30))
        self.assertEqual(parse_hhmm("25:00", default=(1, 2)), (1, 2))

    def test_resolve_path(self) -> None:
        self.assertEqual(
            resolve_path("data/db.sqlite", default=Path("x"), base_dir=Path("C:/root")),
            Path("C:/root") / "data/db.sqlite",
        )
        self.assertEqual(resolve_path("", default=Path("fallback")), Path("fallback"))


if __name__ == "__main__":
    unittest.main()

