# Agent 系统架构说明文档（v1.0 MVP）

> 基于学生管理系统二阶段需求，在现有项目主干上新增的智能体子系统。学业导师 Agent，支持成绩查询、知识问答、学业分析和基础情绪陪伴。

---

## 一、整体架构

```
                        ┌─────────────────────┐
                        │   AgentView.vue      │  ← 前端聊天 UI（SSE 流式展示）
                        └──────────┬──────────┘
                                   │ POST /agent/chat/stream (SSE)
                                   │ POST /agent/chat        (同步)
                                   │ GET  /agent/sessions
                                   │ GET  /agent/sessions/{id}/messages
                                   │ GET  /agent/personas
                                   ▼
                        ┌─────────────────────┐
                        │   agent_api.py       │  ← FastAPI 路由层，参数校验 + 鉴权
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  agent_service.py    │  ← 编排层，串联全流程
                        └──────────┬──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
     │   planner/    │    │   executor/   │    │   memory/    │
     │ 意图分类      │    │ 计划执行      │    │ 对话记忆     │
     │ 计划生成      │    │ 工具分发      │    │ TalkSession  │
     │               │    │ LLM 总结      │    │ TalkMessage  │
     └──────┬───────┘    └──────┬───────┘    └──────────────┘
            │                   │
            │    ┌──────────────┤
            │    │              │
            ▼    ▼              ▼
     ┌──────────────────────────────────┐
     │            tools/                 │
     │  score_tool    rag_tool           │
     │  nl2sql_tool   student_tool       │
     └──────────┬───────────────────────┘
                │
     ┌──────────▼───────────────────────┐
     │        现有系统能力               │
     │  service/score_service            │
     │  service/nl2sql_service           │
     │  service/work_service             │  ← 天气查询
     │  util/email                       │  ← 邮件生成+发送
     │  RAG/retrieval_service            │
     │  DAO/student_dao  DAO/talk_dao    │
     └──────────────────────────────────┘
```

### 核心设计原则

1. **局部嫁接，不重构主干**：`agent_system/` 独立于现有 `API/`、`service/`、`DAO/` 目录
2. **Planner 驱动，受控执行**：意图 → 计划 → 执行，不放开 LLM 自由选工具
3. **现有能力先包装成工具再调用**：不跨层直接 import `DAO` 或 RAG 底层模块
4. **Persona 只在最终回复注入**：意图分类保持客观

### 为什么不用 LangChain Agent 框架

项目已有的 `llm_basic.py` 基于 LangChain（`ChatOllama`/`ChatOpenAI`），`extract_service.py` 也用了 `SystemMessage`/`HumanMessage`/`JsonOutputParser`。但在 Agent 核心链路（意图→计划→执行）中，刻意没有使用 LangChain 的 AgentExecutor、ToolNode、LCEL 链式调用等能力，原因如下：

**1. MVP 阶段的核心需求是"受控"而非"智能"**

LangChain Agent 框架的核心价值在于：把工具定义发给 LLM，让 LLM 在对话中自主判断什么时候调什么工具（tool calling / ReAct 模式）。这适合工具数量多、任务组合灵活的开放场景。但本系统 MVP 只有 2~4 个工具，且 6 种意图中每种对应的工具链是固定的——`score_query` 一定调 `score_tool`，`knowledge_qa` 一定调 `rag_tool`。让 LLM 自主选工具的收益为零，反而引入了不可控风险（LLM 可能不调工具、调错工具、或反复调同一工具）。

**2. Planner 驱动的可审计性远高于 LLM 自由决策**

Planner 模式每一步都是确定的：
- 意图是谁判的 → `classify_intent()` 的日志
- 计划是谁生成的 → `build_plan()` 的输出，失败还有硬编码兜底
- 工具是谁调的 → `_TOOL_REGISTRY` 的分发表，精确到函数名

出问题时一眼看到哪个环节错了。LLM 自由 tool calling 模式下，你可能需要翻多轮消息才能还原 LLM 到底做了什么决策。

