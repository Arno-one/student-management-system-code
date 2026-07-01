# Agent 系统 v2.3 迭代总结与下版本规划

> 本文档记录 Agent 系统 v2.3 从周边生活服务、运营监控、Supervisor 多 Agent 协作、Persona 体验、WorkView 天气复用到卡片协议收口的完整迭代结果，并沉淀 v2.4 建议目标。

---

## 一、版本定位

v2.3 的版本主题是：**地图生活服务扩展、运营观测增强、Supervisor 架构预研与体验收口**。

v2.2 已完成记忆压缩、通勤规划、route 卡片、UI 回归护栏和历史摘要体验修复。v2.3 在这个基础上继续向三个方向推进：

1. **地图能力业务化**：从通勤路线扩展到周边生活服务推荐，支持餐饮、医院、打印店等 POI 查询。
2. **结构化展示完善**：落地 `poi_list` 卡片，收口 `weather`、`route`、`poi_list` 三类卡片协议，并明确 `map_location` 仅预留。
3. **运营观测增强**：把 provider、MCP 健康、差评原因、卡片摘要和工具监控接入 Agent 监控面板。
4. **Supervisor 架构一期**：完成跨域“通勤规划 + 邮件通知”最小可跑闭环，为后续多 Agent 协作预留状态机和 handoff 数据结构。
5. **体验收口**：悬浮 Agent 记住 persona 偏好，新增“昕哥”角色，WorkView 天气展示复用 `WeatherCard`。

一句话概括：

> v2.3 让 Agent 从“会规划路线并展示卡片”进一步变成“能查周边生活服务、能被运营观测、能初步跨 Agent 协作，并把 UI 与协议维护成本收回来”的系统。

---

## 二、迭代范围与状态

### 2.1 已完成

| # | 功能 | 优先级 | 状态 | 测试文档 |
|---|------|--------|------|----------|
| 1 | 周边生活服务推荐 Agent 能力 | P1 | 已完成 | `docs/testing/Agent系统v2.3-周边生活服务推荐Agent能力测试数据.md` |
| 2 | 周边服务口语餐饮关键词回归 | 回归修复 | 已完成 | `docs/testing/Agent系统v2.3-周边服务口语餐饮关键词回归测试.md` |
| 3 | Agent 监控面板增强 | P1 | 已完成 | `docs/testing/Agent系统v2.3-Agent监控面板增强测试数据.md` |
| 4 | Supervisor 多 Agent 协作设计一期 | P1 | 已完成 | `docs/testing/Agent系统v2.3-Supervisor多Agent协作设计一期测试数据.md` |
| 5 | FloatingAgent Persona 记忆与昕哥角色 | P2 | 已完成 | `docs/testing/Agent系统v2.3-FloatingAgentPersona记忆测试数据.md` |
| 6 | WorkView 复用 WeatherCard | P2 | 已完成 | `docs/testing/Agent系统v2.3-WorkView复用WeatherCard测试数据.md` |
| 7 | 卡片协议继续泛化 | P2 | 已完成 | `docs/testing/Agent系统v2.3-卡片协议继续泛化测试数据.md` |

### 2.2 本轮明确暂不做

| 功能 | 处理方式 | 原因 |
|---|---|---|
| `map_location` 详情卡片 | 协议预留，不实现组件 | 用户已确认本轮只做 `poi_list` 完整闭环 |
| 大规模 Supervisor 自动协作 | 只做一期最小闭环 | 需要任务持久化、失败恢复、Agent 角色边界成熟后再铺开 |
| 长期用户画像 | 暂缓 | 当前 persona 记忆只属于 UI 偏好，不写入数据库 |
| 多级审批流 | 暂缓 | 当前 HITL 轻量确认已能覆盖邮件发送风险点 |

结论：**v2.3 规划中的 P1 与主要 P2 收口项均已完成，`map_location` 按已确认边界仅保留协议预留。**

---

## 三、关键设计决策

