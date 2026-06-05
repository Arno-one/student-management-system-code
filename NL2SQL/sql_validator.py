"""
SQL 安全校验器：对 LLM 生成的 SQL 做多层校验，确保只执行安全的只读查询。
"""
import re
from NL2SQL.schema_context import get_business_table_names


# 禁止的 SQL 关键字（DML / DDL / 危险操作）
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE",
    "REPLACE", "LOAD", "IMPORT", "GRANT", "REVOKE", "RENAME", "EXECUTE",
    "INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE", "SLEEP", "BENCHMARK",
]

# 只允许的语句类型
ALLOWED_PREFIXES = ["SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN"]

# 需要加 is_deleted 过滤的业务表
BUSINESS_TABLES = get_business_table_names()


def validate(sql: str) -> tuple[bool, str]:
    """
    校验 SQL 语句的安全性。
    返回 (is_valid, error_message)，is_valid=True 表示通过。
    """
    if not sql or not sql.strip():
        return False, "SQL 语句为空"

    sql_upper = sql.strip().upper()
    # 去掉注释后再做关键字检查
    sql_clean = _strip_comments(sql_upper)

    # 1. 语句类型检查
    if not any(sql_clean.startswith(prefix.upper()) for prefix in ALLOWED_PREFIXES):
        return False, f"不允许的语句类型。仅支持: {', '.join(ALLOWED_PREFIXES)}"

    # 2. 禁止关键字检查
    for kw in FORBIDDEN_KEYWORDS:
        if _keyword_present(sql_clean, kw.upper()):
            return False, f"SQL 包含禁止的关键字: {kw}"

    # 3. UNSUPPORTED 标记（大模型自己判断无法回答）
    if sql_clean.strip() == "UNSUPPORTED":
        return False, "该问题无法转换为 SQL 查询"

    return True, "ok"


def ensure_is_deleted(sql: str) -> str:
    """
    自动补全 is_deleted=0 条件。
    对每个出现在 FROM/JOIN 中的业务表，如果 WHERE 中未提到它的 is_deleted，
    则在 WHERE 子句末尾追加 AND xxx.is_deleted=0。
    """
    tables_in_query = _extract_table_aliases(sql)

    for table_name, alias in tables_in_query.items():
        if table_name not in BUSINESS_TABLES:
            continue
        col_ref = f"{alias}.is_deleted" if alias else f"{table_name}.is_deleted"
        if col_ref.lower() in sql.lower():
            continue  # 已经有了，跳过

        sql = _append_condition(sql, f"{col_ref} = 0")

    return sql


def check_syntax(sql: str, db) -> tuple[bool, str]:
    """
    用 EXPLAIN 做语法校验（不实际执行查询）。
    返回 (is_valid, error_message)。
    """
    try:
        from sqlalchemy import text
        db.execute(text(f"EXPLAIN {sql}"))
        return True, "ok"
    except Exception as e:
        return False, f"SQL 语法错误: {e}"


# ---- 内部辅助函数 ----

def _strip_comments(sql_upper: str) -> str:
    """移除 SQL 注释（单行 -- 和多行 /* */）"""
    sql_upper = re.sub(r'/\*.*?\*/', '', sql_upper, flags=re.DOTALL)
    sql_upper = re.sub(r'--[^\n]*', '', sql_upper)
    return sql_upper


def _keyword_present(sql_clean: str, keyword: str) -> bool:
    """
    用词边界匹配检查关键字是否存在（避免误判，如 'DELETE' 不匹配 'DELETE_FLAG'）。
    """
    return bool(re.search(r'\b' + re.escape(keyword) + r'\b', sql_clean))


def _extract_table_aliases(sql: str) -> dict[str, str | None]:
    """
    从 SQL 中提取 FROM/JOIN 子句的表名和别名。
    返回 {table_name: alias_or_none}。
    """
    result = {}
    # 匹配: FROM table_name alias 或 JOIN table_name alias
    pattern = r'(?:FROM|JOIN)\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?'
    matches = re.findall(pattern, sql, re.IGNORECASE)
    for table_name, alias in matches:
        table_name_lower = table_name.lower()
        if table_name_lower in BUSINESS_TABLES:
            result[table_name_lower] = alias or table_name
    return result


def _append_condition(sql: str, condition: str) -> str:
    """在 SQL 的 WHERE 或最后追加条件"""
    if re.search(r'\bWHERE\b', sql, re.IGNORECASE):
        # 已有 WHERE：在 GROUP BY / ORDER BY / LIMIT / HAVING 之前插入
        boundaries = r'(GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING|$)'
        sql = re.sub(
            r'\b(' + boundaries + r')',
            rf' AND {condition} \1',
            sql, count=1, flags=re.IGNORECASE
        )
    else:
        # 没有 WHERE：在 GROUP BY / ORDER BY / LIMIT / HAVING 之前插入 WHERE
        boundaries = r'(GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING|$)'
        sql = re.sub(
            r'\b(' + boundaries + r')',
            rf' WHERE {condition} \1',
            sql, count=1, flags=re.IGNORECASE
        )
    return sql
