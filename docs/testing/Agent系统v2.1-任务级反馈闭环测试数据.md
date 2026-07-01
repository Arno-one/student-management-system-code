# Agent 系统 v2.1 - 任务级反馈闭环测试数据

> 本文档记录 v2.1 第一个功能“Agent 任务级反馈闭环”的测试数据、验证步骤和测试结论。该功能实现完成后，需由用户确认无误，再进入下一个需求功能。

---

## 一、测试范围

本次测试覆盖：

- `AgentFeedback` 任务级反馈新增。
- 同一任务重复反馈时覆盖旧反馈。
- `/agent/feedback` 任务归属校验。
- SSE `done` 事件携带 `task_id` 的代码链路。
- `AgentView.vue` 反馈按钮构建通过。
- `FloatingAgent.vue` 反馈按钮构建通过。
- 点踩反馈在用户提交原因后只调用一次反馈接口，提交成功后关闭原因输入和提交按钮。

---

## 二、涉及文件

| 类型 | 文件 |
|------|------|
| 后端 DAO | `DAO/agent_dao.py` |
| 后端 API | `agent_system/api/agent_api.py` |
| 后端服务 | `agent_system/service/agent_service.py` |
| 响应模型 | `agent_system/schemas/agent_response.py` |
| 前端全页入口 | `frontend-vue/src/views/AgentView.vue` |
| 前端悬浮入口 | `frontend-vue/src/components/FloatingAgent.vue` |

---

## 三、测试数据

### 3.1 内存数据库测试数据

使用 SQLite 内存库构造最小数据：

```text
TalkSession:
  user_id = alice
  session_title = 测试会话

AgentTask:
  user_id = alice
  persona = academic_mentor
  intent = daily_chat
  original_message = 你好
```

### 3.2 反馈测试数据

第一次提交：

```json
{
  "task_id": 1,
  "rating": 5,
  "comment": "满意",
  "tool_name": null
}
```

第二次覆盖：

```json
{
  "task_id": 1,
  "rating": 1,
  "comment": "回答太泛",
  "tool_name": null
}
```

归属校验：

```text
任务归属用户：alice
非法提交用户：bob
预期结果：bob 被拒绝，返回 404
```

---

## 四、执行命令与结果

### 4.1 Python 编译检查

命令：

```powershell
python -m compileall agent_system DAO model
```

结果：

```text
通过。agent_api.py、agent_response.py、agent_service.py、agent_dao.py 等文件编译成功。
```

### 4.2 前端生产构建

首次命令：

```powershell
npm run build
```

结果：

```text
PowerShell 禁止执行 npm.ps1，非代码错误。
```

改用 Windows 可执行文件：

```powershell
npm.cmd run build
```

结果：

```text
vite build 成功，62 modules transformed，生产包构建完成。
```

### 4.3 DAO upsert 验证

验证点：

- 第一次提交反馈时新增 `AgentFeedback`。
- 第二次对同一 `task_id + tool_name is null` 提交反馈时覆盖同一条记录。
- 覆盖后 `feedback_id` 不变。
- 覆盖后 `rating` 和 `comment` 更新。

输出摘要：

```text
task_id = 1
feedback_id = 1
updated_second_submit = True
rating = 1
```

说明：

- 控制台对中文 comment 的显示出现问号，这是 PowerShell 编码显示问题，不影响断言结果。
- Python 断言全部通过。

### 4.4 API 归属校验验证

验证点：

- `alice` 是任务归属用户，可以提交反馈。
- `bob` 不是任务归属用户，提交同一 `task_id` 会被拒绝。

输出摘要：

```text
owner_submit_code = 200
foreign_user_rejected = True
task_id = 1
```

---

## 五、前端行为预期

### 5.1 AgentView

预期：

- Agent 回复完成后，如果 SSE `done` 携带 `task_id`，助手消息下方展示反馈按钮。
- 点击“满意”提交 `rating=5`，提交成功后按钮锁定，不能重复提交。
- 点击“不满意”只展开原因输入框，不会立即调用反馈接口。
- 用户填写原因并点击“提交原因”后，提交 `rating=1` 和原因文本。
- 点踩原因提交成功后，原因输入框关闭，提交按钮不再显示，反馈按钮锁定。
- 历史消息如果 metadata 中包含 `task_id`，重新打开后仍可提交反馈。

### 5.2 FloatingAgent

预期：

- 悬浮助手的 Agent 回复完成后展示轻量 👍 / 👎 按钮。
- 点击 👍 后提交一次并锁定按钮。
- 点击 👎 后只展示简短原因输入框，不立即提交。
- 用户点击“提交”后才提交点踩原因，提交成功后关闭输入框并锁定按钮。
- 与 AgentView 共用 `/agent/feedback` 接口。

### 5.3 防重复提交补充验证

用户补充要求：

```text
👎 反馈用户提交原因后就关闭提交按钮，一次反馈只提交一次防止多提交
```

实现结果：

- `AgentView.vue` 和 `FloatingAgent.vue` 的反馈状态新增 `submitted`。
- `submitted=true` 后，👍/👎 按钮禁用。
- `submitted=true` 后，点踩原因输入框不再渲染。
- 点踩按钮只负责展开原因输入，不调用 `/agent/feedback`。
- 只有“提交原因/提交”按钮会发送点踩反馈。

验证命令：

```powershell
npm.cmd run build
```

验证结果：

```text
vite build 成功，62 modules transformed，生产包构建完成。
```

---

## 六、验收结论

当前测试结论：

- 后端语法检查通过。
- 前端生产构建通过。
- DAO 层 upsert 行为符合设计。
- API 层任务归属校验符合设计。
- 两个前端入口已接入反馈 UI。
- 点踩反馈已改为“填写原因后提交一次”，提交成功后关闭输入和按钮，避免多次提交。

该功能可以进入用户确认阶段。用户确认无误后，再开始 v2.1 下一个功能：Agent 行为监控面板。
