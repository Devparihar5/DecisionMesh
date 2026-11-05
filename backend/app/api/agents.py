"""Agent catalog HTTP routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from backend.app.agents.registry import AgentRegistry
from backend.app.api.dependencies import registry
from backend.app.schemas.agents import AgentDefinition, AgentInput

router = APIRouter(prefix="/api/agents", tags=["agents"])
Catalog = Annotated[AgentRegistry, Depends(registry)]


@router.get("", response_model=list[AgentDefinition])
async def list_agents(catalog: Catalog):
    return catalog.list_agents()


@router.post("", response_model=AgentDefinition, status_code=201)
async def create_agent(body: AgentInput, catalog: Catalog):
    return catalog.create(body)


@router.put("/{agent_id}", response_model=AgentDefinition)
async def update_agent(agent_id: str, body: AgentInput, catalog: Catalog):
    return catalog.update(agent_id, body)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, catalog: Catalog):
    catalog.delete(agent_id)
    return Response(status_code=204)
