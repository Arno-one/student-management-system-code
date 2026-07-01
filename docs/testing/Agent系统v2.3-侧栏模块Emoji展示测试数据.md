# Agent系统 v2.3 - 侧栏模块 Emoji 展示测试数据

## 一、测试目标

验证左侧模块导航已按配置驱动方式接入 emoji 展示：

1. 每个模块在 `moduleNavigation.js` 中都可配置 `emoji`。
2. `Sidebar` 优先展示 `emoji`，缺失时再回退 `short`。
3. 展开态和折叠态都能正常显示模块 emoji。
4. 折叠态点击模块入口的既有跳转行为不受影响。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `frontend-vue/src/config/moduleNavigation.js` | 为各模块新增 `emoji` 配置 |
| `frontend-vue/src/components/Sidebar.vue` | 侧栏图标位改为优先渲染 `item.emoji` |
| `frontend-vue/src/assets/styles.css` | 新增侧栏 emoji 图标样式，兼容展开态与折叠态 |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增侧栏模块 emoji 静态护栏 |
| `frontend-vue/scripts/ui-regression-playwright.mjs` | 新增折叠态系统管理 emoji 回归检查 |

## 三、当前模块 Emoji 配置

```text
🧑‍🎓 学生信息管理
📝 考核成绩管理
💼 就业信息管理
🏫 班级管理
🧑‍🏫 教师管理
📈 统计分析
✨ AI 作业模块
📧 邮件管理
📊 NL2SQL 智能问数
📚 RAG 知识库工作台
🤖 智能 Agent 助手
⚙️ 系统管理
```

## 四、测试用例

### 用例 1：展开态显示模块 Emoji

预期：

```text
侧栏展开时，每个模块左侧图标位优先显示 emoji
模块标题与描述继续正常展示
```

结果：

```text
通过
```

### 用例 2：折叠态显示模块 Emoji

预期：

```text
侧栏折叠时，只保留模块 emoji 图标
不再显示旧的字母缩写作为主展示
```

结果：

```text
通过
```

### 用例 3：系统管理折叠态入口仍可点击

预期：

```text
折叠侧栏下，系统管理图标显示为 ⚙️
点击后正常跳转到 /system?sub=sys-users
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
UI 回归检查通过：145/145
PASS Sidebar 模块图标优先展示 emoji
PASS Sidebar 为 emoji 图标提供独立样式类
PASS 模块导航配置包含学生管理 emoji
PASS 模块导航配置包含系统管理 emoji
PASS 全局样式包含侧栏 emoji 图标样式
PASS 折叠态侧栏包含 emoji 图标样式
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

左侧模块导航的 emoji 展示已经接入完成，当前采用与快捷工具面板一致的“配置驱动 + 渲染层兜底”方式，后续新增模块时只需要补一条配置即可。
