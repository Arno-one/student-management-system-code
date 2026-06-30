"""NL2SQL 智能问数工具 — 封装 service/nl2sql_service.query()"""
from sqlalchemy.orm import Session
from langchain_core.tools import tool

from agent_system.tools.base import BaseTool, ToolContext
from service import nl2sql_service
from util.log import get_logger

logger = get_logger(__name__)


class Nl2sqlTool(BaseTool):
    name = "nl2sql_tool"
    description = "将自然语言转为 SQL 查询数据库，用于开放式数据统计问题"
    inputs_schema = {"question": str, "user_id": str}

    def run(self, ctx: ToolContext) -> dict:
        question = ctx.params.get("question", "")
        user_id = ctx.params.get("user_id", ctx.user.get("username", ""))
        return _query_data(
            question=question, user_id=user_id,
            db_readonly=ctx.db_readonly, db_rw=ctx.db,
        )


@tool
def query_data(
    question: str,
    user_id: str,
) -> dict:
    """
    将自然语言问题转为 SQL 查询数据库（开放式数据统计）。

    Args:
        question: 自然语言数据问题，如 "3班有多少学生"
        user_id: 用户标识，用于对话隔离和缓存
    """
    # 实际调用由 executor 完成
    pass


def _query_data(
    question: str,
    user_id: str,
    db_readonly: Session,
    db_rw: Session,
    session_id: int | None = None,
) -> dict:
    """内部实现"""
    try:
        result = nl2sql_service.query(
            question=question,
            user_id=user_id,
            db_readonly=db_readonly,
            db_rw=db_rw,
            session_id=session_id,
        )

        # 兼容 service 在失败场景下返回 data=None，避免工具层再次对 None 调 .get()。
        data = result.get("data")
        if not isinstance(data, dict):
            data = {}

        if result.get("code") != 200:
            logger.warning("NL2SQL 查询失败: question='%s', msg=%s", question[:60], result.get("msg"))
            return {
                "success": False,
                "sql": data.get("sql", ""),
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": result.get("msg", "查询失败"),
            }

        row_count = data.get("row_count", 0)
        logger.info("NL2SQL 查询成功: question='%s', rows=%s", question[:60], row_count)
        return {
            "success": True,
            "sql": data.get("sql", ""),
            "columns": data.get("columns", []),
            "rows": data.get("rows", []),
            "row_count": row_count,
            "error": None,
            "hint": "查询执行成功，但数据库中暂无符合条件的数据，你可以尝试调整查询条件" if row_count == 0 else None,
        }
    except Exception as e:
        logger.exception("NL2SQL 查询异常: question='%s', %s", question[:60], e)
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": f"数据查询失败: {e}",
        }
