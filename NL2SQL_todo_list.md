# NL2SQL 智能问数 — 开发任务清单

## 一、总览

本模块实现"用自然语言查询数据库"的能力。用户输入中文问题，系统通过 DeepSeek 大模型将其转换为 SQL 语句，经安全校验后在只读连接上执行，结果返回前端展示。

## 二、核心原则

- **纵深防御**：Prompt 约束 → 语法校验 → 只读数据库连接，三道防线
- **关注点分离**：NL2SQL 专用会话表独立于 Talk 模块
- **缓存优先**：相同问题命中缓存则跳过 LLM 调用，降本提速

## 三、任务清单

### P0 — 基础可用（单轮 NL2SQL）

- [x] **NL2SQL 专用会话表** — 新建 `nl2sql_session` 和 `nl2sql_message` ORM 模型
  - `nl2sql_session`: id, user_id, title, create_time, update_time, is_deleted
  - `nl2sql_message`: id, session_id, question, generated_sql, result_json, cost_ms, is_cached, create_time
  - 对应的 DAO 层增删改查方法
- [x] **MySQL 只读用户** — 创建 `nl2sql_reader` 账号，仅授予 SELECT 权限
- [x] **只读引擎** — 在 `database.py` 中新增 `engine_readonly` 和 `get_db_readonly()` 依赖
- [x] **Schema 上下文构建器** (`NL2SQL/schema_context.py`)
  - **动态反射为主**：调用 `inspect(engine)` 自动获取表名、字段名、字段类型、nullable、主键、外键
  - **注释字典为辅**：反射拿不到的中文含义和业务规则，用小配置字典映射（`field_comments`、`table_comments`）
  - 表间 JOIN 关系从外键反射自动推导，同时显式列出跨表关联路径
  - 业务规则注入（is_deleted=0、聚合口径默认值）
  - 枚举值与字典映射（gender、title 等）
  - 注意：反射时排除 NL2SQL 会话表自身及 Talk 相关表，仅暴露业务域表
- [x] **Prompt 组装器** (`NL2SQL/prompt_builder.py`)
  - System Prompt（角色定义 + 约束规则）
  - Schema 上下文注入
  - Few-shot 示例（覆盖 JOIN、聚合、GROUP BY、ORDER BY、LIMIT、子查询 六种模式）
  - 用户问题拼入
- [x] **SQL 安全校验器** (`NL2SQL/sql_validator.py`)
  - 语句类型检查：只允许 SELECT / SHOW / DESCRIBE / EXPLAIN
  - 禁止关键字拦截：DROP、DELETE、INSERT、UPDATE、ALTER、TRUNCATE、CREATE
  - 表名/字段名白名单校验（基于 Schema 上下文中声明的表和字段）
  - is_deleted=0 自动补充（涉及业务表时）
  - EXPLAIN 语法校验（不实际执行，仅验证语法正确性）
- [x] **SQL 执行器** (`NL2SQL/sql_executor.py`)
  - 使用只读引擎执行
  - 查询超时 10 秒
  - 结果集上限 1000 行
  - 结果转为统一 JSON 格式（columns + rows + row_count）
- [x] **SQL 美化器** (`NL2SQL/sql_formatter.py`)
  - 采用方案 A + C：后端 `sqlparse` 结构化格式化 + 前端 `highlight.js` 语法着色
  - sqlparse 格式化：关键字大写、每个子句另起一行、字段缩进对齐
  - 前端 highlight.js SQL 语言包：关键字蓝色、字符串绿色、数字橙色
- [x] **NL2SQL 业务编排** (`service/nl2sql_service.py`)
  - 串联：接收问题 → 查缓存 → 调 LLM → 校验 → 执行 → 存会话 → 返回
  - 问题-结果写入 `nl2sql_message` 持久化
- [x] **API 路由** (`API/nl2sql_api.py`)
  - `POST /nl2sql/query` — 单轮 NL2SQL 查询
  - `GET /nl2sql/schema` — 返回表结构概览（供前端展示"可以问什么"）
  - 遵循统一响应格式 `{code, msg, data, total}`
  - 在 `main.py` 中注册路由

### P1 — 体验提升（多轮追问 + 缓存）

- [ ] **问题-SQL 缓存** — 对相同问题（标准化后）命中缓存直接返回，跳过 LLM
- [ ] **多轮追问** — 支持上下文延续追问（"那李四呢？""按班级分呢？"），将上一轮 SQL 及结果摘要注入 prompt
- [ ] **前端推荐问题** — API 返回常用问题示例列表，降低用户上手门槛

### P2 — 鲁棒性与可视化

- [ ] **SQL 自修复** — 执行报错时将错误信息反馈 LLM 自动修正，最多重试 2 次
- [ ] **结果可视化** — 根据结果类型自动选择图表（柱状图/饼图/折线图），前端渲染
- [ ] **向量召回** — 历史问答做 embedding，新问题召回最相似 Few-shot 注入 prompt

### P3 — 运维与监控

- [ ] **调用成本统计** — 记录每次 LLM 调用的 token 消耗和费用
- [ ] **慢查询告警** — 执行超过 3 秒的 SQL 记录 WARNING 日志
- [ ] **问题审批** — 敏感问题（如涉及全体学生数据导出）需确认后执行

---

## 四、SQL 美化方案

**最终选型：A + C**

| 角色 | 方案 | 负责内容 |
|---|---|---|
| 后端 | A. sqlparse | 结构化格式化（缩进、关键字大写、子句换行） |
| 前端 | C. highlight.js | 视觉呈现（语法着色） |

已排除的方案及原因：

| 方案 | 排除原因 |
|---|---|
| B. sqlfmt | 额外依赖重，规则不可定制，中文注释支持弱 |
| D. Prompt 要求 | LLM 输出格式不稳定，不可控 |

---

## 五、新增/修改文件清单

```
新增:
  NL2SQL/__init__.py
  NL2SQL/schema_context.py       — Schema 上下文构建
  NL2SQL/prompt_builder.py       — Prompt 组装
  NL2SQL/sql_validator.py        — SQL 安全校验
  NL2SQL/sql_executor.py         — SQL 执行器
  NL2SQL/sql_formatter.py        — SQL 美化器
  model/NL2SQL.py                — ORM 模型（nl2sql_session / nl2sql_message）
  DAO/nl2sql_dao.py              — 数据访问层
  service/nl2sql_service.py      — 业务编排
  API/nl2sql_api.py              — FastAPI Router

修改:
  database.py                    — 新增 engine_readonly 和 get_db_readonly()
  main.py                        — 注册 nl2sql_api 路由
  requirements.txt               — 新增 sqlparse
```
