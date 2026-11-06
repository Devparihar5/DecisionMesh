"""Agno-specific construction and execution of a specialist role."""
import asyncio
import json

try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
except ImportError:
    Agent = None
    OpenAIChat = None

from backend.app.core.config import Settings
from backend.app.schemas.agents import AgentDefinition


def agno_available() -> bool:
    return Agent is not None and OpenAIChat is not None


class AgnoRunner:
    def __init__(self, settings: Settings):
        self.settings = settings
        # Bound model calls to suit local servers with limited generation capacity.
        self._slots = asyncio.Semaphore(1)

    async def run(self, config: AgentDefinition, model_id: str, prompt: str) -> str:
        return await self._execute(config, model_id, prompt, structured=False)

    async def propose(self, config: AgentDefinition, model_id: str, prompt: str) -> str:
        return await self._execute(config, model_id, prompt, structured=True)

    async def _execute(self, config: AgentDefinition, model_id: str, prompt: str, structured: bool) -> str:
        if not agno_available():
            raise RuntimeError("Agno is missing. Run poetry install.")

        async with self._slots:
            model = OpenAIChat(
                id=model_id,
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key,
                timeout=self.settings.agent_timeout_seconds,
                max_retries=0,
                # Keep instruction roles compatible with servers that do not
                # support OpenAI's newer developer role.
                role_map={**OpenAIChat.default_role_map, "system": "system", "developer": "system"},
                # Request one JSON completion explicitly; browser workflow
                # events use an independent SSE stream.
                request_params={"stream": False},
            )
            agent = Agent(
                name=config.name,
                role=config.role,
                model=model,
                instructions=[
                    config.instructions,
                    ("Return ONLY one valid JSON object with exactly three keys: action, reason, evidence. "
                     "action must be hold, overtime, backup, or defer. reason must be a brief plain sentence of at most 40 words. "
                     "evidence must be an array of the supplied short references such as E1 or E2. "
                     "Do not invent references, add keys, use code fences, or add text outside JSON. Do not execute actions."
                     if structured else
                     "Return a concise assessment (at most 180 words). Use only supplied facts; label assumptions. Do not claim to execute actions."),
                ],
                markdown=not structured,
                telemetry=False,
            )
            result = await asyncio.wait_for(
                agent.arun(prompt), timeout=self.settings.agent_timeout_seconds
            )
            content = result.content
            if content is None or content == "":
                raise RuntimeError("The local model returned an empty response.")
            return content if isinstance(content, str) else json.dumps(content, default=str)
