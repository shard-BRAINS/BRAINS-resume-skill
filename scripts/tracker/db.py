"""SQLite connection + migration runner for the tracker module.

The single public function is open_db(). It returns a sqlite3.Connection
with foreign keys enabled and all pending migrations applied. The db file
lives at ~/.brains-resume/tracker.db by default; tests override via the
BRAINS_TRACKER_DB_PATH environment variable.
"""
import importlib.util
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path


DEFAULT_DB_DIR = Path.home() / ".brains-resume"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "tracker.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_db_path() -> Path:
    """Return the tracker db path, honouring BRAINS_TRACKER_DB_PATH override."""
    override = os.environ.get("BRAINS_TRACKER_DB_PATH")
    if override:
        return Path(override)
    return DEFAULT_DB_PATH


def open_db() -> sqlite3.Connection:
    """Open (creating if needed) the tracker db, run pending migrations,
    apply post-migration backfill hooks, enable foreign keys, return the
    connection."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_migrations_table(conn)
    _run_pending_migrations(conn)
    _run_post_migration_hooks(conn)
    return conn


def _run_post_migration_hooks(conn: sqlite3.Connection) -> None:
    """Idempotent post-migration backfill. Safe to run on every open."""
    from scripts.tracker._post_migration import run_b_backfill
    run_b_backfill(conn)


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _run_pending_migrations(conn: sqlite3.Connection) -> None:
    applied = {
        row[0] for row in conn.execute("SELECT version FROM migrations")
    }
    for version, description, module in _discover_migrations():
        if version in applied:
            continue
        module.apply(conn)
        conn.execute(
            "INSERT INTO migrations (version, applied_at, description) VALUES (?, ?, ?)",
            (version, datetime.utcnow().isoformat() + "Z", description),
        )
        conn.commit()


def _discover_migrations():
    """Yield (version, description, module) for each migration script in order."""
    if not MIGRATIONS_DIR.exists():
        return
    pattern = re.compile(r"^(\d{4})_(.+)\.py$")
    for script in sorted(MIGRATIONS_DIR.glob("*.py")):
        if script.name.startswith("_"):
            continue
        match = pattern.match(script.name)
        if not match:
            continue
        version = int(match.group(1))
        description = match.group(2).replace("_", " ")
        spec = importlib.util.spec_from_file_location(
            f"_migration_{version}", script
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield version, description, module
