# Agent 系统 v2.1 功能需求设计

> 本文档基于 `Agent系统v2.0迭代总结与下版本规划.md` 的“八、下版本迭代目标”梳理，并结合本轮 grill-me 已确认的设计决策形成。v2.1 的重点不是继续堆叠新工具，而是把 v2.0 已完成的 Agent 能力接入反馈、监控、治理和可复用 MCP 底座，形成可运营、可观察、可持续迭代的闭环。

---

## 一、版本定位

**版本名称**：Agent 系统 v2.1：运营闭环与可观测版本

**主线目标**：优先建设 Agent 运营闭环，而不是优先新增 Agent 能力。

v2.0 已经完成：

- 8 种 Agent 意图。
- 6 个工具。
- 1 条 HITL 邮件确认流。
- 3 层输入中间件。
- 独立 `AgentTask` / `AgentFeedback` 数据表。
- 全局 `FloatingAgent` 入口。

v2.1 要解决的问题是：

- 用户对回答是否满意，目前没有反馈入口。
- 管理员不知道 Agent 调用量、耗时、失败率和角色使用情况。
- HITL 仍偏邮件专用，缺少通用高风险操作确认规则。
- 腾讯地图 MCP 不应只做天气补丁，而应沉淀为后续地图能力复用底座。

---

## 二、迭代范围总览

### P1：本版本必做

| # | 功能 | 优先级 | 目标 |
|---|------|--------|------|
| 1 | Agent 任务级反馈闭环 | P1 | 让用户可对每次 Agent 回复点赞/点踩，并沉淀反馈数据 |
| 2 | Agent 行为监控面板 | P1 | 让管理员看见调用量、成功率、耗时、失败工具和反馈质量 |
| 3 | HITL 轻量规则系统 | P1 | 将邮件确认抽象为可配置的高风险动作确认规则 |
| 4 | 腾讯地图 MCP 能力底座 + 天气首发接入 | P1 | MCP 优先，失败自动降级，同时为后续地图 tool 扩展打基础 |

### P2：P1 完成后择机实现

| # | 功能 | 优先级 | 目标 |
|---|------|--------|------|
| 5 | 陪伴班主任 Persona | P2 | 增加共情陪伴型角色，但不改变工具选择逻辑 |
| 6 | 天气卡片 Vue 组件 | P2 | 将结构化天气数据渲染为卡片，替代纯文本天气播报 |

### 暂不纳入 v2.1

| 功能 | 处理方式 | 原因 |
|------|----------|------|
| `working_memory.py` / `summary_memory.py` | 移至 v2.2 预研 | 会扩大记忆、摘要、隐私和上下文压缩设计面 |
| 多 Agent 协作编排 | 放入 v3.0 路线图 | 需要 `supervisor_agent.py`、跨角色状态机和任务编排 |
| 长期用户画像 | 后续基于反馈数据沉淀再做 | v2.1 才开始收集反馈，数据基础不足 |
| Parser 层独立 | 后续架构优化项 | 当前不是用户价值最高的改造点 |

---

## 三、P1-1：Agent 任务级反馈闭环

### 3.1 需求目标

建立从“Agent 回复”到“用户评价”的最小闭环，为后续效果评估、用户画像和回答质量优化提供数据基础。

### 3.2 反馈粒度

v2.1 先做**任务级反馈**，暂不做工具步骤级反馈。

设计原则：

- 用户对一次 Agent 回复整体点赞或点踩。
- 后端反馈绑定 `AgentTask.id`。
- `AgentFeedback.tool_name` 继续保留为空，作为后续步骤级反馈扩展字段。
- 前端只有拿到 SSE `done.task_id` 后才展示反馈按钮。
- HITL 等待确认类回复也允许反馈，反馈对象仍是本次 Agent 任务整体体验。

### 3.3 重复反馈策略

同一个任务重复反馈时，采用 **upsert 覆盖旧反馈**，不重复新增多条记录。

规则：

- 任务级唯一口径：`task_id + tool_name is null`。
- 用户只能反馈自己的 `AgentTask`。
- 如果已有反馈，则更新 `rating/comment`。
- 如果没有反馈，则新增。
- 暂不在 `AgentFeedback` 冗余存储 `user_id`，通过 `AgentTask.user_id` 校验归属。

