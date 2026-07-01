# Agent 系统 v2.0 迭代总结与下版本规划

> 本文档记录 v2.0 版本从需求设计、grill-me 细节敲定、代码实现到最终架构的全过程，并列出 v1.0 MVP 设计文档中未实现的功能和推荐的下版本优化方向。

---

## 一、v2.0 迭代范围

v2.0 基于 v1.0 MVP（学业导师单角色 + 4 工具），完成以下 7 大需求 + 4 项 P2 优化 + 1 项体验增强：

| # | 类型 | 功能 | 来源 |
|---|------|------|------|
| 1 | P1 需求 | 接入天气查询工具 | MVP 文档 §六.1 |
| 2 | P1 需求 | 接入邮件生成+发送工具 + HITL 机制 | MVP 文档 §六.2 |
| 3 | P1 需求 | 独立 Agent 数据表 | MVP 文档 §六.4 |
| 4 | P1 需求 | NL2SQL 统一 LLM 入口（评估后保持独立） | MVP 文档 §六.5 |
| 5 | P1 需求 | 多角色切换 | MVP 文档 §六.6 |
| 6 | P1 需求 | Agent 输入中间层 | MVP 文档 §六.7 |
| 7 | P2 优化 | SSE 流式 full_reply 优化 | MVP 文档 §六.8 |
| 8 | P2 优化 | 工具调用结果缓存 | MVP 文档 §六.9 |
| 9 | P2 优化 | 知识问答来源高亮 | MVP 文档 §六.10 |
| 10 | P2 优化 | 前端 Markdown 渲染 | MVP 文档 §六.11 |
| 11 | 体验增强 | 全局悬浮 Agent 助手（FloatingAgent） | 用户需求 |

**明确搁置**：校务知识库独立 collection（MVP 文档 §六.3）——校务文档量不足（19 chunks），拆分无实际效果，由用户决定搁置。

---

## 二、Grill-Me 关键设计决策

v2.0 的 7 个需求在实现前通过 grill-me 逐项敲定了以下设计决策：

| # | 决策点 | 选型 | 原因 |
|---|--------|------|------|
| 1 | 天气 geocode→weather 两步链 | 扩展 PlanStep 增加 `inputs_from` + schema 驱动字段匹配 | 通用方案，email/其他链式场景也受益 |
| 2 | HITL 暂停/恢复机制 | 两段式 API（SSE `awaiting_confirmation` → `POST /agent/step/confirm`） | 保持 SSE 传输不动，只加一个恢复端点 |
| 3 | 工具间数据传递 | Schema 驱动：工具声明 `inputs_schema`，executor 自动按字段名从上游结果匹配参数 | 工具自描述、无需 planner 感知映射细节 |
| 4 | HITL 确认粒度 | 任务级（一次对话一个评分），预留 `tool_name` 字段 | 用户操作成本低，后续可扩展到步骤级 |
| 5 | NL2SQL 统一 LLM | **保持独立**，仅加文档注释说明差异 | `max_tokens=500`、严格 SQL 格式、自有缓存层合理 |
| 6 | Persona 影响范围 | **仅回复风格**，不参与意图分类和工具选择 | 保持系统简单，意图分类客观 |
| 7 | 中间件执行顺序 | `input_guard → query_rewriter → policy_checker` 三层分离 | guard 最便宜先跑；rewriter 用改写后文本过 policy |
| 8 | 查询改写策略 | 混合模式：规则快速判断 + 仅命中模糊 pattern 时触发 LLM | 大部分明确问题零额外延迟 |
| 9 | 改写上下文范围 | 当前消息 + 最近 6 轮对话历史 | 可消解"这个""那个"等指代词 |
| 10 | RAG 知识库隔离 | 两个独立 Milvus collection，school 优先 + novels fallback | 校务文档量不足导致实际效果有限，先搁置 |
| 11 | 工具缓存策略 | session 级，tool_name + 参数指纹做 key，仅缓存读操作 | 同一会话内成绩等数据不会变 |
| 12 | 邮件收件人白名单 | 独立文件 `email_whitelist.py`，首发 `337429025@qq.com` | 防止 Agent 被注入诱导乱发邮件 |
| 13 | 全局 Agent 入口 | 右下角悬浮按钮 + 侧边面板，挂在 App.vue | 任意功能页面可用，不干扰原有全页 `/agent` 入口 |

