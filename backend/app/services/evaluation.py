"""Controlled local model benchmarks with explicit simulation-based ground truth."""
import json
import math
import statistics
import time
from pathlib import Path

from backend.app.core.errors import ApplicationError
from backend.app.orchestration.events import timestamp
from backend.app.orchestration.negotiation import apply_resolution, proposal_prompt
from backend.app.orchestration.twin import oracle
from backend.app.schemas.agents import AgentDefinition
from backend.app.schemas.enterprise import BenchmarkInput, Inventory, Job, TwinState
from backend.app.services.enterprise import build_case
from backend.app.services.research_jobs import ResearchJobs
from backend.app.storage.enterprise import fingerprint

DATASET = json.loads(Path(__file__).with_name('benchmark_cases.json').read_text())
CENTRAL_AGENT = AgentDefinition(id='centralized_baseline', name='Centralized baseline', role='Enterprise decision analyst',
    instructions='Consider operations, cost, risk, and policy together. Choose one feasible action from the supplied simulations. Return only the requested JSON.')


def summarize(trials: list[dict]) -> dict:
    result = {}
    for architecture in ('centralized', 'orchestrated'):
        samples = [trial for trial in trials if trial['architecture'] == architecture]
        durations = sorted(sample['machine_time_ms'] for sample in samples)
        qualities = [sample['quality_score'] for sample in samples]
        count = len(samples)
        if not count:
            continue
        mean = statistics.mean(qualities)
        interval = 1.96 * statistics.stdev(qualities) / math.sqrt(count) if count > 1 else None
        result[architecture] = {'samples': count, 'quality_score': round(mean, 2),
            'quality_ci95_approx': [round(max(0, mean - interval), 2), round(min(100, mean + interval), 2)] if interval is not None else None,
            'optimal_decision_rate': round(100 * sum(sample['optimal'] for sample in samples) / count, 2),
            'policy_compliance_rate': round(100 * sum(sample['policy_compliant'] for sample in samples) / count, 2),
            'mean_machine_time_ms': round(statistics.mean(durations)),
            'p95_machine_time_ms': durations[math.ceil(.95 * count) - 1],
            'model_calls': sum(sample['model_calls'] for sample in samples),
            'conflict_rate': round(100 * sum(sample['conflicts'] > 0 for sample in samples) / count, 2) if architecture == 'orchestrated' else None,
            'review_required_rate': round(100 * sum(sample['requires_review'] for sample in samples) / count, 2),
            'provider_or_format_failure_rate': round(100 * sum(not sample['valid_response'] for sample in samples) / count, 2),
            'evidence_coverage_rate': round(statistics.mean(sample['evidence_coverage'] for sample in samples), 2),
            'recovery_time_ms': None, 'human_trust_score': None}
    return result


