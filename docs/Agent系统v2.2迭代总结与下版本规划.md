# Agent 系统 v2.2 迭代总结与下版本规划

> 本文档记录 Agent 系统 v2.2 从记忆系统、地图通勤能力、卡片协议、UI 回归护栏到历史摘要体验修复的完整迭代结果，并沉淀 v2.3 建议目标。

---

## 一、版本定位

v2.2 的版本主题是：**记忆压缩、地图业务化、结构化展示与体验回归护栏**。

v2.1 已完成反馈、监控、HITL、MCP 底座和天气卡片。v2.2 没有急着进入多 Agent 协作，而是先把几个基础能力做稳：

1. **记忆能力**：把历史上下文从“完整堆叠”改为“会话摘要 + 最近 5 条原文”。
2. **地图能力**：把腾讯地图 MCP 从天气扩展到通勤规划。
3. **卡片能力**：从天气卡片扩展到路线卡片，并建立卡片版本过滤。
4. **回归能力**：把主题、卡片、loading 和历史摘要布局纳入自动化检查。
5. **体验修复**：修复反馈重复提交、历史摘要排布和短会话摘要冗长问题。

一句话概括：

> v2.2 让 Agent 从“能调用工具并显示结果”进一步变成“能压缩上下文、规划真实路线、展示结构化卡片，并用自动化回归守住体验质量”的系统。

---

## 二、迭代范围与状态

### 2.1 已完成

| # | 功能 | 优先级 | 状态 | 测试文档 |
|---|------|--------|------|----------|
| 1 | Agent 记忆系统一期：working_memory + summary_memory | P1 | 已完成 | `docs/testing/Agent系统v2.2-记忆系统一期测试数据.md` |
| 2 | 反馈按钮历史回放锁定回归 | 回归修复 | 已完成 | `docs/testing/Agent系统v2.2-反馈按钮历史回放锁定回归测试.md` |
| 3 | 通勤规划 Agent 能力 | P1 | 已完成 | `docs/testing/Agent系统v2.2-通勤规划Agent能力测试数据.md` |
| 4 | route 卡片协议泛化 | P1 | 已完成 | `docs/testing/Agent系统v2.2-route卡片协议泛化测试数据.md` |
| 5 | UI 可视化回归检查 | P1 | 已完成 | `docs/testing/Agent系统v2.2-UI可视化回归检查测试数据.md` |
| 6 | Agent 历史摘要右侧布局 | 体验修复 | 已完成 | `docs/testing/Agent系统v2.2-历史摘要右侧布局回归测试数据.md` |
| 7 | 短会话标题式摘要策略 | 体验修复 | 已完成 | `docs/testing/Agent系统v2.2-历史摘要右侧布局回归测试数据.md` |

### 2.2 顺延到 v2.3

以下是 v2.1 总结文档中列出的 v2.2 P2 / 视时间目标，本轮未展开实现，建议进入 v2.3：

| # | 功能 | 顺延原因 |
|---|------|----------|
| 1 | 周边生活服务推荐 Agent 能力 | 依赖 POI 搜索、地点详情和 `poi_list` 卡片闭环，适合单独做一轮 |
| 2 | Agent 监控面板增强 | 需要把 MCP provider、健康状态、差评原因等运营指标重新组织 |
| 3 | FloatingAgent Persona 记忆 | 需要先明确“会话级记忆”和“用户偏好记忆”的边界，避免误做长期画像 |
| 4 | WorkView 复用 WeatherCard | 属于 UI 组件复用优化，收益明确但优先级低于地图能力和回归护栏 |
| 5 | Supervisor 多 Agent 协作设计 | 已讨论过设计方向，建议作为 v2.3/v3.0 的架构型目标 |

结论：**v2.2 P1 主线已完成，P2 项未算漏项，统一顺延到下个版本。**

---

## 三、关键设计决策

