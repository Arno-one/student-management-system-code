# Agent系统 v2.3 - Agent监控首屏自动加载测试数据

## 一、测试目标

验证进入系统管理的 `Agent监控` 子功能时，页面会自动展示默认近 7 天范围的数据，不再要求用户手动点击“刷新”按钮。

## 二、问题背景

原实现里，`Agent监控` 的自动加载依赖 `useModuleSubPage` 的回调链触发，进入 `sys-agent-monitor` 时不够稳定。

实际表现是：

1. 用户已经进入 `Agent监控` 窗口
2. 页面首屏没有任何监控数据
3. 必须再手动点击“刷新”才会显示

这和监控页的使用预期不一致。

## 三、修复设计

本次采用方案 A：

- 在 `SystemView.vue` 中直接监听 `sub.value`
- 只要子功能切换到 `sys-agent-monitor`
- 就立即调用 `loadAgentMonitor()`
- 且保留“刷新”按钮，作为用户主动重查入口

这样可以保证：

1. 首次直接打开 `/#/system?sub=sys-agent-monitor` 会自动加载
2. 从 `sys-users` / `sys-roles` 切换到 `sys-agent-monitor` 也会自动加载
3. 默认查询参数仍然是 `days=7`

## 四、回归用例

### 用例 1：直接打开 Agent监控路由，首屏自动加载

前置条件：

- 已登录管理员账号
- 当前用户具备 `system:page` 权限

操作步骤：

1. 直接访问 `/#/system?sub=sys-agent-monitor`
2. 不点击“刷新”

预期结果：

- 自动发起 `GET /agent/admin/dashboard?days=7`
- 自动发起 `GET /agent/admin/tasks?days=7...`
- `#sys-agent-monitor.show` 正常显示
- 页面出现监控数据，不是空白
- 页面出现“Agent 监控数据加载成功”

### 用例 2：从系统管理其他子功能切到 Agent监控，自动加载

操作步骤：

1. 先打开 `/#/system?sub=sys-users`
2. 再点击系统管理下的 `Agent监控`
3. 不点击“刷新”

预期结果：

- 自动加载近 7 天监控数据
- 最近任务表格可见
- 详情区可选择任务

### 用例 3：刷新按钮仍可手动重查

操作步骤：

1. 进入 `Agent监控`
2. 修改筛选条件，例如时间范围改成 `近30天`
3. 点击“刷新”

预期结果：

- 继续调用 `loadAgentMonitor()`
- 按新筛选条件重查成功

## 五、自动化验证

### 前端静态回归

命令：

```bash
npm.cmd run test:ui-regression:static
```

验证点：

- `SystemView` 存在 `watch(() => sub.value, ...)`
- 存在 `if (nextSub === 'sys-agent-monitor')`
- 进入监控页自动加载逻辑仍在

### Playwright UI 回归

命令：

```bash
npm.cmd run test:ui-regression:e2e
```

新增覆盖点：

- 直接打开 `/#/system?sub=sys-agent-monitor`
- 不点击刷新
- 自动请求 dashboard / tasks
- 页面展示 mock 的监控任务内容

## 六、涉及文件

- `frontend-vue/src/views/SystemView.vue`
- `frontend-vue/scripts/ui-regression-check.mjs`
- `frontend-vue/scripts/ui-regression-playwright.mjs`

## 七、结论

本次修复后，`Agent监控` 终于符合正常使用习惯了：

- 进入窗口即自动展示默认近 7 天数据
- 用户不需要先点一次“刷新”
- 手动刷新仍然保留，方便主动重查
