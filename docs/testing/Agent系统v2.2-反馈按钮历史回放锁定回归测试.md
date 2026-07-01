# Agent 系统 v2.2 - 反馈按钮历史回放锁定回归测试

## 一、问题现象

用户在某轮 Agent 回复后已经提交过反馈，当前页面内按钮会正确锁定；但切换到其他对话再切回历史会话后，同一轮回复的反馈按钮又变成可点击状态。

## 二、问题原因

历史消息接口 `/agent/sessions/{session_id}/messages` 只返回 assistant 消息 metadata 里的 `task_id`，没有把 `AgentFeedback` 表里的已反馈状态合并返回。

前端 `loadSession()` 看到 `metadata.task_id` 后会重新执行 `createFeedback(task_id)`，而 `createFeedback()` 默认 `submitted=false`，导致历史回放时按钮重新可点。

同时，后端 `/agent/feedback` 原先使用 upsert 语义，重复提交会覆盖旧反馈，不符合“每轮对话只能反馈一次”的约定。

## 三、修复方案

采用前后端双保险：

- 后端历史消息接口批量查询 `AgentFeedback`，在 assistant metadata 中补充 `feedback.submitted/rating/comment/feedback_id`。
- 前端历史回放时用 `metadata.feedback` 初始化反馈状态，已反馈按钮直接锁定。
- 后端反馈提交接口在写入前检查同一 `task_id + tool_name` 是否已有反馈；已有则返回 409，禁止重复提交。

## 四、涉及文件

| 文件 | 说明 |
|------|------|
| `agent_system/api/agent_api.py` | 历史消息接口补充反馈状态；反馈提交接口拒绝重复提交 |
| `frontend-vue/src/views/AgentView.vue` | `createFeedback()` 支持从历史反馈初始化；409 时同步锁定 |

## 五、验证记录

### 1. 后端编译检查

命令：

```bash
python -m compileall agent_system DAO model main.py
```

结果：

```text
通过。agent_api.py 编译成功。
```

### 2. 前端生产构建

命令：

```bash
cd frontend-vue
npm.cmd run build
```

结果：

```text
通过。AgentView.vue 改动可正常打包。
```

### 3. 最小后端回归

测试方式：

- 使用内存 SQLite 创建 `TalkSession`、`TalkMessage`、`AgentTask`、`AgentFeedback`。
- 构造一条带 `task_id` 的历史 assistant 消息。
- 构造该任务已有任务级反馈。
- 直接调用 `get_messages()`，验证返回 metadata 中包含 `feedback.submitted=true`。
- 再调用 `submit_feedback()` 重复提交，验证返回 409。

结果：

```text
{'submitted': True, 'rating': 5, 'duplicate_status': 409}
```

## 六、验收结论

该回归已修复：

- 切换历史会话后，已反馈的回复仍会保持锁定。
- 同一轮对话不能通过接口重复提交反馈。
- 前端显示和后端约束保持一致。
