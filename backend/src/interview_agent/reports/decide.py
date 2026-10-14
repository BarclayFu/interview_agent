from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DecideResult(BaseModel):
    score: int = Field(ge=0, le=10)
    rationale: str
    evidence: str = ""
    next_action: Literal["followup", "next_question", "switch_project", "closing"]
    reply: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def _round_score(cls, v: object) -> object:
        """模型偶尔返回小数分（实测 2.5）：取整而非报错。"""
        return round(v) if isinstance(v, float) else v
