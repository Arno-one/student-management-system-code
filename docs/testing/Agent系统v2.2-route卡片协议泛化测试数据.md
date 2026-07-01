# Agent 系统 v2.2 - route 卡片协议泛化测试数据

## 一、测试目标

验证 v2.2 第三个功能“卡片协议泛化：route card”是否满足已确认边界：

- 后端 `cards` 协议统一补充 `card_version: 1`。
- 天气卡片继续兼容 `type=weather`。
- 通勤规划成功或部分成功时生成 `type=route` 卡片。
- `AgentView` 和 `FloatingAgent` 都能展示 `route` 卡片。
- 未知 card type 或未知 card version 被安全忽略，不影响 Markdown 回复。
- 字段缺失时前端组件不抛异常，用兜底文案展示。

## 二、涉及文件

| 文件 | 说明 |
|------|------|
| `agent_system/executor/agent_executor.py` | `_extract_cards()` 为 weather/route 卡片补充 `card_version=1`，并从 `commute_plan_tool` 提取 route card |
| `frontend-vue/src/components/RouteCard.vue` | 新增路线规划卡片组件 |
| `frontend-vue/src/views/AgentView.vue` | 主 Agent 接入 `RouteCard`，并过滤未知版本 |
| `frontend-vue/src/components/FloatingAgent.vue` | 悬浮 Agent 接入 `RouteCard` compact 模式，并过滤未知版本 |

## 三、后端卡片协议

### weather

```json
{
  "type": "weather",
  "card_version": 1,
  "data": {}
}
```

### route

```json
{
  "type": "route",
  "card_version": 1,
  "data": {
    "provider": "tencent_mcp",
    "status": "success | partial_success",
    "origin_text": "宝安",
    "destination_text": "龙岗",
    "routes": [],
    "weather_reminder": "天气辅助提醒"
  }
}
```

## 四、测试用例

### 1. 后端编译检查

命令：

```bash
python -m compileall agent_system DAO model main.py
```

结果：

```text
通过。agent_executor.py 编译成功。
```

### 2. 前端生产构建

命令：

```bash
cd frontend-vue
npm.cmd run build
```

结果：

```text
通过。新增 RouteCard.vue 后，Vite build 成功。
```

### 3. `_extract_cards()` 协议回归

测试输入：

- `weather_tool.success = true`
- `commute_plan_tool.success = true`
- `commute_plan_tool.status = partial_success`
- 通勤路线包含 1 条成功路线和 1 条失败路线

核心断言：

```text
cards 类型顺序 = ["weather", "route"]
所有 card.card_version = 1
route.data.status = partial_success
route.data.routes 数量 = 2
route.data.routes[0].mode = transit
```

结果：

```text
{'card_types': ['weather', 'route'], 'versions': [1, 1], 'route_count': 2}
```

### 4. 前端入口接入检查

主 Agent：

```text
AgentView.vue 已导入 RouteCard
AgentView.vue 已渲染 type=route 且 card_version=1 的卡片
AgentView.vue 通过 isCardVersionSupported() 过滤未知版本
```

悬浮 Agent：

```text
FloatingAgent.vue 已导入 RouteCard
FloatingAgent.vue 已渲染 type=route 且 card_version=1 的卡片
FloatingAgent.vue 使用 compact 模式展示 route 卡片
FloatingAgent.vue 通过 isCardVersionSupported() 过滤未知版本
```

## 五、验收结论

本功能已完成 `route` 卡片闭环：

- 后端 `cards` 协议升级到 `card_version: 1`。
- 通勤规划结构化结果可以生成 route card。
- 主 Agent 和悬浮 Agent 都能渲染路线卡片。
- `poi_list/map_location` 暂不实现组件，留到周边生活服务推荐功能。

## 六、后续建议

- 下一个功能“可视化回归测试”应把 route card 纳入主 Agent 和悬浮 Agent 的布局检查。
- 后续 P2 周边生活服务推荐再完整落地 `poi_list` 卡片。