**3. 错误控制粒度不同**

Planner 驱动的每个环节都有独立的错误处理和降级策略——意图分类失败 → `general_chat`，计划生成失败 → 硬编码兜底计划，工具调用失败 → 记录错误并继续下一步。LLM tool calling 模式下所有决策权在 LLM 手里，你只能在外层设一个超时或最大轮次，出了问题很难精准定位。

**4. LangChain 的 Agent 框架引入的复杂度远超其带来的便利**

LangChain Agent 框架要求你理解 AgentExecutor、AgentAction、AgentFinish、intermediate_steps 等概念，工具必须用 `@tool` 或 `StructuredTool` 定义。当工具需要注入 db session 这种 FastAPI 依赖时（如 `score_tool` 需要 `db: Session`），还得绕一圈——要么把 db 放进工具输入的 dict 里，要么用 `RunnableConfig`。而 Planner 驱动模式直接调 Python 函数，传什么参数完全由 executor 控制，没有任何框架约束。

**5. 对 LLM 的工程化约束在 MVP 阶段比灵活性更重要**

本系统定位是学生管理系统中的受控智能体，不是通用聊天机器人。每个意图的执行路径是经过产品设计的（如学业导师看到 "academic_advice" 必须先查成绩再分析，不能跳过数据直接给建议）。Planner 驱动模式能保证这些约束被严格执行，而 LLM tool calling 模式下你可能需要写十几行 prompt 来描述"什么时候该调 score_tool"，效果还不一定能保证。

**综上**：MVP 阶段 LangChain 的实际使用仅局限于 `ChatOpenAI`（调 LLM 的薄封装）、`SystemMessage`/`HumanMessage`（两个消息 dataclass）、以及 `@tool` 装饰器（当前未被 executor 调用，仅作为 schema 定义预留后续 LLM tool calling 扩展）。这是刻意设计——不是"用少了 LangChain"，而是 Planner 驱动模式本身就绕开了 LangChain Agent 框架的用武之地。

---

## 二、目录结构与模块职责

```
agent_system/
├── __init__.py
├── api/
│   └── agent_api.py          # HTTP 路由层
├── service/
│   └── agent_service.py      # 业务编排层
├── planner/
│   ├── intent_classifier.py  # 意图分类（LLM 结构化输出）
│   └── task_planner.py       # 计划生成（LLM + 硬编码兜底）
├── executor/
│   └── agent_executor.py     # 计划执行 + 流式/同步 LLM 调用
├── tools/
│   ├── score_tool.py         # 成绩查询工具
│   ├── rag_tool.py           # RAG 检索 + FAQ 精确匹配
│   ├── nl2sql_tool.py        # NL2SQL 问数工具
│   └── student_tool.py       # 学生身份解析工具
├── memory/
│   └── conversation_memory.py # 多轮对话记忆
├── schemas/
│   ├── agent_request.py      # 请求模型
│   ├── agent_response.py     # 响应模型
│   └── task_state.py         # ExecutionPlan + PlanStep
└── prompts/
    ├── intent_prompt.py      # 意图分类 prompt + IntentResult schema
    ├── persona_prompt.py     # 学业导师 Persona + 角色注册表
    └── planner_prompt.py     # 计划生成 prompt + PlanSchema
```

### 各层职责

| 层 | 职责 | 禁止事项 |
|---|---|---|
| `api/` | 参数校验、鉴权、调用 service、返回响应 | 不直接调 LLM 或工具 |
| `service/` | 串联意图→计划→执行→记忆，SSE 事件编排 | 不处理 HTTP 细节 |
| `planner/` | 意图分类、结构化计划生成 | 不直接调工具、不生成最终回复 |
| `executor/` | 按计划逐步执行，工具分发，LLM 总结 | 不重新判断意图、不跨层打 DAO |
| `tools/` | 封装现有 service 为统一接口 | 不写业务分析逻辑 |
| `memory/` | 会话/消息 CRUD，复用 TalkSession/TalkMessage | 不混用 NL2SQL 的表 |
| `schemas/` | 纯数据模型定义 | 不含业务逻辑 |
| `prompts/` | Prompt 模板 + 输出 schema | 不含运行时逻辑 |

