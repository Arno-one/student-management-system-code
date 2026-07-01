# Agent系统 v2.3 - Agent 文生图工具与图片卡片测试数据

## 一、测试目标

验证本轮 v2.3 第一段功能“Agent 文生图工具 + 图片卡片”已经形成完整闭环：

1. Agent 能独立识别 `image_generation` 意图。
2. Planner 能规划并执行 `image_tool`。
3. Executor 能返回 `image` 类型卡片。
4. `AgentView` 和 `FloatingAgent` 都能渲染图片卡片。
5. 图片卡片操作 `重新生成 / 复制提示词 / 复制图片链接` 可用。
6. 图片卡片样式跟随系统浅色 / 深色主题。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `agent_system/tools/image_tool.py` | 新增 Agent 文生图工具，复用现有工作台文生图能力 |
| `agent_system/prompts/intent_prompt.py` | 新增 `image_generation` 意图说明 |
| `agent_system/prompts/planner_prompt.py` | 新增 `image_tool` 规划规则 |
| `agent_system/planner/task_planner.py` | 新增 `image_generation` 回退执行计划 |
| `agent_system/executor/agent_executor.py` | 接入 `image_tool` 注册、摘要、原始结果和 `image` 卡片提取 |
| `frontend-vue/src/components/ImageCard.vue` | 新增图片卡片组件 |
| `frontend-vue/src/views/AgentView.vue` | 主 Agent 页面接入图片卡片 |
| `frontend-vue/src/components/FloatingAgent.vue` | 悬浮 Agent 接入图片卡片 |
| `docs/Agent卡片协议v1.md` | 新增 `image` 卡片协议说明 |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增图片卡片静态回归检查 |
| `frontend-vue/scripts/ui-regression-playwright.mjs` | 新增图片卡片 E2E 回归场景 |

## 三、关键设计

### 1. 卡片协议

```json
{
  "type": "image",
  "card_version": 1,
  "data": {
    "provider": "qwen_image",
    "model": "qwen-image-2.0-pro",
    "prompt": "生成一张校园学习海报风格插画，暖色调，书桌、台灯、笔记本清晰可见",
    "image_url": "https://example.com/generated-image.png"
  }
}
```

### 2. 前端交互

```text
重新生成：直接以“请根据以下提示词重新生成一张图片：...”发起新一轮 Agent 对话
复制提示词：复制原始 prompt
复制图片链接：复制 image_url
```

### 3. 主题策略

```text
ImageCard 只使用 var(--panel)、var(--text)、var(--line)、var(--gold-bg) 等主题变量
不写死 theme-light / theme-dark
主 Agent 和悬浮 Agent 共用同一套图片卡片样式
```

## 四、测试用例

### 用例 1：意图识别与执行链路

输入示例：

```text
帮我画一张校园学习海报
```

预期：

```text
命中 image_generation
Planner 规划 image_tool
Executor 返回图片已生成摘要
done.cards 中包含 type=image, card_version=1
```

结果：

```text
通过
```

### 用例 2：主 Agent 渲染图片卡片

预期：

```text
AgentView 渲染 .agent-image-card
图片预览可见
显示提示词、provider、model
显示“重新生成 / 复制提示词 / 复制图片链接”
```

结果：

```text
通过
```

### 用例 3：悬浮 Agent 渲染图片卡片

预期：

```text
FloatingAgent 渲染 .agent-image-card
深色主题下卡片仍正常显示
卡片不横向溢出悬浮面板
```

结果：

```text
通过
```

### 用例 4：重新生成操作

操作：

```text
点击图片卡片“重新生成”
```

预期：

```text
前端直接发起新的 /agent/chat/stream 请求
请求体中包含“请根据以下提示词重新生成一张图片：”
```

结果：

```text
通过
```

### 用例 5：协议护栏

预期：

```text
AgentView 与 FloatingAgent 只渲染 weather / image / route / poi_list
未知 card type 安全忽略
不支持的 card_version 安全忽略
map_location 仍只保留协议，不做渲染
```

结果：

```text
通过
```

## 五、自动化验证

### 1. 后端编译

命令：

```text
python -m compileall agent_system
```

结果：

```text
通过
```

### 2. 前端静态回归

命令：

```text
npm.cmd run test:ui-regression:static
```

关键结果：

```text
UI 回归检查通过：108/108
PASS AgentView 接入 image 卡片
PASS FloatingAgent 接入 image 卡片
PASS ImageCard 使用主题变量
PASS ImageCard 支持重新生成事件
PASS ImageCard 支持复制提示词和链接
PASS 卡片协议文档声明 image 卡片接线
```

### 3. Playwright 端到端回归

命令：

```text
npm.cmd run test:ui-regression:e2e
```

结果：

```text
Playwright 主 Agent 浅色主题图片卡片回归：通过
Playwright 悬浮 Agent 深色主题图片卡片回归：通过
Playwright 折叠侧栏系统管理入口回归：通过
Playwright UI 回归通过：3/3
```

## 六、结论

本轮 v2.3 第一段功能“Agent 文生图工具 + 图片卡片”已开发完成，并通过后端编译、前端静态回归和 Playwright 可视化回归验证。

当前交付边界：

1. 只做单图卡片，不做多图。
2. 只做图片卡片，不做欢迎语和快捷工具面板。
3. `重新生成` 采用直接发起新一轮对话的方式。