| 决策点 | 最终方案 | 原因 |
|--------|----------|------|
| 记忆上下文 | 会话摘要 + 最近 5 条原文 | 避免长对话无限塞上下文，同时保留最近上下文细节 |
| 摘要触发 | 每轮回复后刷新摘要 | 历史列表能尽快展示摘要，不再长期显示“Agent 对话” |
| 短会话摘要 | 5 轮以内用第一轮用户问题生成短标题 | 避免短对话被总结成全文复盘 |
| 用户画像 | 不展示给用户 | 当前只做会话级摘要，不做跨会话长期画像 |
| 通勤输入校验 | LangGraph 中间件先检查起点、终点、方式 | 输入缺失时直接进入 `clarification`，不误调 MCP |
| 地图工具调用 | 后端封装 `commute_plan_tool` | Agent 不直接裸调 MCP route tools，业务边界更清楚 |
| 地理编码 | MCP geocoder 优先，REST 宽松模式兜底 | 解决“宝安/龙岗”等短区名 MCP 偶发无坐标问题 |
| 通勤状态 | 新增 `clarification`、`partial_success` | 区分“需补充信息”和“部分路线可用” |
| route 卡片 | 仅落地 `type=route`，`poi_list/map_location` 预留 | 当前业务先服务通勤规划，POI 等到生活服务推荐再做 |
| 卡片版本 | `card_version=1`，前端过滤未知版本 | 防止旧协议或未来协议字段变化导致前端异常 |
| UI 回归 | 静态护栏 + Playwright Edge 真浏览器回归 | 不只查源码，也能真实验证 DOM、主题和移动端溢出 |
| 历史摘要布局 | 右侧摘要栏，主区只保留当前对话 | 历史不再打断当前聊天，信息架构更清楚 |

---

## 四、功能实现详解

### 4.1 Agent 记忆系统一期

目标：
- 拆出工作记忆和摘要记忆。
- 长对话不再把完整历史无限塞进上下文。
- 为后续长期用户画像打基础，但本轮不做跨会话画像。

设计：
- `working_memory.py` 负责把数据库消息转成 LLM 可读历史项、截取最近 5 条原文、估算上下文长度。
- `summary_memory.py` 负责会话摘要生成、兜底摘要、摘要保存和上下文组装。
- `conversation_memory.get_history()` 默认返回“会话摘要 + 最近 5 条原文”。

具体实现：
- 新增 `agent_system/memory/working_memory.py`。
- 新增 `agent_system/memory/summary_memory.py`。
- 修改 `agent_system/memory/conversation_memory.py`，把历史读取接到 `build_summary_context()`。
- 摘要失败只记录 warning，不阻断 Agent 回复。

后续修正：
- 根据历史摘要 UI 反馈，摘要刷新改为每轮回复后即时刷新。
- 5 轮以内会话使用第一轮用户问题生成短标题。
- 长会话 LLM 摘要提示词改为“24 字以内标题式摘要”，不再生成全文复盘。

核心链路：

```text
用户消息 / Agent 回复保存
  → refresh_summary_safely()
  → 5 轮以内：第一轮问题短标题
  → 5 轮以上：LLM 标题式摘要
  → TalkSession.summary / session_title 更新
  → get_history() 返回 summary + 最近 5 条原文
```

测试结论：
- `python -m compileall agent_system DAO model main.py` 通过。
- 摘要样例：
  - `从宝安到龙岗坐地铁怎么去？` → `从宝安到龙岗坐地铁怎么去`
  - `帮我查一下我的成绩` → `查一下我的成绩`

### 4.2 反馈按钮历史回放锁定回归

问题：
- 已反馈过的 Agent 历史消息，切换历史会话后反馈按钮又变成可点击。
- 这会破坏“每轮对话只能反馈一次”的规则。

设计：
- 后端历史消息接口返回已提交反馈状态。
- 前端恢复历史消息时重建 `feedback.submitted = true`。
- 后端重复提交返回 409，形成双保险。

具体实现：
- `/agent/sessions/{session_id}/messages` 聚合 `AgentFeedback`。
- `AgentView.vue` 的 `loadSession()` 从 `metadata.feedback` 恢复按钮锁定状态。
- `createFeedback(taskId, saved)` 支持历史反馈初始化。

核心链路：

```text
切换历史会话
  → GET /agent/sessions/{id}/messages
  → 后端注入 metadata.feedback
  → 前端 createFeedback(task_id, saved)
  → submitted=true 时按钮禁用
```

测试结论：
- 历史回放后已反馈按钮保持锁定。
- 重复提交由后端拒绝。

### 4.3 通勤规划 Agent 能力

目标：
- 基于腾讯地图 MCP 实现学生实习/外出通勤规划。
- 支持公交/地铁、开车、步行等方式。
- 天气只作为辅助，不阻断路线结果。

