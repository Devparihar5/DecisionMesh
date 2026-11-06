"""Focused regression coverage using an isolated database and deterministic model fixtures."""
import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from agno.models.openai import OpenAIChat
from openai import AsyncOpenAI

from backend.app.agents.factory import AgnoRunner
from backend.app.agents.registry import AgentRegistry
from backend.app.core.config import Settings
from backend.app.core.errors import ApplicationError
from backend.app.orchestration.negotiation import arbitrate, parse_proposal
from backend.app.orchestration.twin import candidates, oracle
from backend.app.schemas.enterprise import AgentProposal, ApprovalInput, BenchmarkInput, EnterpriseEvent, EntityInput, ExecutionInput, Inventory
from backend.app.services.enterprise import EnterpriseService
from backend.app.services.evaluation import DATASET, EvaluationService
from backend.app.services.research_jobs import ResearchJobs
from backend.app.storage.agents import AgentRepository
from backend.app.storage.database import Database
from backend.app.storage.enterprise import EnterpriseRepository


class FixtureModels:
    async def resolve(self, requested):
        return 'fixture-model'


class FixtureRunner:
    def __init__(self):
        self.calls = []
        self.paused = None
        self.started = None
        self.invalid = False
        self.invalid_once = False
        self.disagree = False

    async def propose(self, agent, model, prompt):
        return await self.run(agent, model, prompt)

    async def run(self, agent, model, prompt):
        self.calls.append((agent.id, prompt))
        if self.started:
            self.started.set()
        if self.paused:
            await self.paused.wait()
        if self.invalid:
            return 'not a valid JSON proposal'
        if self.invalid_once:
            self.invalid_once = False
            return 'A malformed first answer that must be repaired.'
        data, _ = json.JSONDecoder().raw_decode(prompt.split('snapshot:\n', 1)[1])
        valid = [option for option in data['candidate_simulations'] if not option['violations']]
        action = max(valid, key=lambda option: option['utility'])['action']
        if self.disagree and 'Previous round' not in prompt and agent.id == 'finance':
            action = 'defer'
        return json.dumps({'action': action, 'reason': 'Select a feasible action based on the supplied simulated service and cost evidence.', 'evidence': data['evidence_ids']})


class EnterpriseTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'enterprise.sqlite3'
        self.database = Database(self.path)
        self.repository = EnterpriseRepository(self.database)
        self.service = EnterpriseService(self.repository)
        self.repository.create_entity(EntityInput(id='qa-warehouse', name='QA warehouse'))
        self.registry = AgentRegistry(AgentRepository(self.database))
        self.runner = FixtureRunner()
        self.jobs = ResearchJobs(self.repository, FixtureModels(), self.registry, self.runner)
        self.addAsyncCleanup(self.jobs.shutdown)
        self.clock = datetime.now(timezone.utc) - timedelta(seconds=30)
        self.sequence = 0

    def ingest(self, changes=None, occurred_at=None):
        self.sequence += 1
        return self.service.ingest(EnterpriseEvent(event_id=str(self.sequence), source='fixture-source', entity_id='qa-warehouse',
            occurred_at=occurred_at or self.clock + timedelta(seconds=self.sequence), changes=changes or {'demand': 140}))

    def approval(self, case_id, action='defer'):
        case = self.repository.case(case_id)
        return self.repository.approve(case_id, ApprovalInput(action=action, state_version=case.state_version,
            reviewer='QA operator', rationale='Explicitly accept this feasible simulated choice.'))

    async def await_job(self, job_id):
        for _ in range(100):
            await asyncio.sleep(.01)
            job = self.repository.job(job_id)
            if job.status != 'running':
                return job
        self.fail('Fixture job did not terminate')

    def test_atomic_ingestion_deduplication_and_event_identity_conflict(self):
        event = EnterpriseEvent(event_id='fixed', source='fixture-source', entity_id='qa-warehouse', occurred_at=self.clock, changes={'capacity': 25})
        first = self.service.ingest(event)
        second = self.service.ingest(event)
        self.assertEqual(first['state_version'], 1)
        self.assertEqual(second['case_id'], first['case_id'])
        self.assertTrue(second['duplicate'])
        with self.assertRaises(ApplicationError) as error:
            self.service.ingest(event.model_copy(update={'description': 'changed content'}))
        self.assertEqual(error.exception.status_code, 409)
        snapshot = self.service.snapshot('qa-warehouse')
        self.assertEqual(snapshot['entity']['version'], 1)
        self.assertEqual(len(snapshot['cases']), 1)
        self.assertEqual(len(snapshot['events']), 1)

    def test_stale_future_and_out_of_order_observations_do_not_change_state(self):
        self.ingest()
        for instant in (self.clock - timedelta(days=2), self.clock, datetime.now(timezone.utc) + timedelta(minutes=2)):
            self.assertEqual(self.ingest(occurred_at=instant)['status'], 'rejected')
        self.assertEqual(self.repository.entity('qa-warehouse').version, 1)
        self.assertEqual(len(self.repository.events('qa-warehouse')), 4)

    def test_budget_block_and_operator_override_are_explicit(self):
        case_id = self.ingest({'budget': 0})['case_id']
        with self.assertRaises(ApplicationError):
            self.approval(case_id, 'backup')
        accepted = self.approval(case_id, 'defer')
        self.assertEqual(accepted['adapter'], 'local_simulator')
        self.assertIn('operator_override', accepted)
        self.assertTrue(self.repository.case(case_id).requires_review)

    def test_execution_is_idempotent_and_creates_feedback_once(self):
        case_id = self.ingest()['case_id']
        approval = self.approval(case_id, 'backup')
        request = ExecutionInput(approval_id=approval['id'], idempotency_key='qa-idempotency-one')
        first = self.repository.execute(case_id, request, self.service.transition)
        second = self.repository.execute(case_id, request, self.service.transition)
        self.assertEqual(first, second)
        self.assertEqual(self.repository.entity('qa-warehouse').version, 2)
        self.assertEqual(len(self.repository.executions('qa-warehouse')), 1)
        self.assertEqual(len(self.repository.cases('qa-warehouse')), 2)
        feedback = self.repository.case(first['feedback_case_id'])
        self.assertEqual(feedback.parent_case_id, case_id)
        self.assertEqual(feedback.state.state.demand, first['outcome']['unmet'])
        with self.assertRaises(ApplicationError):
            self.repository.execute(case_id, request.model_copy(update={'idempotency_key': 'qa-idempotency-two'}), self.service.transition)

    def test_new_observation_invalidates_old_approval(self):
        case_id = self.ingest()['case_id']
        approval = self.approval(case_id)
        self.ingest({'demand': 180})
        with self.assertRaises(ApplicationError) as error:
            self.repository.execute(case_id, ExecutionInput(approval_id=approval['id'], idempotency_key='qa-stale-approval'), self.service.transition)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(self.repository.executions('qa-warehouse')), 0)

    def test_expired_approval_is_rejected(self):
        case_id = self.ingest()['case_id']
        approval = self.approval(case_id)
        approval['expires_at'] = self.clock.isoformat()
        with self.database.connection() as connection:
            connection.execute('UPDATE action_approvals SET payload=? WHERE id=?', (json.dumps(approval), approval['id']))
        with self.assertRaises(ApplicationError) as error:
            self.repository.execute(case_id, ExecutionInput(approval_id=approval['id'], idempotency_key='qa-expired-approval'), self.service.transition)
        self.assertIn('expired', error.exception.detail)

    def test_drift_reconciles_only_the_unobserved_simulation_prediction(self):
        case_id = self.ingest()['case_id']
        approval = self.approval(case_id, 'backup')
        self.repository.execute(case_id, ExecutionInput(approval_id=approval['id'], idempotency_key='qa-drift-execution'), self.service.transition)
        first = self.repository.case(self.ingest({'inventory': 55})['case_id'])
        self.assertIsNotNone(first.drift)
        second = self.repository.case(self.ingest({'inventory': 60})['case_id'])
        self.assertIsNone(second.drift)

    async def test_peer_exchange_contract_and_atomic_resolution(self):
        case_id = self.ingest()['case_id']
        self.runner.disagree = True
        job = await self.jobs.negotiate(case_id, '', ['operations', 'finance'])
        final = await self.await_job(job.id)
        self.assertEqual(final.status, 'complete')
        case = self.repository.case(case_id)
        self.assertEqual(len(case.rounds), 3)
        self.assertTrue(case.rounds[1].conflicts)
        self.assertFalse(case.rounds[2].conflicts)
        self.assertEqual(len(self.runner.calls), 4)
        self.assertIn('Previous round', self.runner.calls[-1][1])
        self.assertEqual(final.result['selected_action'], case.selected_action)

    async def test_invalid_model_proposals_are_saved_and_escalated(self):
        case_id = self.ingest()['case_id']
        self.runner.invalid = True
        job = await self.jobs.negotiate(case_id, '', ['operations', 'finance'])
        final = await self.await_job(job.id)
        case = self.repository.case(case_id)
        self.assertEqual(final.status, 'complete')
        self.assertEqual(case.selected_action, 'defer')
        self.assertTrue(case.requires_review)
        self.assertEqual(len([item for item in final.progress if item['stage'] == 'invalid_proposal']), 8)

    async def test_one_repair_recovers_format_and_preserves_original_attempt(self):
        case_id = self.ingest()['case_id']
        self.runner.invalid_once = True
        job = await self.jobs.negotiate(case_id, '', ['operations', 'finance'])
        final = await self.await_job(job.id)
        self.assertEqual(final.status, 'complete')
        self.assertEqual(len(self.runner.calls), 3)
        self.assertEqual(len([item for item in final.progress if item['stage'] == 'invalid_proposal']), 1)
        self.assertEqual(len([item for item in final.progress if item['stage'] == 'proposal']), 2)
        self.assertIn('Previous answer to correct', self.runner.calls[1][1])
        proposals = self.repository.case(case_id).rounds[-1].proposals
        self.assertTrue(all(reference.startswith(('state:', 'fixture-source:')) for item in proposals for reference in item.evidence))

    async def test_benchmark_includes_format_repair_in_actual_call_counts(self):
        self.runner.invalid_once = True
        job = await EvaluationService(self.jobs).start(BenchmarkInput())
        final = await self.await_job(job.id)
        self.assertEqual(final.status, 'complete')
        self.assertEqual(final.result['summary']['centralized']['model_calls'], 7)
        self.assertEqual(final.result['summary']['centralized']['quality_score'], 100)
        recorded = sum(item['stage'] == 'agent_start' for item in final.progress)
        self.assertEqual(recorded, sum(item['model_calls'] for item in final.result['trials']))

    async def test_stale_negotiation_cannot_replace_newer_state(self):
        case_id = self.ingest()['case_id']
        self.runner.started, self.runner.paused = asyncio.Event(), asyncio.Event()
        job = await self.jobs.negotiate(case_id, '', ['operations', 'finance'])
        await self.runner.started.wait()
        self.ingest({'demand': 190})
        self.runner.paused.set()
        final = await self.await_job(job.id)
        self.assertEqual(final.status, 'failed')
        self.assertIn('changed the state', final.error)
        self.assertEqual(len(self.repository.case(case_id).rounds), 1)

    async def test_cancellation_retains_progress_and_releases_case(self):
        case_id = self.ingest()['case_id']
        self.runner.started, self.runner.paused = asyncio.Event(), asyncio.Event()
        job = await self.jobs.negotiate(case_id, '', ['operations', 'finance'])
        await self.runner.started.wait()
        cancelled = self.jobs.cancel(job.id)
        self.assertEqual(cancelled.status, 'cancelled')
        await asyncio.sleep(.01)
        self.assertTrue(self.repository.job(job.id).progress)
        self.assertEqual(len(self.repository.case(case_id).rounds), 1)
        self.assertTrue(self.approval(case_id))

    async def test_fixture_benchmark_records_all_twelve_trials_and_rubric_scores(self):
        job = await EvaluationService(self.jobs).start(BenchmarkInput())
        final = await self.await_job(job.id)
        self.assertEqual(final.status, 'complete', final.error)
        self.assertEqual(len(final.result['trials']), 12)
        self.assertEqual(len(final.config['dataset']), 6)
        self.assertTrue(final.config['dataset_hash'])
        for architecture in ('centralized', 'orchestrated'):
            summary = final.result['summary'][architecture]
            self.assertEqual(summary['samples'], 6)
            self.assertEqual(summary['quality_score'], 100)
            self.assertEqual(summary['policy_compliance_rate'], 100)
        self.assertIsNone(final.result['summary']['orchestrated']['recovery_time_ms'])

    def test_recovery_preserves_checkpoints_and_job_progress(self):
        case_id = self.ingest()['case_id']
        job = self.repository.create_job('negotiation', case_id, {'model': 'fixture-model'})
        self.repository.update_job(job.id, progress={'stage': 'proposal_received'})
        reloaded = EnterpriseRepository(Database(self.path))
        reloaded.recover_jobs()
        self.assertEqual(reloaded.job(job.id).status, 'interrupted')
        self.assertEqual(reloaded.job(job.id).progress[0]['stage'], 'proposal_received')
        self.assertEqual(reloaded.case(case_id).state_version, 1)

    def test_fabricated_evidence_is_rejected_and_equivalent_outcomes_do_not_conflict(self):
        with self.assertRaises(ValueError):
            parse_proposal('{"action":"backup","reason":"Use the supplied evidence","evidence":["invented"]}', ['real'])
        options = candidates(Inventory(inventory=200, demand=100))
        proposals = [AgentProposal(agent_id=agent, action=action, round=1, reason='All demand is served without spend.', evidence=['real']) for agent, action in [('operations', 'hold'), ('finance', 'defer')]]
        self.assertFalse(arbitrate(proposals, options, 1).conflicts)
        for item in DATASET:
            winner = oracle(candidates(Inventory(**item['state'])))
            self.assertFalse(winner.violations)


class StructuredAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_proposal_json_contract_is_in_system_instructions_without_markdown(self):
        def completion(request):
            payload = json.loads(request.content)
            instructions = '\n'.join(item['content'] for item in payload['messages'] if item['role'] == 'system')
            self.assertIn('Return ONLY one valid JSON object', instructions)
            self.assertNotIn('Use markdown to format', instructions)
            self.assertNotIn('response_format', payload)
            self.assertIs(payload['stream'], False)
            return httpx.Response(200, json={'id': 'qa-proposal', 'object': 'chat.completion', 'created': 1,
                'model': 'fixture-model', 'choices': [{'index': 0, 'finish_reason': 'stop',
                    'message': {'role': 'assistant', 'content': '{"action":"defer","reason":"Respect the remaining budget.","evidence":["E1"]}'}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(completion)) as http:
            client = AsyncOpenAI(base_url='http://local.invalid/v1', api_key='local', http_client=http)
            with patch('backend.app.agents.factory.OpenAIChat', wraps=OpenAIChat) as adapter:
                adapter.default_role_map = OpenAIChat.default_role_map
                adapter.side_effect = lambda **kwargs: OpenAIChat(**kwargs, async_client=client)
                output = await AgnoRunner(Settings('http://local.invalid/v1', 'local', '')).propose(
                    AgentRegistry().get('risk'), 'fixture-model', 'Choose a feasible inventory action using E1.')
            self.assertEqual(json.loads(output)['evidence'], ['E1'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
