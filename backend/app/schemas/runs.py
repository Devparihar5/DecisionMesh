"""Run input and terminal event contracts."""
from pydantic import BaseModel, ConfigDict, Field


class RunInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scenario: str = Field(min_length=8, max_length=6000)
    model: str = Field(default="", max_length=200)
    selected_agents: list[str] = Field(min_length=1, max_length=32)
    require_approval: bool = True
