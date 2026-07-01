"""HITL 管理器 — 执行暂停/恢复/超时管理"""
import time
from agent_system.hitl.hitl_schema import HitlState
from util.log import get_logger

logger = get_logger(__name__)

# 内存状态存储（后续可迁移到 Redis）
_paused_states: dict[str, HitlState] = {}
DEFAULT_TTL_SECONDS = 600  # 兜底 10 分钟超时


def pause_execution(task_id: str, step_id: int, state: HitlState) -> None:
    """保存暂停的执行状态"""
    key = f"{task_id}:{step_id}"
    if state.expires_at is None:
        state.expires_at = state.paused_at + (state.timeout_seconds or DEFAULT_TTL_SECONDS)
    _paused_states[key] = state
    logger.info("HITL 暂停: key=%s, tool=%s, expires_at=%s", key, state.tool_name, state.expires_at)


def get_paused_state(task_id: str, step_id: int) -> HitlState | None:
    """获取暂停状态，超时自动清理"""
    key = f"{task_id}:{step_id}"
    state = _paused_states.get(key)
    if state is None:
        return None
    expires_at = state.expires_at or (state.paused_at + (state.timeout_seconds or DEFAULT_TTL_SECONDS))
    if time.time() > expires_at:
        del _paused_states[key]
        logger.info("HITL 超时清理: key=%s", key)
        return None
    return state


def clear_paused_state(task_id: str, step_id: int) -> None:
    """确认/取消后清理状态"""
    key = f"{task_id}:{step_id}"
    _paused_states.pop(key, None)
    logger.info("HITL 清理: key=%s", key)


def set_hitl_message_id(task_id: str, step_id: int, message_id: int) -> None:
    """存入 TalkMessage 主键，供 confirm 端点回写结果"""
    key = f"{task_id}:{step_id}"
    state = _paused_states.get(key)
    if state:
        state.message_id = message_id
        logger.info("HITL 关联消息: key=%s, message_id=%s", key, message_id)


def set_hitl_agent_task_id(task_id: str, step_id: int, agent_task_id: int) -> None:
    """存入 AgentTask 主键，供 confirm 端点回写监控状态"""
    key = f"{task_id}:{step_id}"
    state = _paused_states.get(key)
    if state:
        state.agent_task_id = agent_task_id
        logger.info("HITL 关联 AgentTask: key=%s, agent_task_id=%s", key, agent_task_id)