### 3.4 后端 API 设计

#### `POST /agent/feedback`

请求体：

```json
{
  "task_id": 123,
  "rating": 5,
  "comment": "回答很清楚",
  "tool_name": null
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | int | 是 | 关联的 `AgentTask.id` |
| `rating` | int | 是 | 评分，范围 1-5；点赞默认 5，点踩默认 1 |
| `comment` | string | 否 | 用户补充评价 |
| `tool_name` | string | 否 | v2.1 任务级反馈先传空，后续步骤级反馈使用 |

返回体：

```json
{
  "feedback_id": 88,
  "task_id": 123,
  "rating": 5,
  "comment": "回答很清楚",
  "updated": false
}
```

### 3.5 SSE 改造

`done` 事件新增 `task_id`：

```json
{
  "intent": "weather_query",
  "persona": "academic_mentor",
  "tool_calls": [],
  "sources": null,
  "reply": "今天深圳天气...",
  "task_id": 123
}
```

### 3.6 前端改造

覆盖两个 Agent 入口：

- `frontend-vue/src/views/AgentView.vue`
- `frontend-vue/src/components/FloatingAgent.vue`

交互要求：

- 助手消息完成后显示点赞/点踩按钮。
- 点赞默认提交 `rating=5`。
- 点踩默认提交 `rating=1`，并允许填写简短原因。
- 已反馈后显示当前状态，允许用户再次点击修改反馈。
- HITL 确认卡片中的反馈按钮放在“确认发送/取消发送”下方，避免混淆。

### 3.7 验收标准

- Agent 正常回复后，前端能展示反馈按钮。
- 点赞/点踩能成功写入 `AgentFeedback`。
- 同一任务重复反馈时不会新增多条任务级反馈。
- 用户无法反馈不属于自己的 `AgentTask`。
- `done` 事件中稳定返回 `task_id`。

---

## 四、P1-2：Agent 行为监控面板

### 4.1 需求目标

基于 `AgentTask` 和 `AgentFeedback`，为管理员提供轻量 Agent 运营监控视图，帮助判断：

- Agent 用得多不多。
- Agent 是否稳定。
- 哪些意图最常用。
- 哪些工具最容易失败。
- 用户对回答是否满意。

### 4.2 页面位置

监控面板放入现有 `SystemView.vue`，作为系统管理第三个子页：

- 用户管理
- 角色权限
- Agent 监控

暂不新增一级菜单。

权限策略：

- v2.1 先复用 `system:page` 或管理员角色访问。
- 后续可独立拆分 `agent:monitor` 权限。

### 4.3 UI 形态

第一版做轻量工作台，不引入 ECharts 等复杂图表库。

页面结构：

1. 顶部指标卡。
2. 分布区。
3. 最近任务表。
4. 筛选条件。

### 4.4 顶部指标卡

默认统计近 7 天：

- 总调用量。
- 任务成功率。
- 平均耗时。
- p50 耗时。
- p99 耗时。
- 反馈数。
- 好评率。

### 4.5 分布区

建议展示：

- 意图调用排行。
- 角色使用占比。
- 工具失败排行。
- 每日调用趋势。

每日趋势第一版可用 CSS 条形图或列表展示，不强依赖图表库。

### 4.6 最近任务表

字段建议：

| 字段 | 说明 |
|------|------|
| 时间 | `AgentTask.create_time` |
| 用户 | `AgentTask.user_id` |
| 角色 | `AgentTask.persona` |
| 意图 | `AgentTask.intent` |
| 状态 | `AgentTask.status` |
| 耗时 | `AgentTask.total_duration_ms` |
| 工具调用 | 从 `steps_json/tool_calls` 摘要 |
| 用户反馈 | 关联 `AgentFeedback.rating/comment` |
| 原始问题 | `original_message` 截断展示 |

### 4.7 筛选条件

- 时间范围：1 天 / 7 天 / 30 天。
- 状态：全部 / 成功 / 失败 / HITL 等待 / 已取消。
- 意图：全部 / 指定意图。

### 4.8 统计口径

#### 任务成功率

主指标按 `AgentTask.status` 统计：

- `success`：成功。
- `error`：失败。
- `cancelled`：单独统计，不混入失败率。
- `awaiting_hitl`：单独统计，不混入失败率。
- `running/pending`：不纳入完成率，避免正在执行的任务影响口径。

#### 工具失败率

辅助诊断指标从 `AgentTask.steps_json` 解析：

- 每个工具调用次数。
- 每个工具成功次数。
- 每个工具失败次数。
- 每个工具失败率。

一句话口径：**管理员看任务成功率，工程师看工具失败率。**

### 4.9 后端 API 设计

#### `GET /agent/admin/metrics?days=7`

返回：

- 总调用量。
- 成功率。
- 平均耗时。
- p50/p99。
- 反馈数。
- 好评率。
- 差评率。

#### `GET /agent/admin/metrics/timeseries?days=7`

返回：

- 按天调用量。
- 按天失败量。
- 按天平均耗时。

#### `GET /agent/admin/metrics/intents?days=7`

返回：

- 各意图调用数。
- 各意图平均耗时。
- 各意图 p50/p99。

#### `GET /agent/admin/metrics/tools?days=7`

返回：

- 各工具调用次数。
- 成功次数。
- 失败次数。
- 失败率。

#### `GET /agent/admin/tasks?limit=50`

返回最近任务列表，用于排查具体问题。

### 4.10 验收标准

- 管理员可在系统管理中进入 `Agent监控`。
- 默认展示近 7 天指标。
- 能看到任务成功率和工具失败率。
- 能看到最近任务表。
- 筛选条件生效。
- 不引入新的复杂图表依赖。

---

## 五、P1-3：HITL 轻量规则系统

### 5.1 需求目标

将 v2.0 的邮件专用 HITL 确认，抽象为轻量规则系统，为后续更多高风险操作提供统一确认入口。

### 5.2 设计边界

v2.1 做轻量规则系统，不做复杂多级审批流。

本版本支持：

- 按 `tool_name` 配置是否需要确认。
- 配置风险等级：`low / medium / high`。
- 配置确认标题和确认说明。
- 配置超时时间。
- 超时自动取消。
- 取消后回写状态。

本版本不做：

- 多级审批人。
- 审批流转记录。
- 短信/邮件通知管理员。
- 复杂审批权限矩阵。

### 5.3 规则配置

新增 `agent_system/hitl/escalation_rules.py`：

```python
"""HITL 高风险操作规则配置"""

