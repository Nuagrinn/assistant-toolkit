from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from assistant_toolkit.db import Database


class DatabaseTests(unittest.TestCase):
    def test_migrations_apply_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            migrations = root / "migrations"
            migrations.mkdir()
            (migrations / "001_initial.sql").write_text(
                "CREATE TABLE items (id TEXT PRIMARY KEY, title TEXT NOT NULL);",
                encoding="utf-8",
            )
            (migrations / "002_insert.sql").write_text(
                "INSERT INTO items (id, title) VALUES ('a', 'A');",
                encoding="utf-8",
            )

            db = Database(root / "data" / "app.sqlite3", migrations_dir=migrations)
            first = db.migrate()
            second = db.migrate()

            self.assertEqual(first.applied, ["001_initial", "002_insert"])
            self.assertEqual(second.applied, [])
            self.assertEqual(second.skipped, ["001_initial", "002_insert"])
            self.assertEqual(db.applied_migrations(), ["001_initial", "002_insert"])

            with db.session() as conn:
                row = conn.execute("SELECT title FROM items WHERE id = 'a'").fetchone()
            self.assertEqual(row["title"], "A")


if __name__ == "__main__":
    unittest.main()

