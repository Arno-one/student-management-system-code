# 把“自然语言问题”变成“可执行 SQL”：这个学生管理系统里的 NL2SQL 模块是怎么设计的

> 这篇文章不是泛泛而谈的“NL2SQL 原理介绍”，而是**完全基于你这个项目当前代码**做的实现拆解。  
> 我会按“请求从前端进来，到 SQL 执行完再回前端”的顺序，把模块的设计思路、调用链、关键代码、当前优点和现阶段边界都讲清楚。

---

## 一、先说结论：这个模块的本质是什么？

这个项目里的 NL2SQL，不是“让大模型随便写一条 SQL 然后直接执行”那么简单。

它的真实设计思路是下面这条链：

```text
用户输入中文问题
    ↓
前端调用 /nl2sql/query
    ↓
FastAPI 路由接收请求 + 权限校验
    ↓
Service 编排层统一串联整个流程
    ↓
Prompt Builder 组装提示词
    ↓
Schema Context 动态注入数据库结构信息
    ↓
调用 DeepSeek 生成 SQL
    ↓
SQL 格式化
    ↓
SQL 安全校验
    ↓
自动补全 is_deleted = 0
    ↓
EXPLAIN 语法检查
    ↓
只读数据库连接执行 SQL
    ↓
结果转 JSON
    ↓
写入 NL2SQL 会话/消息历史
    ↓
返回前端展示 SQL + 查询结果 + 耗时 + 缓存状态
```

一句话概括：

> **这是一个“以大模型生成为起点，以安全校验和只读执行为护栏”的 NL2SQL 查询流水线。**

---

## 二、当前项目里，哪些文件真正参与了 NL2SQL？

如果只看当前正式接入主应用的实现链路，核心文件就是这些：

### 后端

- `API/nl2sql_api.py`：NL2SQL 的 FastAPI 路由入口
- `service/nl2sql_service.py`：业务编排核心
- `NL2SQL/schema_context.py`：动态构建 Schema 上下文
- `NL2SQL/prompt_builder.py`：拼装发给大模型的 messages
- `NL2SQL/sql_validator.py`：SQL 安全校验与逻辑删除补全
- `NL2SQL/sql_executor.py`：只读执行 SQL
- `NL2SQL/sql_formatter.py`：SQL 美化
- `DAO/nl2sql_dao.py`：会话与消息持久化
- `model/NL2SQL.py`：会话 / 消息 ORM 模型
- `database.py`：读写连接 + 只读连接
- `config.py`：DeepSeek 和数据库配置
- `main.py`：注册 `/nl2sql` 路由

### 前端

- `frontend-vue/src/views/NL2SQLView.vue`：NL2SQL 页面
- `frontend-vue/src/api/index.js`：统一请求封装
- `frontend-vue/src/router/index.js`：前端路由注册
- `frontend-vue/src/components/Sidebar.vue`：左侧菜单入口

### 权限

- `util/rbac_auth_init.sql`：菜单权限 `nl2sql:page` 与操作权限 `nl2sql:use`

注意一点：

仓库里虽然还有 `LLM/ds_llm.py` 这种早期实验文件，但**当前主应用真正接入的正式实现**，是上面这套 `API -> service -> NL2SQL/* -> DAO/model -> frontend-vue` 链路。

---

## 三、从一次请求开始：NL2SQL 是怎么跑起来的？

我们直接顺着真实请求链看。

---

### 1）入口层：FastAPI 路由负责接请求、做权限控制、绑定数据库依赖

代码位置：`API/nl2sql_api.py:27`

关键代码如下：

```python
@nl2sql_router.post("/query", summary="NL2SQL 智能问数", dependencies=[Depends(require_permission('nl2sql:use'))])
def nl2sql_query(
    req: QueryRequest,
    current_user: dict = Depends(get_current_user),
    db_rw: Session = Depends(get_db),
    db_readonly: Session = Depends(get_db_readonly),
):
    logger.info("NL2SQL 查询请求 | user=%s | question=%s", current_user['username'], req.question[:100])
    return query(
        question=req.question,
        user_id=current_user['username'],
        db_readonly=db_readonly,
        db_rw=db_rw,
        session_id=req.session_id,
    )
```

这一层做了 4 件事：

1. **权限控制**：必须拥有 `nl2sql:use` 才能发起自然语言问数。  
2. **读取当前登录用户**：不是相信前端传来的 user_id，而是从登录态里拿 `current_user['username']`。  
3. **同时注入两套数据库会话**：
   - `db_rw`：读写，用来保存会话和历史消息
   - `db_readonly`：只读，用来执行最终 SQL