---

## 三、请求全链路流程

### 3.1 同步链路（POST /agent/chat）

```
用户消息
  → agent_api.chat()              # 鉴权、参数校验
  → agent_service.handle_agent_chat()
      1. classify_intent()         # LLM 意图分类 → {intent, confidence}
      2. get_or_create_session()   # 复用 TalkSession
      3. get_history()             # 读取最近 20 轮对话
      4. save_message("user")      # 持久化用户消息
      5. build_plan()              # LLM 生成 ExecutionPlan → 失败则用硬编码兜底
      6. run_plan()                # 按 plan.steps 执行工具 → LLM 总结 / 直接回复
      7. save_message("assistant") # 持久化 AI 回复（含 intent + tool_calls 元数据）
  → 返回统一 JSON: {code, msg, data: AgentChatResponse}
```

### 3.2 流式链路（POST /agent/chat/stream）

```
用户消息
  → agent_api.chat_stream()                     # StreamingResponse(text/event-stream)
  → agent_service.handle_agent_chat_stream()
      1-5. 同同步链路
      6. run_plan_stream()                       # 逐步产出 SSE 事件
           ├── event: intent → {intent, confidence}
           ├── event: session → {session_id}
           ├── event: plan → {intent, steps, need_llm_summary}
           ├── event: tool_start → {tool_name}
           ├── event: tool_end → {tool_name, status, summary}
           ├── event: chunk → {text}             ← 逐个 LLM token
           └── event: done → {intent, tool_calls, sources}
      7. 解析 chunk 收集 full_reply → save_message()
  → SSE 流结束
```

### 3.3 6 种意图的处理路径

| 意图 | 工具步骤 | LLM 总结 | 回复生成方式 |
|---|---|---|---|
| `score_query` | score_tool | 是 | LLM 流式总结成绩数据 |
| `academic_advice` | student_tool → score_tool | 是 | LLM 流式分析 + 建议 |
| `knowledge_qa` | rag_tool（FAQ 优先 → RAG 向量检索） | 是 | LLM 流式总结检索结果 |
| `data_query` | nl2sql_tool | 否 | 直接格式化 columns/rows |
| `emotional_support` | 无 | — | LLM 流式人格化共情回复 |
| `general_chat` | 无 | — | LLM 流式通用回复 |

---

## 四、各模块设计思路

### 4.1 意图分类（intent_classifier.py）

**设计选择**：纯 LLM 分类，不复用规则匹配。

用户项目中已有的 `extract_service.py` 验证了 "Pydantic schema + prompt + LLM JSON 输出" 模式可用。意图分类复用同一套基础设施——`llm_basic.structured_complete()`。

6 种意图的 prompt 不含 Persona 信息，保持分类客观。LLM 返回非 JSON 时降级为 `general_chat`，不阻塞后续流程。

### 4.2 计划生成（task_planner.py）

**设计选择**：LLM 生成 + 硬编码兜底。

Planner prompt 里为每种意图预设了步骤规则（调哪个工具、是否需要 LLM 总结、总结指令怎么写）。这样 LLM 输出稳定可控。

`_FALLBACK_PLANS` 字典为每种意图提供了预定义的 `ExecutionPlan`。LLM 调用失败时直接使用兜底计划，保证系统不中断。

计划的输入含最近 3 轮对话历史摘要，支持多轮追问（如"那数学呢"能关联上文理解"是问数学成绩"）。

### 4.3 工具层（tools/）

**统一接口规范**：每个工具提供两层

