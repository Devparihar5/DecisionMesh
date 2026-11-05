"""SQLite connection lifecycle and versioned schema initialization."""
import sqlite3
import tempfile
from contextlib import closing
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, definition TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    scenario TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER,
    require_approval INTEGER NOT NULL,
    degraded INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    agent_snapshot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS run_events (
    run_id TEXT NOT NULL REFERENCES runs(id),
    sequence INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (run_id, sequence)
);
CREATE TABLE IF NOT EXISTS agent_executions (
    run_id TEXT NOT NULL REFERENCES runs(id),
    agent_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    color TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER,
    content TEXT,
    error TEXT,
    PRIMARY KEY (run_id, agent_id)
);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_agent ON agent_executions(agent_id);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._import_previous_default()
        with self.connection() as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version > 1:
                raise RuntimeError('Local memory database was created by a newer application version.')
            connection.executescript(SCHEMA)
            connection.execute('PRAGMA user_version=1')

    def _import_previous_default(self) -> None:
        """Preserve existing local memory when adopting the DecisionMesh name."""
        legacy = self.path.with_name('orchestrate.sqlite3')
        if self.path.name != 'decisionmesh.sqlite3' or self.path.exists() or not legacy.exists():
            return
        # SQLite backup also includes committed WAL data from a live source.
        # Publish the copy atomically and keep the original file recoverable.
        with tempfile.NamedTemporaryFile(dir=self.path.parent, suffix='.sqlite3', delete=False) as temporary:
            backup = Path(temporary.name)
        try:
            with closing(sqlite3.connect(f'{legacy.as_uri()}?mode=ro', uri=True)) as source:
                with closing(sqlite3.connect(backup)) as destination:
                    source.backup(destination)
            backup.replace(self.path)
        finally:
            backup.unlink(missing_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        try:
            with connection:
                yield connection
        finally:
            connection.close()
