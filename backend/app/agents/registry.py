"""Agent catalog and validation, backed by local persistence in the app."""
import json
import re
from pathlib import Path
from uuid import uuid4

from backend.app.core.errors import ApplicationError
from backend.app.schemas.agents import AgentDefinition, AgentInput
from backend.app.storage.agents import AgentRepository


class AgentRegistry:
    def __init__(self, repository: AgentRepository | None = None) -> None:
        source = Path(__file__).with_name("defaults.json")
        self._agents = {
            data["id"]: AgentDefinition.model_validate(data)
            for data in json.loads(source.read_text())
        }
        self.repository = repository
        if repository:
            repository.seed(list(self._agents.values()))
            self._agents = {agent.id: agent for agent in repository.list_agents()}

    def list_agents(self) -> list[AgentDefinition]:
        return [agent.model_copy(deep=True) for agent in self._agents.values()]

    def get(self, agent_id: str) -> AgentDefinition:
        if agent_id not in self._agents:
            raise ApplicationError("Agent not found.", 404)
        return self._agents[agent_id].model_copy(deep=True)

    def create(self, body: AgentInput) -> AgentDefinition:
        if len(self._agents) >= 32:
            raise ApplicationError("The local workspace supports up to 32 agents.")
        if any(a.name.casefold() == body.name.casefold() for a in self._agents.values()):
            raise ApplicationError("An agent with this name already exists.", 409)
        slug = re.sub(r"[^a-z0-9]+", "_", body.name.lower()).strip("_")[:40]
        # Distinguish a recreated/deleted role from its historical identity.
        agent_id = f"{slug or 'specialist'}_{uuid4().hex[:8]}" if self.repository else slug or f"specialist_{uuid4().hex[:8]}"
        if agent_id in self._agents:
            agent_id = f"{agent_id}_{uuid4().hex[:6]}"
        agent = AgentDefinition(id=agent_id, **body.model_dump())
        if self.repository:
            self.repository.save(agent)
        self._agents[agent.id] = agent
        return agent.model_copy(deep=True)

    def update(self, agent_id: str, body: AgentInput) -> AgentDefinition:
        existing = self.get(agent_id)
        if existing.core:
            raise ApplicationError("Core oversight and synthesis roles cannot be edited.")
        if any(a.id != agent_id and a.name.casefold() == body.name.casefold() for a in self._agents.values()):
            raise ApplicationError("An agent with this name already exists.", 409)
        agent = AgentDefinition(id=agent_id, **body.model_dump())
        if self.repository:
            self.repository.save(agent)
        self._agents[agent_id] = agent
        return agent.model_copy(deep=True)

    def delete(self, agent_id: str) -> None:
        if self.get(agent_id).core:
            raise ApplicationError("Core oversight and synthesis roles cannot be removed.")
        if self.repository:
            self.repository.delete(agent_id)
        del self._agents[agent_id]

    def specialists(self, selected_ids: list[str]) -> list[AgentDefinition]:
        # Reject stale/unknown selections instead of silently changing the team.
        for agent_id in selected_ids:
            self.get(agent_id)
        selected = set(selected_ids)
        specialists = [a for a in self.list_agents() if a.id in selected and not a.core]
        if not specialists:
            raise ApplicationError("Select at least one specialist agent.")
        return specialists