HITL_RULES = {
    "email_tool": {
        "enabled": True,
        "risk_level": "medium",
        "timeout_seconds": 600,
        "confirm_title": "确认发送邮件",
        "confirm_message": "请确认收件人、主题和正文无误后再发送。"
    }
}
```

### 5.4 状态扩展

`HitlState` 建议增加：

- `risk_level`
- `confirm_title`
- `confirm_message`
- `expires_at`
- `rule`

### 5.5 执行逻辑

1. 工具返回 `status="awaiting_confirmation"`。
2. executor 根据 `tool_name` 查找 HITL 规则。
3. 生成 `awaiting_confirmation` SSE 数据。
4. `hitl_manager` 保存暂停状态和过期时间。
5. 前端展示通用确认卡片。
6. `/agent/step/confirm` 恢复时检查是否过期。
7. 超时后返回“确认已过期，请重新发起任务”。

### 5.6 验收标准

- 邮件工具仍能正常预览、确认、取消。
- 确认文案来自规则配置，而不是写死在前端或 executor。
- 超时后无法继续确认。
- 超时或取消后状态能正确回写。
- 后续新增高风险工具时，只需配置规则和工具封装即可接入 HITL。

---

## 六、P1-4：腾讯地图 MCP 能力底座 + 天气首发接入

### 6.1 需求目标

接入腾讯地图 MCP，但不把它做成天气专用补丁，而是沉淀为后续地图能力可复用的 MCP 工具网关。

天气查询作为 v2.1 首个正式接入场景：

- 优先走 MCP。
- MCP 不可用时自动降级到现有 REST 链路。
- 不影响 FastAPI 启动。
- 不影响 planner/executor 对外接口。

### 6.2 设计原则

- MCP 是增强路线，不是系统生死线。
- MCP 客户端应复用，不要命名为天气专用客户端。
- Agent 不能裸调用所有 MCP tool，必须通过后端工具白名单封装。
- 天气功能对外仍是 `weather_tool`，planner/executor 不需要改动。

### 6.3 新增 MCP 客户端

新增文件：

```text
agent_system/tools/mcp_client.py
```

建议类名：

```python
class TencentMapMcpClient:
    """腾讯地图 MCP 客户端，封装连接、工具发现、调用和健康状态"""
