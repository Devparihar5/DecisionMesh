"""Thin API for event ingestion, twins, negotiations, and simulated actions."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.app.schemas.enterprise import (
    ActionApproval, ActionReceipt, ApprovalInput, DecisionCase, EnterpriseEvent,
    EnterpriseSnapshot, EntityInput, EventReceipt, ExecutionInput, Job, NegotiationInput, TwinState,
)
from backend.app.services.enterprise import EnterpriseService
from backend.app.services.research_jobs import ResearchJobs

router = APIRouter(prefix='/api/enterprise', tags=['enterprise'])


def enterprise(request: Request) -> EnterpriseService:
    return request.app.state.enterprise


def research_jobs(request: Request) -> ResearchJobs:
    return request.app.state.research_jobs


Service = Annotated[EnterpriseService, Depends(enterprise)]
Jobs = Annotated[ResearchJobs, Depends(research_jobs)]


@router.get('/entities', response_model=list[TwinState])
def entities(service: Service):
    return service.repository.entities()


@router.post('/entities', status_code=201, response_model=TwinState)
def create_entity(body: EntityInput, service: Service):
    return service.repository.create_entity(body)


@router.get('/entities/{entity_id}', response_model=EnterpriseSnapshot)
def snapshot(entity_id: str, service: Service):
    return service.snapshot(entity_id)


@router.post('/events', response_model=EventReceipt)
def ingest_event(body: EnterpriseEvent, service: Service):
    return service.ingest(body)


@router.get('/cases/{case_id}', response_model=DecisionCase)
def case(case_id: str, service: Service):
    return service.repository.case(case_id)


@router.post('/cases/{case_id}/negotiate', status_code=202, response_model=Job)
async def negotiate(case_id: str, body: NegotiationInput, jobs: Jobs):
    return await jobs.negotiate(case_id, body.model, body.agents)


@router.post('/cases/{case_id}/approvals', status_code=201, response_model=ActionApproval)
def approve(case_id: str, body: ApprovalInput, service: Service):
    return service.repository.approve(case_id, body)


@router.post('/cases/{case_id}/execute', response_model=ActionReceipt)
def execute(case_id: str, body: ExecutionInput, service: Service):
    return service.repository.execute(case_id, body, service.transition)
