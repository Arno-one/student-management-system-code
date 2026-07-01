"""
SQL 执行器：使用只读连接执行校验通过的 SQL，带超时保护和结果集上限。
"""
import json
from sqlalchemy import text
from decimal import Decimal
from datetime import date, datetime

MAX_ROWS = 1000
QUERY_TIMEOUT_SECONDS = 10


class SqlExecutionError(Exception):
    """SQL 执行异常"""
    pass


def execute(sql: str, db) -> dict:
    """
    在只读数据库连接上执行 SELECT 语句，返回统一格式的查询结果。
    :param sql: 已通过安全校验的 SQL 语句
    :param db: 只读数据库会话（来自 get_db_readonly）
    :return: {"columns": [...], "rows": [[...], ...], "row_count": N}
    """
    # 注入超时保护（MySQL 5.7.8+ 支持 max_execution_time hint）
    sql_with_timeout = sql.strip()
    if sql_with_timeout.upper().startswith("SELECT"):
        sql_with_timeout = f"SELECT /*+ MAX_EXECUTION_TIME({QUERY_TIMEOUT_SECONDS * 1000}) */ " + sql_with_timeout[6:]

    # 追加 LIMIT（如用户未指定）
    if "LIMIT" not in sql_with_timeout.upper():
        sql_with_timeout += f" LIMIT {MAX_ROWS}"

    try:
        result = db.execute(text(sql_with_timeout))

        if result.returns_rows:
            columns = list(result.keys())
            rows = [_serialize_row(row) for row in result.fetchall()]
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }
        else:
            return {"columns": [], "rows": [], "row_count": 0}
    except Exception as e:
        raise SqlExecutionError(str(e))


def result_to_json(result: dict) -> str:
    """将查询结果 dict 序列化为 JSON 字符串（用于存入 nl2sql_message.result_json）"""
    return json.dumps(result, ensure_ascii=False, default=_json_serializer)


# ---- 内部辅助 ----

def _serialize_row(row) -> list:
    """将 Row 对象转为可 JSON 序列化的列表"""
    return [_serialize_value(v) for v in row]


def _serialize_value(v):
    """将非标量值（Decimal/date/datetime）转为可 JSON 序列化的类型"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v


def _json_serializer(obj):
    """json.dumps 的 default 回调"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
