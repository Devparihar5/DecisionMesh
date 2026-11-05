"""Behavior checks use a fake runner; no model requests or paid services."""
import asyncio
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from agno.models.openai import OpenAIChat
from openai import AsyncOpenAI

from backend.app.agents.registry import AgentRegistry
from backend.app.agents.factory import AgnoRunner
from backend.app.core.config import Settings
from backend.app.core.errors import ApplicationError
from backend.app.main import create_app
from backend.app.orchestration.coordinator import Coordinator, EventSequence
from backend.app.schemas.agents import AgentInput
from backend.app.schemas.runs import RunInput
from backend.app.services.models import ModelService


class FakeRunner:
    def __init__(self, fail=()):
        self.fail = set(fail)
        self.prompts = {}

    async def run(self, config, model_id, prompt):
        self.prompts[config.id] = prompt
        if config.id in self.fail:
            raise RuntimeError('Simulated provider failure')
        return f'Finding from {config.name}'


class CatalogTests(unittest.TestCase):
    def test_core_roles_protected_and_custom_roles_mutable(self):
        catalog = AgentRegistry()
        self.assertEqual(len(catalog.list_agents()), 7)
        body = AgentInput(name='Customer impact', role='Experience', instructions='Assess customer impact.')
        agent = catalog.create(body)
        self.assertEqual(agent.id, 'customer_impact')
        updated = catalog.update(agent.id, body.model_copy(update={'name': 'Customer outcomes'}))
        self.assertEqual(updated.id, agent.id)
        with self.assertRaises(ApplicationError):
            catalog.delete('decision_synth')
        catalog.delete(agent.id)
        with self.assertRaises(ApplicationError):
            catalog.get(agent.id)

    def test_selection_rejects_unknown_or_only_core_agents(self):
        catalog = AgentRegistry()
        for ids in [[], ['finance', 'missing'], ['human_review']]:
            with self.subTest(ids=ids), self.assertRaises(ApplicationError):
                catalog.specialists(ids)
        self.assertEqual([a.id for a in catalog.specialists(['finance', 'finance'])], ['finance'])


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def events(self, runner, ids=('finance',), approval=True):
        catalog = AgentRegistry()
        request = RunInput(scenario='A supplier outage delays an order.', selected_agents=list(ids), require_approval=approval)
        coordinator = Coordinator(runner)
        events = [event async for event in coordinator.events(
            request, 'local-model', catalog.specialists(list(ids)),
            catalog.get('human_review'), catalog.get('decision_synth'),
        )]
        if events[-1].type == 'review_required':
            findings = [(event.name, event.content) for event in events if event.type == 'agent_done']
            failed = [event.name for event in events if event.type == 'agent_error']
            sequence = EventSequence(events[-1].run_id, events[-1].sequence)
            events.extend([event async for event in coordinator.synthesize(
                request, 'local-model', catalog.get('decision_synth'), findings, failed, sequence,
            )])
        return events

    async def test_review_is_in_synthesis_and_events_ordered(self):
        runner = FakeRunner()
        events = await self.events(runner)
        self.assertIn('Finding from Human oversight', runner.prompts['decision_synth'])
        self.assertEqual(events[-1].type, 'complete')
        self.assertTrue(events[-1].human_reviewed)
        self.assertEqual([e.sequence for e in events], list(range(1, len(events) + 1)))
        self.assertEqual(len({e.run_id for e in events}), 1)
        self.assertTrue(events[0].sse().endswith('\n\n'))

    async def test_partial_failure_is_visible_and_marked_degraded(self):
        runner = FakeRunner(fail=['finance'])
        events = await self.events(runner, ids=('finance', 'operations'))
        self.assertTrue(any(e.type == 'agent_error' for e in events))
        self.assertTrue(events[-1].degraded)
        self.assertIn('Missing assessments: Finance', runner.prompts['decision_synth'])

    async def test_no_findings_and_failed_synthesis_never_complete(self):
        for failure in ['finance', 'decision_synth']:
            with self.subTest(failure=failure):
                events = await self.events(FakeRunner(fail=[failure]))
                self.assertEqual(events[-1].type, 'error')
                self.assertFalse(any(e.type == 'complete' for e in events))

    async def test_operator_may_skip_review(self):
        runner = FakeRunner()
        events = await self.events(runner, approval=False)
        self.assertNotIn('human_review', runner.prompts)
        self.assertFalse(events[-1].human_approval_required)

    async def test_cancellation_reaches_async_runner(self):
        cancelled = asyncio.Event()

        class SlowRunner:
            async def run(self, config, model_id, prompt):
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

        catalog = AgentRegistry()
        request = RunInput(scenario='A supplier outage delays an order.', selected_agents=['finance'])
        stream = Coordinator(SlowRunner()).events(request, 'local', catalog.specialists(['finance']), catalog.get('human_review'), catalog.get('decision_synth'))
        await anext(stream)
        await anext(stream)
        task = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(cancelled.is_set())


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_validates_selected_model(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={'data': [{'id': 'local-model'}]}))
        async with httpx.AsyncClient(transport=transport) as client:
            service = ModelService(Settings('http://127.0.0.1:11434/v1', 'local', ''), client)
            self.assertEqual(await service.resolve(''), 'local-model')
            with self.assertRaises(ApplicationError):
                await service.resolve('missing')

    async def test_endpoint_failure_becomes_actionable_status(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(503))
        async with httpx.AsyncClient(transport=transport) as client:
            service = ModelService(Settings('http://127.0.0.1:11434/v1', 'local', ''), client)
            health = await service.health()
            self.assertFalse(health.llm_online)
            self.assertIn('model server', health.error)


