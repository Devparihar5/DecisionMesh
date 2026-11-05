"""Async OpenAI-compatible model discovery; all provider HTTP lives here."""
import httpx

from backend.app.agents.factory import agno_available
from backend.app.core.config import Settings
from backend.app.core.errors import ApplicationError
from backend.app.schemas.health import HealthStatus


class ModelService:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client

    async def models(self) -> list[str]:
        try:
            response = await self.client.get(
                f"{self.settings.llm_base_url}/models",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()["data"]
            return list(dict.fromkeys(item["id"] for item in data if isinstance(item.get("id"), str)))
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ApplicationError(
                "Cannot discover models. Start your model server and check LLM_BASE_URL and LLM_API_KEY.", 503
            ) from exc

    async def resolve(self, requested: str) -> str:
        models = await self.models()
        if not models:
            raise ApplicationError("The model server returned no available models. Download or enable a model, then refresh.", 503)
        chosen = requested.strip() or self.settings.llm_model or models[0]
        if chosen not in models:
            raise ApplicationError("Selected model is unavailable. Refresh the model connection.", 400)
        return chosen

    async def health(self) -> HealthStatus:
        status = HealthStatus(
            agno_installed=agno_available(),
            llm_url=self.settings.llm_base_url,
            default_model=self.settings.llm_model,
        )
        try:
            status.models = await self.models()
            status.llm_online = True
        except ApplicationError as exc:
            status.error = exc.detail
        return status
