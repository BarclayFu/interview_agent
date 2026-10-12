"""round_project 子图状态（spec §5.4）。"""

import operator
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

NextAction = Literal["followup", "next_question", "switch_project", "closing"]
PendingAction = Literal["answer", "hint", "end"]
Phase = Literal["opening", "deep_dive", "closing"]


class ProjectRoundState(TypedDict, total=False):
    # 标识与配置（进入图时注入，只读）
    session_id: str
    resume_summary: str  # 简历摘要（常驻上下文）
    projects: list[dict[str, Any]]  # 结构化项目清单（resumes.parsed_projects）
    max_questions: int  # 默认 8（spec §5.4 守卫）

    # 进度（覆盖式）
    phase: Phase
    current_project_idx: int
    current_question: str
    question_count: int  # 项目问题数（追问不计）
    followup_depth: int  # 当前问题的追问层数

    # 累加（reducer）
    asked_questions: Annotated[list[str], operator.add]
    scores: Annotated[list[dict[str, Any]], operator.add]
    transcript: Annotated[list[AnyMessage], add_messages]

    # 控制流（覆盖式）
    pending_action: PendingAction
    last_answer: str
    hint_count: int
    next_action: NextAction
    pending_question_instruction: str  # decide 产出、ask 消费的「下一句话指令」

    # 终局
    closing_summary: str
