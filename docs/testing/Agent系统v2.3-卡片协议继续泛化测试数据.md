# Agent系统v2.3-卡片协议继续泛化测试数据

## 一、测试目标

验证 v2.3 当前迭代功能「卡片协议继续泛化」是否完成协议收口：

1. `weather`、`route`、`poi_list` 三类已实现卡片有字段级协议说明。
2. `map_location` 明确为预留卡片，本版本不实现、不渲染。
3. 前端继续坚持未知类型、未知版本安全忽略策略。
4. UI 回归脚本能守住卡片协议文档和前端渲染边界。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `docs/Agent卡片协议v1.md` | 补全 `weather`、`route`、`poi_list` 字段契约，新增 `map_location` 预留协议 |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增协议文档静态检查，并确认前端暂不渲染 `map_location` |

## 三、关键设计

### 当前可渲染卡片

```text
weather
route
poi_list
```

### 当前预留但不实现卡片

```text
map_location
```

边界：

```text
不新增 MapLocationCard.vue
AgentView 不渲染 map_location
FloatingAgent 不渲染 map_location
如果后端误返回 map_location，前端按未知类型安全忽略
```

### 通用兼容规则

```text
前端只渲染已知 type
前端只渲染 card_version=1 或未声明版本的历史卡片
未知 type、未知 card_version 必须安全忽略
字段缺失时组件做降级展示，不抛运行时异常
```

## 四、测试用例

### 用例 1：weather 协议完整性

预期文档包含：

```text
provider
fallback_reason
location_text
lat / lng
adcode
geocode
weather
实时天气
多日预报
逐时预报
```

结论：通过。

### 用例 2：route 协议完整性

预期文档包含：

```text
provider
status
origin_text / destination_text
origin / destination
travel_modes
departure_time_text
routes
weather_reminder
partial_success
```

结论：通过。

### 用例 3：poi_list 协议完整性

预期文档包含：

```text
query
center
radius_meters
provider
fallback_used
items
默认 2000 米
最多 10 条
compact 模式前 3 条
```

结论：通过。

### 用例 4：map_location 预留边界

预期：

```text
docs/Agent卡片协议v1.md 声明 map_location 为预留，不实现
AgentView.vue 不出现 MapLocationCard
FloatingAgent.vue 不出现 MapLocationCard
AgentView.vue 不过滤并渲染 c.type === 'map_location'
FloatingAgent.vue 不过滤并渲染 c.type === 'map_location'
```

结论：通过。

### 用例 5：未知卡片安全忽略

预期：

```text
AgentView 和 FloatingAgent 不直接 v-for 渲染 msg.cards
必须按 type + card_version 过滤后再交给具体卡片组件
```

结论：通过。

## 五、自动化验证

### 后端编译

命令：

```text
python -m compileall agent_system DAO model main.py
```

预期：

```text
后端编译通过
```

实际结果：

```text
通过
```

### 前端构建

命令：

```text
npm.cmd run build
```

预期：

```text
前端生产构建通过
```

实际结果：

```text
通过，Vite 生产构建完成
```

### UI 回归

命令：

```text
npm.cmd run test:ui-regression
```

新增静态护栏：

```text
PASS AgentView 暂不渲染 map_location 预留卡片
PASS FloatingAgent 暂不渲染 map_location 预留卡片
PASS 卡片协议文档声明当前可渲染类型
PASS 卡片协议文档声明 map_location 仅预留
PASS 卡片协议文档声明字段降级策略
PASS 卡片协议文档声明未知卡片安全忽略
PASS 卡片协议文档覆盖逐时天气展示边界
PASS 卡片协议文档覆盖 poi_list 默认半径
PASS 卡片协议文档覆盖 poi_list 展示数量
PASS 卡片协议文档约束本版本不实现 map_location 组件
```

实际结果：

```text
UI 回归检查通过：81/81
Playwright UI 回归通过：2/2
```

## 六、结论

本轮完成了 v2.3 卡片协议收口。当前系统只承诺渲染 `weather`、`route`、`poi_list`，并通过文档和自动化回归同时约束 `map_location` 暂不落地，避免后续实现时出现协议和前端能力不一致的问题。