---

## 三、架构演进

### 3.1 目录结构变化

v1.0 MVP（8 个目录）→ v2.0（12 个目录）：

```
agent_system/
├── __init__.py
├── api/
│   └── agent_api.py              # + POST /agent/step/confirm（HITL 恢复端点）
├── service/
│   └── agent_service.py          # + 中间件管线接入 + AgentTask 埋点
├── planner/
│   ├── intent_classifier.py      # + weather_query / email_draft 意图
│   └── task_planner.py           # + 新意图兜底计划
├── executor/
│   └── agent_executor.py         # ★ 重写：通用分发 + inputs_from + HITL + 缓存
├── tools/
│   ├── base.py                   # ★ NEW：BaseTool + ToolContext 统一接口
│   ├── score_tool.py             # 重构为 BaseTool 子类
│   ├── rag_tool.py               # 重构为 BaseTool 子类
│   ├── nl2sql_tool.py            # 重构为 BaseTool 子类
│   ├── student_tool.py           # 重构为 BaseTool 子类
│   ├── weather_tool.py           # ★ NEW：天气查询（geocode + weather 内链）
│   ├── email_tool.py             # ★ NEW：邮件预览（LLM 生成 + 白名单校验）
│   └── email_whitelist.py        # ★ NEW：收件人白名单配置
├── memory/
│   └── conversation_memory.py    # save_message() 返回 TalkMessage 对象
├── hitl/                         # ★ NEW
│   ├── hitl_schema.py            # HitlState + HitlConfirmRequest
│   └── hitl_manager.py           # 暂停/恢复/超时/message_id 关联
├── middleware/                   # ★ NEW
│   ├── middleware_schema.py      # MiddlewareResult（pass/rewrite/reject）
│   ├── input_guard.py            # 提示注入/敏感操作/超长检测
│   ├── query_rewriter.py         # 混合改写：规则 + LLM
│   └── policy_checker.py         # 改写后最终安全核验
├── schemas/
│   ├── agent_request.py
│   ├── agent_response.py
│   └── task_state.py             # PlanStep + params + inputs_from
└── prompts/
    ├── intent_prompt.py          # + weather_query / email_draft
    ├── persona_prompt.py
    └── planner_prompt.py         # + 天气/邮件路由规则
```

**新增 model 层**：
```
model/
├── AgentTask.py                  # ★ NEW：任务执行记录（13 字段）
└── AgentFeedback.py              # ★ NEW：用户反馈记录
```

**新增 DAO 层**：
```
DAO/
└── agent_dao.py                  # ★ NEW：AgentTask/AgentFeedback CRUD（含日志）
```

**修改的现有文件**：
```
llm_basic.py                      # 添加 NL2SQL 独立设计说明注释
database.py                       # 注册 AgentTask/AgentFeedback 模型
DAO/talk_dao.py                   # 新增 get_message_by_id()
tools/__init__.py                 # 导出新工具类
main.py                           # agent_router 已注册（v1.0 已完成）
```

**前端新增/修改**：
```
frontend-vue/src/
├── components/
│   └── FloatingAgent.vue         # ★ NEW：全局悬浮 Agent 助手（400px 面板）
└── views/
    └── AgentView.vue             # + 角色选择器 + HITL 确认卡片 + Markdown 渲染 + 来源编号
```

### 3.2 请求链路变化

v1.0 链路：
```
agent_api → agent_service → classify_intent → build_plan → run_plan → 回复
```

v2.0 链路：
```
agent_api → agent_service
  ├── input_guard        (reject/pass)          ← NEW
  ├── query_rewriter     (pass/rewrite, SSE 广播) ← NEW
  ├── policy_checker     (pass/reject)          ← NEW
  ├── classify_intent    (8 种意图)
  ├── build_plan         (LLM + 兜底)
  └── run_plan_stream    (SSE 流式)
      ├── _TOOL_REGISTRY[step.tool_name].run(ctx)  ← 通用分发
      ├── _cache_get / _cache_set                   ← session 缓存
      ├── _build_tool_context → inputs_from 匹配     ← 链式调用
      └── awaiting_confirmation → pause → break     ← HITL 暂停
```

