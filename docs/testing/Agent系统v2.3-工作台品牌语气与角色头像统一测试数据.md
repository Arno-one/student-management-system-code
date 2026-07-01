# Agent系统 v2.3 - 工作台品牌语气与角色头像统一测试数据

## 一、测试目标

验证本轮界面统一化调整已经完成：

1. 左侧品牌区与顶部标题区使用统一视觉语气。
2. 品牌文案统一为“Campus AI Workspace / 校园智能工作台”体系。
3. Agent 对话中的助手头像改为“角色 emoji，缺省回退 AI”。
4. `AgentView` 与 `FloatingAgent` 都生效。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `frontend-vue/src/components/Sidebar.vue` | 统一品牌区英文标签、中文标题与描述 |
| `frontend-vue/src/components/TopBar.vue` | 统一顶部标题英文标签与胶囊文案 |
| `frontend-vue/src/views/AgentView.vue` | 主 Agent 助手头像改为 persona emoji，缺省回退 AI |
| `frontend-vue/src/components/FloatingAgent.vue` | 悬浮 Agent 助手头像改为 persona emoji，缺省回退 AI |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增品牌语气与头像静态护栏 |
| `frontend-vue/scripts/ui-regression-playwright.mjs` | 新增品牌文案与 persona 头像 E2E 检查 |

## 三、设计说明

### 1. 品牌语气统一

统一后的文案：

```text
Sidebar 品牌区：
Campus AI Workspace
校园智能工作台
统一承载学生、教务、统计与智能 Agent 能力。

TopBar 标题区：
Campus AI Workspace
统一业务工作台
```

### 2. 助手头像策略

```text
优先显示当前 persona 的 icon
未命中时回退 AI
用户头像继续保留“我”
```

当前角色对应：

```text
学业导师：🎓
陪伴班主任：🌶
昕哥：😁
```

## 四、测试用例

### 用例 1：品牌区文案统一

预期：

```text
左侧品牌区出现 Campus AI Workspace
中文标题显示为 校园智能工作台
顶部标题区也使用同一英文标签
顶部胶囊显示 统一业务工作台
```

结果：

```text
通过
```

### 用例 2：主 Agent 助手头像跟随 persona

预期：

```text
默认学业导师 persona 下
主 Agent 助手头像显示 🎓
不再显示固定“师”
```

结果：

```text
通过
```

### 用例 3：悬浮 Agent 助手头像跟随 persona

预期：

```text
切换到昕哥 persona 后
悬浮 Agent 助手头像显示 😁
不再固定显示 AI
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
UI 回归检查通过：152/152
PASS AgentView 助手头像按 persona emoji 回退 AI
PASS AgentView 不再使用固定“师”头像
PASS FloatingAgent 助手头像按 persona emoji 回退 AI
PASS FloatingAgent 不再固定使用 AI 头像
PASS 侧栏品牌区使用统一英文标签
PASS 侧栏品牌区使用统一中文标题
PASS 顶部标题使用统一英文标签
PASS 顶部标题使用统一胶囊文案
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

工作台品牌语气和 Agent 助手头像已经统一完成，当前界面会更像同一套产品体系：导航、标题、Agent persona 三者的视觉语言已经打通。
