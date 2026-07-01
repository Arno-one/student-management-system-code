# Agent 系统 v2.1 迭代总结与下版本规划

> 本文档记录 Agent 系统 v2.1 从需求设计、逐功能实现、测试验证到最终设计沉淀的全过程，并列出建议进入 v2.2 的迭代需求。

---

## 一、版本定位

v2.1 的版本主题是：**运营闭环与可观测版本**。

v2.0 已经让 Agent 具备“能理解意图、能调用工具、能流式回复、能做 HITL 确认”的基础能力。v2.1 继续往前补齐三类能力：

1. **可运营**：用户能反馈，管理员能看到 Agent 使用效果。
2. **可治理**：高风险动作不再写死为邮件专用确认，而是进入轻量规则系统。
3. **可扩展**：腾讯地图 MCP 不只服务天气，而是沉淀为后续地图类 Agent 能力的统一底座。

一句话概括：

> v2.1 把 v2.0 的“可用 Agent”升级为“可反馈、可观察、可治理、可持续扩展的 Agent 子系统”。

---

## 二、v2.1 迭代范围

| # | 功能 | 优先级 | 状态 | 测试文档 |
|---|------|--------|------|----------|
| 1 | Agent 任务级反馈闭环 | P1 | 已完成 | `docs/testing/Agent系统v2.1-任务级反馈闭环测试数据.md` |
| 2 | Agent 行为监控面板 | P1 | 已完成 | `docs/testing/Agent系统v2.1-Agent行为监控面板测试数据.md` |
| 3 | HITL 轻量规则系统 | P1 | 已完成 | `docs/testing/Agent系统v2.1-HITL轻量规则系统测试数据.md` |
| 4 | 腾讯地图 MCP 能力底座 + 天气首发接入 | P1 | 已完成 | `docs/testing/Agent系统v2.1-腾讯地图MCP能力底座测试数据.md` |
| 5 | 陪伴班主任 Persona | P2 | 已完成 | `docs/testing/Agent系统v2.1-陪伴班主任Persona测试数据.md` |
| 6 | 天气卡片系统 | P2 | 已完成 | `docs/testing/Agent系统v2.1-天气卡片组件测试数据.md` |
| 7 | Agent 对话加载态回归修复 | 体验修复 | 已完成 | `docs/testing/Agent系统v2.1-Agent对话加载态回归测试数据.md` |

---

## 三、设计过程与关键决策

### 3.1 迭代方式

本版本采用“一个功能一个功能实现”的节奏：

1. 先根据 v2.0 文档中的“下版本迭代目标”整理 v2.1 功能需求设计。
2. 每个功能实现前先明确边界和验收口径。
3. 每个功能完成后运行后端编译、前端构建和针对性验证。
4. 每个功能单独输出测试数据文档到 `docs/testing/`。
5. 用户确认后再进入下一个功能。

这个节奏的收益是：每个功能都有独立验收闭环，后面出现 UI 或接口回归时也能快速定位到对应功能和测试文档。

### 3.2 关键设计决策

| 决策点 | 最终方案 | 原因 |
|--------|----------|------|
| 反馈粒度 | 先做任务级反馈，保留 `tool_name` 扩展字段 | 用户操作成本低，后续可扩展到工具步骤级反馈 |
| 点踩反馈 | 点踩先展开原因输入，用户提交原因后只提交一次并锁定按钮 | 防止一次负反馈被多次提交 |
| 监控入口 | 复用 `SystemView.vue`，新增 `Agent监控` 子页 | 不增加一级菜单，符合后台管理信息架构 |
| 监控图表 | 第一版使用轻量 CSS 条形图和表格，不引入 ECharts | 降低依赖和维护成本 |
| HITL 规则 | 新增 `escalation_rules.py`，按 `tool_name` 配置风险等级、文案、超时 | 后续新增高风险工具时只需配置规则 |
| HITL 状态 | `awaiting_hitl`、`cancelled`、超时失效独立处理 | 管理员能区分失败、取消和等待确认 |
| 腾讯地图 MCP | MCP 优先，失败自动 REST 兜底 | MCP 是增强能力，不应影响基础天气查询 |
| MCP 接入层 | 新建通用 `TencentMapMcpClient`，不写成天气专用客户端 | 后续路线、地点、周边搜索等能力都能复用 |
| 真实天气链路 | `geocoder(address)` → `weather(adcode/location, type)` | 腾讯地图 MCP 的 `weather` 不直接吃自然语言地点 |
| MCP tools 暴露 | Agent 不裸调用全部 MCP tools，后端按需封装 | 避免工具面过大导致不可控调用 |
| Persona 影响范围 | 只影响回复风格，不参与意图分类和工具选择 | 延续 v2.0 决策，保持意图识别客观稳定 |
| 天气卡片协议 | 后端生成 `cards`，前端按 `type=weather` 渲染组件 | 不从 LLM Markdown 里反向解析结构化数据 |
| 天气卡片主题 | 只读取项目 CSS 变量，不写全局 `.theme-light` 覆盖 | 防止污染页面浅色主题背景 |
| Agent 加载态 | 复用当前 `_streaming` assistant 消息展示 loading | 避免等待回复时出现两个 Agent 头像 |

