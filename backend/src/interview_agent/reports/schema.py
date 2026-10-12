"""评估报告 schema v1。schema_version=1；M2 加「对标岗位」段时升 2 并保持向后兼容。"""

from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    name: str  # 项目复杂度/个人贡献清晰度/技术深度/取舍与权衡意识/复盘反思/量化能力
    score: int = Field(ge=1, le=5)
    comment: str


class PerQuestion(BaseModel):
    question: str
    answer_summary: str
    comment: str
    reference_points: list[str] = []


class EvidenceItem(BaseModel):
    text: str
    evidence: str  # 必须是候选人原话片段（门禁校验可定位）


class ReportV1(BaseModel):
    schema_version: int = 1
    headline: str
    total_score: int = Field(ge=1, le=5)
    dimensions: list[DimensionScore]
    per_question: list[PerQuestion]
    highlights: list[EvidenceItem] = Field(max_length=3)
    issues: list[EvidenceItem] = Field(max_length=3)
    improvements: list[str] = Field(max_length=3)  # ≤3 条，按优先级
    next_focus: str


DIMENSIONS = ["项目复杂度", "个人贡献清晰度", "技术深度", "取舍与权衡意识", "复盘反思", "量化能力"]
