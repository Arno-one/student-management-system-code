"""对话记忆 — 复用 TalkSession + TalkMessage"""
import json
from sqlalchemy.orm import Session

from DAO import talk_dao
from model.Talk import TalkSession
from util.log import get_logger
from .summary_memory import build_summary_context
from .working_memory import build_recent_history

logger = get_logger(__name__)


def get_or_create_session(user_id: str, session_id: int | None, db: Session) -> TalkSession:
    """
    获取或创建会话。

    如果传了 session_id 且会话存在且属于当前用户 → 返回已有会话；
    否则创建新会话。
    """
    if session_id:
        session = talk_dao.get_session_by_id(session_id, db)
        if session and session.user_id == user_id:
            logger.info("复用已有会话: id=%s, user_id=%s", session_id, user_id)
            return session
        logger.warning("会话不存在或不属于当前用户: id=%s, user_id=%s，将创建新会话", session_id, user_id)

    session = talk_dao.create_session(user_id=user_id, title="Agent 对话", db=db)
    logger.info("创建新会话: id=%s, user_id=%s", session.id, user_id)
    return session


def get_history(session_id: int, db: Session, max_messages: int = 5) -> list[dict]:
    """
    获取紧凑历史：会话摘要 + 最近 N 条原文。

    Returns:
        [{"role": "summary", "content": "..."}, {"role": "user", "content": "..."}, ...]
    """
    if max_messages == 5:
        return build_summary_context(session_id, db)

    messages = talk_dao.get_messages_by_session(session_id, db)
    return build_recent_history(messages, max_messages=max_messages)


def save_message(
    session_id: int,
    role: str,
    content: str,
    metadata: dict | None = None,
    db: Session = None,
):
    """
    保存一条消息到会话。

    Args:
        session_id: 会话 ID
        role: "user" 或 "assistant"
        content: 消息内容
        metadata: 仅 assistant 消息时，可附带 {intent, tool_calls, plan} 等结构化元数据

    Returns:
        TalkMessage 对象（assistant 消息时可用于后续更新 HITL 状态）
    """
    msg = None
    if role == "user":
        msg = talk_dao.add_message(
            session_id=session_id,
            role=role,
            user_content=content,
            db=db,
        )
    elif role == "assistant":
        if metadata:
            data = {"reply": content, **metadata}
            ai_content = json.dumps(data, ensure_ascii=False)
        else:
            ai_content = content
        msg = talk_dao.add_message(
            session_id=session_id,
            role=role,
            ai_content=ai_content,
            db=db,
        )

    talk_dao.touch_session(session_id, db)
    logger.debug("消息已保存: session=%s, role=%s, len=%s", session_id, role, len(content))
    return msg
