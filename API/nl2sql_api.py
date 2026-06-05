"""NL2SQL 智能问数 API 路由"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from database import get_db, get_db_readonly
from sqlalchemy.orm import Session
from service.nl2sql_service import query
from NL2SQL.schema_context import build_schema_text, get_business_table_names
from util.log import get_logger

logger = get_logger(__name__)

nl2sql_router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(..., description="自然语言问题", min_length=1, max_length=1000)
    user_id: str = Field(default="anonymous", description="用户标识")
    session_id: int | None = Field(default=None, description="NL2SQL 会话 ID，不传则自动创建")


class QueryResponse(BaseModel):
    code: int
    msg: str
    data: dict | None = None


@nl2sql_router.post("/query", summary="NL2SQL 智能问数")
def nl2sql_query(
    req: QueryRequest,
    db_rw: Session = Depends(get_db),
    db_readonly: Session = Depends(get_db_readonly),
):
    """
    将自然语言问题转换为 SQL 并查询数据库。

    - **question**: 中文自然语言问题，如 "张三的平均成绩是多少？"
    - **user_id**: 用户标识，用于对话隔离
    - **session_id**: 可选，传入已有会话 ID 可实现多轮追问
    """
    logger.info("NL2SQL 查询请求 | user=%s | question=%s", req.user_id, req.question[:100])
    return query(
        question=req.question,
        user_id=req.user_id,
        db_readonly=db_readonly,
        db_rw=db_rw,
        session_id=req.session_id,
    )


@nl2sql_router.get("/schema", summary="获取数据库表结构概览")
def nl2sql_schema():
    """返回数据库表结构摘要，供前端展示"可以问什么"。"""
    logger.info("NL2SQL 获取表结构概览")
    schema_text = build_schema_text()
    tables = get_business_table_names()
    logger.info("NL2SQL 表结构概览返回：%s 张业务表", len(tables))
    return {
        "code": 200,
        "msg": "ok",
        "data": {
            "tables": tables,
            "schema": schema_text,
        },
    }


@nl2sql_router.get("/sessions", summary="获取 NL2SQL 历史会话")
def nl2sql_sessions(user_id: str = "anonymous", db: Session = Depends(get_db)):
    """查询某个用户的所有 NL2SQL 对话会话及消息。"""
    logger.info("NL2SQL 获取历史会话：user_id=%s", user_id)
    from DAO.nl2sql_dao import get_sessions_by_user, get_messages_by_session
    sessions = get_sessions_by_user(user_id, db)
    logger.info("NL2SQL 历史会话返回：user_id=%s, %s 个会话", user_id, len(sessions))
    result = []
    for s in sessions:
        msgs = get_messages_by_session(s.id, db)
        result.append({
            "id": s.id,
            "title": s.title,
            "update_time": s.update_time.isoformat() if s.update_time else None,
            "messages": [
                {
                    "id": m.id,
                    "question": m.question,
                    "generated_sql": m.generated_sql,
                    "result_json": m.result_json,
                    "cost_ms": m.cost_ms,
                    "is_cached": m.is_cached,
                    "create_time": m.create_time.isoformat() if m.create_time else None,
                }
                for m in msgs
            ],
        })
    return {"code": 200, "msg": "ok", "data": result}
