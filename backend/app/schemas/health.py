"""Local model connectivity contract."""
from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    agno_installed: bool
    llm_url: str
    llm_online: bool = False
    models: list[str] = Field(default_factory=list)
    default_model: str = ""
    error: str | None = None
