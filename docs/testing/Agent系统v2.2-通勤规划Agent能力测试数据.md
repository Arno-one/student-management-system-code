# Agent 系统 v2.2 - 通勤规划 Agent 能力测试数据

## 一、测试目标

验证 v2.2 第二个功能“腾讯地图 MCP 多能力扩展一期：通勤规划 Agent 能力”是否满足已确认边界：

- 用 LangGraph 中间件检查通勤规划输入完整性。
- 缺少起点、终点或出行方式时，直接返回澄清提示，不进入 planner 和 MCP。
- 澄清任务写入 `AgentTask.status = clarification`。
- 完整通勤请求进入 `commute_plan_tool`。
- 路线规划支持公交/地铁、驾车、步行三类方式。
- 天气只作为辅助建议，天气失败不影响路线结果。
- 部分出行方式失败时，任务状态支持 `partial_success`。

## 二、涉及文件

| 文件 | 说明 |
|------|------|
| `agent_system/middleware/middleware_graph.py` | 新增 LangGraph 中间件管线 |
| `agent_system/middleware/commute_parser.py` | 通勤请求解析，供中间件和工具复用 |
| `agent_system/middleware/commute_input_checker.py` | 通勤输入完整性检查节点 |
| `agent_system/service/agent_service.py` | 接入 clarification 短路流程和任务状态推导 |
| `agent_system/tools/commute_plan_tool.py` | 新增通勤规划业务工具，封装腾讯地图 MCP route tools |
| `agent_system/executor/agent_executor.py` | 注册 `commute_plan_tool`，保留 `partial_success` 状态 |
| `agent_system/prompts/intent_prompt.py` | 新增 `commute_plan` 意图说明 |
| `agent_system/prompts/planner_prompt.py` | 新增 `commute_plan_tool` 计划规则 |
| `agent_system/planner/task_planner.py` | 新增 `commute_plan` 兜底计划 |
| `agent_system/api/agent_api.py` | 监控指标兼容 `partial_success` 和 `clarification` |
| `model/AgentTask.py` | 任务状态注释补充新状态 |
| `requirements.txt` | 补充 `langgraph` 与 `mcp` 依赖声明 |

## 三、测试用例

### 1. 后端编译检查

命令：

```bash
python -m compileall agent_system DAO model main.py
```

结果：

```text
通过。新增 middleware、tool、planner、service 改动均无语法错误。
```

### 2. LangGraph 中间件输入完整性检查

测试输入：

```text
从学校到腾讯滨海大厦坐地铁怎么去
到腾讯滨海大厦坐地铁怎么去
从学校到腾讯滨海大厦怎么去
```

核心断言：

```text
完整输入 -> decision = pass
缺起点 -> decision = clarification
缺出行方式 -> decision = clarification
```

结果：

```text
middleware_cases_ok
```

### 3. clarification 服务层短路

测试方式：

- 使用内存 SQLite 创建 `TalkSession`、`TalkMessage`、`AgentTask`。
- 调用 `handle_agent_chat()`。
- 输入：`到腾讯滨海大厦坐地铁怎么去`。

核心断言：

```text
响应 code = 200
响应 intent = commute_plan
AgentTask.status = clarification
TalkMessage 数量 = 2（用户消息 + assistant 澄清消息）
```

结果：

```text
{'intent': 'commute_plan', 'task_status': 'clarification', 'messages': 2}
```

### 4. commute_plan_tool 部分成功与天气兜底

测试方式：

- 使用 mock 腾讯地图 MCP client。
- `geocoder` 成功。
- `directionTransit` 成功，返回 `distance=18000`、`duration=2700`。
- `directionWalking` 抛出异常。
- mock `WeatherTool.run()` 返回失败。

核心断言：

```text
工具 success = True
工具 status = partial_success
路线顺序 = transit, walking
transit duration_seconds = 2700
transit distance_meters = 18000
walking status = error
weather.success = False
```

结果：

```text
{'status': 'partial_success', 'route_statuses': ['success', 'error'], 'weather_success': False}
```

### 5. MCP SDK 依赖验证

问题现象：

```text
commute_plan_tool
通勤规划失败: 未安装 MCP Python SDK
```

修复方式：

- 在 `requirements.txt` 中补充 `mcp`。
- 当前开发环境执行 `python -m pip install mcp`。

验证命令：

```bash
python -c "import importlib.util; print('mcp', bool(importlib.util.find_spec('mcp'))); from agent_system.tools.mcp_client import tencent_map_mcp_client; sdk=tencent_map_mcp_client._load_sdk(); print([x.__name__ for x in sdk])"
```

结果：

```text
mcp True
['ClientSession', 'streamablehttp_client']
```

