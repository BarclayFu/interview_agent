"""评估报告 schema v1。schema_version=1；M2 加「对标岗位」段时升 2 并保持向后兼容。"""

from pydantic import BaseModel, Field, field_validator


class DimensionScore(BaseModel):
    name: str  # 项目复杂度/个人贡献清晰度/技术深度/取舍与权衡意识/复盘反思/量化能力
    score: int = Field(ge=1, le=5)
    comment: str

    @field_validator("score", mode="before")
    @classmethod
    def _round_score(cls, v: object) -> object:
        return round(v) if isinstance(v, float) else v


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
    highlights: list[EvidenceItem]
    issues: list[EvidenceItem]
    improvements: list[str]
    next_focus: str

    @field_validator("total_score", mode="before")
    @classmethod
    def _round_total(cls, v: object) -> object:
        """模型偶尔返回小数总分（实测 2.5）：取整而非报错。"""
        return round(v) if isinstance(v, float) else v

    @field_validator("highlights", "issues", "improvements", mode="before")
    @classmethod
    def _cap_three(cls, v: object) -> object:
        """模型常超出条数限制（实测返回 5 条 issues）：超出即截断，不让整份报告失败。"""
        if isinstance(v, list):
            return v[:3]
        return v


DIMENSIONS = ["项目复杂度", "个人贡献清晰度", "技术深度", "取舍与权衡意识", "复盘反思", "量化能力"]
