"""Aggregate observed run and agent metrics from durable local records."""
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from backend.app.schemas.agents import AgentDefinition
from backend.app.schemas.analytics import AgentPerformance, AnalyticsReport, DailyRuns
from backend.app.storage.database import Database


def average(values: list[int]) -> int | None:
    return round(sum(values) / len(values)) if values else None


class AnalyticsService:
    def __init__(self, database: Database):
        self.database = database

    def report(self, days: int = 30) -> AnalyticsReport:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = (today - timedelta(days=days - 1)).isoformat() if days else ''
        with self.database.connection() as connection:
            runs = [dict(row) for row in connection.execute('SELECT * FROM runs WHERE created_at >= ?', (cutoff,))]
            executions = [dict(row) for row in connection.execute(
                'SELECT e.*, r.created_at FROM agent_executions e JOIN runs r ON r.id=e.run_id WHERE r.created_at >= ? ORDER BY r.created_at', (cutoff,))]
            # Include current roles that have no attempts yet; deleted roles remain
            # visible from immutable historical execution snapshots.
            definitions = [row['definition'] for row in connection.execute('SELECT definition FROM agents')]
        counts = Counter(run['status'] for run in runs)
        finished = sum(counts[status] for status in ['complete', 'failed', 'cancelled', 'interrupted'])
        completed_durations = [run['duration_ms'] for run in runs if run['status'] == 'complete' and run['duration_ms'] is not None]
        grouped = defaultdict(list)
        for execution in executions:
            grouped[execution['agent_id']].append(execution)
        metrics = {agent_id: self._agent(agent_id, rows) for agent_id, rows in grouped.items()}
        for definition in definitions:
            agent = AgentDefinition.model_validate_json(definition)
            if agent.id not in metrics:
                metrics[agent.id] = AgentPerformance(agent_id=agent.id, name=agent.name, role=agent.role, color=agent.color,
                    attempts=0, completed=0, failed=0, cancelled=0, interrupted=0, running=0, skipped=0,
                    success_rate=None, average_duration_ms=None, p95_duration_ms=None, last_run_at=None)
        trend_days = days or 90
        daily = []
        by_date = defaultdict(list)
        for run in runs:
            by_date[run['created_at'][:10]].append(run)
        for offset in range(trend_days - 1, -1, -1):
            date = (today - timedelta(days=offset)).date().isoformat()
            day_counts = Counter(run['status'] for run in by_date[date])
            daily.append(DailyRuns(date=date, total=len(by_date[date]), completed=day_counts['complete'],
                failed=day_counts['failed'], cancelled=day_counts['cancelled'], interrupted=day_counts['interrupted']))
        return AnalyticsReport(period_days=days, total_runs=len(runs), completed_runs=counts['complete'],
            partial_runs=sum(bool(run['degraded']) for run in runs if run['status'] == 'complete'),
            failed_runs=counts['failed'], cancelled_runs=counts['cancelled'], interrupted_runs=counts['interrupted'],
            awaiting_review_runs=counts['awaiting_review'], revised_runs=counts['revised'],
            running_runs=counts['running'], completion_rate=round(counts['complete'] / finished * 100, 1) if finished else None,
            average_duration_ms=average(completed_durations),
            agents=sorted(metrics.values(), key=lambda item: (-item.attempts, item.name)), daily=daily)

    @staticmethod
    def _agent(agent_id: str, rows: list[dict]) -> AgentPerformance:
        latest = rows[-1]
        counts = Counter(row['status'] for row in rows)
        completed_or_failed = counts['complete'] + counts['failed']
        durations = sorted(row['duration_ms'] for row in rows if row['status'] == 'complete' and row['duration_ms'] is not None)
        attempted = [row for row in rows if row['started_at'] is not None]
        return AgentPerformance(agent_id=agent_id, name=latest['name'], role=latest['role'], color=latest['color'],
            attempts=len(attempted), completed=counts['complete'], failed=counts['failed'], cancelled=counts['cancelled'],
            interrupted=counts['interrupted'], running=counts['running'], skipped=counts['skipped'],
            success_rate=round(counts['complete'] / completed_or_failed * 100, 1) if completed_or_failed else None,
            average_duration_ms=average(durations), p95_duration_ms=durations[math.ceil(.95 * len(durations)) - 1] if durations else None,
            last_run_at=attempted[-1]['created_at'] if attempted else None)
