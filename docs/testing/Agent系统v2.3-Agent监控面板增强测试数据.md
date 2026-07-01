# Agent系统v2.3-Agent监控面板增强测试数据

## 一、测试目标

验证 v2.3 第二个功能「Agent 监控面板增强」是否完成轻量运营观测闭环：

1. 监控总览能独立展示 `partial_success`、`clarification`、`empty` 状态。
2. 工具排行能统计成功、部分成功、空结果、失败。
3. 地图类工具能按 provider 聚合 `tencent_mcp` / `tencent_rest_fallback`。
4. 能展示腾讯地图 MCP 当前健康状态。
5. 能对 1-2 分差评做轻量关键词归因。
6. 最近任务能展示 provider 摘要和卡片摘要。
7. 最近任务详情速查能展示 `tool_calls`、`tool_monitoring`、`cards` 原始结构摘要。

## 二、后端接口范围

| 接口 | 说明 |
| --- | --- |
| `GET /agent/admin/metrics` | 新增 `partial_success_count`、`clarification_count`、`empty_count` 等状态统计 |
| `GET /agent/admin/metrics/tools` | 工具维度新增 `partial_success`、`empty`、`clarification` 统计 |
| `GET /agent/admin/metrics/providers` | 新增地图 provider 聚合、兜底率、空结果率、失败率 |
| `GET /agent/admin/metrics/feedback-reasons` | 新增差评原因关键词聚合 |
| `GET /agent/admin/mcp/tencent-map/health` | 前端接入已有 MCP 健康状态接口 |
| `GET /agent/admin/tasks` | 最近任务新增 `provider_summary`、`card_summary`、`tool_monitoring`、`cards` |

## 三、模拟回归用例

### 用例 1：周边服务空结果 + REST 兜底

模拟 `AgentTask.steps_json`：

```json
{
  "tool_calls": [
    {"tool_name": "nearby_service_tool", "status": "empty"}
  ],
  "tool_monitoring": {
    "nearby_service_tool": {
      "status": "empty",
      "provider": "tencent_rest_fallback",
      "fallback_used": true,
      "result_count": 0
    }
  },
  "cards": [
    {"type": "poi_list", "card_version": 1}
  ]
}
```

预期最近任务行：

```text
provider_summary=nearby_service_tool: tencent_rest_fallback，兜底，0条
card_summary=poi_list×1
```

验证命令：

```text
python -c "import json; from types import SimpleNamespace; from agent_system.api import agent_api as a; raw=json.dumps({'tool_calls':[{'tool_name':'nearby_service_tool','status':'empty'}],'tool_monitoring':{'nearby_service_tool':{'status':'empty','provider':'tencent_rest_fallback','fallback_used':True,'result_count':0}},'cards':[{'type':'poi_list','card_version':1}]}, ensure_ascii=False); task=SimpleNamespace(id=1,create_time=None,user_id='u1',persona='academic_mentor',intent='nearby_service',status='empty',total_duration_ms=120,steps_json=raw,original_message='宝安中心附近有什么好吃的'); row=a._task_to_admin_row(task, {}); assert row['provider_summary']=='nearby_service_tool: tencent_rest_fallback，兜底，0条', row; assert row['card_summary']=='poi_list×1', row; assert a._negative_reason_label('地图路线不准确')=='地图定位'; print('agent monitor helper regression passed')"
```

实际结果：

```text
agent monitor helper regression passed
```

结论：通过。

## 四、前端展示验证

系统管理的 Agent 监控页新增：

1. `澄清/空结果` 指标卡。
2. `地图 MCP` 健康状态卡。
3. `地图兜底率` 指标卡。
4. `地图 Provider 分布` 排行面板。
5. `差评原因聚合` 面板。
6. 最近任务表新增 `Provider`、`卡片` 两列。
7. 最近任务下方新增 `任务详情速查`，支持按任务查看工具步骤、工具监控和卡片摘要。

## 五、自动化验证

### 后端编译

命令：

```text
python -m compileall agent_system DAO model main.py
```

结果：

```text
后端编译通过
```

### 前端构建

命令：

```text
npm.cmd run build
```

结果：

```text
前端生产构建通过
```

### UI 回归

命令：

```text
npm.cmd run test:ui-regression
```

结果：

```text
UI 回归检查通过：53/53
Playwright UI 回归通过：2/2
```

## 六、结论

v2.3 第二个功能「Agent 监控面板增强」已完成最小完整闭环：

```text
AgentTask.steps_json
  -> tool_calls / tool_monitoring / cards
  -> 后端监控聚合接口
  -> SystemView Agent监控页
  -> provider、MCP健康、状态分布、差评原因、最近任务摘要和详情速查可视化
```

本功能完成后，管理员可以回答三个关键问题：

1. 哪些 Agent 状态异常或需要用户补充信息。
2. 地图 MCP 和 REST 兜底各自使用情况如何。
3. 用户差评主要集中在哪类问题。
