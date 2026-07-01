"""Agent 数据访问层"""
from datetime import datetime
from sqlalchemy.orm import Session
from model.AgentTask import AgentTask
from model.AgentFeedback import AgentFeedback
from util.log import get_logger

logger = get_logger(__name__)


def create_task(
    db: Session, user_id: str, persona: str, intent: str,
    original_message: str, session_id: int | None = None,
) -> AgentTask:
    task = AgentTask(
        session_id=session_id, user_id=user_id, persona=persona,
        intent=intent, original_message=original_message, status="running",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info("AgentTask 已创建: id=%s, user=%s, intent=%s", task.id, user_id, intent)
    return task


def update_task(db: Session, task_id: int, **kwargs) -> AgentTask | None:
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        logger.warning("AgentTask 不存在: id=%s", task_id)
        return None
    for key, val in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, val)
    db.commit()
    db.refresh(task)
    logger.info("AgentTask 已更新: id=%s, fields=%s", task_id, list(kwargs.keys()))
    return task


def get_task_by_id(db: Session, task_id: int) -> AgentTask | None:
    return db.query(AgentTask).filter(AgentTask.id == task_id).first()


def get_tasks_by_user(db: Session, user_id: str, limit: int = 20) -> list[AgentTask]:
    return (
        db.query(AgentTask)
        .filter(AgentTask.user_id == user_id)
        .order_by(AgentTask.create_time.desc())
        .limit(limit)
        .all()
    )


def get_admin_tasks(
    db: Session,
    since: datetime,
    status: str | None = None,
    intent: str | None = None,
    limit: int | None = None,
) -> list[AgentTask]:
    """管理员监控用任务查询，按时间倒序返回"""
    query = db.query(AgentTask).filter(AgentTask.create_time >= since)
    if status:
        query = query.filter(AgentTask.status == status)
    if intent:
        query = query.filter(AgentTask.intent == intent)
    query = query.order_by(AgentTask.create_time.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def get_feedbacks_by_task_ids(db: Session, task_ids: list[int]) -> list[AgentFeedback]:
    """批量查询任务反馈，用于监控面板汇总"""
    if not task_ids:
        return []
    return db.query(AgentFeedback).filter(AgentFeedback.task_id.in_(task_ids)).all()


def create_feedback(db: Session, task_id: int, rating: int, comment: str | None = None,
                    tool_name: str | None = None) -> AgentFeedback:
    fb = AgentFeedback(task_id=task_id, rating=rating, comment=comment, tool_name=tool_name)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    logger.info("AgentFeedback 已创建: id=%s, task_id=%s, rating=%s", fb.id, task_id, rating)
    return fb


def get_feedback_by_task_tool(
    db: Session,
    task_id: int,
    tool_name: str | None = None,
) -> AgentFeedback | None:
    """按任务和工具名查询反馈；tool_name 为空时表示任务级反馈"""
    query = db.query(AgentFeedback).filter(AgentFeedback.task_id == task_id)
    if tool_name is None:
        query = query.filter(AgentFeedback.tool_name.is_(None))
    else:
        query = query.filter(AgentFeedback.tool_name == tool_name)
    return query.first()


def upsert_feedback(
    db: Session,
    task_id: int,
    rating: int,
    comment: str | None = None,
    tool_name: str | None = None,
) -> tuple[AgentFeedback, bool]:
    """新增或覆盖反馈，返回反馈对象和是否为更新操作"""
    fb = get_feedback_by_task_tool(db, task_id=task_id, tool_name=tool_name)
    updated = fb is not None
    if fb:
        fb.rating = rating
        fb.comment = comment
    else:
        fb = AgentFeedback(
            task_id=task_id,
            rating=rating,
            comment=comment,
            tool_name=tool_name,
        )
        db.add(fb)
    db.commit()
    db.refresh(fb)
    logger.info(
        "AgentFeedback 已%s: id=%s, task_id=%s, rating=%s",
        "更新" if updated else "创建",
        fb.id,
        task_id,
        rating,
    )
    return fb, updated