4. **把真正业务处理转交给 `service.nl2sql_service.query()`**。

这里有一个非常值得肯定的设计点：

> 虽然 `QueryRequest` 里保留了 `user_id` 字段，但真正落库用的是当前登录用户，不给前端伪造身份的机会。

这说明这个模块在“谁发起查询”这件事上，是按认证上下文来做隔离的，而不是信任前端传参。

---

### 2）编排层：`service/nl2sql_service.py` 才是整条流水线的大脑

代码位置：`service/nl2sql_service.py:63`

这是最核心的函数：

```python
def query(question: str, user_id: str, db_readonly, db_rw,
          session_id: int | None = None) -> dict:
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
            result=None,
            cached_result_json=cached["result_json"],
            cost_ms=0,
            is_cached=True,
        )

    # ---- 2. 调用 LLM 生成 SQL ----
    sql, cost_ms = _call_llm(question)

    if not sql or sql.upper().strip() == "UNSUPPORTED":
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
        return {"code": 400, "msg": f"生成的 SQL 未通过安全校验: {err_msg}", "data": None}

    # ---- 5. 自动补全 is_deleted ----
    sql = ensure_is_deleted(sql)

    # ---- 6. 语法校验（EXPLAIN） ----
    syntax_ok, syntax_err = check_syntax(sql, db_readonly)
    if not syntax_ok:
        return {"code": 400, "msg": f"SQL 语法错误: {syntax_err}", "data": None}

    # ---- 7. 执行 SQL ----
    try:
        result = execute(sql, db_readonly)
    except SqlExecutionError as e:
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
```

这段代码非常像一条“工厂流水线”：

- 先看缓存
- 再调大模型
- 再做格式化
- 再做安全检查
- 再补全逻辑删除条件
- 再做 EXPLAIN
- 再执行
- 最后入库并返回

也就是说，这个模块不是“到处散着写逻辑”，而是明显采用了：

> **Service 层统一编排，工具模块各司其职**

这是一个非常清晰的后端组织方式。

---

## 四、为什么这套设计能让大模型“知道库里有什么表”？答案在 Schema Context

NL2SQL 最怕什么？

最怕模型瞎编表名、瞎编字段、瞎猜关联关系。

所以这个项目没有把提示词写成一句空泛的“请帮我生成 SQL”，而是专门做了一个 **Schema 上下文构建器**。

代码位置：`NL2SQL/schema_context.py:129`

它做的事情可以概括成四层：

1. **动态反射数据库表结构**
2. **补充中文业务注释**
3. **补充关键 JOIN 路径**
4. **补充枚举值和聚合口径**

### 1）先看它排除了什么

```python
EXCLUDE_TABLES = {
    "talk_session", "talk_message",
    "nl2sql_session", "nl2sql_message",
}
```

这一步很重要。

它不让模型看到内部会话表、聊天表，避免模型把系统内部表也当作业务数据源去查询。

### 2）再看它手工补充的业务语义

```python
TABLE_COMMENTS = {
    "student":        "学生基本信息表",
    "class_info":     "班级信息表",
    "student_score":  "学生考核成绩表",
    "employment":     "学生就业信息表",
    "teacher":        "教师信息表",
}
```

以及字段注释：

```python
FIELD_COMMENTS = {
    "student.student_no":        "学号（唯一标识）",
    "student.class_id":          "所属班级ID → class_info.id",
    "student_score.student_no":  "学号 → student.student_no",
    "employment.student_no":     "学生编号 → student.student_no（唯一）",
    "teacher.class_id":          "所带班级ID → class_info.id",
}
```

这里的设计很实用：

> 反射可以拿到“结构”，但拿不到“语义”；于是项目用手工字典把业务含义补了进去。

这会大幅提高模型选表、选字段、写 JOIN 的准确性。

### 3）它还额外标出了关键 JOIN 路径

```python
EXTRA_JOIN_PATHS = [
    {"left": "student.class_id",       "right": "class_info.id",             "note": "学生所属班级"},
    {"left": "student.student_no",     "right": "student_score.student_no",  "note": "学生成绩（一对多）"},
    {"left": "student.student_no",     "right": "employment.student_no",     "note": "学生就业信息（一对一）"},
    {"left": "teacher.class_id",       "right": "class_info.id",             "note": "教师所带班级"},
]
```

这其实是在告诉模型：

- 学生成绩要通过 `student.student_no = student_score.student_no` 连
- 学生就业要通过 `student.student_no = employment.student_no` 连
- 班级与学生、教师怎么连

