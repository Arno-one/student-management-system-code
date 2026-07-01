# Agent系统v2.1-天气卡片组件测试数据

## 一、测试目标

验证 v2.1 P2 功能「天气卡片 Vue 组件」是否满足以下要求：

1. Agent 回复仍保留 Markdown 自然语言总结。
2. 天气结构化数据通过 `cards` 单独下发，不从 Markdown 文本中反向解析。
3. SSE 当前消息、同步接口响应、历史消息 metadata 都能携带 `cards`。
4. Agent 主页面和全局悬浮 Agent 都能展示天气卡片。
5. 前端组件不使用 `v-html` 拼天气卡片，避免 HTML 字符串维护和安全问题。
6. MCP / REST 两种天气数据来源都能被卡片兼容展示。

## 二、涉及文件

| 文件 | 说明 |
| --- | --- |
| `agent_system/schemas/agent_response.py` | `AgentChatResponse` 新增 `cards` 字段 |
| `agent_system/executor/agent_executor.py` | 新增 `_extract_cards()`，从 `weather_tool` 结果生成天气卡片数据 |
| `agent_system/service/agent_service.py` | SSE `done` 事件和历史消息 metadata 持久化 `cards` |
| `frontend-vue/src/components/WeatherCard.vue` | 新增天气卡片组件 |
| `frontend-vue/src/views/AgentView.vue` | Agent 主页面渲染天气卡片 |
| `frontend-vue/src/components/FloatingAgent.vue` | 全局悬浮 Agent 渲染紧凑天气卡片 |

## 三、cards 协议

SSE `done` 事件新增字段：

```json
{
  "cards": [
    {
      "type": "weather",
      "data": {
        "provider": "tencent_rest_fallback",
        "fallback_reason": "mock fallback",
        "location_text": "Shenzhen",
        "lat": 22.5431,
        "lng": 114.0579,
        "adcode": "440300",
        "geocode": null,
        "weather": {
          "实时天气": {},
          "多日预报": {}
        }
      }
    }
  ]
}
```

说明：

- `reply` 继续是 Markdown 文本。
- `cards` 是结构化卡片，不依赖 LLM 输出格式。
- 历史消息中 `metadata.cards` 与 SSE `done.cards` 保持同构。

## 四、测试数据

### 用例 1：后端能从 weather_tool 结果抽取天气卡片

测试脚本：

```python
from agent_system.executor.agent_executor import _extract_cards

now_key = "\u5b9e\u65f6\u5929\u6c14"
future_key = "\u591a\u65e5\u9884\u62a5"
context = {
    "weather_tool": {
        "success": True,
        "provider": "tencent_rest_fallback",
        "fallback_reason": "mock fallback",
        "location_text": "Shenzhen",
        "lat": 22.5431,
        "lng": 114.0579,
        "adcode": "440300",
        "weather": {
            now_key: {
                "status": 0,
                "result": {
                    "realtime": [
                        {
                            "city": "Shenzhen",
                            "district": "Nanshan",
                            "infos": {
                                "weather": "cloudy",
                                "temperature": 28,
                                "humidity": 66
                            }
                        }
                    ]
                }
            },
            future_key: {
                "status": 0,
                "result": {
                    "forecast": [
                        {
                            "infos": [
                                {
                                    "week": "today",
                                    "date": "2026-06-27",
                                    "day": {
                                        "weather": "cloudy",
                                        "temperature": 30
                                    },
                                    "night": {
                                        "weather": "overcast",
                                        "temperature": 25
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
}

cards = _extract_cards(context)
assert cards and cards[0]["type"] == "weather"
assert cards[0]["data"]["provider"] == "tencent_rest_fallback"
assert cards[0]["data"]["weather"][now_key]["result"]["realtime"][0]["infos"]["temperature"] == 28
assert cards[0]["data"]["weather"][future_key]["result"]["forecast"][0]["infos"][0]["day"]["temperature"] == 30
assert _extract_cards({"weather_tool": {"success": False}}) is None
```

