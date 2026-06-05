"""
Schema 上下文构建器：动态反射数据库表结构 + 中文注释字典，为 LLM 生成 SQL 提供准确的"数据地图"。
"""
from sqlalchemy import inspect
from database import engine

# ---- 反射时排除的内部表（非业务域） ----
EXCLUDE_TABLES = {
    "talk_session", "talk_message",
    "nl2sql_session", "nl2sql_message",
}

# ---- 业务表中文名 ----
TABLE_COMMENTS = {
    "student":        "学生基本信息表",
    "class_info":     "班级信息表",
    "student_score":  "学生考核成绩表",
    "employment":     "学生就业信息表",
    "teacher":        "教师信息表",
}

# ---- 字段中文含义（反射拿不到的语义信息） ----
FIELD_COMMENTS = {
    # student
    "student.id":                "学生主键ID",
    "student.student_no":        "学号（唯一标识）",
    "student.class_id":          "所属班级ID → class_info.id",
    "student.student_name":      "学生姓名",
    "student.gender":            "性别",
    "student.age":               "年龄",
    "student.native_place":      "籍贯",
    "student.graduate_school":   "毕业院校",
    "student.major":             "专业",
    "student.education":         "学历",
    "student.admission_time":    "入学时间",
    "student.graduate_time":     "毕业时间",
    "student.advisor_id":        "顾问编号",
    "student.is_deleted":        "逻辑删除标记（0=有效 1=已删）",
    "student.create_time":       "创建时间",
    "student.update_time":       "更新时间",
    # class_info
    "class_info.id":             "班级主键ID",
    "class_info.class_code":     "班级编号（唯一）",
    "class_info.class_name":     "班级名称",
    "class_info.start_time":     "开班时间",
    "class_info.is_deleted":     "逻辑删除标记（0=有效 1=已删）",
    "class_info.create_time":    "创建时间",
    "class_info.update_time":    "更新时间",
    # student_score
    "student_score.id":          "成绩主键ID",
    "student_score.student_no":  "学号 → student.student_no",
    "student_score.exam_order":  "考核序次",
    "student_score.score":       "学生成绩（DECIMAL 5,1）",
    "student_score.is_deleted":  "逻辑删除标记（0=有效 1=已删）",
    "student_score.create_time": "创建时间",
    "student_score.update_time": "更新时间",
    # employment
    "employment.id":             "就业信息主键ID",
    "employment.student_no":     "学生编号 → student.student_no（唯一）",
    "employment.student_name":   "学生姓名（冗余）",
    "employment.class_id":       "班级ID（冗余）",
    "employment.job_open_time":  "就业开放时间",
    "employment.offer_send_time":"Offer发送时间",
    "employment.company_name":   "就业公司",
    "employment.salary":         "就业薪资（整数）",
    "employment.is_deleted":     "逻辑删除标记（0=有效 1=已删）",
    "employment.create_time":    "创建时间",
    "employment.update_time":    "更新时间",
    # teacher
    "teacher.id":                "教师主键ID",
    "teacher.name":              "教师姓名",
    "teacher.gender":            "性别（枚举: man=1, woman=2）",
    "teacher.birth_date":        "出生日期",
    "teacher.phone":             "联系电话",
    "teacher.email":             "邮箱",
    "teacher.title":             "职务",
    "teacher.class_id":          "所带班级ID → class_info.id",
    "teacher.hire_date":         "入职日期",
    "teacher.is_deleted":        "逻辑删除标记（0=有效 1=已删）",
    "teacher.create_time":       "创建时间",
    "teacher.update_time":       "更新时间",
}

