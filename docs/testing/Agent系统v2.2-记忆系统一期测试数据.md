# Agent 系统 v2.2 - 记忆系统一期测试数据

## 一、测试目标

验证 `working_memory + summary_memory` 一期能力是否满足 v2.2 约定：

- 同一会话消息超过 10 条，或历史文本估算超过 6000 字时触发会话摘要。
- Agent 后续上下文使用“会话摘要 + 最近 5 条原文”。
- 摘要失败不影响 Agent 正常回复。
- 陪伴班主任类对话摘要只保存主题和建议，不记录过度敏感细节。
- 前端会话列表优先展示摘要内容。

## 二、涉及文件

| 文件 | 说明 |
|------|------|
| `agent_system/memory/working_memory.py` | 新增工作记忆模块，负责消息转历史项、最近 5 条原文截取、上下文长度估算 |
| `agent_system/memory/summary_memory.py` | 新增摘要记忆模块，负责摘要触发、生成、兜底和保存 |
| `agent_system/memory/conversation_memory.py` | `get_history()` 改为返回“摘要 + 最近原文” |
| `agent_system/service/agent_service.py` | assistant 回复保存后刷新摘要，失败不阻塞主流程 |
| `agent_system/middleware/query_rewriter.py` | 支持 `summary` 历史角色展示 |
| `agent_system/planner/task_planner.py` | 支持 `summary` 历史角色展示 |
| `frontend-vue/src/views/AgentView.vue` | 会话列表优先显示 `summary` |

## 三、测试用例

### 1. 后端编译检查

命令：

```bash
python -m compileall agent_system DAO model main.py
```

结果：

```text
通过。新增 memory 模块、服务层和 planner/middleware 均无语法错误。
```

### 2. 前端生产构建

命令：

```bash
cd frontend-vue
npm.cmd run build
```

结果：

```text
通过。Vite build 成功，AgentView 改动可正常打包。
```

### 3. 摘要触发与上下文压缩

测试方式：

- 使用内存 SQLite 创建 `TalkSession` 和 `TalkMessage`。
- 构造同一会话 12 条消息。
- 模拟 LLM 摘要失败，验证规则兜底不影响流程。
- 调用 `refresh_summary_if_needed()` 和 `get_history()`。

核心断言：

```text
session.summary 非空
session.session_title 已更新为摘要短标题
get_history() 返回 6 条：1 条 summary + 最近 5 条原文
第一条 role = summary
最后一条为最近 assistant 原文
```

结果：

```text
通过。超过 10 条消息后触发摘要；LLM 失败时使用规则兜底；上下文长度符合“摘要 + 最近 5 条原文”。
```

## 四、验收结论

本功能已完成 v2.2 第一项“Agent 记忆系统一期”的基础闭环：

- 长对话不会继续无限塞入完整历史。
- planner 和 query_rewriter 能读取摘要上下文。
- 摘要生成失败不会中断 Agent 回复。
- 会话列表具备摘要标题展示能力。

## 五、后续建议

- 下一个功能“通勤规划 Agent 能力”接入 LangGraph 中间件时，可以直接复用当前 `get_history()` 的紧凑上下文。
- 后续长期用户画像暂不建议在本阶段实现，避免把会话级摘要误扩展成跨会话记忆。