这一步本质上是在替模型缩小搜索空间。

### 4）最后再把这些信息拼成大块 schema 文本

```python
def build_schema_text() -> str:
    insp = inspect(engine)
    all_tables = insp.get_table_names()
    business_tables = [t for t in all_tables if t not in EXCLUDE_TABLES]

    sections = []

    for table_name in business_tables:
        table_comment = TABLE_COMMENTS.get(table_name, "")
        sections.append(f"## {table_name}  —  {table_comment}")

        columns = insp.get_columns(table_name)
        for col in columns:
            sections.append(_format_column(col, table_name))

        fks = insp.get_foreign_keys(table_name)
        if fks:
            sections.append("  --- 外键 ---")
            for fk in fks:
                sections.append(_format_fk(fk, table_name))

        sections.append("")

    sections.append("## 跨表 JOIN 路径（关键关联）")
    for jp in EXTRA_JOIN_PATHS:
        sections.append(f"  {jp['left']}  ↔  {jp['right']}  — {jp['note']}")

    return "\n".join(sections)
```

这个函数的核心思想是：

> **每次都从当前数据库实时反射结构，再叠加人工补充的业务知识，最终生成给 LLM 使用的“数据库说明书”。**

这也是整个模块最关键的一环。

---

## 五、Prompt 是怎么设计的？它并不是一句话

代码位置：`NL2SQL/prompt_builder.py:5`

项目里的提示词设计，不是只有一个 system prompt，而是：

- 一个系统角色说明
- 一份数据库结构说明书
- 一组 few-shot 示例
- 最后再追加用户真实问题

### 1）System Prompt：先把“边界”钉死

```python
SYSTEM_PROMPT = """你是一个 MySQL 查询专家。根据给定的数据库表结构，将用户的自然语言问题转换为一条合法的 MySQL SELECT 语句。

【硬性规则 — 必须遵守】
1. 只生成 SELECT 语句，禁止 INSERT / UPDATE / DELETE / DROP / ALTER / TRUNCATE / CREATE
2. 所有涉及业务表的查询，WHERE 条件中必须加入对应表的 is_deleted=0（逻辑删除过滤）
3. 只返回纯 SQL 语句，不要任何解释、注释、markdown 代码块标记
4. 如果问题无法转换为 SQL（与数据查询无关），只返回一个词：UNSUPPORTED
5. 字段名和表名必须与【数据库表结构】中列出的完全一致，不得臆造
6. 查询结果默认最多返回 100 行，除非用户明确指定数量
7. 如果用户问题含义模糊（如"成绩最好"可能指最高分/平均分最高），默认按合理的聚合口径处理
"""
```

这段提示词里最核心的，不是“你是 MySQL 专家”，而是后面那几条约束：

- 只能 SELECT
- 必须加 `is_deleted=0`
- 不允许解释文字
- 不会答就返回 `UNSUPPORTED`
- 不准臆造字段

这说明作者对这个模块的定位很清楚：

> 大模型不是聊天机器人，而是一个**受强约束的 SQL 生成器**。

### 2）Few-shot 示例：教模型学会你项目里的问法

```python
FEW_SHOT_EXAMPLES = [
    {
        "question": "张三的平均成绩是多少？",
        "sql": "SELECT s.student_name, AVG(ss.score) AS avg_score FROM student s JOIN student_score ss ON s.student_no = ss.student_no WHERE s.student_name = '张三' AND s.is_deleted = 0 AND ss.is_deleted = 0 GROUP BY s.student_name"
    },
    {
        "question": "每个班级有多少学生？",
        "sql": "SELECT ci.class_name, COUNT(*) AS student_count FROM class_info ci JOIN student s ON ci.id = s.class_id WHERE ci.is_deleted = 0 AND s.is_deleted = 0 GROUP BY ci.id, ci.class_name"
    },
    {
        "question": "就业薪资最高的前5名学生是谁？",
        "sql": "SELECT s.student_name, e.salary, e.company_name FROM student s JOIN employment e ON s.student_no = e.student_no WHERE s.is_deleted = 0 AND e.is_deleted = 0 ORDER BY e.salary DESC LIMIT 5"
    },
]
```

这套 few-shot 覆盖了：

- JOIN
- GROUP BY
- ORDER BY
- LIMIT
- 条件过滤
- 子查询
- 不可回答问题

也就是说，它不仅给模型看“数据库长什么样”，还给模型看“这个项目里，典型问题应该怎么翻译成 SQL”。

### 3）最终 message 的拼接方式

