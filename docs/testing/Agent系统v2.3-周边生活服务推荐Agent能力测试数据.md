# Agent系统v2.3-周边生活服务推荐Agent能力测试数据

## 一、测试目标

验证 v2.3 第一个功能「周边生活服务推荐 Agent 能力」是否满足以下要求：

1. 通过 LangGraph 中间件识别周边服务意图。
2. 缺地点或服务类型时直接返回 `clarification`，不误调地图工具。
3. 信息完整时调用 `nearby_service_tool` 查询腾讯地图 POI。
4. 返回 `poi_list` 卡片，主 Agent 和悬浮 Agent 均可渲染。
5. `poi_list` 支持版本过滤、字段缺失降级、compact 前 3 条展示。
6. 工具结果提前埋入 provider、fallback、result_count、error_code 等轻量监控字段。

## 二、已实现范围

| 模块 | 说明 |
| --- | --- |
| `agent_system/middleware/nearby_parser.py` | 解析周边服务地点、关键词、半径、数量 |
| `agent_system/middleware/nearby_input_checker.py` | 缺地点/类别时返回澄清 |
| `agent_system/tools/nearby_service_tool.py` | 封装 geocoder + placeSearchNearby + REST fallback |
| `agent_system/middleware/middleware_graph.py` | 接入 nearby 节点，优先于 commute |
| `agent_system/executor/agent_executor.py` | 注册工具、提取 `poi_list` 卡片和 `tool_monitoring` |
| `frontend-vue/src/components/PoiListCard.vue` | 渲染 POI 列表卡片 |
| `AgentView.vue` / `FloatingAgent.vue` | 接入 `poi_list` 卡片 |
| `docs/Agent卡片协议v1.md` | 沉淀 weather / route / poi_list 协议 |

## 三、关键规则

```text
默认半径：2000 米
半径上限：5000 米
返回数量：10 条
排序：腾讯地图默认综合排序优先，前端按距离从近到远兜底
```

状态：

```text
clarification：缺地点或类别
success：查到 POI
empty：地点解析成功但无结果
error：地理编码失败或工具异常
```

## 四、解析测试

### 用例 1：完整周边餐饮请求

输入：

```text
腾讯滨海大厦附近有什么吃饭的地方
```

预期：

```text
decision=pass
intent=nearby_service
center_text=腾讯滨海大厦
keyword=餐饮
radius_meters=2000
limit=10
```

结论：通过。

### 用例 2：短行政区 + 医疗服务

输入：

```text
宝安附近有没有医院
```

预期：

```text
decision=pass
center_text=宝安
keyword=医疗
```

说明：后续地理编码阶段会沿用深圳默认短区名补全能力。

结论：通过。

### 用例 3：学校附近不盲猜

输入：

```text
学校附近有哪些医院
```

实际结果：

```text
decision=clarification
intent=nearby_service
missing_fields=["center"]
```

预期文案：

```text
你想查哪个地点附近的医疗？可以补充学校、公司、小区或具体地标。
```

结论：通过。

### 用例 4：只说附近有什么

输入：

```text
附近有什么
```

实际结果：

```text
decision=clarification
intent=nearby_service
missing_fields=["center", "query"]
```

结论：通过。

### 用例 5：通勤句不被 nearby 抢走

输入：

```text
从宝安到龙岗坐地铁怎么去
```

实际结果：

```text
decision=pass
nearby_intent=None
```

结论：通过。该请求继续交给通勤规划链路。

## 五、工具层测试

### 用例 6：mock 腾讯地图 MCP 查询成功

测试桩：

```python
c.connected = True
c.tools = [{"name": "geocoder"}, {"name": "placeSearchNearby"}]
```

`geocoder` 返回：

```json
{
  "status": 0,
  "result": {
    "location": {"lat": 22.53, "lng": 113.93},
    "ad_info": {"adcode": "440305"},
    "address": "深圳市南山区海天二路"
  }
}
```

`placeSearchNearby` 返回：

```json
{
  "status": 0,
  "data": [
    {
      "id": "p1",
      "title": "南山餐厅一号",
      "category": "餐饮",
      "address": "深圳市南山区海天一路1号",
      "location": {"lat": 22.531, "lng": 113.931},
      "_distance": 180
    }
  ]
}
```

实际结果：

```text
status=success
provider=tencent_mcp
result_count=1
items[0].name=南山餐厅一号
```

结论：通过。

## 六、前端与回归测试

### 构建验证

命令：

```text
npm.cmd run build
```

结果：

```text
✓ built
```

结论：通过。

### 静态 UI 回归

命令：

```text
npm.cmd run test:ui-regression:static
```

结果：

```text
UI 回归检查通过：53/53
```

覆盖点：

1. `PoiListCard` 不覆盖全局主题类。
2. `PoiListCard` 使用主题变量。
3. `PoiListCard` 字段缺失时安全降级。
4. AgentView / FloatingAgent 均过滤 `poi_list` 的 `card_version`。
5. AgentView / FloatingAgent 均支持“去这里”填充通勤输入。

结论：通过。

### Playwright Edge 回归

命令：

```text
npm.cmd run test:ui-regression:e2e
```

结果：

```text
PASS Playwright 主 Agent 浅色主题卡片回归
PASS Playwright 悬浮 Agent 移动端卡片回归
Playwright UI 回归通过：2/2
```

覆盖点：

1. 主 Agent 能渲染 `weather`、`route`、`poi_list`。
2. 未知 `type` 和未知 `card_version` 不渲染。
3. `poi_list` 的“去这里”可填充通勤规划输入。
4. 悬浮 Agent compact 模式只显示前 3 条 POI。
5. 卡片不横向溢出移动端悬浮面板。

结论：通过。

## 七、后端编译验证

命令：

```text
python -m compileall agent_system DAO model main.py
```

结果：

```text
后端编译通过
```

结论：通过。

## 八、暂未执行项

真实腾讯地图 MCP / REST 外网调用未在本次自动化中强断言结果内容，原因是地图结果会随时间和服务状态变化。当前采用：

1. mock 工具层验证结构和字段。
2. 前端 mock card 验证稳定 UI 回归。
3. 保留真实调用场景用于人工联调：

```text
腾讯滨海大厦附近有什么吃饭的地方
深圳市宝安区附近有没有医院
广州市天河区附近有没有打印店
火星基地附近有没有打印店
```

## 九、结论

v2.3 第一个功能「周边生活服务推荐 Agent 能力」已完成完整闭环：

```text
用户输入
→ nearby LangGraph 中间件
→ nearby_service_tool
→ geocoder + POI 搜索
→ poi_list card
→ AgentView / FloatingAgent 渲染
→ UI 回归护栏
```

本功能满足“一次一个功能、完成后产出测试文档、用户确认后再进入下一项”的迭代要求。