class EvaluationService:
    def __init__(self, jobs: ResearchJobs):
        self.jobs = jobs

    async def start(self, value: BenchmarkInput) -> Job:
        model = await self.jobs.resolve_model(value.model)
        available = [agent for agent in self.jobs.registry.list_agents() if not agent.core]
        preferred = ['operations', 'finance', 'risk', 'compliance']
        agents = sorted(available, key=lambda agent: preferred.index(agent.id) if agent.id in preferred else len(preferred))[:4]
        if len(agents) < 2:
            raise ApplicationError('Benchmark needs at least two specialist definitions.')
        if any(job.status == 'running' for job in self.jobs.repository.jobs('benchmark')):
            raise ApplicationError('A benchmark is already running. Wait or cancel it.', 409)
        config = {'model': model, 'repetitions': value.repetitions, 'dataset_version': 'inventory-six-v1',
            'dataset': DATASET, 'dataset_hash': fingerprint({'cases': DATASET}), 'rule_version': 'inventory-v1',
            'architectures': ['centralized', 'orchestrated'], 'agents': [agent.model_dump() for agent in agents],
            'central_agent': CENTRAL_AGENT.model_dump(), 'max_rounds': 2, 'max_format_repairs': 1,
            'prompt_template_version': 'inventory-proposal-v2',
            'quality_rubric': '100 × clamp(chosen utility / oracle utility, 0, 1), zero for hard policy violations or invalid output',
            'timing': 'Wall-clock machine phase including model queueing; excludes human review time',
            'limitations': ['Synthetic inventory tasks, not empirical enterprise decision quality',
                'Different call counts are reported; compute budgets are not equal',
                'The orchestrated variant adds deterministic policy/arbitration; gains cannot be attributed solely to agent reasoning',
                'Model-server seed, temperature defaults, hardware, and caching are uncontrolled',
                'Evidence coverage checks reference IDs, not semantic truth of explanations',
                'Review required is a policy indicator, not measured human intervention',
                'Recovery time and human trust are not measured',
                'Approximate confidence intervals pool repeated synthetic tasks; samples are not independent field observations']}
        job = self.jobs.repository.create_job('benchmark', 'inventory-six-v1', config)
        self.jobs.start(job, lambda: self._run(job, agents, model, value.repetitions))
        return job

    async def _run(self, job: Job, agents: list[AgentDefinition], model: str, repetitions: int) -> dict:
        trials = []
        for repetition in range(repetitions):
            for index, dataset_case in enumerate(DATASET):
                state = TwinState(id=dataset_case['id'], name=dataset_case['name'], state=Inventory(**dataset_case['state']),
                                  updated_at=timestamp())
                case = build_case(state, [f'benchmark:{dataset_case["id"]}'], 'benchmark')
                expected = oracle(case.candidates)
                order = ['centralized', 'orchestrated'] if (index + repetition) % 2 == 0 else ['orchestrated', 'centralized']
                for architecture in order:
                    self.jobs.repository.update_job(job.id, progress={'stage': 'trial_start', 'scenario': dataset_case['id'],
                        'architecture': architecture, 'repetition': repetition + 1})
                    started = time.perf_counter()
                    chosen = None
                    raw = None
                    errors = []
                    proposal_count, calls, conflicts = 0, 0, 0
                    requires_review = True
                    trace = []
                    def progress(event: dict) -> None:
                        nonlocal calls
                        if event['stage'] == 'agent_start':
                            calls += 1
                        self.jobs.repository.update_job(job.id, progress={**event, 'architecture': architecture,
                            'scenario': dataset_case['id'], 'repetition': repetition + 1})
                    if architecture == 'centralized':
                        proposal, error = await self.jobs.collect_proposal(CENTRAL_AGENT, case, model, proposal_prompt(case), 1, progress)
                        if proposal:
                            chosen = next(item for item in case.candidates if item.action == proposal.action)
                            proposal_count = 1
                            requires_review = chosen.requires_review or bool(chosen.violations)
                            trace = [proposal.model_dump()]
                        if error:
                            errors.append(error)
                    else:
                        rounds = await self.jobs.rounds(case, agents, model, progress)
                        resolved = apply_resolution(case, rounds)
                        chosen = next(item for item in case.candidates if item.action == resolved.selected_action)
                        errors = [error for turn in rounds for error in turn.errors]
                        proposal_count = sum(len(turn.proposals) for turn in rounds)
                        conflicts = len(rounds[0].conflicts)
                        requires_review = resolved.requires_review
                        trace = [turn.model_dump() for turn in rounds]
                    compliant = chosen is not None and not chosen.violations
                    valid = proposal_count > 0
                    quality = (100.0 if abs(chosen.utility - expected.utility) < .00001 else
                        round(100 * min(1, max(0, chosen.utility) / max(expected.utility, .000001)), 2)) if compliant and valid else 0.0
                    trial = {'scenario': dataset_case['id'], 'repetition': repetition + 1, 'architecture': architecture,
                        'action': chosen.action if chosen else None, 'oracle_action': expected.action,
                        'oracle_utility': expected.utility, 'outcome': chosen.model_dump() if chosen else None,
                        'quality_score': quality, 'optimal': bool(compliant and valid and abs(chosen.utility - expected.utility) < .00001),
                        'policy_compliant': bool(compliant and valid), 'valid_response': valid and not errors,
                        'machine_time_ms': round((time.perf_counter() - started) * 1000), 'model_calls': calls,
                        'conflicts': conflicts, 'requires_review': requires_review,
                        'evidence_coverage': round(100 * proposal_count / calls, 2) if calls else 0,
                        'errors': errors, 'trace': trace, 'raw_response': raw}
                    trials.append(trial)
                    self.jobs.repository.update_job(job.id, progress={'stage': 'trial_complete', 'trial': trial})
        return {'summary': summarize(trials), 'trials': trials, 'completed_trials': len(trials)}