### 3.3 新增 SSE 事件类型

v1.0 事件：`intent` / `session` / `plan` / `tool_start` / `tool_end` / `chunk` / `done`

v2.0 新增：`guard_pass` / `rewritten` / `awaiting_confirmation` / `error`

---

## 四、v2.0 已实现的全部功能清单

### 后端（agent_system/）

| 模块 | 功能 | 关键文件 |
|------|------|----------|
| **工具基类** | BaseTool + ToolContext 统一接口，6 个工具全部重构 | `tools/base.py` |
| **天气工具** | 地址→经纬度→实时+预报+空气+预警，内部串联 geocode+weather | `tools/weather_tool.py` |
| **邮件工具** | LLM 生成内容 → 白名单校验 → 从 prompt 自动提取邮箱 → 返回预览 | `tools/email_tool.py` |
| **邮件白名单** | 独立配置文件，首发 `337429025@qq.com`、`786453528@qq.com` | `tools/email_whitelist.py` |
| **HITL 机制** | SSE `awaiting_confirmation` → 暂停 → `POST /agent/step/confirm` → 恢复/取消 → 消息回写 | `hitl/` + `api/agent_api.py` |
| **意图分类** | 6 种 → 8 种（+ weather_query / email_draft） | `prompts/intent_prompt.py` |
| **计划生成** | 8 种意图的 LLM + 兜底计划 | `prompts/planner_prompt.py` + `planner/task_planner.py` |
| **PlanStep 扩展** | 新增 `params` 和 `inputs_from` 字段，支持工具间数据传递 | `schemas/task_state.py` |
| **Executor 重构** | 消除硬编码 if/elif，改为 ToolContext + 查表调用 + inputs_from 自动字段匹配 | `executor/agent_executor.py` |
| **工具缓存** | session 级，tool_name + 参数指纹，仅缓存读操作（score/student/rag） | `executor/agent_executor.py` |
| **来源高亮** | rag_tool 结果格式化为 `[来源 N \| 类型 \| 文件名]`，LLM prompt 要求引用 | `executor/agent_executor.py` |
| **输入守卫** | 提示注入 / 敏感操作 / 超长检测 → reject | `middleware/input_guard.py` |
| **查询改写** | 规则快速判断 + LLM 消歧（传入最近 6 轮历史） | `middleware/query_rewriter.py` |
| **策略检查** | 改写后最终安全核验 | `middleware/policy_checker.py` |
| **中间件管线** | `_run_middleware()` 串联三层，输出 pass/rewrite/reject + SSE 广播 | `service/agent_service.py` |
| **AgentTask 表** | 13 字段：session_id, user_id, persona, intent, original_message, rewritten_message, plan_json, steps_json, status, total_duration_ms | `model/AgentTask.py` |
| **AgentFeedback 表** | 6 字段：task_id, rating, comment, tool_name（预留步骤级） | `model/AgentFeedback.py` |
| **DAO 层** | create_task / update_task / get_task_by_id / get_tasks_by_user / create_feedback | `DAO/agent_dao.py` |
| **SSE 优化** | done 事件 data 新增 `reply` 字段，避免 service 层二次拼接 | `executor/agent_executor.py` + `service/agent_service.py` |
| **消息持久化** | HITL 预览数据写入 TalkMessage metadata，确认后回写结果状态 | `memory/conversation_memory.py` + `api/agent_api.py` |
| **日志覆盖** | 全部 agent_system/*.py 接入 `util.log`，含 agent_dao 和 HITL 回写 | 全模块 |

### 前端（frontend-vue/）

| 功能 | 描述 | 文件 |
|------|------|------|
| **FloatingAgent** | 右下角悬浮按钮（🤖 + 脉冲动画）→ 400×560px 聊天面板，在各功能页面全局可用 | `components/FloatingAgent.vue` |
| **角色选择器** | CustomSelect 组件切换 Persona，自动加载 `/agent/personas` | `views/AgentView.vue` |
| **HITL 确认卡片** | 邮件预览面板（收件人/主题/正文可编辑 + 确认/取消按钮 + 状态回显） | `views/AgentView.vue` |
| **Markdown 渲染** | 安装 `marked`，流式输出中纯文本 → 完成后 `v-html` 渲染 | `views/AgentView.vue` |
| **来源编号** | 前端来源卡片加圆形编号，与 LLM 回复中的 `[来源 N]` 对应 | `views/AgentView.vue` |
| **主题跟随** | FloatingAgent 放在 `.app-layout` 内部，自动继承 light/dark CSS 变量 | `App.vue` |
| **启动修复** | `main.js` 中 `app.mount()` 延迟到 `/auth/me` token 验证后 | `main.js` |
| **SSE 事件扩展** | 新增 `guard_pass` / `rewritten` / `awaiting_confirmation` / `error` 事件处理 | `views/AgentView.vue` + `components/FloatingAgent.vue` |
| **CustomSelect 组件** | 完全自定义下拉框（Teleport 渲染、键盘导航、过渡动画、亮暗主题自动跟随），替换全站 19 个原生 `<select>` | `components/CustomSelect.vue` + 8 个 views |
| **权限面板重设计** | 全宽双列网格布局、胶囊拨动开关（开启/禁止+动画）、模块计数、一键加载角色 | `views/SystemView.vue` |
| **下拉选项美化** | 暗色主题金色选中渐变 + 亮色主题蓝色选中渐变，与文字色区分清晰可读 | `styles.css` + `CustomSelect.vue` |

---

## 五、实现过程中的 Bug 修复

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | Agent 回复"未指定地点" | executor 只注入 `question`/`prompt`，漏了 `location_text` | 新增 `_NL_PARAM_NAMES` 白名单字段名匹配 |
| 2 | 邮件流程返回"查询完成，但无结果返回" | `_format_raw_results` 只处理 success=True，跳过失败/预览结果 | 新增 email_tool preview 输出 + 失败错误信息展示 |
| 3 | 邮件收件人被中文污染 | Python 3 `\w` 默认匹配 Unicode 中文 | 正则改为 ASCII-only：`[a-zA-Z0-9._%+-]+@...` |
| 4 | HITL confirm 返回"步骤不存在或已超时" | executor 用 `hash(db)` 做 task_id，前端用 `session_id`，key 不匹配 | executor 接收 `session_id` 参数，统一用 `str(session_id)` 做 key |
| 5 | 历史消息丢失邮件预览 | 预览数据仅 SSE 流过，未写入 TalkMessage metadata | service 层捕获 `awaiting_confirmation` 事件 → 写 metadata.hitl → confirm 端点回写结果 |
| 6 | FloatingAgent 不跟随主题 | 组件放在 `.app-layout` 外部，无法继承 `.theme-light` 变量 | 移入 `.app-layout` 内部（`position: fixed` 不影响布局） |
| 7 | 首次启动显示 2 个模块而非登录页 | `app.mount()` 在 `bootstrapAuth()` 之前执行 | `app.mount()` 移入 `bootstrapAuth().finally()`，加 5 秒超时保护 |
| 8 | 天气查询"宝安"返回地址解析失败 | `address_to_location` 默认 `policy=0`（标准模式），必须带完整城市名 | 改为 `policy=1`（宽松模式），支持"宝安""龙岗"等区名省略城市 |
| 9 | NL2SQL 查无数据时无友好提示 | `_tool_summary` 仅显示"查询无结果"，`_format_raw_results` 输出空表头 | 0 行时展示执行的 SQL + 提示"数据库中没有符合该条件的数据"；`nl2sql_tool` 追加 `hint` 字段 |
| 10 | 角色管理 DataTable 行高爆炸 | `/system/roles` 返回 `permissions` 等巨型 JSON 数组，DataTable 用 `JSON.stringify` 渲染 | `loadRoles()` 解构去掉三个权限字段再赋值 |
| 11 | CustomSelect 下拉层亮暗颠倒 | Teleport 渲染到 `<body>` 脱离 `.app-layout.theme-light` CSS 变量域 | `positionDrop()` 从 DOM 实时读取主题 class，注入 `cs-theme--light` 上下文；新增 `.cs-theme--light` 覆写全部 CSS 变量 |
| 12 | 下拉选项选中色不分主题 | `.cs-option--selected` 硬编码金色渐变 | 改为 CSS 变量 `--cs-sel-bg-start/end`，暗色默认金色，亮色覆写为蓝色 |

---

## 六、当前 Agent 系统完整能力矩阵

| 能力   | 触发方式      | 工具调用                          | 是否需 LLM 总结  |  HITL  |
| ---- | --------- | ----------------------------- | :---------: | :----: |
| 成绩查询 | "帮我查成绩"   | score_tool                    |      ✅      |   —    |
| 学业分析 | "我最近有进步吗" | student_tool → score_tool     |      ✅      |   —    |
| 知识问答 | "请假流程是什么" | rag_tool（FAQ → RAG）           |      ✅      |   —    |
| 数据统计 | "3班有多少人"  | nl2sql_tool                   |      ❌      |   —    |
| 天气查询 | "今天天气怎么样" | weather_tool（geocode→weather） |      ✅      |   —    |
| 邮件撰写 | "帮我写请假邮件" | email_tool（LLM 生成+白名单）        |      ❌      | ✅ 预览确认 |
| 情绪陪伴 | "我好紧张"    | 无                             | ✅（LLM 个性回复） |   —    |
| 日常闲聊 | "你好"      | 无                             | ✅（LLM 个性回复） |   —    |

---

## 七、设计文档未实现功能清单

以下功能在两个参考设计文档中被提及，但截至 v2.0 尚未实现：

### 来自《Agent接入改造设计文档》

| #   | 功能                                                             | 设计文档出处 | 状态  | 备注                                    |
| --- | -------------------------------------------------------------- | ------ | :-: | ------------------------------------- |
| 1   | `class_tool.py` — 班级查询工具                                       | §五.1   |  ✅  | NL2SQL 已覆盖所有 SQL 查询场景，无需独立工具     |
| 2   | `employment_tool.py` — 就业信息工具                                  | §五.1   |  ✅  | NL2SQL 已覆盖，无需独立工具     |
| 3   | `statistics_tool.py` — 统计分析工具                                  | §五.1   |  ✅  | NL2SQL 已覆盖，无需独立工具     |
| 4   | `work_tool.py` — 作业模块工具                                        | §五.1   |  ❌  | 文生图/评价生成等，非核心优先                       |
| 5   | `working_memory.py` — 工作记忆                                     | §十二    |  ❌  | 当前任务中间状态已由 executor context dict 部分承担 |
| 6   | `summary_memory.py` — 会话摘要记忆                                   | §十二    |  ❌  | work_service.py 已有摘要能力，未接入 Agent      |
| 7   | `companion_agent.py` — 陪伴班主任角色                                 | §六     |  ❌  | PERSONA_REGISTRY 已预留扩展点               |
| 8   | `supervisor_agent.py` — 监督 Agent                               | §四     |  ❌  | 多 Agent 协作编排，P3 优先级                   |
| 9   | `step_runner.py` — 步骤执行器                                       | §十一    |  ❌  | 当前合并于 agent_executor.py               |
| 10  | `state_manager.py` — 状态管理器                                     | §十一    |  ❌  | 当前 HITL 暂停状态在 hitl_manager.py 内存字典    |
| 11  | `intent_parser.py` / `action_parser.py` / `response_parser.py` | §四     |  ❌  | 当前 parser 逻辑分散在 planner 和 executor 中  |
| 12  | `human_review.py` / `escalation_rules.py`                      | §四     |  ❌  | 当前 HITL 仅覆盖邮件发送                       |
| 13  | `monitoring/` 模块（logger/tracer/retry_handler）                  | §四     |  ❌  | 日志已覆盖，但无专用监控面板和链路追踪                   |
| 14  | `POST /agent/feedback` 端点                                      | §八     |  ❌  | 表已建、DAO 已写，API 和前端评分 UI 待做            |
| 15  | 前端评分/反馈 UI                                                     | §八     |  ❌  | 依赖 feedback API                       |

### 来自《Agent系统架构说明文档（v1.0-MVP）》

| # | 功能 | 文档出处 | 状态 |
|---|------|----------|:--:|
| 1 | 校务知识库独立 collection | §六.3 | 🔒 搁置 |
| 2 | NL2SQL LLM 统一入口 | §六.5 | ✅ 已完成（评估后保持独立 + 文档化） |
| 3 | Agent 行为监控与日志面板 | §六.12 | ❌ |
| 4 | 长期用户画像 | §六.13 | ❌ |
| 5 | 天气卡片 Vue 组件（非纯文本） | §六.1 | ❌ |
| 6 | 多角色（陪伴班主任/国风老师）具体 Persona prompt | §六.2 | ❌ 仅注册表预留 |

---

## 八、下版本迭代目标

结合设计文档未实现项和系统当前状态，按优先级排列：

### P1 — 高优先级（建议下版本必做）

1. **Agent 反馈闭环（`POST /agent/feedback`）**  
   表已建（`AgentFeedback`）、DAO 已写。只需新增 API 端点 + 前端消息气泡旁加 👍/👎 按钮，即可开始收集反馈数据，为后续用户画像和效果评估提供基础。

2. **Agent 行为监控面板**  
   `AgentTask` 表（含 `total_duration_ms`、`steps_json`、`status`、`intent`、`persona`）已在 v2.0 中写入生产数据。新增管理端可视化面板——展示近 7 天调用量分布、各类意图耗时 p50/p99、工具失败率趋势、各角色使用占比。

3. **HITL 通用化与告警规则**  
   当前 HITL 仅邮件发送。后续可扩展到其他高风险操作确认。同时新增 `escalation_rules.py`，支持超时自动取消 + 通知。

4. **天气查询接入腾讯地图 MCP**  
   腾讯地图已开放 MCP Server（Streamable HTTP：`https://mcp.map.qq.com/mcp?key=<KEY>&format=0`），本项目 `.env` 已有腾讯地图 key。目标：优先走 MCP 获取天气数据，MCP 不可用时降级到当前 geocode + weather 直连。

   **已敲定的设计决策**：

   | 决策 | 选型 | 原因 |
   |------|------|------|
   | MCP 连接生命周期 | FastAPI `startup` 事件建连 + 心跳保活 + 断线重连 | 持久连接免去每次请求握手延迟 |
   | 传输协议 | Streamable HTTP（`/mcp` 端点） | 单连接双向流，天然适合持久连接 + 多次 tool call |
   | 集成方式 | `WeatherTool.run()` 内部替换：先调 MCP → 失败降级 geocode+weather | 对 planner/executor 零改动，降级逻辑封装在工具内部 |
   | 降级粒度 | 调用级：每次独立判断，偶发超时不影响后续请求 | 比连接级切换更精细 |

   **实现要点**：
   - 安装 Python MCP SDK
   - 新建 `agent_system/tools/mcp_client.py`：封装腾讯地图 MCP 客户端（连接、心跳、tool discovery、断线重连）
   - 重构 `agent_system/tools/weather_tool.py`：`run()` 内 `try: mcp_client.call_tool(...) except: 降级到 address_to_location→query_weather`
   - `main.py` startup/shutdown 事件注册/注销 MCP 客户端
   - 对外接口不变——tool 名仍是 `weather_tool`，planner/executor 无需任何改动

   **后续地图 MCP 能力候选池（v2.3 优先评估）**：
   - `geocoder` / `reverseGeocoder`：地址解析、经纬度反查，可做签到位置语义核验、地址标准化。
   - `placeSuggestion` / `placeSearchNearby` / `placeDetail`：地点搜索、周边服务、POI 详情，可做学校/实习企业周边生活服务推荐。
   - `directionDriving` / `directionTransit` / `directionWalking` / `directionBicycling` / `futureDrivingDirection`：多方式路线规划，可做学生实习通勤规划、外出拜访行程助手。
   - `matrix`：批量距离/耗时计算，可做多学生、多企业、多校区之间的通勤成本评估。
   - `waypointOrder` / `placeAlongby`：途经点排序、沿途搜索，可做多点拜访路线优化、沿途停车场/充电站/服务区推荐。
   - `ipLocation`：IP 定位，可作为轻量位置辅助信息，不单独作为强校验依据。

> **关于 class_tool / employment_tool / statistics_tool**：原开发计划建议将这三个 service 包装为独立 Agent 工具。但 v2.0 已完成 NL2SQL agent tool，能将任意自然语言转为 SQL 查询数据库——"3 班有多少人""就业薪资最高的是谁""班级平均分排名"等问法均可由 NL2SQL 处理。每个业务查询再单独写一个工具属于重复劳动，故不再规划。

### P2 — 中优先级（建议择机实现）

5. **新增陪伴班主任 Persona**  
   `PERSONA_REGISTRY` 已预留扩展点。撰写共情型 system prompt，限定边界（不诊断、不承诺、危险话题引导联系专业人员）。

6. **`working_memory` + `summary_memory` 独立**  
   当前 executor context dict 承担了部分工作记忆角色，长期看应独立为 `working_memory.py`。`summary_memory.py` 可复用 `work_service.py` 的摘要能力做长对话压缩。

7. **天气卡片 Vue 组件**  
   WorkView 已有天气 UI 组件逻辑，可提取为通用 `<WeatherCard>` 并在 AgentView 和 FloatingAgent 中复用，替代当前纯文本天气播报。

### P3 — 低优先级（锦上添花）

8. **多 Agent 协作编排**  
   例如：学业导师分析成绩 → 班主任写评语 → 邮件工具发送给家长。需要 `supervisor_agent.py` 和任务级状态管理。

9. **长期用户画像**  
   基于 `AgentTask` + `AgentFeedback` 历史数据，分析每用户的高频意图、偏好的回复风格、活跃时段，逐步实现个性化。

10. **Parser 层独立**  
    将当前分散在 planner/executor 中的 JSON 解析、结果格式化逻辑收敛到 `parsers/` 目录。

11. **边界场景体验优化（持续迭代）**  
    v2.0 中已修复的体验问题可做为后续同类优化的参考模板：
    - **工具参数适配**：天气查询 `policy=0→1`，让模糊输入（"宝安"）也能正常工作。后续新增工具接入时，应主动检查默认参数是否符合口语化输入场景。
    - **空结果友好提示**：NL2SQL 查到 0 行时展示 SQL 原文 + 引导用户调整条件。后续 score_tool 无成绩、rag_tool 无匹配、student_tool 查无此人等场景均应遵循同样模式——告诉用户"系统做了什么 + 为什么没结果 + 建议下一步怎么做"。
    - **通用原则**：每个工具返回失败/空结果时，不只给 executor 一个 `error` 字符串，还应附带 `hint` 字段供 LLM 总结时生成更人性化的回复。

---

## 九、v2.0 文件变动统计

| 操作 | 数量 | 说明 |
|------|:---:|------|
| 新建 Python 文件 | 16 | tools/base, weather_tool, email_tool, email_whitelist, hitl/*, middleware/*, model/AgentTask, model/AgentFeedback, DAO/agent_dao |
| 修改 Python 文件 | 12 | executor, service, api, planner/prompts 全链路 + database + llm_basic + schemas + tools/__init__ + talk_dao + conversation_memory |
| 新建 Vue 文件 | 2 | FloatingAgent.vue, CustomSelect.vue |
| 修改 Vue 文件 | 11 | AgentView, App, main.js, SystemView, ScoreView, WorkView, ClassView, NL2SQLView, EmploymentView, StudentView, StatisticsView, TeacherView |
| 安装 npm 包 | 1 | `marked` |

---

## 十、一句话总结

v2.0 将 Agent 从单一学业导师扩展到 **8 种意图 × 6 个工具 × 1 个 HITL 确认流 × 3 层输入中间件 × 独立数据表** 的完整智能体子系统，并通过全局悬浮入口覆盖所有功能页面的交互场景。
