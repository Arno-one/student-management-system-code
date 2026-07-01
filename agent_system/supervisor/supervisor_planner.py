"""Supervisor 一期编排器。

当前只接管明确的跨域场景：地图出行任务 + 邮件沟通任务。
它不直接调用 MCP 或邮件服务，而是产出 handoff 轨迹和复用现有工具的 ExecutionPlan。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_system.schemas.task_state import ExecutionPlan, PlanStep


@dataclass
class AgentHandoff:
    """Supervisor 分派给专门 Agent 的最小任务描述。"""

    agent_role: str
    intent: str
    tool_name: str
    reason: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class SupervisorDecision:
    """Supervisor 路由结果，供 service 层执行和落库。"""

    intent: str
    plan: ExecutionPlan
    state_trace: list[str]
    handoffs: list[AgentHandoff]

    def to_metadata(self) -> dict:
        """转成可 JSON 序列化的监控/历史元数据。"""
        return {
            "mode": "supervisor",
            "intent": self.intent,
            "state_trace": self.state_trace,
            "handoffs": [
                {
                    "agent_role": item.agent_role,
                    "intent": item.intent,
                    "tool_name": item.tool_name,
                    "reason": item.reason,
                    "depends_on": item.depends_on,
                }
                for item in self.handoffs
            ],
        }


_MAP_HINTS = [
    "路线", "通勤", "怎么去", "如何去", "坐地铁", "坐公交", "开车", "驾车", "步行", "到",
]
_EMAIL_HINTS = ["邮件", "发给", "发送", "通知", "写信", "请假", "回复"]
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def build_supervisor_decision(
    message: str,
    persona: str = "academic_mentor",
) -> SupervisorDecision | None:
    """命中跨域请求时生成 Supervisor 多 Agent 执行计划，否则返回 None。"""
    text = (message or "").strip()
    if not _is_map_email_request(text):
        return None

    handoffs = [
        AgentHandoff(
            agent_role="MapAgent",
            intent="commute_plan",
            tool_name="commute_plan_tool",
            reason="用户需要先获得出行路线或通勤方案。",
        ),
        AgentHandoff(
            agent_role="CommunicationAgent",
            intent="email_draft",
            tool_name="email_tool",
            reason="用户需要把路线或沟通内容整理成邮件并进入 HITL 确认。",
            depends_on=["commute_plan_tool"],
        ),
    ]
    plan = ExecutionPlan(
        intent="supervisor_multi_agent",
        persona=persona,
        steps=[
            PlanStep(step_id=1, tool_name="commute_plan_tool"),
            # 邮件正文仍使用原始用户输入；路线结果通过 inputs_from 留给后续工具升级读取。
            PlanStep(step_id=2, tool_name="email_tool", inputs_from=["commute_plan_tool"]),
        ],
        need_llm_summary=False,
    )
    return SupervisorDecision(
        intent="supervisor_multi_agent",
        plan=plan,
        state_trace=["route", "delegate", "merge", "complete"],
        handoffs=handoffs,
    )


def _is_map_email_request(text: str) -> bool:
    """只识别明确同时包含地图和邮件沟通语义的请求，避免抢单一意图。"""
    if not text:
        return False
    has_map = any(word in text for word in _MAP_HINTS) and "从" in text
    has_email = any(word in text for word in _EMAIL_HINTS) or bool(_EMAIL_RE.search(text))
    return has_map and has_email
