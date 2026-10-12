"""简历抽取的 Pydantic schema。"""

from pydantic import BaseModel


class ExtractedProject(BaseModel):
    name: str
    period: str = ""
    role: str = ""
    tech: list[str] = []
    claims: list[str] = []


class ExtractedProjects(BaseModel):
    projects: list[ExtractedProject]
