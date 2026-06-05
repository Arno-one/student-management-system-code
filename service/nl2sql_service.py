"""
NL2SQL 业务编排层：串联 问题接收 → 缓存检查 → LLM生成SQL → 校验 → 美化 → 执行 → 持久化 → 返回。
"""
import time
import re
from openai import OpenAI
import config
from util.log import get_logger
from NL2SQL.prompt_builder import build_messages
from NL2SQL.sql_validator import validate, ensure_is_deleted, check_syntax
from NL2SQL.sql_formatter import format_sql
from NL2SQL.sql_executor import execute, result_to_json, SqlExecutionError

logger = get_logger(__name__)

# DeepSeek 客户端（复用项目统一的密钥和 base_url）
_client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

# 内存缓存: {normalized_question: {"sql": "...", "result_json": "..."}}
# P1 可升级为 Redis
_cache: dict[str, dict] = {}

MODEL_NAME = "deepseek-v4-flash"


def normalize_question(question: str) -> str:
    """标准化问题文本，用于缓存 key 匹配"""
    return re.sub(r'\s+', '', question.strip())


def _call_llm(question: str) -> tuple[str, int]:
    """
    调用 DeepSeek 生成 SQL。
    返回 (sql_or_error, cost_ms)。
    """
    messages = build_messages(question)
    t0 = time.time()
    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        stream=False,
        max_tokens=500,
    )
    cost_ms = int((time.time() - t0) * 1000)
    raw = response.choices[0].message.content.strip()
    # 清理可能的 markdown 代码块包裹
    sql = _extract_sql(raw)
    logger.info("LLM 生成 SQL 耗时 %s ms，原始输出：%s", cost_ms, raw[:200])
    return sql, cost_ms


def _extract_sql(raw: str) -> str:
    """从 LLM 输出中提取纯 SQL（去除可能的 markdown 代码块）"""
    # 匹配 ```sql ... ``` 或 ``` ... ```
    match = re.search(r'```(?:\w+)?\s*\n?(.*?)```', raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()


def query(question: str, user_id: str, db_readonly, db_rw,
          session_id: int | None = None) -> dict:
    """
    NL2SQL 单轮查询入口。
    :param question: 用户自然语言问题
    :param user_id: 用户标识
    :param db_readonly: 只读数据库会话（用于执行 SQL）
    :param db_rw: 读写数据库会话（用于持久化消息）
    :param session_id: 可选，已有 NL2SQL 会话 ID
    :return: 统一格式结果 dict
    """
    t0 = time.time()

    # ---- 1. 缓存命中检查 ----
    norm = normalize_question(question)
    cached = _cache.get(norm)
    if cached:
        logger.info("NL2SQL 缓存命中：%s", question[:50])
        _save_message(
            db_rw, session_id, user_id, question,
            cached["sql"], cached["result_json"],
            cost_ms=0, is_cached=1,
        )
        return _build_response(
            sql=cached["sql"],
            result=None,  # 缓存的结果 JSON 直接返回
            cached_result_json=cached["result_json"],
            cost_ms=0,
            is_cached=True,
        )

    # ---- 2. 调用 LLM 生成 SQL ----
    sql, cost_ms = _call_llm(question)

    if not sql or sql.upper().strip() == "UNSUPPORTED":
        logger.info("NL2SQL 问题无法转换：%s", question[:50])
        return {
            "code": 400,
            "msg": "该问题无法转换为数据库查询，请尝试更具体的问题。",
            "data": None,
        }

    # ---- 3. SQL 美化 ----
    sql = format_sql(sql)

    # ---- 4. SQL 安全校验 ----
    valid, err_msg = validate(sql)
    if not valid:
        logger.warning("NL2SQL 校验未通过：%s | SQL: %s", err_msg, sql[:200])
        return {"code": 400, "msg": f"生成的 SQL 未通过安全校验: {err_msg}", "data": None}

    # ---- 5. 自动补全 is_deleted ----
    sql = ensure_is_deleted(sql)

    # ---- 6. 语法校验（EXPLAIN） ----
    syntax_ok, syntax_err = check_syntax(sql, db_readonly)
    if not syntax_ok:
        logger.warning("NL2SQL 语法校验失败：%s | SQL: %s", syntax_err, sql[:200])
        return {"code": 400, "msg": f"SQL 语法错误: {syntax_err}", "data": None}

    # ---- 7. 执行 SQL ----
    try:
        result = execute(sql, db_readonly)
    except SqlExecutionError as e:
        logger.error("NL2SQL 执行失败：%s | SQL: %s", e, sql[:200])
        return {"code": 500, "msg": f"查询执行失败: {e}", "data": None}

    result_json = result_to_json(result)

    # ---- 8. 写入缓存 ----
    _cache[norm] = {"sql": sql, "result_json": result_json}

    # ---- 9. 持久化消息 ----
    _save_message(
        db_rw, session_id, user_id, question,
        sql, result_json,
        cost_ms=cost_ms, is_cached=0,
    )

    total_ms = int((time.time() - t0) * 1000)
    logger.info("NL2SQL 查询完成，总耗时 %s ms，返回 %s 行", total_ms, result["row_count"])

    return _build_response(
        sql=sql,
        result=result,
        cost_ms=cost_ms,
        is_cached=False,
    )


# ---- 内部辅助 ----

def _save_message(db_rw, session_id: int | None, user_id: str,
                  question: str, sql: str, result_json: str,
                  cost_ms: int, is_cached: int):
    """持久化本轮 NL2SQL 问答到数据库"""
    from DAO.nl2sql_dao import create_session, add_message, touch_session
    if session_id is None:
        session = create_session(user_id, title=question[:30], db=db_rw)
        session_id = session.id
    else:
        touch_session(session_id, db_rw)
    add_message(session_id, question, sql, result_json, cost_ms, is_cached, db=db_rw)


def _build_response(sql: str, result: dict | None,
                    cached_result_json: str | None = None,
                    cost_ms: int = 0, is_cached: bool = False) -> dict:
    """组装统一响应格式"""
    import json
    data = {
        "sql": sql,
        "cost_ms": cost_ms,
        "is_cached": is_cached,
    }
    if result is not None:
        data["columns"] = result["columns"]
        data["rows"] = result["rows"]
        data["row_count"] = result["row_count"]
    elif cached_result_json is not None:
        cached = json.loads(cached_result_json)
        data["columns"] = cached.get("columns", [])
        data["rows"] = cached.get("rows", [])
        data["row_count"] = cached.get("row_count", 0)

    return {
        "code": 200,
        "msg": "ok",
        "data": data,
    }
