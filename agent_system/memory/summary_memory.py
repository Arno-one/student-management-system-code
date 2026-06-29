"""Agent 摘要记忆 — 会话级摘要压缩，不做跨会话长期记忆。"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, SystemMessage

from DAO import talk_dao
from llm_basic import get_model
from util.log import get_logger
from .working_memory import build_recent_history, estimate_history_chars, message_to_history_item

logger = get_logger(__name__)

SUMMARY_MESSAGE_THRESHOLD = 10
SUMMARY_CHAR_THRESHOLD = 6000
RECENT_CONTEXT_MESSAGES = 5
SUMMARY_PROVIDER = "deepseek"

_SUMMARY_PROMPT = """你是学生管理系统 Agent 的会话摘要器。

请把历史对话压缩成一个很短的会话标题，供历史列表展示和后续 Agent 理解主题。

规则：
1. 只保留用户最核心的目标或主题，不写完整过程复盘。
2. 不跨用户、不跨会话推断长期画像。
3. 对陪伴班主任或情绪支持类对话，只记录主题，不记录具体敏感细节。
4. 不记录身份证、手机号、邮箱、详细住址、隐私病史等敏感内容。
5. 24 字以内，直接输出标题文本，不要句号，不要“用户询问/本轮对话”等套话。"""


def should_refresh_summary(session_id: int, db: Session) -> bool:
    """判断是否达到摘要刷新阈值：超过 10 条消息或历史文本超过 6000 字。"""
    messages = talk_dao.get_messages_by_session(session_id, db)
    if len(messages) > SUMMARY_MESSAGE_THRESHOLD:
        return True
    history = [item for item in (message_to_history_item(msg) for msg in messages) if item]
    return estimate_history_chars(history) > SUMMARY_CHAR_THRESHOLD


def refresh_summary_if_needed(session_id: int, persona: str, db: Session) -> None:
    """摘要刷新失败不能影响 Agent 主流程。"""
    try:
        if should_refresh_summary(session_id, db):
            refresh_summary(session_id=session_id, persona=persona, db=db)
    except Exception as exc:
        logger.warning("会话摘要刷新失败，已跳过: session=%s, error=%s", session_id, exc)


def refresh_summary_safely(session_id: int, persona: str, db: Session) -> None:
    """每轮对话后立即刷新摘要；失败只记录日志，不影响用户拿到回复。"""
    try:
        refresh_summary(session_id=session_id, persona=persona, db=db)
    except Exception as exc:
        logger.warning("会话摘要即时刷新失败，已跳过: session=%s, error=%s", session_id, exc)


def refresh_summary(session_id: int, persona: str, db: Session) -> str | None:
    """生成并保存会话摘要，同时把会话标题更新为摘要短标题。"""
    session = talk_dao.get_session_by_id(session_id, db)
    if not session:
        return None

    messages = talk_dao.get_messages_by_session(session_id, db)
    history = [item for item in (message_to_history_item(msg) for msg in messages) if item]
    if not history:
        return None

    current_summary = session.summary or ""
    summary = _summarize_history(history=history, current_summary=current_summary, persona=persona)
    if not summary:
        return None

    safe_summary = _sanitize_summary(summary)
    style = session.style or _infer_style(persona)
    talk_dao.update_session_summary(session_id=session_id, summary=safe_summary, style=style, db=db)
    talk_dao.update_session_title(session_id=session_id, title=_build_summary_title(safe_summary), db=db)
    logger.info("会话摘要已刷新: session=%s, len=%s", session_id, len(safe_summary))
    return safe_summary


def build_summary_context(session_id: int, db: Session) -> list[dict[str, str]]:
    """返回“会话摘要 + 最近 5 条原文”的紧凑上下文。"""
    session = talk_dao.get_session_by_id(session_id, db)
    messages = talk_dao.get_messages_by_session(session_id, db)
    recent = build_recent_history(messages, max_messages=RECENT_CONTEXT_MESSAGES)

    from .working_memory import build_context_history
    return build_context_history(summary=session.summary if session else None, recent_history=recent)


def _summarize_history(history: list[dict[str, str]], current_summary: str, persona: str) -> str:
    """调用 LLM 摘要；失败时使用保守的规则摘要兜底。"""
    user_turns = [item for item in history if item.get("role") == "user" and item.get("content")]
    if len(user_turns) <= 5:
        return _short_title_from_first_turn(user_turns)

    lines = []
    for item in history:
        role = _role_label(item.get("role"))
        content = str(item.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content[:500]}")
    history_text = "\n".join(lines)
    user_message = (
        f"当前角色: {persona}\n"
        f"已有摘要: {current_summary or '无'}\n\n"
        f"完整历史:\n{history_text}"
    )

    try:
        model = get_model(SUMMARY_PROVIDER)
        response = model.invoke([SystemMessage(content=_SUMMARY_PROMPT), HumanMessage(content=user_message)])
        content = str(response.content).strip()
        if content:
            return content
    except Exception as exc:
        logger.warning("LLM 摘要失败，使用规则兜底: %s", exc)

    return _fallback_summary(history)


def _fallback_summary(history: list[dict[str, str]]) -> str:
    """LLM 不可用时的保守摘要，确保功能降级但不中断。"""
    user_items = [item["content"] for item in history if item.get("role") == "user" and item.get("content")]
    if not user_items:
        return "常规咨询"
    return _compact_title(user_items[-1])


def _sanitize_summary(summary: str) -> str:
    """做轻量隐私截断和清洗，避免摘要保存过细敏感内容。"""
    text = " ".join(summary.replace("\n", " ").split())
    text = re.sub(r"^(用户|同学)?(想要|希望|询问|咨询|查询|了解|需要|本轮对话|本次对话)[:：，,\s]*", "", text)
    text = text.strip(" 。；;，,、")
    if len(text) > 36:
        text = text[:33] + "..."
    return text


def _build_summary_title(summary: str) -> str:
    """会话列表标题用摘要短句展示。"""
    if len(summary) <= 32:
        return summary
    return summary[:29] + "..."


def _short_title_from_first_turn(user_turns: list[dict[str, str]]) -> str:
    """5 轮以内固定用第一轮用户问题生成短标题，避免短会话被总结成全文复盘。"""
    first_user = str(user_turns[0].get("content", "")).strip() if user_turns else ""
    return _compact_title(first_user)


def _compact_title(text: str) -> str:
    """把用户原问题压缩成历史列表可扫读的短标题。"""
    cleaned = " ".join(str(text or "").replace("\n", " ").split())
    cleaned = re.sub(r"^(请|帮我|麻烦|能不能|可以|我想|我想要|我需要|帮忙)", "", cleaned)
    cleaned = cleaned.strip(" 。？?！!；;，,、")
    if not cleaned:
        return "常规咨询"
    if len(cleaned) > 24:
        return cleaned[:21] + "..."
    return cleaned


def _infer_style(persona: str) -> str:
    """记录轻量风格标签，后续长期画像版本可继续扩展。"""
    if persona == "companion_head_teacher":
        return "supportive"
    return "academic"


def _role_label(role: str | None) -> str:
    if role == "user":
        return "用户"
    if role == "summary":
        return "摘要"
    return "助手"