---

## 四、功能实现总结

### 4.1 Agent 任务级反馈闭环

已实现能力：

- 后端新增 `/agent/feedback`。
- SSE `done` 事件携带 `task_id`。
- `AgentView.vue` 和 `FloatingAgent.vue` 均支持 👍 / 👎 反馈。
- 点赞默认提交 `rating=5`。
- 点踩先展开原因输入，提交原因后写入 `rating=1`。
- 同一任务重复反馈采用 upsert 覆盖，不新增重复记录。
- 用户只能反馈属于自己的 `AgentTask`。
- 用户提交点踩原因后关闭提交按钮和原因输入框，避免多次提交。

实现原理：

1. `AgentTask` 记录一次 Agent 任务。
2. `AgentFeedback` 绑定 `AgentTask.id`。
3. 后端通过 `task_id + tool_name is null` 表达任务级唯一反馈。
4. 前端收到 `done.task_id` 后才展示反馈按钮。
5. 反馈状态在前端维护 `loading/submitted/open/status`，提交成功后锁定。

核心价值：

> 让 Agent 回复从“用户看完就结束”变成“可被评价、可被统计、可被优化”的闭环。

### 4.2 Agent 行为监控面板

已实现能力：

- 管理员接口：
  - `GET /agent/admin/metrics`
  - `GET /agent/admin/metrics/timeseries`
  - `GET /agent/admin/metrics/intents`
  - `GET /agent/admin/metrics/tools`
  - `GET /agent/admin/tasks`
- 系统管理页新增 `Agent监控` 子页。
- 展示总调用量、成功率、平均耗时、P99 耗时、反馈数、待确认/取消数。
- 展示每日调用趋势、意图排行、工具失败排行、最近任务表。
- 支持时间范围、状态、意图筛选。
- 权限口径复用 `require_role("admin")`。

实现原理：

1. 从 `AgentTask` 聚合任务级指标。
2. 从 `AgentTask.steps_json` 解析工具调用成功/失败。
3. 从 `AgentFeedback` 汇总反馈数、好评率和差评率。
4. `awaiting_hitl` 和 `cancelled` 单独统计，不混入任务失败率。

核心价值：

> 管理员能看见 Agent 是否稳定、哪些意图高频、哪些工具容易失败、用户是否满意。

### 4.3 HITL 轻量规则系统

已实现能力：

- 新增 `agent_system/hitl/escalation_rules.py`。
- `email_tool` 的确认标题、说明、风险等级、超时时间来自规则配置。
- `awaiting_confirmation` SSE 事件携带：
  - `risk_level`
  - `timeout_seconds`
  - `expires_at`
  - `confirm_title`
  - `confirm_message`
- `HitlState` 保存规则元数据、消息 ID、AgentTask ID。
- 超时确认会自动失效。
- 用户取消确认后回写 `AgentTask.status = cancelled`。
- HITL 暂停任务写入 `AgentTask.status = awaiting_hitl`。

实现原理：

1. 工具返回 `awaiting_confirmation` 状态。
2. executor 根据 `tool_name` 查找 HITL 规则。
3. `hitl_manager` 保存暂停状态和过期时间。
4. 前端根据 SSE 中的规则字段渲染确认卡片。
5. `/agent/step/confirm` 恢复或取消任务，并回写任务状态。