| 决策点 | 最终方案 | 原因 |
|--------|----------|------|
| 周边服务范围 | 只做 `poi_list`，暂不做 `map_location` | 先把列表推荐闭环做稳，详情卡片留到下一版 |
| 默认半径 | 2000 米 | 足够覆盖“附近”常见生活服务，不至于结果过大 |
| 返回数量 | 10 条 | 主 Agent 可读性较好，悬浮 Agent compact 只展示前 3 条 |
| 排序规则 | 腾讯地图默认综合排序优先，前端按距离兜底排序 | 尊重地图服务排序，同时保证展示稳定 |
| 周边输入校验 | LangGraph 中间件检查地点和服务类别 | 缺信息时返回 `clarification`，不误调地图工具 |
| 餐饮口语归一 | “好吃/吃啥/吃什么”等归一为 `餐饮` | 避免地图 POI 直接搜“好吃”导致空结果 |
| POI provider | MCP 优先，REST fallback | 地图 MCP 不稳定时仍尽量给出结构化结果 |
| 监控增强 | 聚合 provider、状态、卡片、差评原因 | 管理员能看到工具是否稳定、用户为何不满意 |
| Supervisor 定位 | Supervisor 是轻编排层，不直接承担地图 MCP 能力 | 腾讯地图 MCP 适合放在 `MapAgent` 下，不适合当 Supervisor |
| Supervisor 一期场景 | “通勤规划 + 邮件通知” | 同时覆盖 MapAgent、CommunicationAgent 和 HITL |
| HITL step_id | 前后端都使用真实 `step_id` | 解决 Supervisor 第二步邮件确认失败问题 |
| Persona 记忆 | `localStorage` 保存悬浮 Agent 最近角色 | 只解决 UI 偏好，不扩展成长期画像 |
| 新增角色 | 增加“昕哥” persona，并展示 emoji 标识 | 让角色选择更直观，也满足用户指定风格 |
| WorkView 天气 | 保留查询表单，结果复用 `WeatherCard` | 减少两套天气 UI 维护成本 |
| 卡片协议 | `weather`、`route`、`poi_list` 已实现，`map_location` 预留 | 明确当前能力和后续扩展边界 |

---

## 四、功能实现详解

### 4.1 周边生活服务推荐 Agent 能力

目标：
- 支持用户询问某地附近的餐饮、医院、打印店等生活服务。
- 地点或服务类别不完整时先澄清。
- 信息完整时调用腾讯地图 POI 能力，并返回 `poi_list` 卡片。

设计：
- `nearby_parser.py` 负责从自然语言中解析地点、关键词、半径和数量。
- `nearby_input_checker.py` 负责判断是否缺地点或服务类别。
- `nearby_service_tool.py` 封装 geocoder、`placeSearchNearby` 和 REST fallback。
- `PoiListCard.vue` 负责统一渲染 POI 列表。
- executor 从工具结果中提取 `type=poi_list`、`card_version=1` 卡片。

具体实现：
- 新增 `agent_system/middleware/nearby_parser.py`。
- 新增 `agent_system/middleware/nearby_input_checker.py`。
- 新增 `agent_system/tools/nearby_service_tool.py`。
- 修改 `agent_system/middleware/middleware_graph.py`，接入 nearby 检查节点，并避免抢走通勤请求。
- 修改 `agent_system/executor/agent_executor.py`，注册 `nearby_service_tool`，提取 `poi_list` 卡片和 `tool_monitoring`。
- 新增 `frontend-vue/src/components/PoiListCard.vue`。
- `AgentView.vue` 和 `FloatingAgent.vue` 接入 `PoiListCard`。

核心规则：

```text
默认半径：2000 米
半径上限：5000 米
返回数量：10 条
主 Agent 展示：最多 10 条
悬浮 Agent compact 展示：前 3 条
排序：腾讯地图默认综合排序优先，前端按 distance_meters 从近到远兜底
```

状态设计：

```text
clarification：缺地点或类别
success：查到 POI
empty：地点解析成功但无结果
error：地理编码失败或工具异常
```

核心链路：