实际结果：

```text
[{"type": "weather", "data": {"provider": "tencent_rest_fallback", ...}}]
```

结论：通过。

### 用例 2：前端构建验证

命令：

```bash
npm.cmd run build
```

结果：

```text
✓ 64 modules transformed.
✓ built in 7.45s
```

结论：通过。`WeatherCard.vue`、`AgentView.vue`、`FloatingAgent.vue` 均可正常编译。

### 用例 3：后端编译验证

命令：

```bash
python -m compileall agent_system DAO model main.py
```

结果：

```text
Compiling 'agent_system\\schemas\\agent_response.py'...
Compiling 'agent_system\\service\\agent_service.py'...
```

结论：通过。

## 五、展示规则

### Agent 主页面

展示顺序：

1. Markdown 自然语言回复。
2. 天气卡片。
3. 工具调用摘要。
4. HITL / 反馈 / 来源等已有模块。

### 全局悬浮 Agent

展示顺序同主页面，但天气卡片使用 `compact` 模式：

- 最多展示 3 天预报。
- 保持卡片宽度跟随聊天气泡。
- 不影响原反馈和 HITL 操作。

## 六、边界说明

1. 如果没有 `cards`，前端完全走旧 Markdown 展示。
2. 如果 `cards` 中没有 `type=weather`，当前版本忽略该卡片类型。
3. 如果天气字段缺失，组件展示可用字段，不抛前端异常。
4. 组件不从 LLM 文本中解析天气 JSON，避免 LLM 改措辞导致卡片失效。

## 七、浅色主题背景污染回归测试

### 问题现象

天气卡片初版样式中使用了 scoped CSS 下的 `:global(.app-layout.theme-light) .agent-weather-card` 选择器，构建后会生成真正的全局 `.app-layout.theme-light` 样式，导致浅色主题页面大背景被天气卡片样式覆盖。

同时天气卡片存在独立浅色主题覆盖逻辑，没有完全跟随项目已有主题变量，切换浅色 / 深色主题时卡片颜色同步不稳定。

### 修复方式

`WeatherCard.vue` 已移除天气卡片里的全局主题选择器，卡片颜色统一改为读取项目主题变量：

- `--panel-solid`
- `--panel-2`
- `--panel-3`
- `--line`
- `--line-strong`
- `--text`
- `--text-soft`
- `--text-dim`
- `--text-muted`
- `--gold`
- `--gold-bg`
- `--blue-2`
- `--shadow-sm`

这样主题仍由 `App.vue` 根节点上的 `.app-layout.theme-light` / `.app-layout.theme-dark` 控制，天气卡片只消费变量，不再反向污染页面背景。

### 验证命令

```bash
npm.cmd run build
python -m compileall agent_system DAO model main.py
```

构建产物 CSS 污染检查：

```powershell
$css = Get-ChildItem -Path frontend-vue/dist/assets -Filter index-*.css | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$content = Get-Content -Path $css.FullName -Raw
$bad = [regex]::Matches($content, "\.app-layout\.theme-light\{border-color:[^}]+background:[^}]+\}").Count
$weather = [regex]::Matches($content, "agent-weather-card").Count
"bad_theme_pollution=$bad"
"weather_selector_count=$weather"
```

### 预期结果

```text
bad_theme_pollution=0
weather_selector_count=1
```

结论：通过。浅色主题页面背景不再被天气卡片覆盖，天气卡片通过主题变量跟随浅色 / 深色主题切换。

## 八、后续建议

1. 后续可将 WorkView 的天气查询结果也切换为复用 `WeatherCard.vue`。
2. 后续地图路线、周边地点等 MCP 能力也可复用同一套 `cards` 协议，例如 `type=route`、`type=poi_list`。
3. 如果天气卡片需要更丰富展示，可在后端 `_extract_cards()` 中增加空气质量、预警、小时级预报等结构化字段。
