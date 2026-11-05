"""Atomic run/event recording and historical retrieval from local memory."""
import json
import sqlite3
from datetime import datetime
from uuid import uuid4

from backend.app.core.errors import ApplicationError
from backend.app.orchestration.events import RunEvent, timestamp
from backend.app.schemas.agents import AgentDefinition
from backend.app.schemas.history import ExecutionRecord, RunDetail, RunPage, RunSummary, StoredRunStatus
from backend.app.schemas.runs import RunInput
from backend.app.storage.database import Database


class RunRepository:
    def __init__(self, database: Database):
        self.database = database

    def create(self, request: RunInput, agents: list[AgentDefinition]) -> str:
        run_id = uuid4().hex
        with self.database.connection() as connection:
            connection.execute(
                'INSERT INTO runs (id, scenario, model, status, created_at, require_approval, agent_snapshot) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (run_id, request.scenario, request.model, 'running', timestamp(), request.require_approval,
                 json.dumps([agent.model_dump() for agent in agents])),
            )
            connection.executemany(
                'INSERT INTO agent_executions (run_id, agent_id, name, role, color) VALUES (?, ?, ?, ?, ?)',
                [(run_id, agent.id, agent.name, agent.role, agent.color) for agent in agents],
            )
        return run_id

    def record(self, event: RunEvent) -> None:
        with self.database.connection() as connection:
            connection.execute('INSERT INTO run_events VALUES (?, ?, ?)',
                               (event.run_id, event.sequence, event.model_dump_json()))
            if event.type == 'start':
                connection.execute('UPDATE runs SET model=? WHERE id=?', (event.model, event.run_id))
            elif event.type == 'agent_start':
                connection.execute("UPDATE agent_executions SET status='running', started_at=? WHERE run_id=? AND agent_id=?",
                                   (event.timestamp, event.run_id, event.agent_id))
            elif event.type in {'agent_done', 'agent_error'}:
                connection.execute(
                    'UPDATE agent_executions SET status=?, finished_at=?, duration_ms=?, content=?, error=? WHERE run_id=? AND agent_id=?',
                    ('complete' if event.type == 'agent_done' else 'failed', event.timestamp, event.duration_ms,
                     event.content, event.message, event.run_id, event.agent_id),
                )
            elif event.type in {'complete', 'error'}:
                connection.execute('UPDATE runs SET degraded=? WHERE id=?', (event.degraded, event.run_id))
                self._finish(connection, event.run_id, 'complete' if event.type == 'complete' else 'failed',
                             event.message, event.elapsed_ms)

    def _finish(self, connection: sqlite3.Connection, run_id: str, status: StoredRunStatus,
                error: str | None = None, duration_ms: int | None = None) -> None:
        row = connection.execute('SELECT status, created_at FROM runs WHERE id=?', (run_id,)).fetchone()
        if not row or row['status'] != 'running':
            return
        now = timestamp()
        if duration_ms is None and status != 'interrupted':
            duration_ms = max(0, round((datetime.fromisoformat(now) - datetime.fromisoformat(row['created_at'])).total_seconds() * 1000))
        connection.execute('UPDATE runs SET status=?, finished_at=?, duration_ms=?, error=? WHERE id=?',
                           (status, now, duration_ms, error, run_id))
        connection.execute("UPDATE agent_executions SET status='skipped' WHERE run_id=? AND status='queued'", (run_id,))
        active_status = status if status in {'cancelled', 'interrupted'} else 'failed'
        connection.execute("UPDATE agent_executions SET status=?, finished_at=?, error=? WHERE run_id=? AND status='running'",
                           (active_status, now, error, run_id))

    def finish(self, run_id: str, status: StoredRunStatus, error: str | None = None) -> None:
        with self.database.connection() as connection:
            self._finish(connection, run_id, status, error)

    def recover_interrupted(self) -> None:
        """A prior process cannot still own a running generation after restart."""
        with self.database.connection() as connection:
            for row in connection.execute("SELECT id FROM runs WHERE status='running'").fetchall():
                self._finish(connection, row['id'], 'interrupted', 'Backend restarted before this workflow finished.')

    @staticmethod
    def _summary(row: sqlite3.Row) -> RunSummary:
        data = dict(row)
        data['agent_count'] = len(json.loads(data.pop('agent_snapshot')))
        return RunSummary.model_validate(data)

    def list_runs(self, limit: int = 20, offset: int = 0, status: StoredRunStatus | None = None,
                  search: str = '') -> RunPage:
        filters, params = ['1=1'], []
        if status:
            filters.append('status=?')
            params.append(status)
        if search:
            filters.append('(instr(lower(scenario), lower(?)) > 0 OR instr(lower(id), lower(?)) > 0)')
            params.extend([search, search])
        where = ' AND '.join(filters)
        with self.database.connection() as connection:
            total = connection.execute(f'SELECT count(*) FROM runs WHERE {where}', params).fetchone()[0]
            rows = connection.execute(f'SELECT * FROM runs WHERE {where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?',
                                      [*params, limit, offset]).fetchall()
        return RunPage(items=[self._summary(row) for row in rows], total=total, limit=limit, offset=offset)

    def detail(self, run_id: str) -> RunDetail:
        with self.database.connection() as connection:
            row = connection.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if not row:
                raise ApplicationError('Run not found.', 404)
            executions = [ExecutionRecord.model_validate(dict(item)) for item in connection.execute(
                'SELECT * FROM agent_executions WHERE run_id=? ORDER BY rowid', (run_id,))]
            events = [RunEvent.model_validate_json(item['payload']) for item in connection.execute(
                'SELECT payload FROM run_events WHERE run_id=? ORDER BY sequence', (run_id,))]
        return RunDetail(**self._summary(row).model_dump(),
                         agents=[AgentDefinition.model_validate(agent) for agent in json.loads(row['agent_snapshot'])],
                         executions=executions, events=events)