class RouteTests(unittest.TestCase):
    def test_catalog_validation_and_sse_route(self):
        with TemporaryDirectory() as directory, TestClient(create_app(Settings(
            'http://127.0.0.1:11434/v1', 'local', '', database_path=Path(directory) / 'memory.sqlite3'
        ))) as client:
            self.assertEqual(len(client.get('/api/agents').json()), 7)
            invalid = client.post('/api/agents', json={'name': '  ', 'role': 'R', 'instructions': ''})
            self.assertEqual(invalid.status_code, 422)
            self.assertEqual(client.delete('/api/agents/human_review').status_code, 400)
            client.app.state.coordinator = Coordinator(FakeRunner())

            class Provider:
                async def resolve(self, requested):
                    return 'local-model'

            client.app.state.models = Provider()
            response = client.post('/api/run', json={'scenario': 'Supplier outage delays a delivery.', 'selected_agents': ['finance']})
            self.assertEqual(response.status_code, 200)
            self.assertIn('text/event-stream', response.headers['content-type'])
            self.assertIn('event: review_required', response.text)
            self.assertNotIn('event: complete', response.text)
            saved = client.get('/api/runs').json()['items'][0]
            finalized = client.post(f"/api/runs/{saved['id']}/review", json={'action': 'finalize', 'feedback': 'Prioritize continuity.'})
            self.assertIn('event: complete', finalized.text)
            self.assertIn('Finding from Human oversight', response.text)
            self.assertEqual(client.post('/api/run', json={'scenario': 'Supplier outage', 'selected_agents': []}).status_code, 422)


class AgnoAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_agno_adapter_uses_local_chat_completion_contract(self):
        requests = []

        def completion(request):
            payload = json.loads(request.content)
            self.assertIs(payload['stream'], False)
            self.assertEqual(payload['messages'][0]['role'], 'system')
            self.assertTrue(all(message['role'] in {'system', 'user', 'assistant'} for message in payload['messages']))
            self.assertTrue(all(isinstance(message['content'], str) for message in payload['messages']))
            requests.append(request)
            return httpx.Response(200, json={
                'id': 'local-completion', 'object': 'chat.completion', 'created': 1,
                'model': 'local-model',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Review the supplier risk.'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 6, 'total_tokens': 16},
            })

        async with httpx.AsyncClient(transport=httpx.MockTransport(completion)) as http:
            client = AsyncOpenAI(base_url='http://127.0.0.1:11434/v1', api_key='local', http_client=http)
            original = OpenAIChat
            # Preserve the adapter's class-level role map while injecting HTTP.
            with patch('backend.app.agents.factory.OpenAIChat', wraps=original) as adapter:
                adapter.default_role_map = original.default_role_map
                adapter.side_effect = lambda **kwargs: original(**kwargs, async_client=client)
                output = await AgnoRunner(Settings('http://127.0.0.1:11434/v1', 'local', '')).run(
                    AgentRegistry().get('risk'), 'local-model', 'A supplier has reported an outage.',
                )
            self.assertEqual(output, 'Review the supplier risk.')
            self.assertEqual(str(requests[0].url), 'http://127.0.0.1:11434/v1/chat/completions')


class ModelConfigurationTests(unittest.TestCase):
    def test_default_endpoint_and_credentials_are_provider_neutral(self):
        with patch.dict(os.environ, {}, clear=True), patch('backend.app.core.config.load_dotenv'):
            settings = Settings.from_env()
        self.assertEqual(settings.llm_base_url, 'http://127.0.0.1:11434/v1')
        self.assertEqual(settings.llm_api_key, 'local')
        self.assertEqual(settings.llm_model, '')

    def test_generic_environment_overrides_are_applied(self):
        values = {'LLM_BASE_URL': 'http://127.0.0.1:8080/custom/v1/',
                  'LLM_API_KEY': 'test-placeholder', 'LLM_MODEL': '  custom-chat  '}
        with patch.dict(os.environ, values, clear=True), patch('backend.app.core.config.load_dotenv'):
            settings = Settings.from_env()
        self.assertEqual(settings.llm_base_url, values['LLM_BASE_URL'].rstrip('/'))
        self.assertEqual(settings.llm_api_key, 'test-placeholder')
        self.assertEqual(settings.llm_model, 'custom-chat')


class CompatibleProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_catalog_uses_configured_endpoint_and_generic_health(self):
        requests = []

        def catalog(request):
            requests.append(request)
            return httpx.Response(200, json={'object': 'list', 'data': [
                {'id': 'llama3.2:latest', 'object': 'model', 'owned_by': 'library'},
            ]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(catalog)) as client:
            service = ModelService(Settings('http://127.0.0.1:11434/v1', 'local', 'llama3.2:latest'), client)
            self.assertEqual(await service.resolve(''), 'llama3.2:latest')
            health = await service.health()
        self.assertTrue(health.llm_online)
        self.assertEqual(health.llm_url, 'http://127.0.0.1:11434/v1')
        self.assertEqual(health.default_model, 'llama3.2:latest')
        self.assertEqual(str(requests[0].url), 'http://127.0.0.1:11434/v1/models')
        self.assertEqual(requests[0].headers['Authorization'], 'Bearer local')

    async def test_custom_compatible_provider_uses_its_url_and_credential(self):
        def catalog(request):
            self.assertEqual(str(request.url), 'https://models.example.test/custom/v1/models')
            self.assertEqual(request.headers['Authorization'], 'Bearer test-placeholder')
            return httpx.Response(200, json={'data': [{'id': 'custom-chat'}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(catalog)) as client:
            service = ModelService(Settings('https://models.example.test/custom/v1', 'test-placeholder', 'custom-chat'), client)
            self.assertEqual(await service.resolve(''), 'custom-chat')
