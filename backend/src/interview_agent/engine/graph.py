"""建图 + 进程级单例（checkpointer 决定持久化语义，见 checkpointer.py）。"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from interview_agent.engine.nodes import (
    ask,
    await_answer,
    decide,
    finalize,
    give_hint,
    route_after_answer,
    route_after_decide,
)
from interview_agent.engine.state import ProjectRoundState


def build_project_graph(checkpointer: Any) -> Any:
    b = StateGraph(ProjectRoundState)
    b.add_node("ask", ask)
    b.add_node("await_answer", await_answer)
    b.add_node("give_hint", give_hint)
    b.add_node("decide", decide)
    b.add_node("finalize", finalize)
    b.add_edge(START, "ask")
    b.add_edge("ask", "await_answer")
    b.add_conditional_edges(
        "await_answer",
        route_after_answer,
        {"give_hint": "give_hint", "decide": "decide", "finalize": "finalize"},
    )
    b.add_edge("give_hint", "await_answer")
    b.add_conditional_edges("decide", route_after_decide, {"ask": "ask", "finalize": "finalize"})
    b.add_edge("finalize", END)
    # 已知坑回归（父设计 §3.2）：子图 compile 必须显式传 checkpointer。
    # 本函数强制要求调用方传入 —— 禁止默认参数偷换成 None。
    return b.compile(checkpointer=checkpointer)


_graph: Any = None
_graph_saver: Any = None


def get_graph() -> Any:
    """进程级单例；checkpointer 被重建（测试/重启）时自动换绑新图。"""
    global _graph, _graph_saver
    from interview_agent.engine.checkpointer import get_checkpointer

    saver = get_checkpointer()
    if _graph is None or _graph_saver is not saver:
        _graph = build_project_graph(saver)
        _graph_saver = saver
    return _graph


def reset_graph() -> None:
    """测试用：清空单例（配合 checkpointer 重建）。"""
    global _graph, _graph_saver
    _graph = None
    _graph_saver = None