# ---- 手动标注的 JOIN 路径（外键之外的关键关联） ----
# 外键反射只能拿到有显式 FK 约束的关系，以下补充所有常用跨表关联路径。
EXTRA_JOIN_PATHS = [
    {"left": "student.class_id",       "right": "class_info.id",          "note": "学生所属班级"},
    {"left": "student.student_no",     "right": "student_score.student_no", "note": "学生成绩（一对多）"},
    {"left": "student.student_no",     "right": "employment.student_no",    "note": "学生就业信息（一对一）"},
    {"left": "teacher.class_id",       "right": "class_info.id",            "note": "教师所带班级"},
    {"left": "class_info.id",          "right": "student.class_id",         "note": "班级下的学生"},
    {"left": "class_info.id",          "right": "teacher.class_id",         "note": "班级下的教师"},
]

# ---- 枚举值与字典映射 ----
ENUM_MAP = {
    "student.gender":   "取值含义：无明确枚举约束，常见值为 '男' / '女'",
    "teacher.gender":   "取值含义：man=男(1)，woman=女(2)；该字段为枚举类型",
    "teacher.title":    "常见职务：班主任、讲师、副教授、教授、辅导员等",
    "student.education": "常见学历：本科、硕士、博士、大专等",
}

# ---- 聚合口径默认值 ----
AGG_DEFAULTS = {
    "成绩排名":   "默认按平均分 DESC 排序",
    "学生人数":   "COUNT(DISTINCT student_no)",
    "及格标准":   "score >= 60 为及格",
    "优秀标准":   "score >= 90 为优秀",
}


def _format_column(col, table_name: str) -> str:
    """格式化单个字段为一行描述"""
    name = col["name"]
    col_type = str(col["type"])
    nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
    pk = " [PK]" if col.get("primary_key") else ""
    comment = FIELD_COMMENTS.get(f"{table_name}.{name}", "")
    return f"  {name}  {col_type}  {nullable}{pk}  -- {comment}"


def _format_fk(fk, table_name: str) -> str:
    """格式化一个外键为一行描述"""
    cols = ", ".join(fk["constrained_columns"])
    ref_table = fk["referred_table"]
    ref_cols = ", ".join(fk["referred_columns"])
    return f"  FOREIGN KEY ({cols}) → {ref_table}.{ref_cols}"


def build_schema_text() -> str:
    """
    动态反射数据库，构建结构化的 schema 说明书文本。
    每次调用都反射一次，保证与当前数据库结构实时同步。
    """
    insp = inspect(engine)
    all_tables = insp.get_table_names()
    business_tables = [t for t in all_tables if t not in EXCLUDE_TABLES]

    sections = []

    for table_name in business_tables:
        table_comment = TABLE_COMMENTS.get(table_name, "")
        sections.append(f"## {table_name}  —  {table_comment}")

        # 字段列表
        columns = insp.get_columns(table_name)
        for col in columns:
            sections.append(_format_column(col, table_name))

        # 外键
        fks = insp.get_foreign_keys(table_name)
        if fks:
            sections.append("  --- 外键 ---")
            for fk in fks:
                sections.append(_format_fk(fk, table_name))

        sections.append("")  # 空行分隔

    # JOIN 路径总览
    sections.append("## 跨表 JOIN 路径（关键关联）")
    for jp in EXTRA_JOIN_PATHS:
        sections.append(f"  {jp['left']}  ↔  {jp['right']}  — {jp['note']}")

    # 枚举值说明
    sections.append("")
    sections.append("## 枚举值与字典映射")
    for key, desc in ENUM_MAP.items():
        sections.append(f"  {key}: {desc}")

    # 聚合口径
    sections.append("")
    sections.append("## 聚合口径约定")
    for key, desc in AGG_DEFAULTS.items():
        sections.append(f"  {key}: {desc}")

    return "\n".join(sections)


def get_business_table_names() -> list[str]:
    """返回所有业务表名（用于安全校验白名单）"""
    insp = inspect(engine)
    return [t for t in insp.get_table_names() if t not in EXCLUDE_TABLES]


def get_business_column_names() -> list[str]:
    """返回所有业务字段名（格式: table.column，用于安全校验白名单）"""
    insp = inspect(engine)
    tables = get_business_table_names()
    result = []
    for t in tables:
        for col in insp.get_columns(t):
            result.append(f"{t}.{col['name']}")
    return result
