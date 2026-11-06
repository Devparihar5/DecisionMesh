"""Human review must gate synthesis and retain operator decisions durably."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from backend.app.agents.registry import AgentRegistry
from backend.app.core.config import Settings
from backend.app.core.errors import ApplicationError
from backend.app.main import create_app
from backend.app.orchestration.coordinator import Coordinator
from backend.app.schemas.reviews import ReviewInput
from backend.app.schemas.runs import RunInput
from backend.app.services.analytics import AnalyticsService
from backend.app.services.runs import RunService
from backend.app.storage.agents import AgentRepository
from backend.app.storage.database import Database
from backend.app.storage.runs import RunRepository


class ReviewModel:
    async def resolve(self, requested):
        return 'test-model'


class ReviewRunner:
    def __init__(self):
        self.calls = []

    async def run(self, config, model, prompt):
        self.calls.append((config.id, prompt))
        return f'{config.name}: assessment {len(self.calls)}'


class ReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'review.sqlite3'
        self.database = Database(self.path)
        self.catalog = AgentRegistry(AgentRepository(self.database))
        self.history = RunRepository(self.database)
        self.runner = ReviewRunner()
        self.service = RunService(self.catalog, ReviewModel(), Coordinator(self.runner), self.history)
        self.request = RunInput(scenario='A supplier outage threatens customer deliveries.', selected_agents=['finance'])

    async def pause(self):
        events = [event async for event in await self.service.prepare(self.request)]
        return events[0].run_id, events

    async def test_review_pauses_before_synthesis_and_stays_pending_after_restart(self):
        run_id, events = await self.pause()
        self.assertEqual(events[-1].type, 'review_required')
        self.assertNotIn('decision_synth', [agent_id for agent_id, _ in self.runner.calls])
        self.assertEqual(self.history.detail(run_id).status, 'awaiting_review')
        restarted = RunRepository(Database(self.path))
        restarted.recover_interrupted()
        self.assertEqual(restarted.detail(run_id).status, 'awaiting_review')
        metrics = AnalyticsService(self.database).report()
        self.assertEqual(metrics.awaiting_review_runs, 1)
        self.assertIsNone(metrics.completion_rate)

    async def test_finalize_incorporates_suggestions_and_preserves_run_and_event_order(self):
        run_id, prior_events = await self.pause()
        reviewed = [event async for event in await self.service.review(
            run_id, ReviewInput(action='finalize', feedback='Prioritize delivery commitments.'),
        )]
        self.assertEqual(reviewed[-1].type, 'complete')
        self.assertTrue(reviewed[-1].human_reviewed)
        self.assertFalse(reviewed[-1].human_approval_required)
        prompt = self.runner.calls[-1][1]
        self.assertIn('Prioritize delivery commitments.', prompt)
        self.assertIn('Human oversight: assessment', prompt)
        self.assertIn('Finance: assessment', prompt)
        detail = self.history.detail(run_id)
        self.assertEqual(detail.status, 'complete')
        self.assertEqual(detail.review_action, 'finalize')
        self.assertEqual(detail.review_feedback, 'Prioritize delivery commitments.')
        self.assertEqual([event.sequence for event in detail.events], list(range(1, len(detail.events) + 1)))
        self.assertEqual(len(detail.events), len(prior_events) + len(reviewed))
        self.assertEqual({event.run_id for event in reviewed}, {run_id})

    async def test_rerun_creates_linked_revision_with_frozen_roles_and_guidance(self):
        run_id, _ = await self.pause()
        self.catalog.delete('finance')
        revised = [event async for event in await self.service.review(
            run_id, ReviewInput(action='rerun', feedback='Compare a partial supplier switch.'),
        )]
        new_id = revised[0].run_id
        self.assertNotEqual(new_id, run_id)
        self.assertEqual(revised[0].parent_run_id, run_id)
        self.assertEqual(revised[-1].type, 'review_required')
        original = self.history.detail(run_id)
        child = self.history.detail(new_id)
        self.assertEqual(original.status, 'revised')
        self.assertEqual(original.review_action, 'rerun')
        self.assertEqual(child.parent_run_id, run_id)
        self.assertEqual(child.input_feedback, 'Compare a partial supplier switch.')
        self.assertEqual(child.executions[0].agent_id, 'finance')
        repeated = [prompt for agent_id, prompt in self.runner.calls if agent_id == 'finance']
        self.assertEqual(len(repeated), 2)
        self.assertIn('Compare a partial supplier switch.', repeated[-1])
        report = AnalyticsService(self.database).report()
        self.assertEqual(report.revised_runs, 1)
        self.assertEqual(report.awaiting_review_runs, 1)
        self.assertIsNone(report.completion_rate)
        finalized = [event async for event in await self.service.review(new_id, ReviewInput(action='finalize'))]
        self.assertEqual(finalized[-1].type, 'complete')
        self.assertIn('Compare a partial supplier switch.', self.runner.calls[-1][1])

    async def test_duplicate_submission_cannot_generate_two_briefs(self):
        run_id, _ = await self.pause()
        first = await self.service.review(run_id, ReviewInput(action='finalize'))
        with self.assertRaises(ApplicationError) as rejected:
            await self.service.review(run_id, ReviewInput(action='finalize'))
        self.assertEqual(rejected.exception.status_code, 409)
        _ = [event async for event in first]
        self.assertEqual(sum(agent_id == 'decision_synth' for agent_id, _ in self.runner.calls), 1)

    async def test_unavailable_provider_leaves_review_pending_for_retry(self):
        class Offline:
            async def resolve(self, requested):
                raise ApplicationError('Model server unavailable.', 503)

        run_id, _ = await self.pause()
        offline = RunService(self.catalog, Offline(), Coordinator(self.runner), self.history)
        with self.assertRaises(ApplicationError):
            await offline.review(run_id, ReviewInput(action='finalize', feedback='Keep the original plan.'))
        detail = self.history.detail(run_id)
        self.assertEqual(detail.status, 'awaiting_review')
        self.assertIsNone(detail.review_action)

    async def test_operator_can_cancel_waiting_review_without_running_synthesis(self):
        run_id, _ = await self.pause()
        self.history.cancel_review(run_id)
        detail = self.history.detail(run_id)
        self.assertEqual(detail.status, 'cancelled')
        self.assertEqual(detail.executions[-1].status, 'skipped')
        self.assertNotIn('decision_synth', [agent_id for agent_id, _ in self.runner.calls])


class ReviewApiTests(unittest.TestCase):
    def test_review_validation_resume_and_duplicate_response(self):
        with TemporaryDirectory() as directory:
            settings = Settings('http://127.0.0.1:11434/v1', 'local', '', database_path=Path(directory) / 'api.sqlite3')
            with TestClient(create_app(settings)) as client:
                client.app.state.models = ReviewModel()
                client.app.state.coordinator = Coordinator(ReviewRunner())
                response = client.post('/api/run', json={'scenario': 'A supplier outage threatens delivery.', 'selected_agents': ['finance']})
                self.assertIn('event: review_required', response.text)
                run_id = client.get('/api/runs?status=awaiting_review').json()['items'][0]['id']
                invalid = client.post(f'/api/runs/{run_id}/review', json={'action': 'rerun', 'feedback': '   '})
                self.assertEqual(invalid.status_code, 422)
                self.assertEqual(client.get(f'/api/runs/{run_id}').json()['status'], 'awaiting_review')
                reviewed = client.post(f'/api/runs/{run_id}/review', json={'action': 'finalize', 'feedback': 'Prioritize continuity.'})
                self.assertEqual(reviewed.status_code, 200)
                self.assertIn('event: complete', reviewed.text)
                self.assertEqual(client.post(f'/api/runs/{run_id}/review', json={'action': 'finalize'}).status_code, 409)
                self.assertEqual(client.get(f'/api/runs/{run_id}').json()['review_feedback'], 'Prioritize continuity.')
