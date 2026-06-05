"""
SQL 美化器：用 sqlparse 对 LLM 生成的原始 SQL 做结构化格式化。
效果：关键字大写、子句换行、字段缩进对齐。
"""
import sqlparse


def format_sql(raw_sql: str) -> str:
    """
    格式化 SQL 语句。
    :param raw_sql: LLM 生成的原始 SQL（通常是单行或格式混乱的文本）
    :return: 格式化后的多行 SQL
    """
    if not raw_sql or raw_sql.strip() == "":
        return raw_sql

    sql = raw_sql.strip()

    # UNSUPPORTED 标记直接原样返回
    if sql.upper() == "UNSUPPORTED":
        return sql

    return sqlparse.format(
        sql,
        reindent=True,          # 重新缩进
        keyword_case="upper",   # 关键字大写
        indent_width=2,         # 缩进宽度 2 空格
        wrap_after=60,          # 单行超过 60 字符则换行
        comma_first=False,      # 逗号在行尾
    )


def format_sql_for_frontend(raw_sql: str) -> str:
    """
    格式化 SQL 并包裹在 <pre><code class="language-sql"> 中，供前端 highlight.js 渲染。
    前端需引入 highlight.js 的 SQL 语言包。
    """
    formatted = format_sql(raw_sql)
    return formatted
