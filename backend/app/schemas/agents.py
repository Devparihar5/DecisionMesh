"""Agent catalog contracts."""
from pydantic import BaseModel, ConfigDict, Field


class AgentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=48)
    role: str = Field(min_length=2, max_length=80)
    instructions: str = Field(min_length=8, max_length=1200)
    icon: str = Field(default="✳", min_length=1, max_length=4)
    color: str = Field(default="#78a9ff", pattern=r"^#[0-9a-fA-F]{6}$")


class AgentDefinition(AgentInput):
    id: str
    core: bool = False
