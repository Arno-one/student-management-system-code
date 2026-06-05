from sqlalchemy.orm import Session
from model.NL2SQL import Nl2sqlSession, Nl2sqlMessage
from typing import Optional
from datetime import datetime
from util.log import get_logger

logger = get_logger(__name__)


# ==================== 会话 CRUD ====================

def create_session(user_id: str, title: str = "新对话", db: Session = None) -> Nl2sqlSession:
    session = Nl2sqlSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("NL2SQL会话已创建：id=%s, user_id=%s", session.id, user_id)
    return session


def get_sessions_by_user(user_id: str, db: Session):
    return db.query(Nl2sqlSession).filter(
        Nl2sqlSession.user_id == user_id,
        Nl2sqlSession.is_deleted == 0
    ).order_by(Nl2sqlSession.update_time.desc()).all()


def get_session_by_id(session_id: int, db: Session) -> Optional[Nl2sqlSession]:
    return db.query(Nl2sqlSession).filter(
        Nl2sqlSession.id == session_id,
        Nl2sqlSession.is_deleted == 0
    ).first()


def soft_delete_session(session_id: int, db: Session) -> bool:
    session = get_session_by_id(session_id, db)
    if not session:
        return False
    session.is_deleted = 1
    db.commit()
    return True


def update_session_title(session_id: int, title: str, db: Session):
    session = get_session_by_id(session_id, db)
    if session:
        session.title = title
        db.commit()
        db.refresh(session)
    return session


def touch_session(session_id: int, db: Session):
    session = db.query(Nl2sqlSession).filter(Nl2sqlSession.id == session_id).first()
    if session:
        session.update_time = datetime.now()
        db.commit()


# ==================== 消息 CRUD ====================

def add_message(session_id: int, question: str, generated_sql: str = None,
                result_json: str = None, cost_ms: int = None,
                is_cached: int = 0, db: Session = None) -> Nl2sqlMessage:
    msg = Nl2sqlMessage(
        session_id=session_id,
        question=question,
        generated_sql=generated_sql,
        result_json=result_json,
        cost_ms=cost_ms,
        is_cached=is_cached,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages_by_session(session_id: int, db: Session):
    return db.query(Nl2sqlMessage).filter(
        Nl2sqlMessage.session_id == session_id
    ).order_by(Nl2sqlMessage.create_time.asc()).all()


def get_message_by_id(message_id: int, db: Session) -> Optional[Nl2sqlMessage]:
    return db.query(Nl2sqlMessage).filter(Nl2sqlMessage.id == message_id).first()
