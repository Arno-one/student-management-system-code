# Agent系统v2.3-Supervisor多Agent协作设计一期测试数据

## 一、测试目标

验证 v2.3 第三个功能「Supervisor 多 Agent 协作设计一期」是否完成最小可跑闭环：

1. 明确跨域请求由 `SupervisorAgent` 接管。
2. Supervisor 生成 `route -> delegate -> merge -> complete` 状态轨迹。
3. 支持 `agent_role / handoff` 数据结构。
4. 地图任务分派给 `MapAgent`，复用 `commute_plan_tool`。
5. 邮件任务分派给 `CommunicationAgent`，复用 `email_tool` 与 HITL 确认。
6. 邮件工具能读取上游通勤结果，把路线摘要写入邮件生成提示。
7. HITL 邮件确认使用真实 `step_id`，支持 Supervisor 场景下第 2 步邮件发送。
8. 单一通勤、单一邮件请求仍走原有单 Agent 链路。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `agent_system/supervisor/supervisor_planner.py` | 新增 Supervisor 一期编排器 |
| `agent_system/supervisor/__init__.py` | 暴露 Supervisor 入口 |
| `agent_system/service/agent_service.py` | 流式/同步链路接入 Supervisor 路由 |
| `agent_system/executor/agent_executor.py` | HITL 事件透传真实 `step_id` |
| `agent_system/hitl/escalation_rules.py` | HITL payload 支持 `step_id` |
| `agent_system/tools/email_tool.py` | 邮件工具读取上游通勤摘要 |
| `agent_system/schemas/agent_response.py` | 响应模型新增 `supervisor` 编排轨迹 |
| `agent_system/prompts/intent_prompt.py` | 补充 `supervisor_multi_agent` 意图说明 |
| `agent_system/planner/task_planner.py` | 补充 Supervisor 兜底计划 |
| `frontend-vue/src/views/AgentView.vue` | 邮件确认/取消使用真实 `step_id` |
| `frontend-vue/src/components/FloatingAgent.vue` | 悬浮 Agent 邮件确认/取消使用真实 `step_id` |
| `frontend-vue/src/views/SystemView.vue` | 监控意图标签新增“多Agent协作” |

## 三、核心设计

### Agent 角色

```text
SupervisorAgent：识别跨域请求、拆解任务、生成 handoff、汇总状态
MapAgent：负责通勤规划、天气、POI 等地图相关能力
CommunicationAgent：负责邮件生成和 HITL 确认
```

### 状态机

```text
route：识别跨域请求
delegate：分派给 MapAgent / CommunicationAgent
merge：保留上游结果，供后续 Agent 使用
complete：交给现有 executor 执行计划并保存 metadata
```

### 最小闭环场景

```text
从宝安中心到龙岗坐地铁怎么去，并写邮件发给337429025@qq.com通知老师
```

预期：

```text
intent=supervisor_multi_agent
handoffs[0].agent_role=MapAgent
handoffs[0].tool_name=commute_plan_tool
handoffs[1].agent_role=CommunicationAgent
handoffs[1].tool_name=email_tool
handoffs[1].depends_on=["commute_plan_tool"]
plan.steps=["commute_plan_tool", "email_tool"]
```

## 四、回归用例

### 用例 1：Supervisor 路由与 handoff 生成

验证命令：

```text
python -c "from agent_system.supervisor import build_supervisor_decision; d=build_supervisor_decision('从宝安中心到龙岗坐地铁怎么去，并写邮件发给337429025@qq.com通知老师'); assert d and d.intent=='supervisor_multi_agent'; assert [h.agent_role for h in d.handoffs]==['MapAgent','CommunicationAgent']; assert [s.tool_name for s in d.plan.steps]==['commute_plan_tool','email_tool']; print(d.to_metadata())"
```

实际结果：

```text
结构断言通过
```

结论：通过。

### 用例 2：邮件工具读取上游通勤摘要

验证命令：

```text
python -c "from agent_system.tools.email_tool import _build_commute_context; ctx=_build_commute_context({'success':True,'origin_text':'宝安中心','destination_text':'龙岗','routes':[{'success':True,'label':'地铁','duration_text':'1小时10分钟','distance_text':'36公里'}],'weather_reminder':'今天可能下雨'}); assert '宝安中心' in ctx and '地铁：1小时10分钟，36公里' in ctx and '今天可能下雨' in ctx; print(ctx.encode('unicode_escape').decode())"
```

实际结果：

```text
\u8d77\u70b9\uff1a\u5b9d\u5b89\u4e2d\u5fc3
\u7ec8\u70b9\uff1a\u9f99\u5c97
\u5730\u94c1\uff1a1\u5c0f\u65f610\u5206\u949f\uff0c36\u516c\u91cc
\u5929\u6c14\u63d0\u9192\uff1a\u4eca\u5929\u53ef\u80fd\u4e0b\u96e8
```

说明：

```text
起点：宝安中心
终点：龙岗
地铁：1小时10分钟，36公里
天气提醒：今天可能下雨
```

结论：通过。

### 用例 3：Supervisor 邮件 HITL 使用第 2 步确认

问题背景：

```text
Supervisor 计划中 commute_plan_tool 是第 1 步，email_tool 是第 2 步。
修复前前端确认邮件时固定提交 step_id=1，后端实际暂停状态保存在 step_id=2，导致确认发送时找不到暂停状态，表现为发送失败。
```

修复点：

```text
executor awaiting_confirmation payload 携带 step_id
service 保存 hitl metadata 和 message/task 关联时使用真实 step_id
AgentView / FloatingAgent 确认和取消时提交 msg.hitl.stepId
```

验证命令：

```text
python -c "from agent_system.hitl.hitl_manager import pause_execution, get_paused_state, clear_paused_state; from agent_system.hitl.hitl_schema import HitlState; pause_execution('session-x', 2, HitlState(tool_name='email_tool', preview={'receiver':'337429025@qq.com'})); assert get_paused_state('session-x', 1) is None; assert get_paused_state('session-x', 2).tool_name == 'email_tool'; clear_paused_state('session-x', 2); print('hitl step_id regression passed')"
```

实际结果：

```text
hitl step_id regression passed
```

结论：通过。

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

## 六、边界说明

当前 Supervisor 一期只接管明确的「地图任务 + 邮件任务」跨域请求。

暂不实现：

1. 大规模多 Agent 自动协作。
2. 多轮任务持久化恢复。
3. 独立 MapAgent / CommunicationAgent 的完整运行时进程。
4. 非地图类跨域任务自动拆解。

这些保留给后续版本，避免一期改动过大影响现有单 Agent 主链路。

## 七、结论

Supervisor 一期已完成最小闭环：

```text
用户跨域请求
  -> SupervisorAgent route
  -> MapAgent handoff: commute_plan_tool
  -> CommunicationAgent handoff: email_tool
  -> email_tool 读取上游通勤摘要
  -> HITL 邮件确认
  -> supervisor metadata / steps_json 落库
```

该功能为后续 Supervisor 模式扩展留下了清晰接口，同时没有破坏现有单 Agent 工具链路。
