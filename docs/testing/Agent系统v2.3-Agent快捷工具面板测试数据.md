# Agent系统 v2.3 - Agent 快捷工具面板测试数据

## 一、测试目标

验证本轮 v2.3 功能“快捷工具面板”已经按方案 A 落地：

1. `AgentView` 和 `FloatingAgent` 都接入快捷工具面板。
2. 面板默认折叠，用户可主动展开。
3. 面板固定提供 6 个工具入口。
4. 每个工具入口都带有对应 emoji 标识。
5. `天气 / 通勤 / 周边 / 邮件` 走模板回填主输入框。
6. `文生图 / NL2SQL智能问数` 支持面板内输入并直接发送真实用户消息。
7. 快捷工具面板样式跟随系统浅色 / 深色主题。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `frontend-vue/src/config/agentQuickTools.js` | 新增快捷工具配置、模板构造器、消息构造器 |
| `frontend-vue/src/components/QuickToolPanel.vue` | 新增复用型快捷工具面板组件 |
| `frontend-vue/src/views/AgentView.vue` | 主 Agent 页面接入快捷工具面板 |
| `frontend-vue/src/components/FloatingAgent.vue` | 悬浮 Agent 接入 compact 快捷工具面板，并整理输入区布局 |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增快捷工具面板静态护栏 |
| `frontend-vue/scripts/ui-regression-playwright.mjs` | 新增快捷工具面板 E2E 回归场景 |

## 三、关键设计

### 1. 工具入口清单

```text
文生图
天气
通勤
周边
邮件
NL2SQL智能问数
```

对应 emoji：

```text
🎨 文生图
🌤️ 天气
🧭 通勤
📍 周边
📧 邮件
📊 NL2SQL智能问数
```

### 2. 两种交互模式

```text
fill_template：
- 天气
- 通勤
- 周边
- 邮件

inline_send：
- 文生图
- NL2SQL智能问数
```

### 3. 发送策略

```text
文生图：
请帮我生成一张图片：{用户输入}

NL2SQL智能问数：
请用 NL2SQL 智能问数帮我查询：{用户输入}
```

### 4. 主题与布局策略

```text
QuickToolPanel 只使用 var(--panel)、var(--panel-2)、var(--text)、var(--line)、var(--gold) 等主题变量
FloatingAgent 输入区调整为“快捷工具面板 + 输入行”结构
compact 模式下卡片信息密度更高，移动端自动单列展示
```

## 四、测试用例

### 用例 1：主 Agent 默认折叠

预期：

```text
进入 /agent 页面后，快捷工具面板默认 aria-expanded=false
不自动展开占用输入区空间
```

结果：

```text
通过
```

### 用例 2：主 Agent 模板回填

操作：

```text
展开快捷工具面板
点击“天气”
点击“通勤”
```

预期：

```text
主输入框依次回填：
帮我查一下 [请补充城市/地点] 的天气。
从 [请补充起点] 到 [请补充终点] 怎么去？
```

结果：

```text
通过
```

### 用例 3：主 Agent 文生图内联直发

输入：

```text
校园学习角，暖色插画
```

预期：

```text
直接发起 /agent/chat/stream 请求
请求体中包含：
请帮我生成一张图片：校园学习角，暖色插画
```

结果：

```text
通过
```

### 用例 4：主 Agent NL2SQL 内联直发

输入：

```text
统计近30天请假人数
```

预期：

```text
直接发起 /agent/chat/stream 请求
请求体中包含：
请用 NL2SQL 智能问数帮我查询：统计近30天请假人数
```

结果：

```text
通过
```

### 用例 5：悬浮 Agent compact 面板

操作：

```text
打开 FloatingAgent
切换到昕哥 persona
展开快捷工具面板
点击“周边”
```

预期：

```text
快捷工具面板默认折叠
展开后使用 compact 布局
快捷工具列表可在面板内部上下滚动浏览
可完整访问全部 6 个工具入口
主输入框回填：
[请补充地点] 附近有什么 [请补充服务类型]？
```

结果：

```text
通过
```

### 用例 6：悬浮 Agent 文生图内联直发

输入：

```text
宿舍自习桌，柔和灯光
```

预期：

```text
直接发起 /agent/chat/stream 请求
请求体中包含：
请帮我生成一张图片：宿舍自习桌，柔和灯光
```

结果：

```text
通过
```

## 五、自动化验证

### 1. 前端静态回归

命令：

```text
npm.cmd run test:ui-regression:static
```

关键结果：

```text
UI 回归检查通过：136/136
PASS 快捷工具配置存在
PASS 快捷工具配置包含 NL2SQL 入口
PASS 快捷工具配置包含模板生成器
PASS 快捷工具配置包含消息生成器
PASS 快捷工具面板组件存在折叠标题
PASS 快捷工具面板支持面板内直接发送
PASS 快捷工具面板支持填入模板
PASS AgentView 接入快捷工具面板
PASS FloatingAgent 以 compact 模式接入快捷工具面板
```

### 2. Playwright 可视化回归

命令：

```text
npm.cmd run test:ui-regression:e2e
```

结果：

```text
Playwright 主 Agent 欢迎语、快捷工具面板与图片卡片回归：通过
Playwright 悬浮 Agent 欢迎语、快捷工具面板与图片卡片回归：通过
Playwright 折叠侧栏系统管理入口回归：通过
Playwright UI 回归通过：3/3
```

## 六、结论

本轮 v2.3 “快捷工具面板”已完成开发和验证，可以进入你的功能验收。

当前交付边界：

1. 本版只做标准版快捷工具面板，不做自动识别推荐工具。
2. `文生图 / NL2SQL` 走面板内联输入，其余工具走主输入框模板回填。
3. 只做前端快捷入口与消息格式化，不新增后端 tool 能力。