设计：
- 用 LangGraph 中间件先检查通勤输入完整性。
- 必填项：起点、终点、出行方式。
- 缺字段直接返回 `clarification`，不调用 MCP。
- 完整请求进入 `commute_plan_tool`。
- 工具内部封装 `geocoder`、`directionTransit`、`directionDriving`、`directionWalking` 和天气辅助查询。

具体实现：
- 新增 `agent_system/middleware/commute_parser.py`。
- 新增 `agent_system/middleware/commute_input_checker.py`。
- 修改 `agent_system/middleware/middleware_graph.py`，接入通勤输入检查节点。
- 新增 `agent_system/tools/commute_plan_tool.py`。
- planner / executor 注册 `commute_plan_tool`。
- 新增 `clarification` 和 `partial_success` 状态。
- `requirements.txt` 增加 `langgraph`、`mcp`。

关键修复：
- “从宝安到龙岗坐地铁怎么去”最初出现终点被截成“龙”的问题，后改为显式按“从 / 到”切分，再按出行方式尾词裁剪。
- 腾讯 MCP geocoder 对“宝安/龙岗”等短区名偶发不返回坐标，增加 REST `address_to_location(policy=1)` 兜底。
- 支持深圳默认短区名补全，也支持用户明确城市时的广州等跨城市行政区补全。

核心链路：

```text
用户输入
  → LangGraph 中间件解析通勤意图
  → 缺起点/终点/方式：clarification
  → 完整：commute_plan_tool
  → normalize_geocode_address()
  → MCP geocoder
  → REST geocoder fallback
  → directionTransit / directionDriving / directionWalking
  → WeatherTool 辅助提醒
  → success / partial_success / error
```

测试结论：
- MCP SDK 依赖验证通过。
- 深圳短区名解析通过。
- 跨城市行政区补全通过。
- MCP geocoder 无坐标时 REST 兜底通过。

### 4.4 route 卡片协议泛化

目标：
- 把天气卡片中的 `cards` 协议扩展为通用卡片协议。
- 本轮优先落地路线规划卡片。

设计：
- 后端继续生成结构化 `cards`。
- 前端按 `card.type` 选择组件。
- 卡片版本通过 `card_version` 控制兼容。
- 未知类型或未知版本安全忽略。

具体实现：
- `agent_system/executor/agent_executor.py` 的 `_extract_cards()` 支持从 `commute_plan_tool` 提取 `type=route` 卡片。
- weather / route 卡片补充 `card_version=1`。
- 新增 `frontend-vue/src/components/RouteCard.vue`。
- `AgentView.vue` 和 `FloatingAgent.vue` 接入 `RouteCard`。
- `FloatingAgent` 使用 `compact` 模式展示路线卡片。

保留边界：
- `poi_list`、`map_location` 只作为协议方向预留，本轮不实现组件。
- 后续周边生活服务推荐再完整落地 `poi_list`。

核心链路：

```text
commute_plan_tool 结构化结果
  → executor._extract_cards()
  → cards = [{ type: "route", card_version: 1, data: ... }]
  → SSE done.cards
  → AgentView / FloatingAgent
  → RouteCard.vue
```

测试结论：
- 主 Agent 和悬浮 Agent 均能渲染 route card。
- 未知版本被过滤。
- 字段缺失时卡片安全降级。

### 4.5 UI 可视化回归检查

目标：
- 把主题污染、卡片渲染、loading 双头像等高频 UI 回归纳入自动化检查。

设计：
- 第一层：静态护栏脚本，检查源码和构建产物。
- 第二层：Playwright 驱动本机 Microsoft Edge 做真实 DOM 回归。
- 不依赖真实后端，脚本内 mock 登录态、Persona、会话和 SSE。

具体实现：
- 新增 `frontend-vue/scripts/ui-regression-check.mjs`。
- 新增 `frontend-vue/scripts/ui-regression-playwright.mjs`。
- `package.json` 增加：
  - `test:ui-regression:static`
  - `test:ui-regression:e2e`
  - `test:ui-regression`
- 安装 `@playwright/test`。
- 浏览器使用 `chromium.launch({ channel: "msedge" })`，复用本机 Edge，不下载 Playwright Chromium。

检查内容：
- WeatherCard / RouteCard 不覆盖全局主题。
- 卡片读取项目 CSS 变量。
- AgentView / FloatingAgent 都接入 weather / route 卡片。
- 未知 card type / card_version 安全过滤。
- loading 只复用当前 assistant 消息，不新增第二个头像。
- 右侧历史摘要栏存在，旧横向会话 chip 不再渲染。