```python
def build_messages(question: str, schema_text: str | None = None) -> list[dict]:
    if schema_text is None:
        schema_text = build_schema_text()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"【数据库表结构】\n{schema_text}"},
    ]

    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example["question"]})
        messages.append({"role": "assistant", "content": example["sql"]})

    messages.append({"role": "user", "content": question})
    return messages
```

这说明当前 Prompt 设计是典型的：

> **System + Schema + Few-shot + Real Question**

这是比“单条提示词”稳定得多的设计方式。

---

## 六、真正调用大模型的时候，做了哪些额外处理？

代码位置：`service/nl2sql_service.py:33`

```python
def _call_llm(question: str) -> tuple[str, int]:
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
    sql = _extract_sql(raw)
    logger.info("LLM 生成 SQL 耗时 %s ms，原始输出：%s", cost_ms, raw[:200])
    return sql, cost_ms
```

这里有两个值得注意的小细节：

### 1）它调用的是 OpenAI 兼容接口，但实际模型是 DeepSeek

```python
_client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

MODEL_NAME = "deepseek-v4-flash"
```

也就是说，这个模块不是直接绑死在 OpenAI 官方服务上，而是利用 OpenAI SDK 的兼容协议去请求 DeepSeek。

### 2）它专门处理了 Markdown 代码块污染

```python
def _extract_sql(raw: str) -> str:
    match = re.search(r'```(?:\w+)?\s*\n?(.*?)```', raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()
```

这很实用。

因为即使 system prompt 已经要求“只输出纯 SQL，不要 markdown 代码块”，模型在实际输出时还是可能返回：

```sql
SELECT ...
```

所以这里又补了一道兜底清洗。

这其实就是一个很典型的工程思路：

> **提示词要求是一层，后处理兜底是另一层。**

---

## 七、为什么这个模块相对安全？因为它不是只靠 Prompt

如果只是靠 system prompt 写一句“请只生成安全 SQL”，那其实不叫安全。

这个项目真正有价值的地方在于，它把安全做成了**分层护栏**。

我把它总结成“五道闸门”。

---

### 第一道闸门：Prompt 层约束

在 `SYSTEM_PROMPT` 里先告诉模型：

- 只能 SELECT
- 不准写 DROP / DELETE / UPDATE
- 必须带 `is_deleted=0`
- 无法回答就 `UNSUPPORTED`

这是一道软约束。

---

### 第二道闸门：代码层关键字校验

代码位置：`NL2SQL/sql_validator.py:21`

```python
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE",
    "REPLACE", "LOAD", "IMPORT", "GRANT", "REVOKE", "RENAME", "EXECUTE",
    "INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE", "SLEEP", "BENCHMARK",
]

ALLOWED_PREFIXES = ["SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN"]


def validate(sql: str) -> tuple[bool, str]:
    if not sql or not sql.strip():
        return False, "SQL 语句为空"

    sql_upper = sql.strip().upper()
    sql_clean = _strip_comments(sql_upper)

    if not any(sql_clean.startswith(prefix.upper()) for prefix in ALLOWED_PREFIXES):
        return False, f"不允许的语句类型。仅支持: {', '.join(ALLOWED_PREFIXES)}"

    for kw in FORBIDDEN_KEYWORDS:
        if _keyword_present(sql_clean, kw.upper()):
            return False, f"SQL 包含禁止的关键字: {kw}"

    if sql_clean.strip() == "UNSUPPORTED":
        return False, "该问题无法转换为 SQL 查询"

    return True, "ok"
```

这里做了几件事：

- 去掉注释再检查
- 限制语句前缀
- 拦截危险关键字
- 拦截 `UNSUPPORTED`

注意：

这个校验器现在**确实做到了只读防护和危险关键词拦截**，但它**还没有真正实现字段名 / 表名白名单校验**。  
虽然 `NL2SQL_todo_list.md` 里写了这个方向，但当前正式代码里并没有走到那一步。

这意味着：

> 目前的安全是“够用的工程护栏”，但还不是“最严格的白名单解析器”。

---

### 第三道闸门：自动补全 `is_deleted = 0`

代码位置：`NL2SQL/sql_validator.py:49`

```python
def ensure_is_deleted(sql: str) -> str:
    tables_in_query = _extract_table_aliases(sql)

    for table_name, alias in tables_in_query.items():
        if table_name not in BUSINESS_TABLES:
            continue
        col_ref = f"{alias}.is_deleted" if alias else f"{table_name}.is_deleted"
        if col_ref.lower() in sql.lower():
            continue

        sql = _append_condition(sql, f"{col_ref} = 0")

    return sql
```

