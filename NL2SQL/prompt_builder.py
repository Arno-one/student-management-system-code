"""
Prompt 组装器：将 System Prompt + Schema 上下文 + Few-shot + 用户问题 拼装为发给 DeepSeek 的完整 messages。
"""
from NL2SQL.schema_context import build_schema_text

SYSTEM_PROMPT = """你是一个 MySQL 查询专家。根据给定的数据库表结构，将用户的自然语言问题转换为一条合法的 MySQL SELECT 语句。

【硬性规则 — 必须遵守】
1. 只生成 SELECT 语句，禁止 INSERT / UPDATE / DELETE / DROP / ALTER / TRUNCATE / CREATE
2. 所有涉及业务表的查询，WHERE 条件中必须加入对应表的 is_deleted=0（逻辑删除过滤）
3. 只返回纯 SQL 语句，不要任何解释、注释、markdown 代码块标记
4. 如果问题无法转换为 SQL（与数据查询无关），只返回一个词：UNSUPPORTED
5. 字段名和表名必须与【数据库表结构】中列出的完全一致，不得臆造
6. 查询结果默认最多返回 100 行，除非用户明确指定数量
7. 如果用户问题含义模糊（如"成绩最好"可能指最高分/平均分最高），默认按合理的聚合口径处理

【建议风格】
- 字段列表不要用 SELECT *，明确写出需要的字段
- 涉及多表查询时使用显式的 JOIN ... ON 语法
- 对可能产生歧义的列名使用别名（AS）"""

FEW_SHOT_EXAMPLES = [
    # ---- JOIN 关联 ----
    {
        "question": "张三的平均成绩是多少？",
        "sql": "SELECT s.student_name, AVG(ss.score) AS avg_score FROM student s JOIN student_score ss ON s.student_no = ss.student_no WHERE s.student_name = '张三' AND s.is_deleted = 0 AND ss.is_deleted = 0 GROUP BY s.student_name"
    },
    # ---- 聚合 + GROUP BY ----
    {
        "question": "每个班级有多少学生？",
        "sql": "SELECT ci.class_name, COUNT(*) AS student_count FROM class_info ci JOIN student s ON ci.id = s.class_id WHERE ci.is_deleted = 0 AND s.is_deleted = 0 GROUP BY ci.id, ci.class_name"
    },
    # ---- ORDER BY + LIMIT ----
    {
        "question": "就业薪资最高的前5名学生是谁？",
        "sql": "SELECT s.student_name, e.salary, e.company_name FROM student s JOIN employment e ON s.student_no = e.student_no WHERE s.is_deleted = 0 AND e.is_deleted = 0 ORDER BY e.salary DESC LIMIT 5"
    },
    # ---- 条件过滤 ----
    {
        "question": "有哪些学生成绩不及格？",
        "sql": "SELECT DISTINCT s.student_no, s.student_name, ss.score, ss.exam_order FROM student s JOIN student_score ss ON s.student_no = ss.student_no WHERE ss.score < 60 AND s.is_deleted = 0 AND ss.is_deleted = 0 ORDER BY ss.score ASC"
    },
    # ---- 子查询 ----
    {
        "question": "哪些学生的成绩高于全班平均分？",
        "sql": "SELECT s.student_no, s.student_name, AVG(ss.score) AS avg_score FROM student s JOIN student_score ss ON s.student_no = ss.student_no WHERE s.is_deleted = 0 AND ss.is_deleted = 0 GROUP BY s.student_no, s.student_name HAVING AVG(ss.score) > (SELECT AVG(score) FROM student_score WHERE is_deleted = 0)"
    },
    # ---- 多表 JOIN ----
    {
        "question": "列出每个班级的班主任姓名？",
        "sql": "SELECT ci.class_name, t.name AS teacher_name FROM class_info ci JOIN teacher t ON ci.id = t.class_id WHERE ci.is_deleted = 0 AND t.is_deleted = 0 AND t.title = '班主任'"
    },
    # ---- 不可回答的问题 ----
    {
        "question": "今天天气怎么样？",
        "sql": "UNSUPPORTED"
    },
]


def build_messages(question: str, schema_text: str | None = None) -> list[dict]:
    """
    组装完整的 messages 列表，可直接传给 DeepSeek / OpenAI client。
    :param question: 用户自然语言问题
    :param schema_text: 数据库结构上下文（不传则自动反射生成）
    """
    if schema_text is None:
        schema_text = build_schema_text()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"【数据库表结构】\n{schema_text}"},
    ]

    # 注入 Few-shot 示例
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example["question"]})
        messages.append({"role": "assistant", "content": example["sql"]})

    # 追加用户真实问题
    messages.append({"role": "user", "content": question})

    return messages
