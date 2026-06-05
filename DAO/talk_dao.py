from sqlalchemy.orm import Session
from model.Talk import TalkSession, TalkMessage
from typing import Optional
from util.log import get_logger

logger = get_logger(__name__)


# ==================== 会话（Session）CRUD ====================

def create_session(user_id: str, title: str = "新对话", db: Session = None) -> TalkSession:
    """创建新会话"""
    session = TalkSession(user_id=user_id, session_title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("会话已创建：id=%s, user_id=%s, title=%s", session.id, user_id, title)
    return session


def get_sessions_by_user(user_id: str, db: Session):
    """查询某用户的所有未删除会话，按更新时间倒序"""
    return db.query(TalkSession).filter(
        TalkSession.user_id == user_id,
        TalkSession.is_deleted == 0
    ).order_by(TalkSession.update_time.desc()).all()


def get_session_by_id(session_id: int, db: Session) -> Optional[TalkSession]:
    """根据会话ID查询（仅未删除）"""
    return db.query(TalkSession).filter(
        TalkSession.id == session_id,
        TalkSession.is_deleted == 0
    ).first()


def soft_delete_session(session_id: int, db: Session) -> bool:
    """逻辑删除会话"""
    session = get_session_by_id(session_id, db)
    if not session:
        return False
    session.is_deleted = 1
    db.commit()
    logger.info("会话已逻辑删除：id=%s", session_id)
    return True


def update_session_title(session_id: int, title: str, db: Session) -> Optional[TalkSession]:
    """更新会话标题"""
    session = get_session_by_id(session_id, db)
    if not session:
        return None
    session.session_title = title
    db.commit()
    db.refresh(session)
    return session


def update_session_summary(session_id: int, summary: str, style: str, db: Session) -> Optional[TalkSession]:
    """更新会话的主题摘要和用户风格偏好"""
    session = db.query(TalkSession).filter(
        TalkSession.id == session_id,
        TalkSession.is_deleted == 0
    ).first()
    if not session:
        return None
    session.summary = summary
    session.style = style
    db.commit()
    db.refresh(session)
    return session


def touch_session(session_id: int, db: Session):
    """更新会话的 update_time（有新消息时调用）"""
    session = db.query(TalkSession).filter(TalkSession.id == session_id).first()
    if session:
        from datetime import datetime
        session.update_time = datetime.now()
        db.commit()


# ==================== 消息（Message）CRUD ====================

def add_message(session_id: int, role: str, user_content: str = None, ai_content: str = None, db: Session = None) -> TalkMessage:
    """往指定会话追加一条消息，user_content 存用户问题，ai_content 存大模型回复"""
    msg = TalkMessage(session_id=session_id, role=role,
                      user_content=user_content, ai_content=ai_content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages_by_session(session_id: int, db: Session):
    """获取某会话的全部消息，按时间正序"""
    return db.query(TalkMessage).filter(
        TalkMessage.session_id == session_id
    ).order_by(TalkMessage.create_time.asc()).all()


def delete_messages_by_session(session_id: int, db: Session):
    """物理删除某会话下的全部消息"""
    count = db.query(TalkMessage).filter(
        TalkMessage.session_id == session_id
    ).delete()
    db.commit()
    logger.info("会话 %s 下的 %s 条消息已清除", session_id, count)
    return count