这个设计非常贴合你项目的数据特点。

因为项目里的很多表都有逻辑删除字段，所以即使模型忘了加，后端也会自动补上。

这等于把“逻辑删除过滤”从提示词约束，提升成了**程序强制约束**。

---

### 第四道闸门：执行前先 `EXPLAIN`

代码位置：`NL2SQL/sql_validator.py:69`

```python
def check_syntax(sql: str, db) -> tuple[bool, str]:
    try:
        from sqlalchemy import text
        db.execute(text(f"EXPLAIN {sql}"))
        return True, "ok"
    except Exception as e:
        return False, f"SQL 语法错误: {e}"
```

这一步的价值在于：

- 先检查语法
- 不直接把错误 SQL 跑到真实查询里
- 能把语法问题拦在执行前

这是一个很典型的“执行前预检”思路。

---

### 第五道闸门：只读数据库连接 + 超时 + 行数上限

代码位置：`database.py:18` 和 `NL2SQL/sql_executor.py:17`

只读连接：

```python
engine_readonly = create_engine(
    f'mysql+pymysql://{_readonly_user}:{_readonly_password}@{host}:{port}/{database}',
    pool_size=3,
    execution_options={"isolation_level": "READ COMMITTED"}
)
```

SQL 执行器：

```python
def execute(sql: str, db) -> dict:
    sql_with_timeout = sql.strip()
    if sql_with_timeout.upper().startswith("SELECT"):
        sql_with_timeout = f"SELECT /*+ MAX_EXECUTION_TIME({QUERY_TIMEOUT_SECONDS * 1000}) */ " + sql_with_timeout[6:]

    if "LIMIT" not in sql_with_timeout.upper():
        sql_with_timeout += f" LIMIT {MAX_ROWS}"

    result = db.execute(text(sql_with_timeout))
```

这里又是三层限制：

1. **数据库账号层面只读**：哪怕代码层漏了，数据库权限也是最后一道底线
2. **超时保护**：最长 10 秒
3. **结果上限**：默认最多 1000 行

注意这个地方还有一个很值得记录的细节：

- Prompt 里写的是“默认最多返回 100 行”
- 执行器里真正兜底加的是 `LIMIT 1000`

也就是说：

> **模型侧期望上限是 100，后端硬性执行上限是 1000。**

这两个数字当前并不完全一致。

---

## 八、查询结果是怎么持久化的？

这个模块不是一次性问完就丢，它把历史会话和消息都存进了数据库。

### 1）数据模型

代码位置：`model/NL2SQL.py:6`

```python
class Nl2sqlSession(Base):
    __tablename__ = "nl2sql_session"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    user_id = Column(String(100), nullable=False, index=True, comment="用户标识（对话隔离）")
    title = Column(String(200), default="新对话", comment="会话标题")
    is_deleted = Column(Integer, nullable=False, default=0, comment="逻辑删除 0-未删 1-已删")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class Nl2sqlMessage(Base):
    __tablename__ = "nl2sql_message"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    session_id = Column(Integer, ForeignKey("nl2sql_session.id"), nullable=False, index=True, comment="所属会话ID")
    question = Column(Text, nullable=False, comment="用户自然语言问题")
    generated_sql = Column(Text, default=None, comment="大模型生成的SQL语句")
    result_json = Column(Text, default=None, comment="查询结果JSON")
    cost_ms = Column(Integer, default=None, comment="LLM调用耗时（毫秒）")
    is_cached = Column(Integer, default=0, comment="是否命中缓存 0-否 1-是")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
```

这个设计很直观：

- `nl2sql_session`：一组对话
- `nl2sql_message`：每一次提问与对应 SQL / 结果

也就是说，当前项目把 NL2SQL 的历史，建模成了一个轻量版“问答会话系统”。

### 2）会话和消息的写入逻辑

代码位置：`service/nl2sql_service.py:155`

```python
def _save_message(db_rw, session_id: int | None, user_id: str,
                  question: str, sql: str, result_json: str,
                  cost_ms: int, is_cached: int):
    from DAO.nl2sql_dao import create_session, add_message, touch_session
    if session_id is None:
        session = create_session(user_id, title=question[:30], db=db_rw)
        session_id = session.id
    else:
        touch_session(session_id, db_rw)
    add_message(session_id, question, sql, result_json, cost_ms, is_cached, db=db_rw)
```

它的策略是：

- 如果没有 `session_id`，就新建一个会话
- 如果有 `session_id`，就刷新会话更新时间
- 每一轮都新增一条 message