核心价值：

> HITL 从“邮件专用逻辑”升级为“高风险操作确认规则”，后续新增工具时只需按规则接入。

### 4.4 腾讯地图 MCP 能力底座 + 天气首发接入

已实现能力：

- 新增 `agent_system/tools/mcp_client.py`。
- FastAPI 启动/关闭阶段初始化和释放腾讯地图 MCP 客户端。
- MCP 初始化失败不阻塞应用启动。
- 新增健康检查接口：`GET /agent/admin/mcp/tencent-map/health`。
- `WeatherTool` 优先尝试 MCP。
- MCP 不可用、超时或结构异常时自动降级到腾讯地图 REST。
- 返回结果新增 `provider`：
  - `tencent_mcp`
  - `tencent_rest_fallback`
- 真实 MCP 天气链路修正为：
  - `geocoder(address)`
  - `weather(adcode/location, type=now)`
  - `weather(adcode/location, type=future)`

已实测腾讯地图 MCP tools/list 返回 15 个工具：

```text
geocoder
placeSuggestion
placeSearchNearby
directionDriving
placeAlongby
placeDetail
matrix
reverseGeocoder
ipLocation
weather
directionWalking
directionBicycling
directionTransit
futureDrivingDirection
waypointOrder
```

实现原理：

1. `TencentMapMcpClient` 负责 MCP 连接、工具发现、调用和健康状态。
2. `WeatherTool` 只把 MCP 当作优先数据源，不改变 planner/executor 对外接口。
3. MCP 失败时落回旧的 REST 链路：`address_to_location(policy=1)` → `query_weather`。
4. MCP 工具不会直接暴露给 Agent 裸调，后端通过业务工具逐个封装。

核心价值：

> 天气只是 MCP 的第一个落点，真正沉淀的是后续路线规划、地点搜索、周边服务、距离矩阵等地图能力底座。

### 4.5 陪伴班主任 Persona

已实现能力：

- `PERSONA_REGISTRY` 新增 `companion_head_teacher`。
- `/agent/personas` 可返回“陪伴班主任”角色。
- executor 能把陪伴班主任 system prompt 注入普通回复和工具结果总结。
- 未知 persona 仍回退到 `academic_mentor`。
- `AgentView.vue` 空态提示和示例问题随角色切换。

设计边界：

- 不做心理疾病诊断。
- 不承诺治疗效果。
- 不替学生做重大决定。
- 不编造学校政策、电话或外部资源。
- 遇到自伤、伤人或现实危险表达时，引导联系现实支持。

实现原理：

> Persona 只是 system prompt 层面的风格控制，不参与意图分类和工具选择。这样“陪伴班主任”既能温和回应压力、拖延、焦虑，也不会破坏成绩查询、天气查询等工具路由。

### 4.6 天气卡片系统

已实现能力：

- `AgentChatResponse` 新增 `cards` 字段。
- executor 新增 `_extract_cards()`，从 `weather_tool` 结果生成 `type=weather` 卡片。
- SSE `done`、同步接口响应、历史消息 metadata 均可携带 `cards`。
- 新增 `frontend-vue/src/components/WeatherCard.vue`。
- `AgentView.vue` 和 `FloatingAgent.vue` 渲染天气卡片。
- 悬浮 Agent 使用 `compact` 模式，最多展示 3 天预报。
- 天气卡片兼容 MCP 和 REST fallback 数据。
- 天气卡片不从 Markdown 中解析 JSON，避免依赖 LLM 输出格式。

实现原理：

1. LLM 继续输出自然语言 Markdown。
2. 结构化天气数据由 executor 从工具结果中抽取为 `cards`。
3. 前端按 `card.type` 选择组件渲染。
4. 当前只支持 `weather`，后续可扩展 `route`、`poi_list`、`map_location` 等卡片。

主题回归修复：

- 初版使用了 scoped CSS 下的 `:global(.app-layout.theme-light)`，构建后污染浅色主题背景。
- 修复后天气卡片只读取项目主题变量，如 `--panel-solid`、`--text`、`--line` 等。
- 构建产物检查结果：`bad_theme_pollution=0`。

核心价值：

> Agent 回复从“纯文本描述”开始具备结构化 UI 承载能力，为后续地图、路线、地点列表等卡片打基础。