```text
用户输入
  → nearby LangGraph 中间件
  → 缺地点/类别：clarification
  → 信息完整：nearby_service_tool
  → geocoder + POI 搜索
  → MCP 优先，REST fallback
  → poi_list card
  → AgentView / FloatingAgent 渲染
```

关键回归：
- “学校附近有哪些医院”不会盲猜学校，返回澄清。
- “附近有什么”同时提示补地点和类别。
- “从宝安到龙岗坐地铁怎么去”不会被 nearby 抢走，继续交给通勤规划。
- “宝安中心附近有什么好吃的”会把关键词归一为 `餐饮`。

测试结论：
- 后端编译通过。
- 前端构建通过。
- 静态 UI 回归与 Playwright Edge 回归通过。
- mock MCP 工具层能返回结构化 `poi_list`。

### 4.2 周边服务口语餐饮关键词回归

问题：
- 用户说“宝安中心附近有什么好吃的”时，解析器能识别周边服务，但关键词停留在“好吃”。
- 地图 POI 直接搜索“好吃”容易返回空结果。

设计：
- 将常见口语餐饮表达归一为更稳定的地图关键词 `餐饮`。
- 保留 `query_text=好吃`，但工具实际查询使用 `keyword=餐饮`。

具体实现：
- 修改 `agent_system/middleware/nearby_parser.py` 的关键词归一逻辑。
- 覆盖“好吃”“好吃的”“吃啥”“吃什么”等常见表达。

验证样例：

```text
输入：宝安中心附近有什么好吃的
center_text=宝安中心
query_text=好吃
keyword=餐饮
radius_meters=2000
limit=10
missing_fields=[]
```

测试结论：
- parser 回归通过。
- 后端编译通过。

### 4.3 Agent 监控面板增强

目标：
- 管理员能看到地图 provider 使用情况、MCP 健康状态、差评原因和最近任务详情。
- `partial_success`、`clarification`、`empty` 不再混在失败或成功里。

设计：
- 后端监控接口从 `AgentTask.steps_json` 中读取 `tool_calls`、`tool_monitoring`、`cards`。
- 前端 SystemView 继续保持轻量，不引入复杂图表库。
- 最近任务展示 provider 摘要、卡片摘要，并提供任务详情速查。

具体实现：
- `GET /agent/admin/metrics` 新增状态统计。
- `GET /agent/admin/metrics/tools` 新增工具维度的 `partial_success`、`empty`、`clarification` 统计。
- `GET /agent/admin/metrics/providers` 新增 provider 聚合、兜底率、空结果率、失败率。
- `GET /agent/admin/metrics/feedback-reasons` 新增差评原因关键词聚合。
- `GET /agent/admin/mcp/tencent-map/health` 接入前端展示。
- `GET /agent/admin/tasks` 新增 `provider_summary`、`card_summary`、`tool_monitoring`、`cards`。
- `frontend-vue/src/views/SystemView.vue` 新增监控卡片、排行面板、最近任务列和详情速查。

核心链路：

```text
AgentTask.steps_json
  → tool_calls / tool_monitoring / cards
  → 后端监控聚合接口
  → SystemView Agent监控页
  → provider、MCP健康、状态分布、差评原因、最近任务摘要和详情速查
```

测试结论：
- helper 回归验证 `provider_summary=nearby_service_tool: tencent_rest_fallback，兜底，0条`。
- 差评关键词“地图路线不准确”归因为“地图定位”。
- 后端编译、前端构建、UI 回归均通过。

### 4.4 Supervisor 多 Agent 协作设计一期

目标：
- 不急着做大规模多 Agent 自动协作，先完成一个最小可跑闭环。
- 跨域请求由 `SupervisorAgent` 接管，拆成地图任务和邮件任务。
- 地图任务交给 `MapAgent`，邮件任务交给 `CommunicationAgent`。

设计：
- `SupervisorAgent` 负责识别跨域请求、生成 handoff、汇总状态。
- `MapAgent` 复用 `commute_plan_tool`。
- `CommunicationAgent` 复用 `email_tool` 和 HITL 确认。
- 状态轨迹为 `route -> delegate -> merge -> complete`。