这个结构本身已经具备“多轮追问”的基础能力。

但是要注意：

> **后端虽然接收 `session_id`，前端当前并没有在 `doQuery()` 里把 `session_id` 继续传回去。**

所以当前用户体验上更接近：

- 有历史记录
- 但还不是真正的“连续追问式上下文问数”

这点是“数据结构已就绪，前端交互还没完全跟上”。

---

## 九、前端页面是怎么设计的？

代码位置：`frontend-vue/src/views/NL2SQLView.vue:1`

这个页面没有只做一个输入框，而是拆成了三个子模块：

1. **智能问数**
2. **表结构概览**
3. **历史记录**

这其实是一个挺好的产品化设计，因为它不仅能“问”，还能“教用户怎么问”。

---

### 1）智能问数区

核心查询代码：`frontend-vue/src/views/NL2SQLView.vue:191`

```javascript
async function doQuery() {
  if (!form.question.trim()) return
  loading.value = true
  queryResult.sql = ''
  queryResult.columns = null
  queryResult.tableData = null
  queryResult.meta = null
  setResult('query', null, '运行中')

  try {
    const r = await request('POST', '/nl2sql/query', {
      body: { question: form.question.trim(), user_id: form.userId }
    })
    if (r.ok && r.data?.code === 200) {
      const d = r.data.data
      queryResult.sql = d.sql || ''
      queryResult.columns = d.columns || []
      queryResult.rows = d.rows || []
      queryResult.rowCount = d.row_count || 0
      queryResult.meta = { cost: d.cost_ms, cached: d.is_cached }

      if (d.columns && d.rows) {
        queryResult.tableData = [d.columns, ...d.rows]
      }
      setResult('query', true, '查询成功')
      await nextTick()
      highlightSql()
    } else {
      setResult('query', false, r.data?.msg || '查询失败')
    }
  } catch (e) {
    setResult('query', false, `网络错误: ${e.message}`)
  } finally {
    loading.value = false
  }
}
```

前端在这里完成了：

- 发起查询
- 接收 SQL / columns / rows / row_count / cost_ms / is_cached
- 把二维结果组装成表格数据
- 查询成功后再调用 `highlightSql()` 高亮 SQL

还有一个小体验点：它提供了示例问题按钮：

```javascript
const exampleQuestions = [
  '每个班级有多少学生？',
  '就业薪资最高的前5名学生是谁？',
  '张三的平均成绩是多少？',
  '有哪些学生成绩不及格？',
  '列出每个班级的班主任姓名',
]
```

这能显著降低用户第一次使用时的理解成本。

---

### 2）SQL 高亮展示

```javascript
import hljs from 'highlight.js/lib/core'
import sql from 'highlight.js/lib/languages/sql'

hljs.registerLanguage('sql', sql)

function highlightSql() {
  if (sqlCodeRef.value) {
    sqlCodeRef.value.innerHTML = hljs.highlight(queryResult.sql, { language: 'sql' }).value
  }
}
```

也就是说，后端负责：

- 结构化格式化 SQL

前端负责：

- 语法着色
- 复制 SQL
- 美观展示

这个职责拆分是合理的。

---

### 3）表结构概览区

前端不是直接渲染后端返回的 `tables` 字段，而是把 `schema` 那段文本再次解析成结构化展示。

代码位置：`frontend-vue/src/views/NL2SQLView.vue:272`

```javascript
function parseSchema(data) {
  const tables = []
  const text = data.schema || ''
  const sections = text.split(/\n## /)

  for (const sec of sections) {
    const lines = sec.trim().split('\n')
    const header = lines[0].trim()
    if (!header) continue

    const nameParts = header.split('—').map(s => s.trim())
    const tableName = nameParts[0] || header
    const tableComment = nameParts[1] || ''

    const fields = []
    for (const line of lines.slice(1)) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('---') || trimmed.startsWith('FOREIGN')) continue
      const parts = trimmed.split(/\s{2,}/)
      if (parts.length >= 1) {
        const fieldName = parts[0].trim()
        const fieldType = parts.length >= 2 ? parts[1].trim() : ''
        const fieldComment = trimmed.includes('--') ? trimmed.split('--').pop().trim() : ''
        fields.push({ name: fieldName, type: fieldType, comment: fieldComment })
      }
    }
    if (fields.length > 0) {
      tables.push({ name: tableName, comment: tableComment, fields })
    }
  }

  return { tables }
}
```

这一段说明了当前 Schema 接口的设计其实是：

