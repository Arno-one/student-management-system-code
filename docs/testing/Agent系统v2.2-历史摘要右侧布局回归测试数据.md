# Agent 系统 v2.2-历史摘要右侧布局回归测试数据

## 一、问题背景

用户反馈当前 Agent 会话历史排布不合理：
- 会话摘要显示在主聊天区域上方，打断当前对话。
- 历史会话横向排列，占用主区域空间。
- 历史项显示“Agent 对话”，无法快速判断每个会话内容。
- 用户画像/风格类信息不应展示给用户。
- 希望每个会话在用户开始对话后就生成摘要，而不是等长对话后才生成。

## 二、修复目标

本轮修复目标：
- 左侧只保留当前 Agent 对话。
- 右侧展示历史摘要列表。
- 历史项只展示 `summary` 摘要内容和更新时间，不展示默认标题“Agent 对话”。
- 不展示 `style` 等用户画像/风格字段。
- 每轮 Agent 回复保存后立即刷新会话摘要，失败不影响本次回复。
- 生成简短标题式摘要，不生成全文摘要；5 轮以内固定使用第一轮用户问题生成短标题。

## 三、变更文件

```text
agent_system/memory/summary_memory.py
agent_system/memory/__init__.py
agent_system/service/agent_service.py
frontend-vue/src/views/AgentView.vue
frontend-vue/scripts/ui-regression-check.mjs
frontend-vue/scripts/ui-regression-playwright.mjs
docs/testing/Agent系统v2.2-UI可视化回归检查测试数据.md
```

## 四、核心实现

### 1. 前端布局

布局改为：
```text
agent-workspace
├─ agent-chat-main：当前对话
└─ agent-summary-panel：右侧历史摘要
```

历史摘要项渲染规则：
```text
优先显示 session.summary
没有 summary 时显示“摘要生成中，继续对话后会自动更新。”
不回退显示 session.title，避免再次出现“Agent 对话”
不展示 style / 用户画像字段
```

### 2. 后端摘要刷新

原逻辑：
```text
超过 10 条消息或 6000 字后才刷新 summary
```

新逻辑：
```text
每轮用户消息 + Agent 回复保存后立即刷新 summary
摘要刷新失败只写日志，不影响 Agent 回复
```

新增函数：
```text
refresh_summary_safely(session_id, persona, db)
```

### 3. 摘要生成策略

短会话规则：
```text
用户轮次 <= 5 时：
只取第一轮用户问题生成短标题
不调用 LLM 生成全文摘要
不输出“用户询问/用户最近关注/本轮对话”等套话
```

长会话规则：
```text
用户轮次 > 5 时：
允许 LLM 生成主题摘要
但输出限制为 24 字以内的标题文本
不复盘完整对话过程
```

样例：
```text
输入：从宝安到龙岗坐地铁怎么去？
摘要：从宝安到龙岗坐地铁怎么去

输入：帮我查一下我的成绩
摘要：查一下我的成绩
```

## 五、验证命令

```bash
python -m compileall agent_system DAO model main.py
cd frontend-vue
npm.cmd run build
npm.cmd run test:ui-regression
```

## 六、验证结果

后端编译：
```text
compileall passed
```

前端构建：
```text
vite build passed
```

UI 回归：
```text
PASS AgentView 使用左右工作区布局
PASS AgentView 右侧历史摘要栏存在
PASS 历史会话只渲染摘要文本
PASS AgentView 不再渲染横向会话 chip
PASS 历史摘要列表不回退显示 Agent 对话标题
UI 回归检查通过：40/40

PASS Playwright 主 Agent 浅色主题卡片回归
PASS Playwright 悬浮 Agent 移动端卡片回归
Playwright UI 回归通过：2/2
```

摘要策略回归：
```text
_summarize_history([第一轮用户: 从宝安到龙岗坐地铁怎么去？]) == 从宝安到龙岗坐地铁怎么去
_summarize_history([第一轮用户: 帮我查一下我的成绩, 第二轮用户: 再分析一下薄弱项]) == 查一下我的成绩
```

## 七、验收结论

本轮已完成 Agent 历史会话展示调整：
- 当前对话和历史摘要分区清晰。
- 历史列表移动到右侧。
- 历史项不再显示“Agent 对话”。
- 右侧只展示会话摘要，不展示用户画像信息。
- 摘要刷新时机提前到每轮回复后，用户开始对话后即可逐步形成摘要。
- 5 轮以内会话的摘要表现为第一轮问题短标题，避免历史列表出现长篇全文摘要。
