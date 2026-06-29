"""HITL 高风险操作规则配置"""
from dataclasses import dataclass


@dataclass(frozen=True)
class HitlRule:
    """HITL 规则，描述某个工具触发人工确认时的展示和超时策略"""
    enabled: bool = True
    risk_level: str = "medium"
    timeout_seconds: int = 600
    confirm_title: str = "确认执行操作"
    confirm_message: str = "请确认内容无误后再继续。"


HITL_RULES: dict[str, HitlRule] = {
    "email_tool": HitlRule(
        enabled=True,
        risk_level="medium",
        timeout_seconds=600,
        confirm_title="确认发送邮件",
        confirm_message="请确认收件人、主题和正文无误后再发送。",
    ),
}


DEFAULT_HITL_RULE = HitlRule(
    enabled=True,
    risk_level="high",
    timeout_seconds=600,
    confirm_title="确认高风险操作",
    confirm_message="该操作需要人工确认，请核对内容后再继续。",
)


def get_hitl_rule(tool_name: str) -> HitlRule:
    """按工具名获取 HITL 规则；未知工具使用保守默认规则"""
    return HITL_RULES.get(tool_name, DEFAULT_HITL_RULE)


def build_hitl_payload(tool_name: str, preview: dict, rule: HitlRule, expires_at: float, step_id: int | None = None) -> dict:
    """构造 SSE awaiting_confirmation 事件数据"""
    return {
        "tool_name": tool_name,
        "step_id": step_id,
        "preview": preview,
        "risk_level": rule.risk_level,
        "timeout_seconds": rule.timeout_seconds,
        "expires_at": expires_at,
        "confirm_title": rule.confirm_title,
        "confirm_message": rule.confirm_message,
    }