- 后端把 schema 主要作为“大块说明文本”返回
- 前端再从这块文本里解析出表和字段

它的优点是开发快、调试方便；但代价是：

> 前后端对文本格式形成了隐式耦合。

只要后端 `build_schema_text()` 的格式变了，前端这个解析器就可能跟着失效。

---

### 4）历史记录区

历史接口代码位置：`API/nl2sql_api.py:68`

```python
@nl2sql_router.get("/sessions", summary="获取 NL2SQL 历史会话", dependencies=[Depends(require_permission('nl2sql:use'))])
def nl2sql_sessions(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user['username']
    from DAO.nl2sql_dao import get_sessions_by_user, get_messages_by_session
    sessions = get_sessions_by_user(user_id, db)
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
```

前端加载历史：

```javascript
async function loadHistory() {
  const r = await request('GET', '/nl2sql/sessions?user_id=' + encodeURIComponent(form.userId))
  if (r.ok && r.data?.code === 200) {
    historySessions.value = r.data.data || []
  }
}
```

这里有个很有意思的实现现状：

- 前端会带 `user_id`
- 但后端实际上**忽略 query string 里的 user_id**
- 后端只认当前登录用户

这依然是一个偏安全的选择。

不过页面里的提示文案写着：

> “点击可重新加载结果”

但当前模板里其实**还没有绑定点击某条历史记录就回填结果**的事件逻辑。  
也就是说，这块现在更像“历史展示”，还不是“历史复用”。

---

## 十、缓存是怎么做的？它解决了什么问题？

代码位置：`service/nl2sql_service.py:21`

```python
_cache: dict[str, dict] = {}


def normalize_question(question: str) -> str:
    return re.sub(r'\s+', '', question.strip())
```

它现在的缓存策略很直接：

- 把问题去空白后作为 key
- value 存 `sql` 和 `result_json`
- 命中后不再调用 LLM

命中逻辑：

```python
cached = _cache.get(norm)
if cached:
    _save_message(
        db_rw, session_id, user_id, question,
        cached["sql"], cached["result_json"],
        cost_ms=0, is_cached=1,
    )
```

这说明当前缓存的目标非常明确：

1. **降本**：少调一次 LLM
2. **提速**：秒回历史问题
3. **可追踪**：虽然走缓存，但依然会在消息表里记录一条 `is_cached=1` 的历史

不过要实话实说：

> 这个缓存目前只是**进程内内存缓存**，不是 Redis，也不是数据库持久缓存。

所以只要服务重启，缓存就会消失。

这和 README 里“缓存记录已持久化到 MySQL”这种表述并不完全一致。  
更准确地说：

- **查询历史**被持久化了
- **缓存命中结果**会记录在历史消息里
- 但**真正的缓存容器**仍然只是内存字典 `_cache`

---

## 十一、这套设计有哪些明显优点？

如果站在工程实现角度看，这个 NL2SQL 模块有几个优点很突出。

### 1）职责拆分清楚

不是所有逻辑都堆在一个文件里，而是拆成：

- schema 构建
- prompt 组装
- SQL 校验
- SQL 执行
- SQL 格式化
- service 编排
- DAO 持久化

这样的结构非常利于后续维护。

### 2）安全不是只靠 Prompt

它用了：

- Prompt 约束
- 关键字校验
- `is_deleted` 自动补全
- EXPLAIN 检查
- 只读连接
- 超时与行数限制

这已经属于比较像样的防护链了。

### 3）Schema 是动态反射的

这意味着数据库字段变了，只要不破坏业务语义字典，这个模块就能较自然地跟上结构变化。

### 4）兼顾了“能问”和“知道怎么问”

页面不只有问答，还包含：

- 示例问题
- 表结构概览
- 历史记录

这比只给一个输入框要成熟得多。

### 5）历史会话模型已经为多轮能力打基础

虽然前端还没把多轮追问真正接通，但后端 `session_id`、`nl2sql_session`、`nl2sql_message` 这些基础设施已经有了。

---

## 十二、当前实现有哪些边界和可以继续改进的地方？

这一部分我尽量写得诚实一点，不吹过头。

### 1）“多轮对话”还没有真正跑通

后端有 `session_id`，数据库也有 session/message 表，**但 Prompt 里并没有注入历史问答上下文**，前端当前也没有持续传 `session_id`。

所以现在更准确的描述应该是：

> **这是“带历史留痕的单轮 NL2SQL”，不是严格意义上的上下文追问式 NL2SQL。**

### 2）表名/字段名白名单校验还没真正落地

`sql_validator.py` 目前主要是：

