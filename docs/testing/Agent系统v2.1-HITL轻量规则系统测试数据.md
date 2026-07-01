# Agent 系统 v2.1 - HITL 轻量规则系统测试数据

> 本文档记录 v2.1 第三个功能“HITL 轻量规则系统”的测试数据、验证步骤和测试结论。该功能实现完成后，需由用户确认无误，再进入下一个需求功能。

---

## 一、测试范围

本次测试覆盖：

- `email_tool` HITL 规则配置。
- `awaiting_confirmation` SSE 事件携带规则字段。
- `HitlState` 保存风险等级、确认文案、超时时间、过期时间。
- `hitl_manager` 按规则超时时间清理暂停状态。
- HITL 暂停任务写入 `AgentTask.status = awaiting_hitl`。
- HITL 取消后回写 `AgentTask.status = cancelled`。
- 前端全页 Agent 和悬浮 Agent 使用规则文案展示确认卡片。
- 前端生产构建。

---

## 二、涉及文件

| 类型 | 文件 |
|------|------|
| 规则配置 | `agent_system/hitl/escalation_rules.py` |
| HITL 状态模型 | `agent_system/hitl/hitl_schema.py` |
| HITL 管理器 | `agent_system/hitl/hitl_manager.py` |
| Executor | `agent_system/executor/agent_executor.py` |
| 服务编排 | `agent_system/service/agent_service.py` |
| API 确认端点 | `agent_system/api/agent_api.py` |
| 前端全页入口 | `frontend-vue/src/views/AgentView.vue` |
| 前端悬浮入口 | `frontend-vue/src/components/FloatingAgent.vue` |

---

## 三、规则配置

当前 v2.1 首个规则化场景为 `email_tool`：

```python
HITL_RULES = {
    "email_tool": HitlRule(
        enabled=True,
        risk_level="medium",
        timeout_seconds=600,
        confirm_title="确认发送邮件",
        confirm_message="请确认收件人、主题和正文无误后再发送。",
    ),
}
```

未知高风险工具会走保守默认规则：

```text
risk_level = high
timeout_seconds = 600
confirm_title = 确认高风险操作
```

---

## 四、SSE 事件字段

`awaiting_confirmation` 事件新增规则字段：

```json
{
  "tool_name": "email_tool",
  "preview": {},
  "risk_level": "medium",
  "timeout_seconds": 600,
  "expires_at": 1730000000.0,
  "confirm_title": "确认发送邮件",
  "confirm_message": "请确认收件人、主题和正文无误后再发送。"
}
```

前端不再硬编码确认标题，而是优先使用：

- `confirm_title`
- `confirm_message`
- `risk_level`

---

## 五、测试数据

### 5.1 规则 payload 测试

输入：

```text
tool_name = email_tool
preview.receiver = 337429025@qq.com
```

预期：

```text
risk_level = medium
timeout_seconds = 600
confirm_title 非空
confirm_message 非空
```

### 5.2 暂停状态测试

构造暂停状态：

```text
task_id = session-1
step_id = 1
tool_name = email_tool
message_id = 99
agent_task_id = 123
expires_at = 当前时间 + 60 秒
```

预期：

- `get_paused_state()` 能取到状态。
- `message_id = 99`。
- `agent_task_id = 123`。
- `clear_paused_state()` 后状态为空。

### 5.3 超时清理测试

构造过期状态：

```text
task_id = expired
step_id = 1
expires_at = 当前时间 - 1 秒
```

预期：

```text
get_paused_state("expired", 1) == None
```

### 5.4 取消确认测试

构造任务：

```text
AgentTask.status = awaiting_hitl
HitlState.agent_task_id = AgentTask.id
confirmed = false
```

预期：

```text
confirm_step 返回 code = 200
AgentTask.status = cancelled
暂停状态已清理
```

---

## 六、执行命令与结果

### 6.1 Python 编译检查

命令：

```powershell
python -m compileall agent_system DAO model
```

结果：

```text
通过。agent_executor.py、hitl_manager.py、hitl_schema.py、escalation_rules.py、agent_service.py、agent_api.py 编译成功。
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

### 6.3 规则与超时验证

输出摘要：

```text
tool_name = email_tool
risk_level = medium
timeout_seconds = 600
expired_cleaned = True
```

验证结论：

- `email_tool` 规则可正常读取。
- SSE payload 所需字段齐全。
- 暂停状态可关联 `message_id` 和 `agent_task_id`。
- 过期暂停状态会自动清理。

### 6.4 取消确认验证

输出摘要：

```text
confirm_cancel_code = 200
task_status = cancelled
state_cleared = True
```

验证结论：

- 用户取消 HITL 操作后，暂停状态会清理。
- 关联的 `AgentTask.status` 会从 `awaiting_hitl` 回写为 `cancelled`。

---

## 七、前端行为预期

### 7.1 AgentView

预期：

- HITL 卡片标题来自 `confirm_title`。
- HITL 卡片说明来自 `confirm_message`。
- 风险等级来自 `risk_level`，高风险时显示警示样式。
- 邮件预览仍支持编辑主题和正文。
- 确认/取消流程保持兼容。

### 7.2 FloatingAgent

预期：

- 小面板展示规则标题和说明。
- 风险等级以轻量标签展示。
- 确认/取消流程保持兼容。

---

## 八、验收结论

当前测试结论：

- 后端编译通过。
- 前端生产构建通过。
- HITL 规则配置可用。
- `awaiting_confirmation` 事件已规则化。
- HITL 暂停状态支持规则超时。
- HITL 暂停任务能写入 `awaiting_hitl`。
- 用户取消确认后能回写 `cancelled`。
- 前端确认卡片已改为使用规则文案，不再硬编码“确认发送邮件”标题。

该功能可以进入用户确认阶段。用户确认无误后，再开始 v2.1 下一个功能：腾讯地图 MCP 能力底座 + 天气首发接入。
