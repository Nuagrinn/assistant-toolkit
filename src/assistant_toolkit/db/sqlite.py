from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MigrationResult:
    applied: list[str]
    skipped: list[str]


class Database:
    """Small SQLite helper with transactions and SQL-file migrations."""

    def __init__(self, path: Path, *, migrations_dir: Path | None = None):
        self.path = Path(path)
        self.migrations_dir = Path(migrations_dir) if migrations_dir else None

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def migrate(self, migrations_dir: Path | None = None) -> MigrationResult:
        directory = Path(migrations_dir) if migrations_dir else self.migrations_dir
        migration_files = sorted(directory.glob("*.sql")) if directory and directory.exists() else []
        applied: list[str] = []
        skipped: list[str] = []

        with self.session() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            existing = {
                row["version"]
                for row in conn.execute("SELECT version FROM schema_migrations")
            }

            for path in migration_files:
                version = path.stem
                if version in existing:
                    skipped.append(version)
                    continue
                conn.executescript(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                applied.append(version)

        return MigrationResult(applied=applied, skipped=skipped)

    def applied_migrations(self) -> list[str]:
        with self.session() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        return [row["version"] for row in rows]

