"""round_project 节点（async）。模式与 demo/nodes.py 一致：
读 State → 计算/调 LLM → 返回局部更新；interrupt() 前无副作用（resume 会重跑节点）。"""

import uuid as _uuid
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.types import interrupt
from sqlalchemy import insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import Message, Report, Round, Session
from interview_agent.engine.guards import must_close, must_stop_followup
from interview_agent.engine.prompts import (
    DECIDE_INSTRUCTION,
    HINT_INSTRUCTION,
    INTERVIEWER_SYSTEM,
    OPENING_INSTRUCTION,
)
from interview_agent.engine.state import ProjectRoundState
from interview_agent.llm.provider import Message as LlmMessage
from interview_agent.llm.provider import get_provider
from interview_agent.reports.decide import DecideResult
from interview_agent.worker.enqueue import enqueue_generate_report


def _emit(writer: Any, event: str, data: dict[str, Any]) -> None:
    writer({"event": event, "data": data})


def _system(state: ProjectRoundState) -> str:
    return INTERVIEWER_SYSTEM.format(
        resume_summary=state["resume_summary"],
        projects=state["projects"],
        question_count=state.get("question_count", 0),
        max_questions=state["max_questions"],
        followup_depth=state.get("followup_depth", 0),
        asked="；".join(state.get("asked_questions", [])) or "无",
    )


def _history(state: ProjectRoundState) -> list[LlmMessage]:
    """把 transcript 转成 chat messages（控制长度：近 12 条）。"""
    msgs: list[LlmMessage] = []
    for m in state.get("transcript", [])[-12:]:
        role = "assistant" if m.type == "ai" else "user"
        msgs.append({"role": role, "content": str(m.content)})
    return msgs


async def ask(state: ProjectRoundState) -> dict[str, Any]:
    """出题/追问：流式输出面试官的下一句话。

    opening（首次进入、transcript 为空）走 OPENING_INSTRUCTION；
    其余情况由 decide 节点把「要说的话」放进 pending_question_instruction。
    """
    provider = get_provider()
    writer = get_stream_writer()
    is_opening = not state.get("transcript")

    instruction = (
        OPENING_INSTRUCTION if is_opening else state.get("pending_question_instruction", "")
    )
    _emit(writer, "node_start", {"node": "ask", "message": "面试官正在出题…"})
    pieces: list[str] = []
    async for tok in provider.stream(
        [
            {"role": "system", "content": _system(state)},
            *_history(state),
            {"role": "user", "content": instruction},
        ],
        node="ask",
        session_id=state["session_id"],
    ):
        pieces.append(tok)
        _emit(writer, "token", {"text": tok})
    question = "".join(pieces)

    is_followup = not is_opening and state.get("next_action") == "followup"
    _emit(writer, "question", {"question": question, "is_followup": is_followup})
    update: dict[str, Any] = {
        "current_question": question,
        "transcript": [AIMessage(content=question)],
    }
    if is_opening:
        update["phase"] = "deep_dive"
        update["question_count"] = 1
        update["followup_depth"] = 0
        update["asked_questions"] = [question]
    elif is_followup:
        update["followup_depth"] = state.get("followup_depth", 0) + 1
    else:
        update["question_count"] = state.get("question_count", 0) + 1
        update["followup_depth"] = 0
        update["asked_questions"] = [question]
    return update


def await_answer(state: ProjectRoundState) -> dict[str, Any]:
    """interrupt 暂停点：等候选人 answer/hint/end（spec §6.2）。"""
    resume = interrupt(
        {
            "event": "await_answer",
            "question": state.get("current_question", ""),
            "question_count": state.get("question_count", 0),
        }
    )
    value = resume or {}
    return {
        "pending_action": value.get("action", "answer"),
        "last_answer": value.get("text", ""),
    }


def route_after_answer(state: ProjectRoundState) -> str:
    action = state.get("pending_action", "answer")
    if action == "hint":
        return "give_hint"
    if action == "end":
        return "finalize"
    return "decide"