1. **`@tool` 装饰器**（LangChain 标准 schema）：为后续放开 LLM tool calling 预留
2. **`_xxx()` 内部函数**：executor 直接调用，传入 db session 等 FastAPI 依赖

**统一返回格式**：`{success: bool, error: str | None, ...}`，executor 据此判断成功/失败并做降级。

**student_tool 的 C2 逻辑**：默认用 `current_user.username` 作为学号去 Student 表查；管理员（username 不在 Student 表）需传 `student_no_override` 覆盖。只查不匹配时返回友好提示。

**rag_tool 的 FAQ 机制**：12 条高频校务问答用关键词+正则精确匹配，命中直接返回预设答案（零幻觉、零延迟），未命中再走 Milvus 向量检索。FAQ 条目放在 `_SchoolFaq.entries` 列表中，后续追加只需新增一条 `_FaqEntry`。

**nl2sql_tool 的接入方式**：不改 `nl2sql_service.py` 内部（它用原生 `openai.OpenAI` + `deepseek-v4-flash`，有独立的缓存和消息表），只在工具层包装 `nl2sql_service.query()` 并统一返回格式。

### 4.4 天气查询（work_service.py，待接入 Agent 工具）

**当前实现**：`service/work_service.py` 中的 `query_weather()` 集成了腾讯地图天气 API。

**接口签名**：

```python
def query_weather(location: str = None, adcode: str = None, weather_type: str = "now",
                  added_fields: str = None, get_md: int = None) -> dict
```

**功能概述**：
- 支持按经纬度坐标（`location`）或行政区划编码（`adcode`）查询
- 三种查询模式：`now`（实时天气）、`future`（多日预报）、`hours`（24 小时逐时）
- 可选附加字段：`alarm`（预警）、`air`（空气质量）
- 配套 `address_to_location()` 函数可将中文地址转为经纬度坐标

**Agent 接入思路**：封装为 `agent_system/tools/weather_tool.py`，Agent 识别到"天气"相关意图时调用。典型场景——学生问"今天会下雨吗""明天适合运动吗"，Agent 先调 `address_to_location()` 获取坐标，再调 `query_weather()` 获取天气数据，最后由 LLM 总结为自然语言回复。

### 4.5 邮件发送（util/email.py，待接入 Agent 工具）

**当前实现**：`util/email.py` 提供完整的邮件生成+发送管线。

**核心函数**：

```python
def generate_email_content(prompt: str) -> dict
    # 调用 DeepSeek 大模型，根据一句话需求生成邮件主题和正文
    # 返回 {"subject": "...", "body": "..."}

def send_email(subject: str, body: str, receiver: str = DEFAULT_RECEIVER) -> dict
    # 通过 QQ 邮箱 SMTP（SSL 465 端口）发送 HTML 邮件
    # 返回 {"success": True/False, "message": "..."}

def ai_send_email(prompt: str, receiver: str = DEFAULT_RECEIVER) -> dict
    # 一站式：生成 + 发送
    # 返回 {"subject", "body", "receiver", "send_result"}
```

**Agent 接入思路**：封装为 `agent_system/tools/email_tool.py`。典型场景——学生说"帮我给班主任写一封请假邮件"，Agent 识别意图后生成邮件内容，**先展示预览给用户确认（HITL）**，用户确认后再执行发送。这是本项目第一个需要人工确认的高风险操作，也是 HITL 机制的最佳切入点。

**为什么邮件发送需要 HITL 而成绩查询不需要**：成绩查询是只读操作，不会产生外部影响。邮件发送会真正把内容发给收件人，一旦内容不当或收件人错误就无法撤回。因此在 Agent 自动生成邮件内容后，必须经过用户确认才能发出。

### 4.6 执行器（agent_executor.py）

**设计选择**：MVP 合并为单文件，工具分发用字典而非 if/elif。

`_TOOL_REGISTRY` 字典按 `tool_name` 字符串映射到内部函数，新增工具只需加一行。工具执行异常全部 catch 并降级，不向上抛。