### 6. 深圳短区名解析回归

问题现象：

```text
用户输入：从宝安到龙岗坐地铁怎么去？
系统结果：终点被解析为“龙”，起点“宝安”无法解析经纬度。
```

根因：

- 通勤解析正则中 `\\?` 在 raw string 里形成了可空匹配，导致终点被非贪婪截断。
- 腾讯地图 geocoder 对“宝安 / 龙岗”这类短区名不够稳定，需要补全城市和行政区。

修复方式：

- 改为显式按“从 / 到”切分，再按“坐地铁、开车、怎么去”等尾部词切掉终点后缀。
- `commute_plan_tool` 对深圳常见区名做 geocoder 查询补全：
  - `宝安 -> 深圳市宝安区`
  - `龙岗 -> 深圳市龙岗区`

核心断言：

```text
parse_commute_request("从宝安到龙岗坐地铁怎么去？").origin_text == "宝安"
parse_commute_request("从宝安到龙岗坐地铁怎么去？").destination_text == "龙岗"
parse_commute_request("从宝安到龙岗坐地铁怎么去？").travel_modes == ["transit"]
_geocode("宝安") 实际查询地址为 "深圳市宝安区"
_geocode("龙岗") 实际查询地址为 "深圳市龙岗区"
```

结果：

```text
解析回归通过。
短区名 geocoder 补全回归通过。
```

### 7. 跨城市行政区补全回归

目标：

支持用户明确城市时的短行政区补全，同时避免在缺少城市上下文时盲猜非默认城市。

测试输入：

```text
从广州市天河到番禺坐地铁怎么去
从天河到番禺坐地铁怎么去
从宝安到龙岗坐地铁怎么去
```

核心断言：

```text
“从广州市天河到番禺坐地铁怎么去” -> pass，city_context = 广州市
“从天河到番禺坐地铁怎么去” -> clarification，要求补充城市信息
“从宝安到龙岗坐地铁怎么去” -> pass，保留深圳默认补全
normalize_geocode_address("天河", "广州市") == "广州市天河区"
normalize_geocode_address("番禺", "广州市") == "广州市番禺区"
normalize_geocode_address("宝安") == "深圳市宝安区"
```

结果：

```text
city_context_cases_ok
middleware_city_context_ok
```

### 8. 地理编码 REST 兜底回归

问题现象：
```text
用户输入：从宝安到龙岗坐地铁怎么去
系统结果：宝安（已按 深圳市宝安区 查询）未解析到经纬度
```

根因：
- 腾讯地图路线规划工具的 `from/to` 参数需要经纬度字符串，不能直接传“宝安/龙岗”这类自然语言地点。
- 当前链路原本是 `geocoder -> directionTransit`，失败点在前置 geocoder 未返回经纬度，导致路线工具没有机会执行。

修复方式：
- `_geocode()` 保持 MCP geocoder 优先。
- 当 MCP geocoder 未返回经纬度或调用异常时，自动回退项目已有的腾讯地图 REST `address_to_location(policy=1)`。
- REST 兜底成功后，继续把 `lat,lng` 组装成路线工具需要的 `from/to` 坐标字符串。

核心断言：
```text
origin.query_address == "深圳市宝安区"
destination.query_address == "深圳市龙岗区"
origin.geocode_provider == "tencent_rest_fallback"
destination.geocode_provider == "tencent_rest_fallback"
routes[0].success == True
```

验证方式：
- 本轮使用临时回归脚本模拟 “MCP geocoder 无经纬度 + REST 兜底成功” 场景，执行后已删除临时脚本。
- 可复跑语法检查命令：
```bash
python -m compileall agent_system DAO model main.py
```

结果：
```text
PASS commute geocode REST fallback
compileall passed
```

## 四、验收结论

本功能已完成通勤规划 Agent 后端能力闭环：

- 通勤类输入不完整时不会误调 MCP，会保存为 `clarification`。
- 完整通勤请求会进入 `commute_plan_tool`。
- MCP route tools 被后端业务工具封装，Agent 不直接裸调 MCP。
- 地址文本会先经 MCP geocoder 转坐标；MCP 未返回坐标时，会使用腾讯地图 REST 宽松地理编码兜底。
- 天气辅助失败不会阻断路线规划。
- 部分路线失败可以通过 `partial_success` 表达，监控统计不再简单归为失败。

## 五、后续建议

- 下一个功能“卡片协议泛化”中，建议把 `commute_plan_tool` 的结构化 routes 输出接到 `route` 卡片。
- `poi_list/map_location` 仍按前面决策只保留协议预留，等周边生活服务推荐功能再完整落地。
