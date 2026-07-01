# Agent系统v2.1-腾讯地图MCP能力底座测试数据

## 一、测试目标

验证 v2.1 第四个功能「腾讯地图 MCP 能力底座 + 天气首个接入」是否满足以下要求：

1. MCP 作为可选增强能力，不影响后端应用启动。
2. 未配置 Key、未安装 MCP SDK、MCP 初始化失败时，天气工具自动回退原腾讯地图 REST 链路。
3. MCP 可用时，天气工具优先使用 MCP 返回结果。
4. 管理员可通过健康检查接口查看腾讯地图 MCP 当前状态。
5. 不改变 planner/executor 对 WeatherTool 的原有调用方式。

## 二、涉及文件

| 文件 | 说明 |
| --- | --- |
| `agent_system/tools/mcp_client.py` | 新增腾讯地图 MCP 通用客户端底座 |
| `agent_system/tools/weather_tool.py` | 天气工具优先 MCP，失败后回退 REST |
| `agent_system/api/agent_api.py` | 新增管理员 MCP 健康检查接口 |
| `main.py` | 应用启动/关闭时初始化和释放 MCP 客户端 |

## 三、接口与返回字段

### 1. 管理员健康检查接口

```http
GET /agent/admin/mcp/tencent-map/health
Authorization: Bearer <admin_token>
```

预期返回字段：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "provider": "tencent_map_mcp",
    "enabled": true,
    "connected": false,
    "endpoint": "https://mcp.map.qq.com/mcp?key=***&format=0",
    "tool_count": 0,
    "tools": [],
    "last_error": "未安装 MCP Python SDK",
    "last_success_at": null
  },
  "total": null
}
```

说明：

- `enabled=false`：通常表示未配置 `TENCENT_MAP_KEY`。
- `enabled=true` 且 `connected=false`：通常表示已配置 Key，但 SDK 未安装或 MCP 远端初始化失败。
- `connected=true`：表示 MCP 初始化成功，天气工具会优先尝试 MCP。

## 四、测试数据

### 用例 1：未安装 MCP SDK 时启动不抛异常

测试脚本：

```python
import asyncio
from agent_system.tools.mcp_client import TencentMapMcpClient

async def main():
    client = TencentMapMcpClient(api_key="fake-key")
    await client.startup()
    health = client.health()
    assert health["connected"] is False
    assert health["enabled"] is True
    assert health["last_error"]

asyncio.run(main())
```

实际结果：

```text
connected= False
enabled= True
last_error= 未安装 MCP Python SDK
```

结论：通过。MCP SDK 不存在时只记录错误，不阻塞系统。

### 用例 2：MCP 不可用时 WeatherTool 回退 REST

测试桩数据：

```python
weather_module.tencent_map_mcp_client.connected = False
weather_module.tencent_map_mcp_client.last_error = "mock mcp unavailable"

weather_module.address_to_location = lambda address, policy=1: {
    "success": True,
    "lat": 22.5431,
    "lng": 114.0579,
    "adcode": "440300",
}

def fake_query_weather(location=None, adcode=None, weather_type="now", added_fields=None, get_md=None):
    return {"status": 0, "type": weather_type, "result": {"temperature": "28"}}
```

实际返回：

```json
{
  "success": true,
  "provider": "tencent_rest_fallback",
  "fallback_reason": "mock mcp unavailable",
  "location_text": "Shenzhen",
  "lat": 22.5431,
  "lng": 114.0579,
  "adcode": "440300",
  "weather": {
    "实时天气": {
      "status": 0,
      "type": "now",
      "result": {
        "temperature": "28"
      }
    },
    "多日预报": {
      "status": 0,
      "type": "future",
      "result": {
        "temperature": "28"
      }
    }
  },
  "error": null
}
```

结论：通过。MCP 不可用时 REST 兜底成功，并保留失败原因。

### 用例 3：MCP 可用时 WeatherTool 优先使用 MCP

测试桩数据：

```python
client.connected = True
client.find_tool_name = lambda keywords: "weather_forecast"
client.call_tool_sync = lambda tool_name, arguments: {
    "content": [
        {
            "type": "text",
            "text": "{\"adcode\":\"440300\",\"weather\":{\"now\":{\"temp\":\"28\"}},\"lat\":22.5431,\"lng\":114.0579}"
        }
    ]
}
```

实际返回：

```json
{
  "success": true,
  "provider": "tencent_mcp",
  "mcp_tool_name": "weather_forecast",
  "location_text": "Shenzhen",
  "lat": 22.5431,
  "lng": 114.0579,
  "adcode": "440300",
  "weather": {
    "adcode": "440300",
    "weather": {
      "now": {
        "temp": "28"
      }
    },
    "lat": 22.5431,
    "lng": 114.0579
  },
  "error": null
}
```

结论：通过。MCP 成功时不会调用 REST 兜底链路。

> 修正说明：真实腾讯地图 MCP 的天气工具名是 `weather`，且不接收自然语言地点；必须先调用 `geocoder(address)` 拿到 `adcode` 或 `lat,lng`，再调用 `weather(adcode/location, type)`。下面用例 3.1 记录修正后的真实链路。

### 用例 3.1：真实 MCP 天气链路为 geocoder → weather

测试桩数据：

```python
client.connected = True
client.tools = [{"name": "geocoder"}, {"name": "weather"}]

