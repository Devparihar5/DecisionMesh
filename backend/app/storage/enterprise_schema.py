"""Additive schema for enterprise event/state/decision provenance."""

ENTERPRISE_SCHEMA = """
CREATE TABLE IF NOT EXISTS twin_entities (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS enterprise_events (
    source TEXT NOT NULL, event_id TEXT NOT NULL, entity_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL, payload TEXT NOT NULL, receipt TEXT NOT NULL,
    received_at TEXT NOT NULL, PRIMARY KEY(source, event_id)
);
CREATE TABLE IF NOT EXISTS decision_cases (
    id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES twin_entities(id),
    created_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cases_entity ON decision_cases(entity_id, created_at DESC);
CREATE TABLE IF NOT EXISTS action_approvals (
    id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES decision_cases(id),
    payload TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS action_executions (
    id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
    case_id TEXT NOT NULL UNIQUE REFERENCES decision_cases(id), fingerprint TEXT NOT NULL,
    payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_jobs (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, target_id TEXT NOT NULL,
    status TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_negotiation ON research_jobs(target_id)
    WHERE kind='negotiation' AND status='running';
"""