测试结论：

```text
npm.cmd run test:ui-regression
UI 回归检查通过：40/40
Playwright UI 回归通过：2/2
```

### 4.6 Agent 历史摘要右侧布局

问题：
- 会话摘要显示在主聊天区域上方，打断当前对话。
- 历史会话横向排列，内容重复且占空间。
- 历史项显示“Agent 对话”，不能快速识别内容。
- 用户画像/风格字段不应该展示给用户。

设计：
- 左侧只保留当前对话。
- 右侧独立展示历史摘要。
- 历史项只展示 `summary` 和时间。
- 不再回退显示 `session.title`，避免再次出现“Agent 对话”。
- 无摘要时显示“摘要生成中，继续对话后会自动更新。”

具体实现：
- `AgentView.vue` 新增 `agent-workspace` 左右布局。
- 主聊天区添加 `agent-chat-main`。
- 右侧新增 `agent-summary-panel`。
- 新增 `sessionSummary(session)`。
- 删除旧横向 `agent-session-chip` UI。
- 回归脚本新增历史摘要栏静态检查和 Edge DOM 检查。

核心链路：

```text
GET /agent/sessions
  → [{ id, title, summary, update_time }]
  → AgentView 只读取 summary / update_time
  → 右侧历史摘要列表
  → 点击摘要项 loadSession(id)
  → 左侧恢复当前会话消息
```

测试结论：
- 历史列表移动到右侧。
- 不展示默认“Agent 对话”标题。
- 不展示用户画像信息。
- UI 回归静态检查和 Edge 回归均通过。

---

## 五、验证结果

本版本主要执行过以下验证：

```text
python -m compileall agent_system DAO model main.py
npm.cmd run build
npm.cmd run test:ui-regression
```

关键结果：

```text
后端编译通过
前端生产构建通过
UI 回归检查通过：40/40
Playwright UI 回归通过：2/2
```

已沉淀测试文档：

```text
docs/testing/Agent系统v2.2-记忆系统一期测试数据.md
docs/testing/Agent系统v2.2-反馈按钮历史回放锁定回归测试.md
docs/testing/Agent系统v2.2-通勤规划Agent能力测试数据.md
docs/testing/Agent系统v2.2-route卡片协议泛化测试数据.md
docs/testing/Agent系统v2.2-UI可视化回归检查测试数据.md
docs/testing/Agent系统v2.2-历史摘要右侧布局回归测试数据.md
```

---

## 六、当前 Agent 能力矩阵

| 能力 | v2.2 后状态 |
|------|-------------|
| 多轮上下文 | 会话摘要 + 最近 5 条原文 |
| 历史摘要 | 每轮回复后更新，5 轮内使用第一轮问题短标题 |
| 反馈闭环 | 历史回放后仍锁定已提交反馈 |
| 通勤规划 | 支持起点、终点、出行方式校验与路线规划 |
| 输入澄清 | `clarification` 状态独立表达 |
| 部分成功 | `partial_success` 状态表达部分路线失败 |
| 地图 MCP | 通勤路线优先 MCP，地理编码可 REST 兜底 |
| 天气辅助 | 通勤天气失败不影响路线规划 |
| 结构化卡片 | 支持 weather / route |
| 卡片兼容 | `card_version=1`，未知版本过滤 |
| UI 回归 | 静态护栏 + Edge 真浏览器回归 |
| 历史列表 | 右侧摘要栏，仅展示摘要内容 |

---

## 七、v2.3 迭代目标建议

v2.3 建议承接 v2.2 顺延项，并开始为多 Agent 协作做架构准备。推荐主题：

> **地图生活服务扩展 + 运营观测增强 + Supervisor 架构预研**

### P1：建议必做

#### 1. 周边生活服务推荐 Agent 能力

目标：
- 基于腾讯地图 MCP 的 POI 能力，支持学校/实习企业/办事地点周边服务推荐。

建议使用 MCP tools：
- `placeSearchNearby`
- `placeDetail`
- `placeSuggestion`
- `geocoder`

典型问题：
```text
学校附近有哪些医院？
腾讯滨海大厦附近有什么吃饭的地方？
实习公司附近有没有打印店？
```

设计原则：
- 不做“最好”“最安全”等绝对判断。
- 展示数据来源、距离、地址、类别。
- 结果使用 `poi_list` 卡片承载。
- 单个地点详情可预留 `map_location` 卡片。