def fake_call_tool_sync(tool_name, arguments):
    if tool_name == "geocoder":
        return {
            "content": [{
                "type": "text",
                "text": "{\"status\":0,\"result\":{\"location\":{\"lat\":22.5431,\"lng\":114.0579},\"ad_info\":{\"adcode\":\"440300\"}}}"
            }]
        }
    if tool_name == "weather":
        return {"content": [{"type": "text", "text": "{\"status\":0,\"type\":\"%s\"}" % arguments["type"]}]}
```

实际返回：

```json
{
  "success": true,
  "provider": "tencent_mcp",
  "mcp_tool_names": [
    "geocoder",
    "weather"
  ],
  "location_text": "Shenzhen",
  "lat": 22.5431,
  "lng": 114.0579,
  "adcode": "440300",
  "weather": {
    "实时天气": {
      "status": 0,
      "type": "now"
    },
    "多日预报": {
      "status": 0,
      "type": "future"
    }
  },
  "error": null
}
```

结论：通过。天气 MCP 首先完成地址解析，再分别查询实时天气和多日预报。

### 用例 3.2：真实 MCP tools/list 返回清单

已通过临时 MCP SDK 调用 `list_tools()`，腾讯地图 MCP `1.2.0` 返回 15 个 tool：

```text
geocoder
placeSuggestion
placeSearchNearby
directionDriving
placeAlongby
placeDetail
matrix
reverseGeocoder
ipLocation
weather
directionWalking
directionBicycling
directionTransit
futureDrivingDirection
waypointOrder
```

结论：通过。后续地图能力扩展可基于这些 tool 按需封装。

### 用例 4：健康检查接口返回结构

测试脚本：

```python
from agent_system.api.agent_api import admin_tencent_map_mcp_health

response = admin_tencent_map_mcp_health({})
assert response["code"] == 200
assert response["data"]["provider"] == "tencent_map_mcp"
assert "connected" in response["data"]
assert "last_error" in response["data"]
```

实际返回：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "provider": "tencent_map_mcp",
    "enabled": true,
    "connected": false,
    "endpoint": "https://mcp.map.qq.com/mcp?key=***&format=0",
    "tool_count": 0,
    "tools": [],
    "last_error": null,
    "last_success_at": null
  },
  "total": null
}
```

结论：通过。健康检查接口结构完整，后续可接入监控面板展示。

## 五、回归命令

```bash
python -m compileall agent_system DAO model main.py
```

结果：

```text
Compiling 'agent_system\\api\\agent_api.py'...
Compiling 'agent_system\\tools\\mcp_client.py'...
Compiling 'agent_system\\tools\\weather_tool.py'...
Compiling 'main.py'...
```

结论：通过。

## 六、风险与后续建议

1. 当前环境未安装 MCP Python SDK，因此真实腾讯地图 MCP 联调需要在安装 SDK 后补测。
2. 腾讯地图 MCP 工具名和参数由远端 `list_tools()` 决定，当前实现按工具名称/描述自动发现天气工具；如果远端天气工具参数严格要求单一字段，后续可根据真实 `inputSchema` 做参数适配。
3. 建议后续把健康检查结果接入 `Agent监控` 页面，便于管理员直接看到 MCP 增强链路是否在线。
