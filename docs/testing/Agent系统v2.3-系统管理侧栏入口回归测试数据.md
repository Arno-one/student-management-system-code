# Agent 系统 v2.3 - 系统管理侧栏入口回归测试数据

## 问题背景

系统管理模块本身仍然配置了二级功能列表：

- 用户管理：`sys-users`
- 角色管理：`sys-roles`
- Agent 监控：`sys-agent-monitor`

但侧栏折叠时，父模块点击只尝试切换子菜单展开态，不会触发页面跳转；由于折叠态不会展示子菜单，用户会被卡在系统管理入口外。

## 修复设计

点击带二级功能的父模块时，保留原有展开 / 收起行为，同时立即导航到该模块的默认子功能。

- 侧栏展开：点击父模块会展开或收起子菜单，并进入已记忆子功能或第一个子功能。
- 侧栏折叠：点击父模块不会依赖子菜单展示，直接进入默认子功能。
- 系统管理默认子功能：`/system?sub=sys-users`。

## 回归用例

### 用例 1：折叠侧栏进入系统管理

前置条件：

- 当前用户为管理员角色。
- 当前用户拥有 `system:page` 菜单权限。
- `localStorage.workspace-sidebar-collapsed = '1'`。

操作步骤：

1. 打开任意业务页面，例如学生信息管理。
2. 点击折叠侧栏里的“系统管理”图标入口。

预期结果：

- 页面跳转到 `/system?sub=sys-users`。
- `#page-system` 正常渲染。
- `#sys-users` 面板处于 `.show` 状态。

### 用例 2：系统管理子功能配置完整

检查内容：

- `moduleNavigation.js` 中存在 `page: 'system'`。
- 系统管理保留 `sys-users`、`sys-roles`、`sys-agent-monitor` 三个子功能。

预期结果：

- 系统管理模块可见性仍由 `adminOnly` 和 `system:page` 权限控制。
- 二级功能列表配置未丢失。

## 自动化验证

已执行命令：

```bash
npm run test:ui-regression:static
npm run test:ui-regression:e2e
```

验证结果：

- 静态 UI 回归：`87/87` 通过。
- Playwright UI 回归：`3/3` 通过。
- 新增 Playwright 场景：折叠侧栏点击系统管理后进入 `/system?sub=sys-users`。

