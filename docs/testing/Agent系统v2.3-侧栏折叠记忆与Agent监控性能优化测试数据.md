# Agent系统 v2.3 - 侧栏折叠记忆与 Agent 监控性能优化测试数据

## 一、测试目标

验证本轮修复是否完成下面 3 个问题的闭环：

1. 左侧模块导航栏折叠后再展开，能够记住并定位到当前功能模块。
2. 折叠态侧栏改为独立的 emoji 导航列表，不再复用展开态的大按钮结构。
3. 系统管理中的 `Agent 监控` 从多接口重复聚合，优化为聚合接口 + 数据库索引补齐，降低加载耗时。

## 二、设计结论

### 1. 侧栏折叠态

- 折叠态单独渲染 `sidebar-rail`
- 只展示模块 emoji 图标按钮
- 子功能选择仍保留在展开态完成

### 2. 侧栏展开记忆

- 当前路由切到某个模块时，同步 `expandedPage`
- 折叠态进入模块后，重新展开侧栏时自动展开当前模块
- 展开后对当前激活模块执行 `scrollIntoView`

### 3. Agent 监控性能优化

- 前端由多次请求改为：
  - `GET /agent/admin/dashboard`
  - `GET /agent/admin/tasks`
- 后端新增聚合构建器 `_build_dashboard_payload`
- 为 `agent_task` 表补齐监控常用索引：
  - `create_time`
  - `status`
  - `intent`

## 三、为什么之前会慢

不是“没有数据库表”。

当前 Agent 监控本来就依赖数据库表：

- `agent_task`
- `agent_feedback`

慢的主要原因有两个：

1. 前端之前会并发请求多组监控接口，后端每个接口都会重复加载并聚合同一批任务数据。
2. 监控筛选常用字段 `create_time`、`status`、`intent` 之前没有补齐到老库索引，容易退化成更重的扫描。

## 四、回归用例

### 用例 1：折叠态侧栏只展示独立 emoji 列表

前置条件：

- 已登录管理员账号
- `localStorage.workspace-sidebar-collapsed = '1'`

操作步骤：

1. 打开任意业务页面，例如 `/#/student`
2. 观察左侧侧栏折叠态导航

预期结果：

- 存在 `data-sidebar-rail`
- 存在 `data-rail-item="system"` 等独立图标按钮
- 折叠态不再渲染展开态主导航 `data-sidebar-main`

### 用例 2：折叠态进入系统管理后，展开侧栏仍定位当前模块

前置条件：

- 已登录管理员账号
- `localStorage.workspace-sidebar-collapsed = '1'`

操作步骤：

1. 打开 `/#/student`
2. 点击折叠态侧栏中的 `系统管理` emoji 按钮
3. 等待页面跳转到 `/#/system?sub=sys-users`
4. 点击顶部侧栏展开按钮

预期结果：

- 成功进入 `#page-system`
- `#sys-users.show` 可见
- 展开态存在 `data-sidebar-main`
- `data-nav-page="system"` 处于激活态
- 系统管理子功能列表已经展开
- `用户管理` 子功能可见
- 当前模块位于展开导航可视区域内

### 用例 3：系统管理回车提交机制不回归

操作步骤：

1. 进入 `/#/system?sub=sys-users`
2. 在用户筛选输入框输入 `admin`
3. 按 `Enter`

预期结果：

- 触发 `/system/users` 查询请求
- 不需要额外点击查询按钮

### 用例 4：Agent 监控改为聚合接口

检查内容：

1. `SystemView.vue` 的 `loadAgentMonitor()` 是否改为请求 `/agent/admin/dashboard`
2. 后端是否存在 `GET /agent/admin/dashboard`
3. 后端是否存在 `_build_dashboard_payload`

预期结果：

- 监控面板不再并发请求多组聚合接口
- dashboard 一次性返回：
  - `metrics`
  - `timeseries`
  - `intents`
  - `tools`
  - `providers`
  - `feedback_reasons`
  - `mcp_health`

### 用例 5：AgentTask 监控索引补齐

检查内容：

1. `model/AgentTask.py` 字段声明包含 `index=True`
2. `database.py` 初始化时对老库执行补索引

预期结果：

- `intent` 字段声明索引
- `status` 字段声明索引
- `create_time` 字段声明索引
- `init_db()` 中存在：
  - `idx_agent_task_create_time`
  - `idx_agent_task_status`
  - `idx_agent_task_intent`

## 五、自动化验证

### 1. 后端编译

命令：

```bash
python -m compileall agent_system model database.py
```

预期结果：

```text
编译通过
```

### 2. 前端静态回归

命令：

```bash
npm.cmd run test:ui-regression:static
```

预期结果：

```text
通过
```

### 3. Playwright UI 回归

命令：

```bash
npm.cmd run test:ui-regression:e2e
```

预期结果：

```text
通过
```

重点覆盖：

- 折叠态 rail 入口点击
- 进入系统管理默认子功能
- 展开侧栏后自动定位当前模块
- 输入框回车触发查询

## 六、本轮落地文件

- `frontend-vue/src/components/Sidebar.vue`
- `frontend-vue/src/assets/styles.css`
- `frontend-vue/src/views/SystemView.vue`
- `frontend-vue/scripts/ui-regression-check.mjs`
- `frontend-vue/scripts/ui-regression-playwright.mjs`
- `agent_system/api/agent_api.py`
- `model/AgentTask.py`
- `database.py`

## 七、结论

本轮修复完成后，侧栏体验和 Agent 监控都更稳定了：

- 用户在折叠态下可以用独立 emoji rail 快速进模块
- 再展开时不会丢失当前模块上下文
- Agent 监控不再重复扫同一批数据，老库也会在启动时自动补齐关键索引
