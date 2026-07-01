"""Agent 工具包导出。

这里不能在包初始化时直接导入所有工具；部分工具会拉起大模型 SDK，
如果主应用只是在启动阶段注册路由，就会白白拖慢启动速度。
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "resolve_student": ("agent_system.tools.student_tool", "resolve_student"),
    "StudentTool": ("agent_system.tools.student_tool", "StudentTool"),
    "_resolve_student": ("agent_system.tools.student_tool", "_resolve_student"),
    "query_student_score": ("agent_system.tools.score_tool", "query_student_score"),
    "ScoreTool": ("agent_system.tools.score_tool", "ScoreTool"),
    "_query_student_score": ("agent_system.tools.score_tool", "_query_student_score"),
    "search_knowledge": ("agent_system.tools.rag_tool", "search_knowledge"),
    "RagTool": ("agent_system.tools.rag_tool", "RagTool"),
    "_search_knowledge": ("agent_system.tools.rag_tool", "_search_knowledge"),
    "query_data": ("agent_system.tools.nl2sql_tool", "query_data"),
    "Nl2sqlTool": ("agent_system.tools.nl2sql_tool", "Nl2sqlTool"),
    "_query_data": ("agent_system.tools.nl2sql_tool", "_query_data"),
    "WeatherTool": ("agent_system.tools.weather_tool", "WeatherTool"),
    "ImageTool": ("agent_system.tools.image_tool", "ImageTool"),
    "EmailTool": ("agent_system.tools.email_tool", "EmailTool"),
    "CommutePlanTool": ("agent_system.tools.commute_plan_tool", "CommutePlanTool"),
    "NearbyServiceTool": ("agent_system.tools.nearby_service_tool", "NearbyServiceTool"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """首次访问具体工具时再导入对应模块。"""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
