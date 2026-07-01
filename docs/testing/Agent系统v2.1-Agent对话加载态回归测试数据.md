# Agent系统v2.1-Agent对话加载态回归测试数据

## 一、测试目标

修复用户与 Agent 对话时，等待回复阶段左侧同时出现两个 Agent 头像的问题。

## 二、问题原因

发送消息后，前端会立即插入一条 `_streaming=true` 的 assistant 消息用于承接 SSE 流式回复。

但 `AgentView.vue` 和 `FloatingAgent.vue` 同时又根据全局 `loading` 状态额外渲染了一条 assistant loading 消息：

- 第一条 assistant 消息：真实流式消息，占一个 Agent 头像。
- 第二条 assistant loading 消息：仅展示“正在思考...”或打点动画，也占一个 Agent 头像。

因此等待 Agent 回复时会看到两个 Agent 头像。

## 三、修复方式

将 loading 动画合并到当前 `_streaming` 的 assistant 消息内部：

- 当 `msg.role === 'assistant' && msg._streaming && !msg.content` 时，在当前消息气泡中显示 loading 动画。
- 当收到首个流式文本后，切换为原有流式文本展示。
- 移除消息列表末尾额外的 `v-if="loading"` assistant loading 消息块。

## 四、测试数据

### 用例 1：主 Agent 页面等待回复

输入：

```text
帮我查一下北京天气
```

预期：

```text
等待首个 SSE 文本片段时，只展示一条 assistant 消息。
左侧只出现 1 个“师”头像。
消息气泡内展示“正在思考...”和打点动画。
```

### 用例 2：全局悬浮 Agent 等待回复

输入：

```text
今天适合出去跑步吗
```

预期：

```text
等待首个 SSE 文本片段时，只展示一条 assistant 消息。
左侧只出现 1 个“AI”头像。
消息气泡内展示打点动画。
```

### 用例 3：收到流式文本后

预期：

```text
loading 动画消失。
同一条 assistant 消息继续承载流式文本。
不会新增第二条 assistant 占位消息。
```

## 五、验证命令

```bash
npm.cmd run build
python -m compileall agent_system DAO model main.py
```

模板检查：

```powershell
Select-String -Path frontend-vue\src\views\AgentView.vue,frontend-vue\src\components\FloatingAgent.vue -Pattern 'agent-msg-assistant" v-if="loading|float-agent-msg-assistant" v-if="loading'
```

预期结果：

```text
无匹配结果
```

## 六、结论

通过。Agent 回复生成期间只保留一条 assistant 消息，避免重复头像，同时不影响后续 SSE 流式文本、工具调用摘要、天气卡片和反馈组件展示。
