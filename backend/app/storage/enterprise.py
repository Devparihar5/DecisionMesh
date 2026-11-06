"""Atomic ingestion, compare-and-set decisions, scoped approvals, and jobs."""
import hashlib
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.app.core.errors import ApplicationError
from backend.app.orchestration.events import timestamp
from backend.app.schemas.enterprise import ApprovalInput, DecisionCase, EnterpriseEvent, EntityInput, ExecutionInput, Job, TwinState
from backend.app.storage.database import Database


def fingerprint(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class EnterpriseRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _entity(connection: sqlite3.Connection, entity_id: str) -> TwinState:
        row = connection.execute('SELECT payload FROM twin_entities WHERE id=?', (entity_id,)).fetchone()
        if not row:
            raise ApplicationError('Supply-chain entity not found.', 404)
        return TwinState.model_validate_json(row['payload'])

    @staticmethod
    def _case(connection: sqlite3.Connection, case_id: str) -> tuple[DecisionCase, int]:
        row = connection.execute('SELECT payload, revision FROM decision_cases WHERE id=?', (case_id,)).fetchone()
        if not row:
            raise ApplicationError('Decision case not found.', 404)
        return DecisionCase.model_validate_json(row['payload']), row['revision']

    @staticmethod
    def _insert_case(connection: sqlite3.Connection, case: DecisionCase) -> None:
        connection.execute('INSERT INTO decision_cases(id, entity_id, created_at, payload) VALUES (?, ?, ?, ?)',
                           (case.id, case.entity_id, case.created_at, case.model_dump_json()))

    def create_entity(self, value: EntityInput) -> TwinState:
        state = TwinState(**value.model_dump(), updated_at=timestamp())
        try:
            with self.database.connection() as connection:
                connection.execute('INSERT INTO twin_entities VALUES (?, ?)', (state.id, state.model_dump_json()))
        except sqlite3.IntegrityError as exc:
            raise ApplicationError('Entity ID already exists.', 409) from exc
        return state

    def entities(self) -> list[TwinState]:
        with self.database.connection() as connection:
            return [TwinState.model_validate_json(row['payload']) for row in connection.execute('SELECT payload FROM twin_entities ORDER BY id')]

    def entity(self, entity_id: str) -> TwinState:
        with self.database.connection() as connection:
            return self._entity(connection, entity_id)

    def case(self, case_id: str) -> DecisionCase:
        with self.database.connection() as connection:
            return self._case(connection, case_id)[0]

    def cases(self, entity_id: str) -> list[DecisionCase]:
        with self.database.connection() as connection:
            return [DecisionCase.model_validate_json(row['payload']) for row in connection.execute(
                'SELECT payload FROM decision_cases WHERE entity_id=? ORDER BY created_at DESC LIMIT 50', (entity_id,))]

    def events(self, entity_id: str) -> list[dict]:
        with self.database.connection() as connection:
            return [{'event': json.loads(row['payload']), 'receipt': json.loads(row['receipt']), 'received_at': row['received_at']}
                    for row in connection.execute('SELECT * FROM enterprise_events WHERE entity_id=? ORDER BY received_at DESC LIMIT 100', (entity_id,))]

    def ingest(self, event: EnterpriseEvent,
               transform: Callable[[TwinState], tuple[TwinState, DecisionCase]]) -> dict:
        payload = event.model_dump(mode='json')
        digest = fingerprint(payload)
        with self.database.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            existing = connection.execute('SELECT fingerprint, receipt FROM enterprise_events WHERE source=? AND event_id=?',
                                          (event.source, event.event_id)).fetchone()
            if existing:
                if existing['fingerprint'] != digest:
                    raise ApplicationError('Event ID was already used with different content.', 409)
                return {**json.loads(existing['receipt']), 'duplicate': True}
            current = self._entity(connection, event.entity_id)
            receipt = {'status': 'accepted', 'duplicate': False, 'event_id': event.event_id, 'source': event.source}
            try:
                next_state, case = transform(current)
            except ApplicationError as exc:
                receipt.update(status='rejected', reason=exc.detail)
            else:
                connection.execute('UPDATE twin_entities SET payload=? WHERE id=?', (next_state.model_dump_json(), current.id))
                self._insert_case(connection, case)
                receipt.update(state_version=next_state.version, case_id=case.id)
            connection.execute('INSERT INTO enterprise_events VALUES (?, ?, ?, ?, ?, ?, ?)',
                (event.source, event.event_id, event.entity_id, digest, json.dumps(payload), json.dumps(receipt), timestamp()))
            return receipt

    def save_negotiation(self, case: DecisionCase, expected_revision: int, job_id: str) -> None:
        with self.database.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            job_row = connection.execute('SELECT payload FROM research_jobs WHERE id=?', (job_id,)).fetchone()
            job = Job.model_validate_json(job_row['payload'])
            if job.status != 'running':
                raise ApplicationError('Negotiation was cancelled before its decision could be committed.', 409)
            state = self._entity(connection, case.entity_id)
            if state.version != case.state_version:
                raise ApplicationError('New events changed the state during negotiation. Open the latest case.', 409)
            count = connection.execute('UPDATE decision_cases SET payload=?, revision=revision+1 WHERE id=? AND revision=?',
                                       (case.model_dump_json(), case.id, expected_revision)).rowcount
            if count != 1:
                raise ApplicationError('Decision changed during negotiation. Refresh the case.', 409)
            job.status, job.updated_at = 'complete', timestamp()
            job.result = {'case_id': case.id, 'selected_action': case.selected_action,
                          'requires_review': case.requires_review, 'rounds': len(case.rounds)}
            connection.execute('UPDATE research_jobs SET status=?, payload=? WHERE id=?', (job.status, job.model_dump_json(), job.id))

    def case_revision(self, case_id: str) -> tuple[DecisionCase, int]:
        with self.database.connection() as connection:
            return self._case(connection, case_id)

    @staticmethod
    def _not_busy(connection: sqlite3.Connection, case_id: str) -> None:
        if connection.execute("SELECT 1 FROM research_jobs WHERE target_id=? AND kind='negotiation' AND status='running'", (case_id,)).fetchone():
            raise ApplicationError('Wait for agent negotiation to finish before approving an action.', 409)

    def approve(self, case_id: str, value: ApprovalInput) -> dict:
        with self.database.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            self._not_busy(connection, case_id)
            case, revision = self._case(connection, case_id)
            state = self._entity(connection, case.entity_id)
            if case.execution_id or state.version != value.state_version or case.state_version != state.version:
                raise ApplicationError('Decision is stale or already executed. Review the latest state.', 409)
            candidate = next(item for item in case.candidates if item.action == value.action)
            if candidate.violations:
                raise ApplicationError('Hard policy violations cannot be overridden: ' + '; '.join(candidate.violations), 409)
            approval = {'id': uuid4().hex, 'case_id': case_id, **value.model_dump(), 'case_revision': revision,
                'created_at': timestamp(), 'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                'adapter': 'local_simulator', 'action_fingerprint': fingerprint(candidate.model_dump()),
                'recommended_action': case.selected_action, 'operator_override': value.action != case.selected_action,
                'rule_version': case.rule_version}
            connection.execute('INSERT INTO action_approvals(id, case_id, payload) VALUES (?, ?, ?)',
                               (approval['id'], case_id, json.dumps(approval)))
            return approval

    def execute(self, case_id: str, value: ExecutionInput,
                transition: Callable[[DecisionCase, TwinState, dict], tuple[TwinState, DecisionCase, dict]]) -> dict:
        digest = fingerprint({'case_id': case_id, 'approval_id': value.approval_id})
        with self.database.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            old = connection.execute('SELECT fingerprint, payload FROM action_executions WHERE idempotency_key=?', (value.idempotency_key,)).fetchone()
            if old:
                if old['fingerprint'] != digest:
                    raise ApplicationError('Idempotency key belongs to another action.', 409)
                return json.loads(old['payload'])
            self._not_busy(connection, case_id)
            case, revision = self._case(connection, case_id)
            row = connection.execute('SELECT * FROM action_approvals WHERE id=? AND case_id=?', (value.approval_id, case_id)).fetchone()
            if not row or row['consumed']:
                raise ApplicationError('A fresh approval for this exact case is required.', 409)
            approval = json.loads(row['payload'])
            state = self._entity(connection, case.entity_id)
            if case.execution_id or state.version != approval['state_version'] or revision != approval['case_revision']:
                raise ApplicationError('Approval is stale or action already executed.', 409)
            if datetime.fromisoformat(approval['expires_at']) <= datetime.now(timezone.utc):
                raise ApplicationError('Approval expired. Review the action again.', 409)
            candidate = next(item for item in case.candidates if item.action == approval['action'])
            if candidate.violations or fingerprint(candidate.model_dump()) != approval['action_fingerprint']:
                raise ApplicationError('Action no longer satisfies the approved policy/simulation.', 409)
            next_state, feedback_case, outcome = transition(case, state, approval)
            receipt = {'id': uuid4().hex, 'case_id': case.id, 'approval': approval, 'idempotency_key': value.idempotency_key,
                'adapter': 'local_simulator', 'status': 'simulated', 'created_at': timestamp(),
                'before_version': state.version, 'after_version': next_state.version, 'feedback_case_id': feedback_case.id, **outcome}
            connection.execute('UPDATE twin_entities SET payload=? WHERE id=?', (next_state.model_dump_json(), state.id))
            self._insert_case(connection, feedback_case)
            case.status, case.execution_id = 'executed_simulation', receipt['id']
            connection.execute('UPDATE decision_cases SET payload=?, revision=revision+1 WHERE id=?', (case.model_dump_json(), case.id))
            connection.execute('UPDATE action_approvals SET consumed=1 WHERE id=?', (value.approval_id,))
            connection.execute('INSERT INTO action_executions VALUES (?, ?, ?, ?, ?, ?)',
                (receipt['id'], value.idempotency_key, case.id, digest, json.dumps(receipt), receipt['created_at']))
            return receipt

    def executions(self, entity_id: str) -> list[dict]:
        with self.database.connection() as connection:
            return [json.loads(row['payload']) for row in connection.execute(
                'SELECT e.payload FROM action_executions e JOIN decision_cases c ON c.id=e.case_id WHERE c.entity_id=? ORDER BY e.created_at DESC LIMIT 50', (entity_id,))]

    def snapshot(self, entity_id: str) -> dict:
        with self.database.connection() as connection:
            connection.execute('BEGIN')
            return {'entity': self._entity(connection, entity_id).model_dump(),
                'cases': [json.loads(row['payload']) for row in connection.execute(
                    'SELECT payload FROM decision_cases WHERE entity_id=? ORDER BY created_at DESC LIMIT 50', (entity_id,))],
                'events': [{'event': json.loads(row['payload']), 'receipt': json.loads(row['receipt']), 'received_at': row['received_at']}
                    for row in connection.execute('SELECT * FROM enterprise_events WHERE entity_id=? ORDER BY received_at DESC LIMIT 100', (entity_id,))],
                'executions': [json.loads(row['payload']) for row in connection.execute(
                    'SELECT e.payload FROM action_executions e JOIN decision_cases c ON c.id=e.case_id WHERE c.entity_id=? ORDER BY e.created_at DESC LIMIT 50', (entity_id,))]}

    def create_job(self, kind: str, target_id: str, config: dict) -> Job:
        job = Job(id=uuid4().hex, kind=kind, status='running', created_at=timestamp(), updated_at=timestamp(), config=config)
        try:
            with self.database.connection() as connection:
                connection.execute('BEGIN IMMEDIATE')
                if connection.execute("SELECT count(*) FROM research_jobs WHERE status='running'").fetchone()[0] >= 2:
                    raise ApplicationError('Two research jobs are already active. Wait or cancel one.', 409)
                if kind == 'negotiation':
                    case, _ = self._case(connection, target_id)
                    if case.execution_id or self._entity(connection, case.entity_id).version != case.state_version:
                        raise ApplicationError('Negotiate the latest unexecuted state.', 409)
                connection.execute('INSERT INTO research_jobs VALUES (?, ?, ?, ?, ?, ?)',
                                   (job.id, kind, target_id, job.status, job.model_dump_json(), job.created_at))
        except sqlite3.IntegrityError as exc:
            raise ApplicationError('Negotiation already running for this case.', 409) from exc
        return job

    def job(self, job_id: str) -> Job:
        with self.database.connection() as connection:
            row = connection.execute('SELECT payload FROM research_jobs WHERE id=?', (job_id,)).fetchone()
            if not row:
                raise ApplicationError('Research job not found.', 404)
            return Job.model_validate_json(row['payload'])

    def jobs(self, kind: str) -> list[Job]:
        with self.database.connection() as connection:
            return [Job.model_validate_json(row['payload']).model_copy(update={'progress': [], 'result': None}) for row in connection.execute(
                "SELECT payload FROM research_jobs WHERE kind=? ORDER BY (status='running') DESC, created_at DESC LIMIT 30", (kind,))]

    def update_job(self, job_id: str, progress: dict | None = None, status: str | None = None,
                   result: dict | None = None, error: str | None = None) -> Job:
        with self.database.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT payload FROM research_jobs WHERE id=?', (job_id,)).fetchone()
            job = Job.model_validate_json(row['payload'])
            if job.status != 'running':
                return job
            if progress:
                job.progress.append({**progress, 'timestamp': timestamp()})
            job.status, job.result, job.error, job.updated_at = status or job.status, result or job.result, error, timestamp()
            connection.execute('UPDATE research_jobs SET status=?, payload=? WHERE id=?', (job.status, job.model_dump_json(), job_id))
            return job

    def recover_jobs(self) -> None:
        with self.database.connection() as connection:
            active = [row['id'] for row in connection.execute("SELECT id FROM research_jobs WHERE status='running'")]
        for job_id in active:
            self.update_job(job_id, status='interrupted', error='Backend restarted; this job was not resumed.')
