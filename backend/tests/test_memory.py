"""SQLite restart, lifecycle, filtering, and analytics regression coverage."""
import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from backend.app.agents.registry import AgentRegistry
from backend.app.core.config import Settings
from backend.app.core.errors import ApplicationError
from backend.app.main import create_app
from backend.app.orchestration.coordinator import Coordinator
from backend.app.orchestration.events import RunEvent, timestamp
from backend.app.schemas.agents import AgentInput
from backend.app.schemas.runs import RunInput
from backend.app.services.analytics import AnalyticsService
from backend.app.services.runs import RunService
from backend.app.storage.agents import AgentRepository
from backend.app.storage.database import Database
from backend.app.storage.runs import RunRepository


class LocalModels:
    async def resolve(self, requested):
        return 'system'


class LocalRunner:
    async def run(self, config, model, prompt):
        return f'Finding: {config.name}'


class MemoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'memory.sqlite3'
        self.database = Database(self.path)
        self.catalog = AgentRegistry(AgentRepository(self.database))
        self.history = RunRepository(self.database)
        self.analytics = AnalyticsService(self.database)
        self.request = RunInput(scenario='A supplier outage affects delivery.', selected_agents=['finance'])

    def service(self, runner=None, models=None):
        return RunService(self.catalog, models or LocalModels(), Coordinator(runner or LocalRunner()), self.history)

    async def test_run_events_findings_and_catalog_survive_restart(self):
        custom = self.catalog.create(AgentInput(name='Customer impact', role='Customer analysis', instructions='Assess customer impact.'))
        events = [event async for event in await self.service().prepare(self.request)]
        run_id = events[0].run_id
        original = self.catalog.get('finance')
        self.catalog.update('finance', AgentInput(name='New finance role', role='Finance', instructions='A different prompt for future runs.'))
        self.catalog.delete('operations')

        restarted = Database(self.path)
        catalog = AgentRegistry(AgentRepository(restarted))
        self.assertEqual(catalog.get(custom.id).name, 'Customer impact')
        with self.assertRaises(ApplicationError):
            catalog.get('operations')
        detail = RunRepository(restarted).detail(run_id)
        self.assertEqual(detail.status, 'complete')
        self.assertEqual(detail.model, 'system')
        self.assertEqual(detail.scenario, self.request.scenario)
        self.assertEqual(detail.agents[0].instructions, original.instructions)
        self.assertEqual(len(detail.events), len(events))
        self.assertEqual(detail.executions[-1].content, 'Finding: Decision synthesizer')

    async def test_provider_failure_is_saved_before_generation(self):
        class Offline:
            async def resolve(self, requested):
                raise ApplicationError('Model unavailable', 503)

        with self.assertRaises(ApplicationError):
            await self.service(models=Offline()).prepare(self.request)
        summary = self.history.list_runs().items[0]
        self.assertEqual(summary.status, 'failed')
        self.assertTrue(all(item.status == 'skipped' for item in self.history.detail(summary.id).executions))
        report = self.analytics.report()
        self.assertEqual(report.failed_runs, 1)
        self.assertEqual(sum(agent.attempts for agent in report.agents), 0)
        self.assertIsNone(next(agent for agent in report.agents if agent.agent_id == 'finance').success_rate)

    async def test_cancelled_generation_is_saved_and_not_counted_as_model_failure(self):
        class Slow:
            async def run(self, config, model, prompt):
                await asyncio.Event().wait()

        source = await self.service(runner=Slow()).prepare(self.request)
        start = await anext(source)
        await anext(source)
        task = asyncio.create_task(anext(source))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        detail = self.history.detail(start.run_id)
        self.assertEqual(detail.status, 'cancelled')
        self.assertEqual(detail.executions[0].status, 'cancelled')
        self.assertTrue(all(item.status == 'skipped' for item in detail.executions[1:]))
        metric = next(item for item in self.analytics.report().agents if item.agent_id == 'finance')
        self.assertEqual(metric.attempts, 1)
        self.assertEqual(metric.cancelled, 1)
        self.assertEqual(metric.failed, 0)
        self.assertIsNone(metric.success_rate)

    async def test_close_between_events_also_finalizes_memory(self):
        source = await self.service().prepare(self.request)
        start = await anext(source)
        await source.aclose()
        self.assertEqual(self.history.detail(start.run_id).status, 'cancelled')

    async def test_restart_marks_abandoned_runs_interrupted(self):
        run_id = self.history.create(self.request, self.catalog.specialists(['finance']))
        self.history.record(RunEvent(sequence=1, run_id=run_id, timestamp=timestamp(), type='agent_start', agent_id='finance'))
        self.history.recover_interrupted()
        detail = self.history.detail(run_id)
        self.assertEqual(detail.status, 'interrupted')
        self.assertEqual(detail.executions[0].status, 'interrupted')
        self.assertIsNone(detail.duration_ms)  # Downtime is not inferred as generation time.
        self.history.recover_interrupted()
        self.assertEqual(self.history.detail(run_id).status, 'interrupted')

    async def test_filtering_and_literal_search(self):
        for scenario in ['Supplier risk with 12% costs', 'Warehouse overflow', 'Supplier timing']:
            request = self.request.model_copy(update={'scenario': scenario})
            _ = [event async for event in await self.service().prepare(request)]
        page = self.history.list_runs(limit=1, offset=1, status='complete', search='supplier')
        self.assertEqual(page.total, 2)
        self.assertEqual(len(page.items), 1)
        self.assertEqual(self.history.list_runs(search='%').total, 1)
        self.assertEqual(self.history.list_runs(status='failed').total, 0)

    async def test_analytics_counts_real_attempts_and_known_percentiles(self):
        # Build a reproducible sample with explicit durations rather than a clock assumption.
        finance = self.catalog.get('finance')
        for index, duration in enumerate([100, 200, 300, None]):
            run_id = self.history.create(self.request, [finance])
            at = timestamp()
            self.history.record(RunEvent(sequence=1, run_id=run_id, timestamp=at, type='agent_start', agent_id='finance'))
            self.history.record(RunEvent(sequence=2, run_id=run_id, timestamp=at,
                type='agent_done' if duration else 'agent_error', agent_id='finance', duration_ms=duration or 10))
            self.history.record(RunEvent(sequence=3, run_id=run_id, timestamp=at,
                type='complete' if duration else 'error', elapsed_ms=duration or 10,
                degraded=index == 2, message=None if duration else 'Synthesis failed.'))
        queued = self.history.create(self.request, [finance])
        self.history.finish(queued, 'cancelled')
        report = self.analytics.report(7)
        self.assertEqual(report.total_runs, 5)
        self.assertEqual(report.completed_runs, 3)
        self.assertEqual(report.partial_runs, 1)
        self.assertEqual(report.completion_rate, 60)
        self.assertEqual(report.average_duration_ms, 200)
        metric = next(agent for agent in report.agents if agent.agent_id == 'finance')
        self.assertEqual(metric.attempts, 4)
        self.assertEqual(metric.success_rate, 75)
        self.assertEqual(metric.average_duration_ms, 200)
        self.assertEqual(metric.p95_duration_ms, 300)
        self.assertEqual(metric.skipped, 1)
        self.assertEqual(len(report.daily), 7)
        self.assertEqual(sum(day.total for day in report.daily), 5)

    async def test_partial_workflow_keeps_deleted_agents_in_analytics(self):
        class FailFinance:
            async def run(self, config, model, prompt):
                if config.id == 'finance':
                    raise RuntimeError('Simulated failure')
                return 'Successful finding'

        request = self.request.model_copy(update={'selected_agents': ['finance', 'operations']})
        events = [event async for event in await self.service(runner=FailFinance()).prepare(request)]
        self.catalog.delete('finance')
        detail = self.history.detail(events[0].run_id)
        self.assertTrue(detail.degraded)
        report = self.analytics.report()
        self.assertEqual(report.partial_runs, 1)
        finance = next(agent for agent in report.agents if agent.agent_id == 'finance')
        self.assertEqual(finance.failed, 1)
        self.assertEqual(finance.success_rate, 0)


