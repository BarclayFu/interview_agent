from typing import Literal

from pydantic import BaseModel, Field


class DecideResult(BaseModel):
    score: int = Field(ge=0, le=10)
    rationale: str
    evidence: str = ""
    next_action: Literal["followup", "next_question", "switch_project", "closing"]
    reply: str = ""