### 4.7 Agent 对话加载态回归修复

问题现象：

- 用户发送消息后，等待 Agent 回复时左侧出现两个 Agent 头像。
- 一个头像属于 `_streaming` assistant 消息。
- 另一个头像属于全局 `loading` 额外渲染的 assistant loading 消息。

修复方式：

- 移除消息列表末尾额外的 `v-if="loading"` assistant loading 消息块。
- 在当前 `_streaming` assistant 消息内部展示 loading 动画。
- 收到首个 SSE 文本片段后，同一条消息切换为流式文本展示。

核心价值：

> 保持消息语义一致：一次 Agent 回复永远只对应一条 assistant 消息。

---

## 五、实现原理总览

### 5.1 任务闭环链路

```text
用户发送消息
  → 创建 AgentTask
  → SSE 流式执行
  → done 返回 task_id / cards / tool_calls / sources
  → 前端展示回复和反馈按钮
  → POST /agent/feedback
  → AgentFeedback upsert
  → 监控面板聚合反馈质量
```

### 5.2 监控聚合链路

```text
AgentTask.status / intent / persona / total_duration_ms
  → 任务成功率、耗时、意图排行、角色占比

AgentTask.steps_json
  → 工具调用次数、失败次数、失败率

AgentFeedback.rating / comment
  → 反馈数、好评率、差评率、最近任务反馈展示
```

### 5.3 HITL 规则链路

```text
工具返回 awaiting_confirmation
  → executor 根据 tool_name 查 HITL_RULES
  → 生成包含风险等级/文案/超时的 SSE 事件
  → hitl_manager 保存暂停状态
  → 前端展示通用确认卡片
  → 用户确认/取消
  → /agent/step/confirm 恢复或取消
  → 回写 AgentTask.status
```

### 5.4 腾讯地图 MCP 天气链路

```text
WeatherTool.run(location_text)
  → MCP 可用？
      → geocoder(address)
      → weather(adcode/location, type=now)
      → weather(adcode/location, type=future)
      → provider = tencent_mcp
  → MCP 不可用/失败？
      → address_to_location(policy=1)
      → query_weather(now/future)
      → provider = tencent_rest_fallback
```

### 5.5 结构化卡片链路

```text
weather_tool 结构化结果
  → executor._extract_cards()
  → cards = [{ type: "weather", data: ... }]
  → SSE done.cards
  → message.metadata.cards
  → WeatherCard.vue 渲染
```

---

## 六、v2.1 文件变动概览

### 后端核心变化

| 模块 | 变化 |
------|------|
| `agent_system/api/agent_api.py` | 新增反馈接口、监控接口、MCP 健康检查接口、HITL 规则字段输出 |
| `DAO/agent_dao.py` | 新增反馈 upsert、监控聚合、最近任务查询 |
| `agent_system/service/agent_service.py` | SSE `done` 扩展 `task_id/cards`，持久化 metadata |
| `agent_system/executor/agent_executor.py` | HITL 规则接入、cards 抽取、Persona prompt 注入 |
| `agent_system/hitl/escalation_rules.py` | 新增 HITL 轻量规则配置 |
| `agent_system/hitl/hitl_schema.py` | 扩展风险等级、文案、过期时间等字段 |
| `agent_system/hitl/hitl_manager.py` | 支持超时清理和暂停状态扩展 |
| `agent_system/tools/mcp_client.py` | 新增腾讯地图 MCP 通用客户端 |
| `agent_system/tools/weather_tool.py` | MCP 优先、REST 兜底、真实 geocoder→weather 链路 |
| `agent_system/prompts/persona_prompt.py` | 新增陪伴班主任 Persona |
| `agent_system/schemas/agent_response.py` | 响应模型新增 `cards` |

### 前端核心变化

| 模块 | 变化 |
------|------|
| `frontend-vue/src/views/AgentView.vue` | 反馈 UI、HITL 规则文案、天气卡片、Persona 空态联动、loading 双头像修复 |
| `frontend-vue/src/components/FloatingAgent.vue` | 反馈 UI、HITL 规则文案、紧凑天气卡片、loading 双头像修复 |
| `frontend-vue/src/components/WeatherCard.vue` | 新增天气卡片组件 |
| `frontend-vue/src/views/SystemView.vue` | 新增 Agent 监控子页 |