具体实现：
- 新增 `agent_system/supervisor/supervisor_planner.py`。
- 新增 `agent_system/supervisor/__init__.py`。
- `agent_system/service/agent_service.py` 接入 Supervisor 路由。
- `agent_system/schemas/agent_response.py` 响应模型新增 `supervisor` 编排轨迹。
- `agent_system/prompts/intent_prompt.py` 增加 `supervisor_multi_agent`。
- `agent_system/planner/task_planner.py` 增加 Supervisor 兜底计划。
- `agent_system/tools/email_tool.py` 读取上游通勤摘要。
- `agent_system/executor/agent_executor.py` 的 HITL 事件透传真实 `step_id`。
- `agent_system/hitl/escalation_rules.py` 的 HITL payload 支持 `step_id`。
- `AgentView.vue` 和 `FloatingAgent.vue` 邮件确认/取消使用 `msg.hitl.stepId`。

最小闭环场景：

```text
从宝安中心到龙岗坐地铁怎么去，并写邮件发给337429025@qq.com通知老师
```

预期结构：

```text
intent=supervisor_multi_agent
handoffs[0].agent_role=MapAgent
handoffs[0].tool_name=commute_plan_tool
handoffs[1].agent_role=CommunicationAgent
handoffs[1].tool_name=email_tool
handoffs[1].depends_on=["commute_plan_tool"]
plan.steps=["commute_plan_tool", "email_tool"]
```

关键修复：
- Supervisor 计划中 `email_tool` 是第 2 步。
- 修复前前端确认邮件固定提交 `step_id=1`，会找不到暂停状态。
- 修复后 awaiting_confirmation payload 携带真实 `step_id`，前端确认和取消都提交 `msg.hitl.stepId`。

核心链路：

```text
用户跨域请求
  → SupervisorAgent route
  → MapAgent handoff: commute_plan_tool
  → CommunicationAgent handoff: email_tool
  → email_tool 读取上游通勤摘要
  → HITL 邮件确认
  → supervisor metadata / steps_json 落库
```

边界：
- 单一通勤、单一邮件请求仍走原有单 Agent 链路。
- 暂不实现多轮任务恢复、独立 Agent 运行时进程、非地图类跨域自动拆解。

测试结论：
- Supervisor 路由与 handoff 结构断言通过。
- 邮件工具读取通勤摘要通过。
- HITL `step_id=2` 回归通过。
- 后端编译、前端构建、UI 回归均通过。

### 4.5 FloatingAgent Persona 记忆与昕哥角色

目标：
- 悬浮 Agent 支持角色切换。
- 记住用户最近选择的 persona。
- 发送消息时使用当前 persona。
- 新增用户指定风格的“昕哥”角色。

设计：
- persona 偏好只存在浏览器 `localStorage`。
- 不写数据库，不扩展成长期用户画像。
- `/agent/personas` 返回 `icon` 字段。
- 主 Agent 和悬浮 Agent 的角色选择都展示 emoji 标识。

具体实现：
- `agent_system/prompts/persona_prompt.py` 新增 `xinge` persona。
- `agent_system/api/agent_api.py` 的 `/agent/personas` 返回 `icon`。
- `frontend-vue/src/views/AgentView.vue` 使用 `personaTitle(p)` 展示 emoji。
- `frontend-vue/src/components/FloatingAgent.vue` 增加 persona 下拉、偏好读写和按 persona 发送。
- `frontend-vue/scripts/ui-regression-check.mjs` 增加 persona 偏好护栏。

新增角色：

```text
id=xinge
name=昕哥
icon=😎
```

提示词特点：

```text
喜欢称呼用户为好兄弟、好兄弟们
喜欢鼓励大家
遇到错误时会讲清为什么不要再犯，以及可能导致什么后果
会适度引经据典
喜欢嘿嘿笑
定位是大家的好老师好兄弟
```

核心链路：

```text
加载 persona 列表
  → 读取 localStorage floating-agent-persona
  → 用户切换角色
  → 保存 selectedPersona
  → 发送消息时使用 persona: selectedPersona.value
```

