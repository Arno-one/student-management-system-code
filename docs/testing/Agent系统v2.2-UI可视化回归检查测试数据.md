# Agent 系统 v2.2-UI 可视化回归检查测试数据

## 一、功能目标

本轮目标是把 v2.1/v2.2 中已经出现过的 UI 回归点沉淀成可重复执行的本地检查命令，避免后续改卡片、主题或 Agent loading 时再次引入问题。

本功能已从“静态护栏”升级为“静态护栏 + Playwright Edge 真浏览器回归”。

覆盖重点：
- 浅色/深色主题不被卡片组件污染。
- `WeatherCard`、`RouteCard` 在主 Agent 和悬浮 Agent 中都按通用卡片协议安全渲染。
- 未知 `card.type` 和不支持的 `card_version` 不会被前端直接渲染。
- 卡片字段缺失时组件安全降级，不抛前端异常。
- Agent 等待首个 SSE 片段时只复用当前 assistant 消息，不新增第二个 assistant 头像。

## 二、变更文件

```text
frontend-vue/package.json
frontend-vue/package-lock.json
frontend-vue/scripts/ui-regression-check.mjs
frontend-vue/scripts/ui-regression-playwright.mjs
```

## 三、测试命令

PowerShell 中建议使用 `npm.cmd`，避免本机执行策略拦截 `npm.ps1`：

```bash
cd frontend-vue
npm.cmd run test:ui-regression
```

该命令会自动执行：
1. `vite build`
2. 主题隔离静态检查
3. 卡片协议渲染检查
4. loading 单头像检查
5. dist CSS 产物污染检查
6. 启动 Vite preview
7. 使用 Playwright 驱动本机 Microsoft Edge 做真实 DOM 回归检查

## 四、核心测试数据

### 1. 主题隔离

检查目标：
```text
WeatherCard.vue
RouteCard.vue
dist/assets/*.css
```

核心断言：
```text
不包含 :global(...theme-light/theme-dark)
不包含 .theme-light / .theme-dark 全局覆盖
组件使用 var(--panel...) 等主题变量
组件包含 overflow: hidden
组件包含 @media (max-width: 680px)
```

结果：
```text
PASS WeatherCard 不覆盖全局主题类
PASS RouteCard 不覆盖全局主题类
PASS 构建产物不包含 scoped 全局主题污染
```

### 2. 卡片协议安全渲染

检查目标：
```text
AgentView.vue
FloatingAgent.vue
WeatherCard.vue
RouteCard.vue
```

核心断言：
```text
AgentView 接入 WeatherCard / RouteCard
FloatingAgent 接入 WeatherCard / RouteCard
msg.cards 必须按 c.type === 'weather' / c.type === 'route' 过滤
必须经过 isCardVersionSupported(c)
card.card_version 只接受空值或 1
不能直接 v-for 渲染未过滤的 msg.cards
RouteCard 校验 routes 必须是数组
WeatherCard / RouteCard 缺少 data 时降级为空对象
```

结果：
```text
PASS AgentView 接入 weather 卡片
PASS AgentView 接入 route 卡片
PASS AgentView 不直接渲染未知 card type
PASS FloatingAgent 接入 weather 卡片
PASS FloatingAgent 接入 route 卡片
PASS FloatingAgent 不直接渲染未知 card type
PASS RouteCard 字段缺失时安全降级
PASS WeatherCard 字段缺失时安全降级
```

### 3. loading 单头像回归

问题背景：
```text
之前 Agent 等待回复时出现过两个 assistant 头像：
一个来自 _streaming assistant 占位消息；
另一个来自全局 loading 额外渲染块。
```

核心断言：
```text
发送消息后创建 role: 'assistant' 占位消息
占位消息带 _streaming: true
loading 动画绑定 msg.role === 'assistant' && msg._streaming && !msg.content
不存在独立 v-if="loading" 的 assistant 消息块
```

结果：
```text
PASS AgentView loading 绑定当前 assistant 消息
PASS AgentView 不新增独立 loading 消息
PASS FloatingAgent loading 绑定当前 assistant 消息
PASS FloatingAgent 不新增独立 loading 消息
```

### 4. Playwright Edge 真浏览器回归

浏览器方案：
```text
Playwright chromium.launch({ channel: 'msedge' })
```