async def give_hint(state: ProjectRoundState) -> dict[str, Any]:
    provider = get_provider()
    writer = get_stream_writer()
    _emit(writer, "node_start", {"node": "give_hint", "message": "面试官正在给提示…"})
    pieces: list[str] = []
    async for tok in provider.stream(
        [
            {"role": "system", "content": _system(state)},
            {
                "role": "user",
                "content": f"{HINT_INSTRUCTION}\n当前问题：{state.get('current_question', '')}",
            },
        ],
        node="give_hint",
        session_id=state["session_id"],
    ):
        pieces.append(tok)
        _emit(writer, "token", {"text": tok})
    hint = "".join(pieces)
    _emit(writer, "hint", {"text": hint})
    return {
        "hint_count": state.get("hint_count", 0) + 1,
        "transcript": [AIMessage(content=f"（提示）{hint}")],
    }


async def decide(state: ProjectRoundState) -> dict[str, Any]:
    """评估回答 → 结构化判定下一步（守卫规则可覆盖 LLM 的 next_action）。"""
    provider = get_provider()
    writer = get_stream_writer()
    _emit(writer, "node_start", {"node": "decide", "message": "面试官正在评价你的回答…"})
    result: DecideResult = await provider.structured(
        DecideResult,
        [
            {"role": "system", "content": _system(state)},
            *_history(state),
            {
                "role": "user",
                "content": (
                    f"{DECIDE_INSTRUCTION}\n当前问题：{state.get('current_question', '')}"
                    f"\n候选人回答：{state['last_answer']}"
                ),
            },
        ],
        node="decide",
        session_id=state["session_id"],
    )

    action = result.next_action
    # 守卫覆盖（spec §5.4：规则优先于模型判断）
    if action == "followup" and must_stop_followup(state.get("followup_depth", 0)):
        action = "next_question"
    if must_close(state.get("question_count", 0), state["max_questions"]):
        action = "closing"
    if action == "switch_project" and state.get("current_project_idx", 0) + 1 >= len(
        state["projects"]
    ):
        action = "closing"

    _emit(writer, "feedback", {"score": result.score, "rationale": result.rationale})
    update: dict[str, Any] = {
        "scores": [
            {
                "question": state.get("current_question", ""),
                "score": result.score,
                "rationale": result.rationale,
                "evidence": result.evidence,
            }
        ],
        "next_action": action,
        "transcript": [HumanMessage(content=state["last_answer"])],
    }
    if action == "followup":
        update["pending_question_instruction"] = result.reply
    elif action == "next_question":
        update["pending_question_instruction"] = "请就当前项目提出下一个问题（换维度深挖）。"
    elif action == "switch_project":
        update["current_project_idx"] = state.get("current_project_idx", 0) + 1
        update["pending_question_instruction"] = (
            "请切换到下一个项目，用一两句话过渡并提出第一个宽问题。"
        )
    return update


def route_after_decide(state: ProjectRoundState) -> str:
    return "finalize" if state.get("next_action") == "closing" else "ask"


async def finalize(state: ProjectRoundState) -> dict[str, Any]:
    """收尾：写 session/round 终态、transcript 落 messages 表（单次写，避免双写漂移）、
    建 reports 占位行并入队报告任务（幂等：ON CONFLICT DO NOTHING + _job_id 去重）。"""
    writer = get_stream_writer()
    sid = _uuid.UUID(state["session_id"])
    _emit(writer, "node_start", {"node": "finalize", "message": "面试结束，评估报告生成中…"})

    now = datetime.now(UTC)
    async with get_session_factory()() as s:
        round_id = (
            await s.execute(
                update(Round)
                .where(Round.session_id == sid)
                .values(status="finished", scores={"items": state.get("scores", [])}, ended_at=now)
                .returning(Round.id)
            )
        ).scalar_one()
        await s.execute(
            update(Session).where(Session.id == sid).values(status="finished", finished_at=now)
        )
        for i, m in enumerate(state.get("transcript", [])):
            is_interviewer = m.type == "ai"
            role = "interviewer" if is_interviewer else "candidate"
            if is_interviewer:
                kind = "hint" if str(m.content).startswith("（提示）") else "question"
            else:
                kind = "answer"
            await s.execute(
                insert(Message).values(
                    session_id=sid,
                    round_id=round_id,
                    seq=i,
                    role=role,
                    kind=kind,
                    content=str(m.content),
                )
            )
        await s.execute(
            pg_insert(Report)
            .values(session_id=sid, status="pending")
            .on_conflict_do_nothing(constraint="reports_session_id_key")
        )
        await s.commit()

    await enqueue_generate_report(state["session_id"], attempt=1)
    _emit(writer, "finished", {"session_id": state["session_id"]})
    return {"phase": "closing"}