```

核心职责：

- 读取 `.env` 中的腾讯地图 key。
- 构造 MCP 地址：`https://mcp.map.qq.com/mcp?key=<KEY>&format=0`。
- FastAPI startup 时初始化连接。
- 做 tool discovery，并缓存可用 tool 列表。
- 提供 `call_tool(tool_name, arguments)`。
- 记录最近一次错误。
- shutdown 时释放连接。
- 初始化失败只记录 warning，不阻止应用启动。

### 6.4 健康状态

客户端需提供内部状态：

- 是否启用。
- 是否连接成功。
- 已发现的 tool 列表。
- 最近一次失败原因。
- 最近一次成功调用时间。

后续可接入监控面板。

### 6.5 天气工具接入方式

`WeatherTool.run()` 内部改造：

1. 校验 `location_text`。
2. 优先调用 MCP 天气相关 tool。
3. MCP 调用成功，统一格式化为当前 `weather_tool` 输出结构。
4. MCP 调用失败、超时或返回结构异常时，降级到：
   - `address_to_location(location_text, policy=1)`
   - `query_weather(location=lat,lng, weather_type=...)`
5. 返回结果新增 `provider`。

返回示例：

```json
{
  "success": true,
  "provider": "tencent_mcp",
  "location_text": "深圳",
  "weather": {}
}
```

降级返回：

```json
{
  "success": true,
  "provider": "tencent_rest_fallback",
  "location_text": "深圳",
  "weather": {}
}
```

### 6.6 后续可封装的 MCP 能力

腾讯地图 MCP 提供大量 tool，v2.1 先不一次性全部暴露，后续按需封装。已实测 `list_tools()` 返回 15 个 tool：

| 能力组 | MCP tools | 后续 Agent 功能方向 |
|--------|-----------|---------------------|
| 地址解析与位置语义 | `geocoder`、`reverseGeocoder`、`ipLocation` | 地址标准化、签到位置语义核验、账号所在地辅助判断 |
| 地点与周边搜索 | `placeSuggestion`、`placeSearchNearby`、`placeDetail` | 学校/实习企业周边餐饮、酒店、医院、打印店、办事点推荐 |
| 天气 | `weather` | 天气卡片、异常天气提醒、通勤/外出建议 |
| 路线规划 | `directionDriving`、`futureDrivingDirection`、`directionTransit`、`directionWalking`、`directionBicycling` | 学生实习通勤规划、外出拜访路线建议、不同出行方式对比 |
| 距离矩阵 | `matrix` | 多学生、多企业、多校区之间的距离/耗时批量评估 |
| 多点与沿途能力 | `waypointOrder`、`placeAlongby` | 多点拜访路线优化、沿途停车场/充电站/服务区推荐 |

后续版本建议优先开发：

1. **学生实习通勤规划 Agent 能力**：结合 `geocoder + directionTransit/directionDriving + weather`，回答“从学校到某企业怎么去、要多久、天气是否影响出行”。
2. **周边生活服务推荐 Agent 能力**：结合 `placeSearchNearby + placeDetail`，围绕学校、宿舍、实习企业查询餐饮、医院、打印店、酒店等。
3. **外出拜访行程助手**：结合 `waypointOrder + directionDriving + placeAlongby`，为老师/管理员规划多企业拜访顺序和沿途服务点。
4. **多地点距离评估**：结合 `matrix`，批量评估学生住所、学校、企业之间的通勤成本，为就业/实习安排提供参考。
5. **签到位置语义核验**：结合 `reverseGeocoder + ipLocation`，辅助判断提交位置是否处于合理区域，注意仅做辅助提示，不做强风控裁决。
- 距离计算。
- 周边服务推荐。