测试结论：
- `localStorage.getItem('floating-agent-persona')` 和 `setItem` 检查通过。
- FloatingAgent 不再硬编码 `persona='academic_mentor'` 发送。
- 昕哥 persona 注册、emoji 展示、空态文案检查通过。
- 后端编译、前端构建、UI 回归均通过。

### 4.6 WorkView 复用 WeatherCard

目标：
- 保留工作台天气查询表单。
- 天气查询结果不再由 `WorkView.vue` 拼接 HTML。
- 实时、多日、逐时天气都交给统一的 `WeatherCard.vue` 渲染。

设计：
- `/work/weather` 请求参数不变。
- `WorkView.vue` 只把接口结果转换为天气卡片协议。
- `WeatherCard.vue` 补充逐时预报展示能力。
- 地址解析结果继续保留原来的 `v-html` 和事件委托，因为它有“查该地天气”按钮联动。

具体实现：
- `frontend-vue/src/views/WorkView.vue` 引入 `WeatherCard`。
- 新增 `weatherCardData` 和 `weatherError` 状态。
- 移除旧的 `renderWeather`、`renderWeatherHead`、`renderMetrics` 拼接逻辑。
- 新增 `buildWeatherCardData()`，把 `/work/weather` 结果转换为：

```js
{
  provider: 'work_weather',
  location_text: '广东省 · 深圳市 · 宝安区',
  adcode: '440306',
  weather: {
    '实时天气': { result },
    '多日预报': { result },
    '逐时预报': { result }
  }
}
```

- `frontend-vue/src/components/WeatherCard.vue` 新增 `逐时预报` 数据块解析和逐时网格。
- UI 回归脚本新增 WorkView 复用 WeatherCard 护栏。

展示边界：
- 实时天气展示城市、天气、温度、风向、风力、湿度、气压。
- 多日预报普通模式最多 5 天，compact 模式最多 3 天。
- 逐时预报普通模式最多 8 条，compact 模式最多 4 条。
- 三类数组都为空时显示「未解析到天气数据」。

测试结论：
- WorkView 不再出现 `weatherHtml`、`renderWeather`、`weatherEmoji` 旧路径。
- 前端构建通过。
- UI 回归检查通过：71/71。
- Playwright UI 回归通过：2/2。

### 4.7 卡片协议继续泛化

目标：
- 把当前已落地的卡片协议写成字段级契约。
- 明确当前只承诺渲染 `weather`、`route`、`poi_list`。
- 明确 `map_location` 是预留卡片，本版本不实现。

设计：
- `docs/Agent卡片协议v1.md` 成为后端 tool、executor、前端组件和 UI 回归脚本共同遵守的协议文档。
- 前端继续只渲染已知 `type` 和 `card_version=1`。
- 未知卡片类型和未知版本安全忽略。

具体实现：
- 重写 `docs/Agent卡片协议v1.md`。
- 补全 `weather`、`route`、`poi_list` 字段说明、示例 JSON 和展示规则。
- 新增 `map_location` 预留协议，明确：
  - 不新增 `MapLocationCard.vue`。
  - `AgentView.vue` 和 `FloatingAgent.vue` 不渲染 `map_location`。
  - 如果后端误返回 `map_location`，前端按未知类型安全忽略。
- `frontend-vue/scripts/ui-regression-check.mjs` 新增协议文档静态检查。

当前卡片清单：

| 类型 | 当前状态 | 后端来源 | 前端组件 |
| --- | --- | --- | --- |
| `weather` | 已实现 | `weather_tool`、`WorkView` 天气查询适配 | `WeatherCard.vue` |
| `route` | 已实现 | `commute_plan_tool` | `RouteCard.vue` |
| `poi_list` | 已实现 | `nearby_service_tool` | `PoiListCard.vue` |
| `map_location` | 预留，不实现 | 暂无 | 暂无 |