建议实现：
- 新增 `nearby_service_tool.py`。
- 新增 `nearby_parser.py` 或接入现有 LangGraph 中间件。
- 新增 `PoiListCard.vue`。
- executor `_extract_cards()` 支持 `type=poi_list`。

#### 2. Agent 监控面板增强

目标：
- 把 v2.2 新增的地图、provider、卡片和反馈信息接入运营视图。

建议增强项：
- MCP 健康状态展示。
- provider 分布：`tencent_mcp` vs `tencent_rest_fallback`。
- `clarification` / `partial_success` 独立统计。
- 最近任务详情弹窗展示 `steps_json`、`cards` 摘要。
- 差评原因关键词粗聚合。

设计原则：
- 保持轻量，不急着引入复杂图表库。
- 管理员能回答三个问题：哪些意图高频、哪些工具不稳定、用户为什么不满意。

#### 3. Supervisor 多 Agent 协作设计一期

目标：
- 不急着大规模实现，但先完成架构设计和一个最小可跑闭环。

建议角色：
- `SupervisorAgent`：负责意图拆解、任务分派、状态汇总。
- `AcademicAgent`：成绩、学业分析、校务知识。
- `MapAgent`：通勤规划、POI、天气地图相关能力。
- `CommunicationAgent`：邮件生成、HITL 确认。

关键判断：
- 腾讯地图 MCP 不适合当 Supervisor，它更适合放在 `MapAgent` 下。
- Supervisor 应该是轻编排层，不直接操作所有 MCP tools。

建议先做：
- 设计 `agent_role` / `handoff` 数据结构。
- 明确 Supervisor 状态机：`route`、`delegate`、`merge`、`clarify`、`complete`。
- 先选一个跨域场景试点，例如“去实习公司路线 + 写邮件通知老师”。

### P2：建议视时间实现

#### 4. FloatingAgent Persona 记忆

目标：
- 悬浮 Agent 支持角色选择。
- 记住用户最近使用的 persona。
- 陪伴班主任角色的空态和示例问题更温和。

注意边界：
- 只记 UI 偏好，不扩展成长期用户画像。
- 不在前端展示用户画像。

#### 5. WorkView 复用 WeatherCard

目标：
- 把 WorkView 的天气 UI 逐步切到通用 `WeatherCard.vue`。
- 减少两套天气展示维护成本。

建议方式：
- 先做只读展示复用。
- 保留 WorkView 原查询表单。
- WeatherCard 继续只消费结构化数据，不解析 Markdown。

#### 6. 卡片协议继续泛化

目标：
- 完成 `poi_list`、`map_location` 两类卡片。
- 补充卡片协议文档，明确每类卡片字段。

建议：
- `route`、`weather`、`poi_list`、`map_location` 都使用 `card_version=1`。
- 前端继续使用未知类型/未知版本安全忽略策略。

### P3：暂缓

| 方向 | 暂缓原因 |
|------|----------|
| 长期用户画像 | 需要更多真实反馈数据，且隐私边界要更明确 |
| 多级审批流 | 当前 HITL 轻量规则足够，复杂审批会扩大权限模型 |
| 大规模多 Agent 自动协作 | 需要 Supervisor 状态机、任务持久化和失败恢复先成熟 |
| Parser 层全面独立 | 有架构价值，但当前业务收益低于 POI 和监控增强 |

---

## 八、建议实施顺序

建议 v2.3 继续沿用“一次一个功能、完成后产出测试文档、用户确认后再进入下一个”的节奏：

1. **周边生活服务推荐 Agent 能力**：先把 POI 搜索跑通。
2. **poi_list / map_location 卡片**：让周边服务有结构化展示。
3. **Agent 监控面板增强**：接入 provider、clarification、partial_success、差评原因。
4. **Supervisor 多 Agent 协作设计一期**：先写架构和最小闭环，不急着铺开。
5. **FloatingAgent Persona 记忆**：做轻量 UI 偏好记忆。
6. **WorkView 复用 WeatherCard**：做组件复用收口。

---

## 九、一句话总结

v2.2 已经完成 Agent 系统的记忆压缩、通勤地图能力、route 卡片展示和 UI 回归护栏；v2.3 建议顺势扩展 POI 周边生活服务、增强运营监控，并开始设计 Supervisor 多 Agent 协作，让 Agent 从“单体工具编排”逐步走向“可分工、可观测、可治理的多 Agent 系统”。
