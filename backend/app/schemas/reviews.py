"""Explicit operator choices at the durable human-review checkpoint."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    action: Literal['finalize', 'rerun']
    feedback: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def rerun_needs_guidance(self) -> 'ReviewInput':
        if self.action == 'rerun' and not self.feedback:
            raise ValueError('Add suggestions before rerunning the agents.')
        return self