### 6.7 验收标准

- 无腾讯地图 key 或 MCP 初始化失败时，后端仍可启动。
- 天气查询优先尝试 MCP。
- MCP 失败时自动降级 REST 链路。
- 降级原因写入日志。
- `weather_tool` 对 planner/executor 的接口不变。
- MCP 客户端具备可复用结构，后续可按需封装其他腾讯地图 tool。

---

## 七、P2-1：陪伴班主任 Persona

### 7.1 需求目标

新增共情陪伴型角色，覆盖学习压力、日常鼓励、轻量学习计划建议等场景。

### 7.2 Persona 定义

建议标识：

```text
companion_head_teacher
```

展示名：

```text
陪伴班主任
```

定位：

- 学习压力陪伴。
- 日常鼓励。
- 学习计划轻建议。
- 情绪安抚。

边界：

- 不诊断心理疾病。
- 不承诺结果。
- 不替代家长、老师或心理咨询师。
- 遇到自伤、伤人、极端危险表达时，引导联系老师、家长或专业人员。

### 7.3 与意图/工具关系

继续遵守 v2.0 决策：

> Persona 只影响回复风格，不参与意图分类和工具选择。

### 7.4 验收标准

- `/agent/personas` 返回陪伴班主任角色。
- `AgentView` 和 `FloatingAgent` 可选择该角色。
- 角色回复风格明显更温和、更共情。
- 危险话题不会给出诊断或承诺。

---

## 八、P2-2：天气卡片 Vue 组件

### 8.1 需求目标

将 `weather_tool` 的结构化天气数据渲染成通用卡片，提升 Agent 天气查询体验。

### 8.2 组件设计

新增：

```text
frontend-vue/src/components/WeatherCard.vue
```

使用位置：

- `AgentView.vue`
- `FloatingAgent.vue`
- 可选复用到 `WorkView.vue`

展示内容：

- 地点。
- 当前天气。
- 温度。
- 风力/湿度。
- 空气质量。
- 未来预报。
- 预警信息。
- 数据来源 provider 轻量标签。

### 8.3 降级策略

- 如果结构化字段完整，则展示天气卡片。
- 如果结构化字段不完整，则保留纯文本回复。
- 不因天气卡片渲染失败影响 Agent 消息展示。

### 8.4 验收标准

- 天气查询成功后能展示卡片。
- Agent 全页和悬浮入口体验一致。
- MCP 和 REST fallback 的天气结果均可展示。
- 字段缺失时不会出现前端报错或空白卡片。

---

## 九、版本验收总标准

v2.1 完成时，应满足：

- 用户可以在 `AgentView` 和 `FloatingAgent` 对 Agent 回复反馈。
- 后端能把反馈写入 `AgentFeedback`，并支持重复反馈覆盖。
- SSE `done` 事件返回 `task_id`。
- 管理员能在系统管理中查看 Agent 监控面板。
- 监控面板能展示任务成功率、工具失败率、耗时、反馈质量和最近任务。
- HITL 邮件确认逻辑由规则驱动。
- HITL 支持超时自动失效。
- 腾讯地图 MCP 客户端具备可复用结构。
- 天气查询优先 MCP，失败自动降级 REST。
- P2 功能不阻塞 P1 发布。

---

## 十、后续路线图

| 版本 | 方向 | 说明 |
|------|------|------|
| v2.1 | 运营闭环与可观测 | 反馈、监控、HITL 规则、MCP 底座 |
| v2.2 | 记忆系统与用户画像预研 | working_memory、summary_memory、长期画像 |
| v2.3 | 地图 MCP 多能力扩展 | POI、路线、地点搜索、距离计算等 |
| v3.0 | 多 Agent 协作编排 | supervisor_agent、跨角色任务流、任务级状态管理 |

---

## 十一、一句话总结

v2.1 的目标是把 v2.0 已经能“回答问题、调用工具”的 Agent，升级成一个能被用户评价、能被管理员观察、能对高风险动作做规则化确认、并能复用腾讯地图 MCP 能力持续扩展的 Agent 子系统。