**三种回复路径**：

1. `need_llm_summary=True` → `_llm_stream_summarize()`：工具结果 JSON + Persona prompt + instruction → LLM 流式总结
2. `fallback_response` 非空 → `_llm_stream_reply()`：原始消息 + Persona prompt → LLM 流式对话
3. 有步骤但不需要总结 → `_format_raw_results()`：直接格式化数据文本

**流式版本**：`run_plan_stream()` 是生成器，逐步骤产出 SSE 事件字符串。`model.stream()` 逐 token 产出 chunk，每收到一个 token 就 yield 一个 `event: chunk`。

### 4.7 对话记忆（conversation_memory.py）

**设计选择**：MVP 复用 `TalkSession` + `TalkMessage`，不做独立 Agent 表。

**ai_content 结构化存储**：assistant 消息的 `ai_content` 存 JSON `{reply, intent, tool_calls}`。`get_history()` 自动提取 `reply` 字段传给 LLM。

**后续扩展预留**：如果 Agent 任务状态越来越复杂，可新增独立 `agent_task` 表记录每次执行的 plan、steps、耗时等。当前复用方案足够。

### 4.8 Persona 系统（persona_prompt.py）

**设计选择**：Persona 只在最终回复 prompt 注入，意图分类保持客观。

`PERSONA_REGISTRY` 是角色注册表，当前只有 `academic_mentor`（学业导师）。后续加角色只需在注册表新增一条，包含 `name`、`description`、`system_prompt`。

学业导师 Persona 定位：温和、鼓励型，先肯定再建议，不做心理诊断，危险话题建议联系专业人员。

### 4.9 基础设施增强

**llm_basic.structured_complete()**：从 `extract_service.py` 提炼的通用能力——Pydantic schema → JSON format instructions → prompt → LLM invoke → JSON 清理 → model_validate。Agent 系统和 extract_service 统一复用。

**RAG/retrieval_service.py**：把原先串在 `controller.py` 里的 6 步 RAG 流程拆成 `search_context()`（只检索）+ 调用方自己组装 prompt + 生成。Agent 调 `search_context()` 只拿上下文片段，复用现有 `rewrite_query → embed → hybrid_search → rerank` 管道。

**RAG/ingestion.py 扩展**：新增 `_find_generic_md_files()` + `_parse_md_sections()`，支持递归扫描子目录中的 `.md` 文件，按 `##` 标题分节后切片入库（`source_type="md"`），自动在 chunk 文本前拼接节标题来提升检索召回。

---

## 五、关键技术决策记录

| # | 决策 | 选型 | 原因 |
|---|---|---|---|
| 1 | LLM 调用入口 | 统一 `llm_basic.get_model()` | extract_service 已验证；一行切换 ollama/qwen/deepseek |
| 2 | 目录策略 | 按需生长，MVP 8 个目录 | 避免建空壳；后续加能力落点明确 |
| 3 | 意图分类 | 纯 LLM | 6 类意图边界清晰；模糊表达规则覆盖不了 |
| 4 | RAG 接入 | B+：拆检索/生成两层 | Agent 只拿上下文不拿答案；CLI/HTTP/Agent 复用同一检索 |
| 5 | 工具调用 | Planner 驱动 + Executor 显式 | MVP 受控；LLM 不自由选工具 |
| 6 | 多轮记忆 | 复用 TalkSession/TalkMessage | MVP 不新建表；ai_content JSON 存元数据 |
| 7 | Persona 时机 | 只在最终回复 prompt 注入 | 意图分类需客观；Persona 影响"怎么回"不管"干什么" |
| 8 | 结构化输出 | 提炼 `llm_basic.structured_complete()` | extract_service 和 Agent 复用，不各写一遍 |
| 9 | 用户-学生映射 | C2：username→学号默认 + 可覆盖 | 学生用学号登录即可自动解析；管理员传参查指定学生 |
| 10 | Plan schema | 精简版：steps + need_llm_summary + fallback | MVP 不需要 need_retrieval/need_human_review 等字段 |
| 11 | 前端 | 独立 AgentView.vue + SSE 流式 | 参考 RAGView 聊天 UI；流式打字机效果增强交互感 |
| 12 | NL2SQL | 不改内部，外层包装 | 有独立模型选择（v4-flash）和缓存逻辑，强行统一有回归风险 |
| 13 | 错误处理 | 统一兜底 + 具体降级回复 + 完整日志 | 用户不看到技术栈；日志记录完整堆栈 |
| 14 | Executor 结构 | 合并为单文件 | MVP 逻辑不足 200 行，拆 3 个文件增加跳转成本 |
| 15 | 流式输出 | SSE + model.stream() | 打字机效果；事件分阶段（intent→tool→chunk→done） |
| 16 | FAQ | 内嵌 rag_tool，关键词精确匹配 | 校务文档 19 chunks 易被名著淹没；FAQ 零幻觉零延迟 |

