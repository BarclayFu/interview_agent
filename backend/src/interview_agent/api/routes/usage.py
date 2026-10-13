"""用量与运行态观测（开发者面板数据源）。

- /usage：cost_ledger 聚合（逐节点 + 总计 + cache 命中率 + 最近调用明细）
- /debug：LangGraph 图状态快照（状态机内部：phase/题数/追问深度/项目指针/守卫结果）
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from interview_agent.api.routes.sessions import _graph_config
from interview_agent.core.db import get_db
from interview_agent.core.models import CostLedger, Session
from interview_agent.engine.graph import get_graph

router = APIRouter()


@router.get("/sessions/{session_id}/usage")
async def session_usage(
    session_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(
                CostLedger.node,
                CostLedger.model,
                func.count().label("calls"),
                func.sum(CostLedger.prompt_tokens).label("prompt_tokens"),
                func.sum(CostLedger.completion_tokens).label("completion_tokens"),
                func.sum(CostLedger.cache_hit_tokens).label("cache_hit_tokens"),
                func.sum(CostLedger.cache_miss_tokens).label("cache_miss_tokens"),
                func.sum(CostLedger.cost_cny).label("cost_cny"),
                func.avg(CostLedger.latency_ms).label("latency_ms_avg"),
            )
            .where(CostLedger.session_id == session_id)
            .group_by(CostLedger.node, CostLedger.model)
            .order_by(func.sum(CostLedger.cost_cny).desc())
        )
    ).all()

    by_node = [
        {
            "node": r.node,
            "model": r.model,
            "calls": int(r.calls),
            "prompt_tokens": int(r.prompt_tokens or 0),
            "completion_tokens": int(r.completion_tokens or 0),
            "cache_hit_tokens": int(r.cache_hit_tokens or 0),
            "cache_miss_tokens": int(r.cache_miss_tokens or 0),
            "cost_cny": round(float(r.cost_cny or 0), 6),
            "latency_ms_avg": int(r.latency_ms_avg or 0),
        }
        for r in rows
    ]
    totals: dict[str, Any] = {
        key: sum(item[key] for item in by_node)
        for key in (
            "calls",
            "prompt_tokens",
            "completion_tokens",
            "cache_hit_tokens",
            "cache_miss_tokens",
        )
    }
    totals["cost_cny"] = round(sum(item["cost_cny"] for item in by_node), 6)
    cache_total = totals["cache_hit_tokens"] + totals["cache_miss_tokens"]
    totals["cache_hit_rate"] = (
        round(totals["cache_hit_tokens"] / cache_total, 3) if cache_total else 0.0
    )

    calls = (
        (
            await db.execute(
                select(CostLedger)
                .where(CostLedger.session_id == session_id)
                .order_by(desc(CostLedger.id))
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return {
        "totals": totals,
        "by_node": by_node,
        "calls": [
            {
                "id": c.id,
                "node": c.node,
                "model": c.model,
                "prompt_tokens": c.prompt_tokens,
                "completion_tokens": c.completion_tokens,
                "cache_hit_tokens": c.cache_hit_tokens,
                "cost_cny": float(c.cost_cny),
                "latency_ms": c.latency_ms,
                "created_at": c.created_at.isoformat(),
            }
            for c in calls
        ],
    }


@router.get("/sessions/{session_id}/debug")
async def session_debug(
    session_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    sess = await db.get(Session, session_id)
    if sess is None:
        raise HTTPException(404, "session not found")
    graph = get_graph()
    snap = await graph.aget_state(_graph_config(session_id))
    values: dict[str, Any] = snap.values or {}
    projects = values.get("projects") or []
    return {
        "state": {
            "phase": values.get("phase"),
            "question_count": values.get("question_count", 0),
            "max_questions": values.get("max_questions"),
            "followup_depth": values.get("followup_depth", 0),
            "current_project_idx": values.get("current_project_idx", 0),
            "project_count": len(projects),
            "project_names": [p.get("name") for p in projects],
            "hint_count": values.get("hint_count", 0),
            "next_action": values.get("next_action"),
            "pending_action": values.get("pending_action"),
            "asked_count": len(values.get("asked_questions") or []),
            "current_question": values.get("current_question"),
        },
        "next": [str(n) for n in (snap.next or [])],
        "paused_tasks": [t.name for t in (snap.tasks or [])],
    }