- 前缀限制
- 危险关键字拦截
- `is_deleted` 补全
- `EXPLAIN`

但它还没有把 SQL 解析成 AST，再严格校验“所有表名/字段名都必须在业务白名单里”。

### 3）Schema 接口返回文本，前端再反解析，耦合偏强

当前做法开发快，但长期看更稳的方式应该是：

- 后端直接返回结构化 schema JSON
- 前端直接渲染

这样会比“文本 -> 再拆回来”更可靠。

### 4）Prompt 上限和执行器上限不一致

- Prompt：默认最多 100 行
- 执行器：无 LIMIT 时自动补 1000

这个口径建议后续统一。

### 5）缓存还只是单实例内存缓存

现在 `_cache = {}` 只能覆盖：

- 当前进程
- 当前服务实例

如果服务重启，或者以后变成多实例部署，这个缓存就不共享了。

### 6）历史记录展示和“历史复用”还差一步

页面提示用户“点击可重新加载结果”，但当前代码还没有真正实现点击某条历史记录后把 SQL / 结果回填到当前展示区的逻辑。

---

## 十三、如果用架构语言总结，这个模块到底是怎么设计的？

如果让我用一句更像“系统设计说明”的话来总结，它是这样的：

> 这个项目中的 NL2SQL 模块，采用了 **Schema-aware Prompting + 分层安全校验 + 只读数据库执行 + 会话化历史持久化** 的设计思路：先通过数据库反射与业务注释构造结构化上下文，再借助 few-shot 与强约束 prompt 生成 SQL，随后通过格式化、危险关键字拦截、逻辑删除补全、EXPLAIN 校验与只读连接执行形成防线，最终将结果和生成 SQL 返回前端并写入会话历史。

这个总结基本能覆盖它的核心设计哲学。

---

## 十四、关键源码速查清单

如果你后面自己要继续讲、继续改、继续答辩，最值得优先看的就是这些位置：

- 路由入口：`API/nl2sql_api.py:27`
- 查询主流程：`service/nl2sql_service.py:63`
- 调用大模型：`service/nl2sql_service.py:33`
- Prompt 组装：`NL2SQL/prompt_builder.py:60`
- Schema 动态构建：`NL2SQL/schema_context.py:129`
- SQL 校验：`NL2SQL/sql_validator.py:21`
- 自动补全 `is_deleted`：`NL2SQL/sql_validator.py:49`
- SQL 执行：`NL2SQL/sql_executor.py:17`
- 会话与消息模型：`model/NL2SQL.py:6`
- 前端查询逻辑：`frontend-vue/src/views/NL2SQLView.vue:191`
- 前端 Schema 解析：`frontend-vue/src/views/NL2SQLView.vue:272`
- 前端历史加载：`frontend-vue/src/views/NL2SQLView.vue:318`

---

## 十五、最后一句话

如果只看当前落地程度，这个 NL2SQL 模块已经不是“玩具 demo”了。

它已经具备了一个可用原型最关键的几个能力：

- 能基于真实表结构生成 SQL
- 有基础安全护栏
- 有只读执行隔离
- 有查询历史
- 有前端产品化页面

但它也还保留着明显的下一阶段演进空间：

- 真正多轮追问
- 更严格的 SQL 白名单/AST 校验
- Redis 级缓存
- 结构化 schema API
- 历史记录回填复用

所以最准确的评价应该是：

> **它已经是一个“有工程化骨架的 NL2SQL 第一版”，而不是简单的 prompt demo。**

---

## 附录：我这次分析时确认过的核心代码来源

- `API/nl2sql_api.py`
- `service/nl2sql_service.py`
- `NL2SQL/schema_context.py`
- `NL2SQL/prompt_builder.py`
- `NL2SQL/sql_validator.py`
- `NL2SQL/sql_executor.py`
- `NL2SQL/sql_formatter.py`
- `DAO/nl2sql_dao.py`
- `model/NL2SQL.py`
- `database.py`
- `config.py`
- `frontend-vue/src/views/NL2SQLView.vue`
- `frontend-vue/src/api/index.js`
- `frontend-vue/src/router/index.js`
- `frontend-vue/src/components/Sidebar.vue`
- `util/rbac_auth_init.sql`
- `NL2SQL_todo_list.md`

如果你愿意，我下一步还可以继续帮你做两件事里的任意一种：

1. 把这篇文档再升级成**更正式的课程报告 / 项目答辩文档版**  
2. 按这篇分析继续补一版**“NL2SQL 模块时序图 + 架构图 + 数据表关系图”**