---

## 六、下版本待优化项

### P1 — 高优先级（建议下版本必做）

1. **接入天气查询工具（weather_tool）**  
   当前 `service/work_service.py` 已有完整的天气查询能力（实时 / 多日预报 / 逐时 + 空气质量 + 预警），只需封装为 `agent_system/tools/weather_tool.py`。Agent 识别到天气相关意图后自动查询并总结。前端可展示原有的天气卡片vue而非纯文本。

2. **接入邮件生成+发送工具（email_tool）+ HITL 机制**  
   当前 `util/email.py` 已有完整的邮件生成（LLM 写内容）+ 发送（QQ邮箱 SMTP）管线。封装为 `agent_system/tools/email_tool.py` 后，Agent 可帮用户写邮件。**这是引入 HITL（人工确认）的最佳切入点**——Agent 生成邮件内容后先展示预览，用户确认后才发送。需要同步新建 `agent_system/hitl/` 目录实现通用的人工确认机制。

3. **新增校务知识库问答机器人**  
   当前 RAG 知识库以四大名著为主（~2400 chunks），校务文档仅 19 chunks。即使 FAQ 覆盖了 12 个高频问题，仍有大量中低频校务问题走向量检索时被名著内容抢占。建议新建独立 collection 或增加校务文档量。

4. **独立 Agent 数据表**  
   当前复用 TalkSession/TalkMessage，`ai_content` 用 JSON 存元数据。随着 Agent 功能增多（多角色、长链任务、用户反馈），建议新增独立的 `agent_task` / `agent_feedback` 表用于记录每次执行的完整 plan、各步骤耗时、用户满意度等。

5. **NL2SQL 统一 LLM 入口**  
   `nl2sql_service.py` 自己 new `openai.OpenAI` 走 `deepseek-v4-flash`，与 `llm_basic.get_model()` 不一致。后续应评估改走统一入口,且使用provider == "deepseek-v4"这个模型与其他agent对话流区分后，评估 SQL 生成质量是否下降，如无影响则统一。

6. **支持多角色切换**  
   当前只有学业导师。`PERSONA_REGISTRY` 已预留了扩展点。下版本可新增陪伴班主任、国风老师等角色，并在 AgentView 中加入角色选择器。需要评估 Persona 是否影响意图分类。

