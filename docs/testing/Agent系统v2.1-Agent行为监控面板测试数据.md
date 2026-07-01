# Agent 系统 v2.1 - Agent 行为监控面板测试数据

> 本文档记录 v2.1 第二个功能“Agent 行为监控面板”的测试数据、验证步骤和测试结论。该功能实现完成后，需由用户确认无误，再进入下一个需求功能。

---

## 一、测试范围

本次测试覆盖：

- Agent 监控总览指标接口。
- Agent 每日调用趋势接口。
- Agent 意图分布指标接口。
- Agent 工具失败率指标接口。
- Agent 最近任务列表接口。
- 最近任务状态筛选。
- 系统管理页新增 `Agent监控` 子页。
- 前端生产构建。

---

## 二、涉及文件

| 类型 | 文件 |
|------|------|
| 后端 API | `agent_system/api/agent_api.py` |
| 后端 DAO | `DAO/agent_dao.py` |
| 前端页面 | `frontend-vue/src/views/SystemView.vue` |

---

## 三、后端接口

### 3.1 总览指标

```http
GET /agent/admin/metrics?days=7
```

返回核心字段：

- `total_tasks`
- `success_rate`
- `avg_duration_ms`
- `p50_duration_ms`
- `p99_duration_ms`
- `feedback_count`
- `positive_rate`
- `negative_rate`

### 3.2 每日趋势

```http
GET /agent/admin/metrics/timeseries?days=7
```

返回每天：

- 调用量。
- 失败量。
- 平均耗时。

### 3.3 意图分布

```http
GET /agent/admin/metrics/intents?days=7
```

返回每个意图：

- 调用次数。
- 成功次数。
- 失败次数。
- 平均耗时。
- p50/p99 耗时。

### 3.4 工具失败率

```http
GET /agent/admin/metrics/tools?days=7
```

从 `AgentTask.steps_json` 中解析工具调用，返回：

- 工具名。
- 调用总数。
- 成功数。
- 失败数。
- 失败率。

### 3.5 最近任务

```http
GET /agent/admin/tasks?days=7&status=success&intent=daily_chat&limit=50
```

返回最近任务列表，用于排查具体问题。

---

## 四、权限口径

监控接口使用与系统管理一致的管理员口径：

```text
require_role("admin")
```

即仅 `admin` 角色可访问 `/agent/admin/...` 监控接口。

---

## 五、测试数据

### 5.1 聚合测试数据

使用 SQLite 内存库构造 4 条任务：

| 用户 | 意图 | 状态 | 耗时 | 工具调用 |
|------|------|------|------|----------|
| alice | weather_query | success | 1200ms | weather_tool success |
| bob | knowledge_qa | error | 3000ms | rag_tool error |
| alice | email_draft | awaiting_hitl | 800ms | email_tool success |
| carol | daily_chat | cancelled | 0ms | 无 |

反馈数据：

| task | rating | comment |
|------|--------|---------|
| weather_query | 5 | 好用 |
| knowledge_qa | 1 | 失败了 |

### 5.2 筛选测试数据

使用 SQLite 内存库构造 3 条任务：

```text
success
error
success
```

调用：

```http
GET /agent/admin/tasks?days=7&status=success
```

预期只返回 2 条 `success` 状态任务。

---

## 六、执行命令与结果

### 6.1 Python 编译检查

命令：

```powershell
python -m compileall agent_system DAO model
```

结果：

```text
通过。agent_api.py、agent_dao.py 等文件编译成功。
```

### 6.2 前端生产构建

命令：

```powershell
npm.cmd run build
```

结果：

```text
vite build 成功，62 modules transformed，生产包构建完成。
```

### 6.3 聚合口径验证

输出摘要：

```text
metrics_total = 4
success_rate = 50.0
feedback_count = 2
timeseries_days = 7
intent_rows = 4
tool_rows = 3
task_rows = 4
```

验证结论：

- 总调用量为 4，正确。
- success/error 完成任务各 1 条，成功率为 50%，正确。
- awaiting_hitl 和 cancelled 单独统计，不混入任务成功率，正确。
- 反馈数为 2，好评率/差评率均为 50%，正确。
- 工具失败率能识别 `rag_tool` 100% 失败，正确。
- 7 天趋势返回 7 个日期桶，正确。

### 6.4 状态筛选验证

输出摘要：

```text
filtered_status = success
rows = 2
```

验证结论：

- 最近任务接口按 `status=success` 筛选后只返回 2 条成功任务，正确。

---

## 七、前端行为预期

系统管理新增第三个子页：

```text
Agent监控
```

页面包含：

- 顶部指标卡：总调用量、任务成功率、平均耗时、P99 耗时、反馈数、待确认/取消。
- 每日调用趋势：使用 CSS 条形图展示，不引入 ECharts。
- 意图调用排行：显示意图名称、原始 intent、P99 和调用次数。
- 工具失败排行：显示成功数、失败数、失败率。
- 最近任务表：显示时间、用户、角色、意图、状态、耗时、工具摘要、反馈和原始问题。
- 筛选条件：时间范围、状态、意图。

---

## 八、验收结论

当前测试结论：

- 后端编译通过。
- 前端生产构建通过。
- 监控总览统计口径符合设计。
- 工具失败率能从 `steps_json` 正确解析。
- 最近任务状态筛选可用。
- `SystemView.vue` 已新增 `Agent监控` 子页，且未引入额外图表依赖。

该功能可以进入用户确认阶段。用户确认无误后，再开始 v2.1 下一个功能：HITL 轻量规则系统。
