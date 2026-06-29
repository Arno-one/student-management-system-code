"""Agent 专用 LangGraph 中间件管线。"""
from __future__ import annotations

from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, StateGraph

from agent_system.middleware.commute_input_checker import check as commute_check
from agent_system.middleware.input_guard import check as guard_check
from agent_system.middleware.nearby_input_checker import check as nearby_check
from agent_system.middleware.policy_checker import check as policy_check
from agent_system.middleware.query_rewriter import check as rewrite_check


class MiddlewareState(TypedDict, total=False):
    """LangGraph 节点之间传递的轻量状态。"""
    message: str
    history: list | None
    decision: str
    reason: str | None
    rewritten: str | None
    clarification: str | None
    metadata: dict


def run_agent_middleware(message: str, history: list | None = None) -> dict:
    """执行 guard → rewrite → policy → nearby_check → commute_check。"""
    graph = _build_graph()
    state = graph.invoke({
        "message": message,
        "history": history or [],
        "decision": "pass",
        "reason": None,
        "rewritten": None,
        "clarification": None,
        "metadata": {},
    })
    return {
        "decision": state.get("decision", "pass"),
        "reason": state.get("reason"),
        "rewritten": state.get("rewritten"),
        "clarification": state.get("clarification"),
        "metadata": state.get("metadata") or {},
    }


@lru_cache(maxsize=1)
def _build_graph():
    builder = StateGraph(MiddlewareState)
    builder.add_node("guard", _guard_node)
    builder.add_node("rewrite", _rewrite_node)
    builder.add_node("policy", _policy_node)
    builder.add_node("nearby", _nearby_node)
    builder.add_node("commute", _commute_node)
    builder.set_entry_point("guard")
    builder.add_conditional_edges("guard", _stop_if_not_pass, {"stop": END, "next": "rewrite"})
    builder.add_edge("rewrite", "policy")
    builder.add_conditional_edges("policy", _stop_if_not_pass, {"stop": END, "next": "nearby"})
    builder.add_conditional_edges("nearby", _stop_if_not_pass, {"stop": END, "next": "commute"})
    builder.add_edge("commute", END)
    return builder.compile()


def _guard_node(state: MiddlewareState) -> MiddlewareState:
    result = guard_check(state["message"])
    if result.decision == "reject":
        state["decision"] = "reject"
        state["reason"] = result.reject_reason
    return state


def _rewrite_node(state: MiddlewareState) -> MiddlewareState:
    result = rewrite_check(state["message"], history=state.get("history"))
    if result.decision == "rewrite":
        state["decision"] = "rewrite"
        state["rewritten"] = result.rewritten_message
    return state


def _policy_node(state: MiddlewareState) -> MiddlewareState:
    result = policy_check(state["message"], state.get("rewritten"))
    if result.decision == "reject":
        state["decision"] = "reject"
        state["reason"] = result.reject_reason
    elif result.decision == "rewrite":
        state["decision"] = "rewrite"
        state["rewritten"] = result.rewritten_message
    return state


def _nearby_node(state: MiddlewareState) -> MiddlewareState:
    effective_message = state.get("rewritten") or state["message"]
    result = nearby_check(effective_message)
    if result.metadata:
        state["metadata"] = {**(state.get("metadata") or {}), **result.metadata}
    if result.decision == "clarification":
        state["decision"] = "clarification"
        state["clarification"] = result.clarification_message
    return state


def _commute_node(state: MiddlewareState) -> MiddlewareState:
    effective_message = state.get("rewritten") or state["message"]
    result = commute_check(effective_message)
    if result.metadata:
        state["metadata"] = {**(state.get("metadata") or {}), **result.metadata}
    if result.decision == "clarification":
        state["decision"] = "clarification"
        state["clarification"] = result.clarification_message
    return state


def _stop_if_not_pass(state: MiddlewareState) -> str:
    return "stop" if state.get("decision") == "reject" else "next"