class MemoryApiTests(unittest.TestCase):
    def test_history_analytics_and_restart_routes(self):
        with TemporaryDirectory() as directory:
            settings = Settings('http://127.0.0.1:11434/v1', 'local', '', database_path=Path(directory) / 'memory.sqlite3')
            with TestClient(create_app(settings)) as client:
                client.app.state.models = LocalModels()
                client.app.state.coordinator = Coordinator(LocalRunner())
                response = client.post('/api/run', json={'scenario': 'Supplier outage delays delivery.', 'selected_agents': ['finance']})
                self.assertEqual(response.status_code, 200)
                saved = client.get('/api/runs').json()
                self.assertEqual(saved['total'], 1)
                run_id = saved['items'][0]['id']
                self.assertEqual(client.get(f'/api/runs/{run_id}').json()['status'], 'complete')
                self.assertEqual(client.get('/api/runs/missing').status_code, 404)
                analytics = client.get('/api/analytics?days=7')
                self.assertEqual(analytics.status_code, 200, analytics.text)
                self.assertEqual(analytics.json()['total_runs'], 1)
                self.assertEqual(client.get('/api/runs?offset=-1').status_code, 422)
            with TestClient(create_app(settings)) as client:
                self.assertEqual(client.get('/api/runs').json()['total'], 1)
                self.assertEqual(client.get('/api/analytics?days=0').json()['completed_runs'], 1)
                self.assertEqual(client.get('/api/analytics?days=8').status_code, 422)


class DatabaseNamingTests(unittest.TestCase):
    def test_new_default_imports_previous_memory_once_without_removing_original(self):
        with TemporaryDirectory() as directory:
            legacy_path = Path(directory) / 'orchestrate.sqlite3'
            legacy = Database(legacy_path)
            registry = AgentRegistry(AgentRepository(legacy))
            request = RunInput(scenario='A historical supplier delivery risk.', selected_agents=['finance'])
            old_history = RunRepository(legacy)
            run_id = old_history.create(request, registry.specialists(['finance']))
            old_history.finish(run_id, 'failed', 'Historical run')
            destination = Path(directory) / 'decisionmesh.sqlite3'
            # Keep a committed WAL write open while importing; backup must include it.
            with legacy.connection() as connection:
                connection.execute("INSERT INTO metadata VALUES ('migration_probe', 'committed')")
                connection.commit()
                imported = Database(destination)
            new_history = RunRepository(imported)
            self.assertEqual(new_history.detail(run_id).scenario, request.scenario)
            self.assertTrue(legacy_path.exists())
            with imported.connection() as connection:
                self.assertEqual(connection.execute("SELECT value FROM metadata WHERE key='migration_probe'").fetchone()[0], 'committed')
            # A later startup must not overwrite newer records from the new database.
            additional = new_history.create(request, registry.specialists(['finance']))
            self.assertEqual(RunRepository(Database(destination)).list_runs().total, 2)
            self.assertEqual(RunRepository(Database(destination)).detail(additional).status, 'running')

    def test_custom_database_location_is_not_seeded_from_previous_default(self):
        with TemporaryDirectory() as directory:
            Database(Path(directory) / 'orchestrate.sqlite3')
            custom = Database(Path(directory) / 'separate-workspace.sqlite3')
            self.assertEqual(RunRepository(custom).list_runs().total, 0)