选择原因：
- 复用本机已安装 Microsoft Edge，不需要额外下载 Playwright Chromium。
- 能真实打开页面、执行 Vue、触发 SSE mock、检查 DOM 和布局。
- 脚本自己启动/关闭 Vite preview，避免 Playwright Test Runner 在 Windows 环境下进程回收不稳。

Mock 数据：
```text
auth/me -> 当前管理员用户
agent/personas -> academic_mentor
agent/sessions -> 空列表
agent/chat/stream -> SSE 返回：
- weather card
- route card
- unknown_debug_card（应被忽略）
- card_version=999 的 route card（应被忽略）
```

核心断言：
```text
主 Agent：
- 浅色主题 .app-layout.theme-light 生效
- loading 阶段 assistant 头像数量为 1
- WeatherCard 可见
- RouteCard 可见
- 未知 card type 不可见
- 不支持 card_version 不可见

悬浮 Agent：
- 移动端视口 390x844
- loading 阶段 assistant 头像数量为 1
- WeatherCard / RouteCard 可见
- 卡片没有横向溢出悬浮面板

历史摘要栏：
- AgentView 使用左右工作区布局
- 右侧历史摘要栏存在
- 历史会话只渲染 summary 文本
- 不再渲染横向会话 chip
- 不回退显示默认标题“Agent 对话”
```

结果：
```text
PASS Playwright 主 Agent 浅色主题卡片回归
PASS Playwright 悬浮 Agent 移动端卡片回归
Playwright UI 回归通过：2/2
```

## 五、完整执行结果

```text
PASS 前端生产构建通过
PASS WeatherCard 不覆盖全局主题类
PASS WeatherCard 使用主题变量
PASS WeatherCard 卡片内容不会溢出外框
PASS WeatherCard 具备移动端约束
PASS RouteCard 不覆盖全局主题类
PASS RouteCard 使用主题变量
PASS RouteCard 卡片内容不会溢出外框
PASS RouteCard 具备移动端约束
PASS AgentView 接入 weather 卡片
PASS AgentView 接入 route 卡片
PASS AgentView 过滤 weather 卡片版本
PASS AgentView 过滤 route 卡片版本
PASS AgentView 只接受受支持卡片版本
PASS AgentView 不直接渲染未知 card type
PASS FloatingAgent 接入 weather 卡片
PASS FloatingAgent 接入 route 卡片
PASS FloatingAgent 过滤 weather 卡片版本
PASS FloatingAgent 过滤 route 卡片版本
PASS FloatingAgent 只接受受支持卡片版本
PASS FloatingAgent 不直接渲染未知 card type
PASS RouteCard 字段缺失时安全降级
PASS RouteCard 校验 routes 数组
PASS WeatherCard 字段缺失时安全降级
PASS WeatherCard 空数据不强制渲染
PASS AgentView 创建 assistant 占位消息
PASS AgentView 使用 streaming 占位状态
PASS AgentView loading 绑定当前 assistant 消息
PASS AgentView 不新增独立 loading 消息
PASS FloatingAgent 创建 assistant 占位消息
PASS FloatingAgent 使用 streaming 占位状态
PASS FloatingAgent loading 绑定当前 assistant 消息
PASS FloatingAgent 不新增独立 loading 消息
PASS AgentView 使用左右工作区布局
PASS AgentView 右侧历史摘要栏存在
PASS 历史会话只渲染摘要文本
PASS AgentView 不再渲染横向会话 chip
PASS 历史摘要列表不回退显示 Agent 对话标题
PASS dist CSS 产物存在
PASS 构建产物不包含 scoped 全局主题污染
UI 回归检查通过：40/40

PASS Playwright 主 Agent 浅色主题卡片回归
PASS Playwright 悬浮 Agent 移动端卡片回归
Playwright UI 回归通过：2/2
```

## 六、验收结论

本功能已完成 UI 回归护栏升级：
- 新增 `npm.cmd run test:ui-regression` 一条命令完成构建、静态护栏和 Edge 真浏览器回归。
- 静态检查守住主题污染、卡片协议、loading 单头像等源码级规则。
- Playwright Edge 检查覆盖主 Agent 和悬浮 Agent 的真实 DOM 渲染、SSE 卡片回放和移动端卡片溢出。

## 七、后续建议

- 可以继续补充截图对比，但建议只对关键卡片做少量快照，避免样式微调造成大量无效失败。
- 可以把该命令纳入后续发版前手动检查清单，与 `python -m compileall agent_system DAO model main.py` 配套执行。
