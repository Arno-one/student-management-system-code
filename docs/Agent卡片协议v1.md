# Agent 卡片协议 v1

> 本文档定义 Agent 结构化卡片的统一协议，供后端 tool、executor、前端组件和 UI 回归脚本共同遵守。

## 一、协议边界

所有卡片都通过 Agent SSE 的 `done.cards` 返回；如果后续有同步接口返回卡片，也必须复用同一结构。

```json
{
  "type": "weather",
  "card_version": 1,
  "data": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `type` | string | 是 | 卡片类型。当前可渲染类型为 `weather`、`image`、`route`、`poi_list` |
| `card_version` | number | 建议必填 | 卡片协议版本，当前统一为 `1` |
| `data` | object | 是 | 卡片业务数据，由对应前端组件消费 |

兼容规则：

1. 前端只渲染已知 `type`。
2. 前端只渲染 `card_version=1` 或未声明版本的历史卡片。
3. 未知 `type`、未知 `card_version` 必须安全忽略。
4. 字段缺失时组件做降级展示，不抛运行时异常。
5. 后端新增卡片类型前，必须先补本文档、前端组件和 UI 回归护栏。

## 二、当前卡片清单

| 类型 | 当前状态 | 后端来源 | 前端组件 |
| --- | --- | --- | --- |
| `weather` | 已实现 | `weather_tool`、`WorkView` 天气查询适配 | `frontend-vue/src/components/WeatherCard.vue` |
| `image` | 已实现 | `image_tool` | `frontend-vue/src/components/ImageCard.vue` |
| `route` | 已实现 | `commute_plan_tool` | `frontend-vue/src/components/RouteCard.vue` |
| `poi_list` | 已实现 | `nearby_service_tool` | `frontend-vue/src/components/PoiListCard.vue` |
| `map_location` | 预留，不实现 | 暂无 | 暂无 |

> 当前 v2.3 继续保留 `map_location` 作为预留协议，不在本轮前端渲染范围内。

## 三、weather 卡片

当前组件：`frontend-vue/src/components/WeatherCard.vue`

### 3.1 数据结构

```json
{
  "type": "weather",
  "card_version": 1,
  "data": {
    "provider": "tencent_mcp",
    "fallback_reason": "",
    "location_text": "深圳市",
    "lat": 22.5431,
    "lng": 114.0579,
    "adcode": "440300",
    "geocode": {},
    "weather": {
      "实时天气": {
        "result": {
          "realtime": []
        }
      },
      "多日预报": {
        "result": {
          "forecast": []
        }
      },
      "逐时预报": {
        "result": {
          "forecast_hours": []
        }
      }
    }
  }
}
```

### 3.2 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | string | 数据来源，如 `tencent_mcp`、`tencent_rest_fallback`、`work_weather` |
| `fallback_reason` | string | 使用兜底 provider 的原因，没有则为空 |
| `location_text` | string | 用户可读地点名 |
| `lat` / `lng` | number | 经纬度，可为空 |
| `adcode` | string | 行政区划编码，可为空 |
| `geocode` | object | 地理编码原始结构，可为空对象 |
| `weather` | object | 天气数据块，按中文标签区分实时、多日、逐时 |

### 3.3 展示规则

1. `实时天气` 展示城市、天气、温度、风向、风力、湿度、气压。
2. `多日预报` 普通模式最多展示 5 天，compact 模式最多展示 3 天。
3. `逐时预报` 普通模式最多展示 8 条，compact 模式最多展示 4 条。
4. `weather` 为空时不强制渲染完整卡片。
5. 组件只消费结构化数据，不解析 Markdown。

## 四、image 卡片

当前组件：`frontend-vue/src/components/ImageCard.vue`

### 4.1 数据结构

```json
{
  "type": "image",
  "card_version": 1,
  "data": {
    "provider": "qwen_image",
    "model": "qwen-image-2.0-pro",
    "prompt": "一个在图书馆认真学习的大学生，阳光从窗边照进来",
    "image_url": "https://example.com/generated-image.png"
  }
}
```

### 4.2 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | string | 图片生成来源，当前为 `qwen_image` |
| `model` | string | 模型名，当前为 `qwen-image-2.0-pro` |
| `prompt` | string | 本次文生图使用的提示词 |
| `image_url` | string | 生成后的图片链接 |

### 4.3 展示规则

1. 第一版只支持单图卡片，不做多图轮播。
2. 卡片必须显示图片预览、提示词、来源信息。
3. 卡片内置 `重新生成`、`复制提示词`、`复制图片链接` 三个操作。
4. `重新生成` 只负责把原提示词回填为新的用户消息，由现有 Agent 流程重新命中文生图意图。
5. `image_url` 为空时不渲染空卡片。
6. 样式必须只使用主题变量，跟随当前浅色/深色主题。

## 五、route 卡片

当前组件：`frontend-vue/src/components/RouteCard.vue`

### 5.1 数据结构

```json
{
  "type": "route",
  "card_version": 1,
  "data": {
    "provider": "tencent_mcp",
    "status": "success",
    "origin_text": "宝安中心",
    "destination_text": "龙岗中心城",
    "origin": {
      "name": "宝安中心",
      "lat": 22.554,
      "lng": 113.883,
      "adcode": "440306"
    },
    "destination": {
      "name": "龙岗中心城",
      "lat": 22.721,
      "lng": 114.246,
      "adcode": "440307"
    },
    "travel_modes": ["transit"],
    "departure_time_text": "当前时间",
    "routes": [
      {
        "mode": "transit",
        "label": "公交/地铁",
        "success": true,
        "distance_meters": 55000,
        "duration_seconds": 5400,
        "distance_text": "55.0 公里",
        "duration_text": "1 小时 30 分钟",
        "summary": "公交/地铁预计耗时 1 小时 30 分钟，距离 55.0 公里。"
      }
    ],
    "weather_reminder": "天气建议暂不可用，路线规划结果不受影响。"
  }
}
```

### 5.2 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | string | 路线 provider |
| `status` | string | `success`、`partial_success` 等 |
| `origin_text` / `destination_text` | string | 用户输入或解析后的起终点文本 |
| `origin` / `destination` | object | 起终点结构化位置，可包含 `name`、`lat`、`lng`、`adcode` |
| `travel_modes` | array | 本次请求覆盖的出行方式 |
| `departure_time_text` | string | 出发时间描述 |
| `routes` | array | 路线列表，至少包含一条可展示路线时才渲染 |
| `weather_reminder` | string | 天气辅助提醒，失败时不影响路线卡片 |

### 5.3 展示规则

1. `status=partial_success` 表示部分出行方式失败，前端仍展示可用路线。
2. `routes` 中单条失败时允许保留 `error` 字段。
3. compact 模式最多展示 2 条路线。
4. 没有可用 `routes` 时不渲染空卡片。

## 六、poi_list 卡片

当前组件：`frontend-vue/src/components/PoiListCard.vue`

### 6.1 数据结构

```json
{
  "type": "poi_list",
  "card_version": 1,
  "data": {
    "query": "餐饮",
    "center": {
      "name": "宝安中心",
      "address": "深圳市宝安区宝安中心",
      "lat": 22.554,
      "lng": 113.883
    },
    "radius_meters": 2000,
    "provider": "tencent_mcp",
    "fallback_used": false,
    "items": [
      {
        "id": "poi-1",
        "name": "示例餐厅",
        "category": "餐饮",
        "address": "深圳市宝安区示例路 1 号",
        "distance_meters": 180,
        "lat": 22.555,
        "lng": 113.884,
        "source": "tencent_map",
        "extra": {
          "tel": "",
          "rating": null,
          "business_hours": ""
        }
      }
    ]
  }
}
```

### 6.2 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `query` | string | 用户查询的服务类别或关键词 |
| `center` | object | 查询中心点，包含 `name`、`address`、`lat`、`lng` |
| `radius_meters` | number | 查询半径，v2.3 默认 2000 米 |
| `provider` | string | 数据来源 |
| `fallback_used` | boolean | 是否使用兜底链路 |
| `items` | array | POI 列表，最多 10 条 |

`items[]` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | POI 标识，没有稳定 ID 时允许使用名称加序号兜底 |
| `name` | string | 地点名称 |
| `category` | string | 地点类别 |
| `address` | string | 地址 |
| `distance_meters` | number | 距离中心点的米数 |
| `lat` / `lng` | number | 地点经纬度，可为空 |
| `source` | string | 原始数据源 |
| `extra` | object | 电话、评分、营业时间等预留字段 |

### 6.3 展示规则

1. 单个 Agent 最多展示 10 条。
2. 悬浮 Agent compact 模式只展示前 3 条。
3. 前端按 `distance_meters` 从近到远兜底排序。
4. 第一版只展示名称、类别、距离、地址、查询中心、半径、数据来源。
5. `tel`、`rating`、`business_hours` 只放在 `extra` 预留，前端暂不展示。
6. 支持复制地址。
7. 支持“去这里”快捷填入通勤规划输入。
8. 不自动发起通勤规划，因为当前没有可靠的默认起点。
9. 不做地图预览、地点详情弹窗、电话拨打、评分/营业时间展示和收藏。

## 七、map_location 预留协议

`map_location` 是后续单地点详情卡片的预留方向，本版本不实现组件、不由 executor 输出、不在前端渲染。

如果后续启用，建议字段如下：

```json
{
  "type": "map_location",
  "card_version": 1,
  "data": {
    "id": "poi-1",
    "name": "示例地点",
    "category": "餐饮",
    "address": "深圳市宝安区示例路 1 号",
    "lat": 22.555,
    "lng": 113.884,
    "adcode": "440306",
    "provider": "tencent_mcp",
    "source": "tencent_map",
    "extra": {}
  }
}
```

当前验收边界：

1. 不新增 `MapLocationCard.vue`。
2. `AgentView.vue` 和 `FloatingAgent.vue` 不渲染 `map_location`。
3. 如果后端误返回 `map_location`，前端按未知类型安全忽略。
4. 后续真正实现时，需要补组件、测试文档和 UI 回归截图。

## 八、回归护栏

当前自动化回归需要覆盖以下协议约束：

1. `WeatherCard`、`ImageCard`、`RouteCard`、`PoiListCard` 都支持 `props.data || props.card?.data || {}` 降级。
2. `AgentView` 和 `FloatingAgent` 只渲染 `weather`、`image`、`route`、`poi_list`。
3. `AgentView` 和 `FloatingAgent` 使用 `card_version === 1` 版本过滤。
4. 未知卡片类型不能被直接 `v-for="msg.cards"` 渲染。
5. `map_location` 仍然只保留协议，不做前端实现。