---

## 七、v2.1 验证结果

本版本每个功能都至少完成以下验证之一：

- Python 编译检查：`python -m compileall agent_system DAO model main.py`
- 前端生产构建：`npm.cmd run build`
- DAO/API 级内存数据验证
- SSE payload 字段验证
- 构建产物 CSS 污染检查
- 模板正则检查

已沉淀测试文档：

```text
docs/testing/Agent系统v2.1-任务级反馈闭环测试数据.md
docs/testing/Agent系统v2.1-Agent行为监控面板测试数据.md
docs/testing/Agent系统v2.1-HITL轻量规则系统测试数据.md
docs/testing/Agent系统v2.1-腾讯地图MCP能力底座测试数据.md
docs/testing/Agent系统v2.1-陪伴班主任Persona测试数据.md
docs/testing/Agent系统v2.1-天气卡片组件测试数据.md
docs/testing/Agent系统v2.1-Agent对话加载态回归测试数据.md
```

---

## 八、当前 Agent 系统能力矩阵

| 能力 | 说明 |
------|------|
| 多意图识别 | 支持成绩、学业分析、知识问答、NL2SQL、天气、邮件、陪伴、闲聊等场景 |
| 多工具调用 | 支持 score、student、rag、nl2sql、weather、email 等工具 |
| 流式回复 | SSE 分阶段返回意图、计划、工具调用、文本片段和完成事件 |
| HITL 确认 | 邮件等高风险操作支持规则化确认、取消、超时 |
| 反馈闭环 | 用户可对每次 Agent 回复点赞/点踩并填写原因 |
| 行为监控 | 管理员可查看调用量、成功率、耗时、工具失败率、反馈质量 |
| MCP 能力底座 | 腾讯地图 MCP 已接入，天气优先 MCP、失败 REST 兜底 |
| 结构化卡片 | 天气结果支持独立 Vue 卡片渲染 |
| 多 Persona | 学业导师、陪伴班主任等角色可影响回复风格 |
| 全局入口 | `/agent` 全页入口 + `FloatingAgent` 悬浮入口 |

---

## 九、v2.2 迭代目标建议

v2.1 已经把反馈、监控、HITL、MCP、卡片协议打通。v2.2 建议不要急着大规模上多 Agent 协作，而是围绕“记忆能力 + 地图能力扩展 + 卡片协议泛化”做一版稳步增强。

### P1：建议 v2.2 必做

#### 1. Agent 记忆系统一期：working_memory + summary_memory

目标：

- 将当前 executor 中临时 context 的职责拆出为 `working_memory.py`。
- 引入 `summary_memory.py`，对长对话做摘要压缩，并且前端对话历史标题显示摘要内容。
- 为后续长期用户画像打基础。

建议范围：

- `working_memory` 只保存当前任务执行中的关键中间结果。
- `summary_memory` 只做会话级摘要，不跨用户、不跨会话做长期记忆。
- 摘要内容需要明确隐私边界，尤其是陪伴类对话。

验收标准：

- 长对话不会无限塞入完整历史。
- 当前任务仍能读取必要上下文。
- 摘要失败不影响 Agent 正常回复。
- 陪伴班主任对话摘要不记录过度敏感细节。

#### 2. 腾讯地图 MCP 多能力扩展一期：通勤规划 Agent 能力

目标：

基于已接入的腾讯地图 MCP，优先实现一个真正有业务价值的地图 Agent 能力：**学生实习/外出通勤规划**。

建议使用 tools：

- `geocoder`
- `directionTransit`
- `directionDriving`
- `directionWalking`
- `weather`

示例问题：

```text
从学校到腾讯滨海大厦怎么去，今天适合出发吗？
我明天去实习公司，帮我看看公交和开车分别要多久。
从宿舍到南山科技园通勤方便吗？
```

设计原则：

- 后端新封装业务工具，例如 `commute_plan_tool`。
- Agent 不直接裸调 MCP route tools。
- 输出结构化结果，同时保留自然语言建议。
- 天气只作为辅助建议，不替代路线规划。

验收标准：