测试结论：
- 协议文档静态护栏通过。
- AgentView / FloatingAgent 暂不渲染 `map_location`。
- UI 回归检查通过：81/81。
- Playwright UI 回归通过：2/2。

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
UI 回归检查通过：81/81
Playwright UI 回归通过：2/2
```

已沉淀测试文档：

```text
docs/testing/Agent系统v2.3-周边生活服务推荐Agent能力测试数据.md
docs/testing/Agent系统v2.3-周边服务口语餐饮关键词回归测试.md
docs/testing/Agent系统v2.3-Agent监控面板增强测试数据.md
docs/testing/Agent系统v2.3-Supervisor多Agent协作设计一期测试数据.md
docs/testing/Agent系统v2.3-FloatingAgentPersona记忆测试数据.md
docs/testing/Agent系统v2.3-WorkView复用WeatherCard测试数据.md
docs/testing/Agent系统v2.3-卡片协议继续泛化测试数据.md
```

---

## 六、当前 Agent 能力矩阵

| 能力 | v2.3 后状态 |
|------|-------------|
| 多轮上下文 | 会话摘要 + 最近 5 条原文 |
| 历史摘要 | 每轮回复后更新，短会话使用第一轮问题短标题 |
| 反馈闭环 | 历史回放后锁定已提交反馈 |
| 天气查询 | Agent 天气卡片 + WorkView 复用 WeatherCard |
| 通勤规划 | 支持起点、终点、方式校验，路线卡片展示 |
| 周边服务 | 支持地点 + 服务类别 POI 查询，返回 `poi_list` |
| 输入澄清 | `clarification` 状态覆盖通勤和周边服务缺字段 |
| 部分成功 | `partial_success` 状态表达部分工具或路线可用 |
| 空结果 | `empty` 状态表达查询成功但无结果 |
| 地图 provider | MCP 优先，REST fallback，可在监控面板聚合 |
| 结构化卡片 | 支持 `weather`、`route`、`poi_list` |
| 卡片兼容 | `card_version=1`，未知类型/版本安全忽略 |
| Supervisor | 支持地图任务 + 邮件任务最小跨域编排 |
| HITL | 邮件确认使用真实 `step_id`，支持 Supervisor 第二步确认 |
| Persona | 主 Agent / 悬浮 Agent 展示 emoji 角色，新增昕哥 |
| 悬浮 Agent 偏好 | `localStorage` 记住最近 persona |
| 运营监控 | 状态、provider、MCP 健康、差评原因、卡片摘要和任务详情 |
| UI 回归 | 静态护栏 + Edge 真浏览器回归 |

---

## 七、v2.4 迭代目标建议

v2.4 建议围绕 v2.3 已经铺好的 POI、卡片协议、Supervisor 和监控能力继续推进。推荐主题：

> **地图详情闭环 + Supervisor 二期 + 协议治理增强**

### P1：建议必做

#### 1. `map_location` 详情卡片落地

目标：
- 在 `poi_list` 的基础上支持单个地点详情展示。
- 用户点击 POI 后可以看到更完整的地点信息。

建议范围：
- 新增 `MapLocationCard.vue`。
- executor 支持 `type=map_location`。
- `PoiListCard` 增加“查看详情”入口。
- 详情字段优先包含名称、类别、地址、经纬度、行政区、provider、来源。
- 电话、评分、营业时间继续作为可选字段，缺失时不展示。

边界：
- 不做复杂地图 SDK 嵌入。
- 不做收藏、评价、电话拨打等强交互。
- 先做详情卡片，不做完整地图应用。

#### 2. Supervisor 多 Agent 协作二期

目标：
- 从“一次跨域请求最小闭环”升级为“可观测、可恢复、可扩展”的 Supervisor 任务编排。

建议实现：
- 明确 `agent_role`、`handoff`、`state_trace` 的持久化结构。
- 最近任务详情展示 Supervisor handoff 轨迹。
- 支持 `clarify` 状态：跨域任务缺信息时由 Supervisor 统一追问。
- 支持更多跨域场景，例如“查周边打印店 + 生成邮件通知同学集合地点”。
- 保持 MapAgent、CommunicationAgent 仍是逻辑角色，不急着拆独立进程。

#### 3. 地图能力统一 MapAgent 门面

目标：
- 把天气、通勤、周边服务、地点详情统一收口到 MapAgent 能力层。

建议实现：
- 梳理 `weather_tool`、`commute_plan_tool`、`nearby_service_tool` 的共用 geocoder / fallback 能力。
- 抽出地图 provider 监控字段规范。
- 减少每个工具各自处理地理编码和 REST fallback 的重复逻辑。

#### 4. 真实地图链路冒烟测试

目标：
- 在 mock 测试之外增加少量可手工或定时运行的真实 MCP / REST 冒烟测试。

建议覆盖：
- 腾讯滨海大厦附近餐饮。
- 宝安中心附近医院。
- 宝安中心到龙岗中心城地铁通勤。
- 天气实时查询。

边界：
- 不把真实地图结果数量写死。
- 只断言接口可用、结构可解析、关键字段存在。

### P2：建议视时间实现

#### 5. 卡片协议 schema 校验

目标：
- 从“文档约束 + 静态字符串检查”升级为“可执行 schema 校验”。

建议：
- 为 `weather`、`route`、`poi_list`、`map_location` 建立 JSON Schema 或 Pydantic model。
- executor 输出卡片前做轻量校验。
- UI 回归脚本读取样例 card，验证字段兼容。

#### 6. Agent 监控趋势增强

目标：
- 让管理员不只看当前统计，还能看趋势变化。

建议：
- provider fallback 趋势。
- clarification 高频问题。
- empty 结果高频地点/关键词。
- 差评原因随时间变化。

边界：
- 继续保持轻量，不急着引入复杂 BI 图表。

#### 7. Persona 体验增强

目标：
- 让不同 persona 的边界更清楚，避免只是语气变化。

建议：
- 为每个 persona 提供 2 到 3 个推荐问题。
- 昕哥、陪伴班主任、学业导师在空态和错误反馈中有更明显差异。
- 仍不写长期用户画像。

#### 8. UI 回归截图快照

目标：
- 在现有 Playwright DOM 检查基础上，给关键卡片加少量截图快照。

建议覆盖：
- `WeatherCard`。
- `RouteCard`。
- `PoiListCard`。
- 后续 `MapLocationCard`。

边界：
- 只对关键卡片做少量快照，避免样式小改动造成大量无效失败。

### P3：继续暂缓

| 方向 | 暂缓原因 |
|------|----------|
| 长期用户画像 | 隐私边界和用户可控性还需要单独设计 |
| 多级审批流 | 当前邮件 HITL 已满足风险控制，复杂审批会扩大权限模型 |
| 独立多 Agent 运行时进程 | 当前逻辑角色足够支撑演示和验证，拆进程会增加部署复杂度 |
| 全量地图 SDK 可视化 | 对当前学生管理系统收益不如详情卡片和 Supervisor 二期明确 |

---

## 八、建议实施顺序

建议 v2.4 继续沿用“一次一个功能、完成后产出测试文档、用户确认后再进入下一个”的节奏：

1. **`map_location` 详情卡片落地**：补齐 v2.3 预留的地点详情卡片。
2. **Supervisor 多 Agent 协作二期**：增加 handoff 可视化、clarify 状态和更多跨域场景。
3. **地图能力统一 MapAgent 门面**：收口 geocoder、provider、fallback 和监控字段。
4. **真实地图链路冒烟测试**：用少量真实场景验证 MCP / REST 可用性。
5. **卡片协议 schema 校验**：让协议从文档约束升级为可执行约束。
6. **监控趋势增强与 UI 快照**：在稳定功能基础上补充运营和回归质量。

---

## 九、一句话总结

v2.3 已经完成 POI 周边生活服务、`poi_list` 卡片、Agent 监控增强、Supervisor 一期、Persona 偏好、WorkView 天气复用和卡片协议收口。v2.4 建议顺势补齐 `map_location` 详情卡片，并把 Supervisor、MapAgent 和卡片协议从“最小闭环”继续推进到“可观测、可校验、可扩展”的阶段。