7. **Agent 输入中间层（Middleware）**  
   在 `agent_api -> agent_service -> planner` 之间新增统一前置处理层，用来先做输入安全检查和问题改写，再进入意图分类与计划编排。这个中间层不建议做成全局 FastAPI Middleware，而是做成 `agent_system/middleware/` 内的 Agent 专用流程组件。  
   核心能力建议包含：  
   - **模糊问题改写**：把“这个”“那个”“帮我看下”等指代不清的问题，改写成更完整、可执行的任务描述。  
   - **禁止词/越权/提示注入检查**：对敏感、违规、越权、攻击性输入直接驳回，避免进入后续 LLM 与工具链。  
   - **原文与改写文同时保留**：原始输入用于审计，改写结果用于后续意图识别与规划。  
   - **统一决策结果**：建议输出 `pass / rewrite / reject` 三类结果，便于 service 层稳定处理。  
   - **改写边界控制**：只允许“补全、消歧、规范化”，不允许改变用户真实意图。  
   推荐新增文件：  
   - `agent_system/middleware/input_guard.py`  
   - `agent_system/middleware/query_rewriter.py`  
   - `agent_system/middleware/policy_checker.py`  
   - `agent_system/middleware/middleware_schema.py`  
   后续接入位置建议放在 `agent_system/service/agent_service.py` 的最前面，先过中间层，再进入 `classify_intent()` 和 `build_plan()`。

### P2 — 中优先级（建议择机实现）

8. **SSE 流式会话记忆保存优化**  
   当前流式链路通过 service 层解析 chunk 事件收集 `full_reply`，存在二次解析开销。可考虑让 executor 的 `run_plan_stream()` 在 `done` 事件中直接携带 `full_reply` 文本。

9. **工具调用结果缓存**  
   同一会话中连续追问时，可能重复调用 `score_tool`（如 "数学多少分" → "语文呢"）。可在 executor 内部对同 session 的工具结果做短期缓存。

10. **知识问答来源高亮**  
   当前 `knowledge_qa` 的 LLM 总结没有显式引用来源编号（如 `[来源 1]`）。可参考 RAGView 的 `build_prompt` 做法，把来源标注注入 LLM 总结 prompt。

11. **前端 Markdown 渲染**  
   当前 Agent 回复是纯文本。Agent 返回的成绩分析、知识问答中包含换行和列表时，前端可渲染为 Markdown 格式提升可读性。

### P3 — 低优先级（锦上添花）

12. **Agent 行为监控与日志面板**  
    新增 `monitoring/` 模块，记录每次请求的完整链路耗时（意图分类、计划生成、各工具调用、LLM 总结），并提供可视化管理面板。

13. **长期用户画像**  
    记录学生的学习偏好、常见问题类型、对话风格，逐步实现个性化推荐和主动关怀。

--
## 七、文件改动清单

### 新建文件（agent_system/ 子系统 17 个 + RAG 2 个）

```
agent_system/__init__.py
agent_system/api/__init__.py
agent_system/api/agent_api.py
agent_system/service/__init__.py
agent_system/service/agent_service.py
agent_system/planner/__init__.py
agent_system/planner/intent_classifier.py
agent_system/planner/task_planner.py
agent_system/executor/__init__.py
agent_system/executor/agent_executor.py
agent_system/tools/__init__.py
agent_system/tools/score_tool.py
agent_system/tools/rag_tool.py
agent_system/tools/nl2sql_tool.py
agent_system/tools/student_tool.py
agent_system/memory/__init__.py
agent_system/memory/conversation_memory.py
agent_system/schemas/__init__.py
agent_system/schemas/agent_request.py
agent_system/schemas/agent_response.py
agent_system/schemas/task_state.py
agent_system/prompts/__init__.py
agent_system/prompts/intent_prompt.py
agent_system/prompts/persona_prompt.py
agent_system/prompts/planner_prompt.py
RAG/retrieval_service.py
```

### 修改文件（7 个）

```
llm_basic.py                    # 新增 structured_complete()
service/extract_service.py      # 重构复用 structured_complete()
RAG/controller.py               # 重构 /ask 走 retrieval_service
RAG/ingestion.py                # 新增通用 Markdown 支持
main.py                         # 注册 agent_router
frontend-vue/src/views/AgentView.vue     # 新建
frontend-vue/src/router/index.js         # 新增 /agent 路由
frontend-vue/src/components/Sidebar.vue  # 新增导航项
```

### 知识库文件

```
RAG/docs/school/学生管理系统规章制度.md   # 基于项目实际功能重写
```