- 可返回起点、终点、出行方式、耗时、距离、天气提醒。
- MCP 失败时能给出明确失败原因。
- 不影响现有天气查询。

#### 3. 卡片协议泛化：route_card / poi_list_card

目标：

把天气卡片中的 `cards` 协议升级为通用卡片协议。

建议新增卡片类型：

- `route`：路线规划卡片。
- `poi_list`：周边地点列表卡片。
- `map_location`：单地点详情卡片。

设计原则：

- 后端只下发结构化数据。
- 前端按 `type` 选择组件。
- 组件读取主题变量，不写全局主题覆盖。
- 卡片失败不影响 Markdown 回复。

验收标准：

- AgentView 和 FloatingAgent 都能展示新卡片。
- 未知 card type 被安全忽略。
- 卡片字段缺失时不抛前端异常。

#### 4. 可视化回归测试：主题、卡片、加载态

目标：

把 v2.1 中出现过的 UI 回归纳入自动化检查。

建议覆盖：

- 浅色主题背景不被组件污染。
- 天气卡片跟随浅色/深色主题变量。
- Agent 等待回复时只有一个 assistant 头像。
- 卡片在主 Agent 和悬浮 Agent 中不溢出。

验收标准：

- 至少建立 Playwright 或等价浏览器测试脚本。
- 能在本地一条命令完成关键 UI 回归检查。
- 测试失败时能指出是哪类回归。

### P2：建议 v2.2 视时间实现

#### 5. 周边生活服务推荐 Agent 能力

基于腾讯地图 MCP：

- `placeSearchNearby`
- `placeDetail`
- `placeSuggestion`

可支持：

- 学校附近医院、餐饮、打印店、酒店查询。
- 实习企业周边生活服务推荐。
- 外出办事周边服务点推荐。

注意：

- 推荐结果应展示数据来源和距离。
- 不做“最好”“最安全”等绝对判断。
- 可用 `poi_list` 卡片承载。

#### 6. Agent 监控面板增强

建议增强项：

- 接入腾讯地图 MCP 健康状态。
- 展示 provider 分布：`tencent_mcp` vs `tencent_rest_fallback`。
- 展示反馈差评原因关键词。
- 最近任务详情弹窗展示 `steps_json` 和 `cards` 摘要。

#### 7. FloatingAgent Persona 记忆

当前陪伴班主任已接入主 Agent 的角色选择。后续可让悬浮 Agent：

- 支持角色选择。
- 记住用户最近使用的 persona。
- 对陪伴类对话使用更温和的空态和示例问题。

#### 8. WorkView 复用 WeatherCard

把已有 `WorkView` 天气展示逐步切换为通用 `WeatherCard.vue`，减少两套天气 UI 的维护成本。

### P3：暂缓到 v2.3 或 v3.0

| 方向 | 暂缓原因 |
|------|----------|
| 多 Agent 协作编排 | 需要 supervisor、任务状态机、跨角色上下文设计，适合 v3.0 |
| 长期用户画像 | 需要先跑一段时间反馈数据和记忆系统，避免过早建模 |
| Parser 层全面独立 | 有架构价值，但当前用户收益低于地图能力和记忆系统 |
| 多级审批流 | 当前 HITL 轻量规则足够，复杂审批会显著扩大权限模型 |

---

## 十、v2.2 推荐实施顺序

建议继续沿用 v2.1 的节奏，一个功能一个功能落地：

1. **Agent 记忆系统一期**：先解决长对话和上下文压缩。
2. **通勤规划 Agent 能力**：验证 MCP 路线工具的真实业务价值。
3. **卡片协议泛化**：为路线和 POI 做前端结构化展示。
4. **UI 可视化回归测试**：把主题和加载态问题自动化兜住。
5. **周边生活服务推荐**：在 MCP 地点搜索能力稳定后扩展。
6. **监控面板增强**：把 MCP 健康、provider 分布、差评原因接进运营视图。

---

## 十一、一句话总结

v2.1 已经完成 Agent 系统从“功能可用”到“可运营、可观测、可治理、可扩展”的关键升级；v2.2 建议继续围绕记忆系统和腾讯地图 MCP 多能力扩展推进，让 Agent 不只是会回答，还能记住上下文、规划路线、展示结构化结果，并通过自动化回归守住体验质量。
