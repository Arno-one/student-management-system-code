# Agent系统v2.3-WorkView复用WeatherCard测试数据

## 一、测试目标

验证 v2.3 当前迭代功能「WorkView 复用 WeatherCard」是否完成闭环：

1. 工作台天气查询表单保持原有交互，不改变 `/work/weather` 请求参数。
2. 天气查询结果不再由 `WorkView.vue` 拼接 HTML。
3. 天气结果统一转换为 Agent 天气卡片协议，并交给 `WeatherCard.vue` 渲染。
4. 实时天气、多日预报、逐时预报三类结果都能被卡片识别。
5. 地址解析结果仍保留原来的 `v-html` 和「查该地天气」事件委托能力。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `frontend-vue/src/views/WorkView.vue` | 引入 `WeatherCard`，新增 `weatherCardData/weatherError` 状态，移除工作台天气 HTML 拼接函数 |
| `frontend-vue/src/components/WeatherCard.vue` | 补充 `逐时预报` 数据块解析和逐时网格展示 |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增 WorkView 复用 WeatherCard 的静态回归护栏 |

## 三、关键设计

### 1. 工作台天气结果协议转换

`/work/weather` 返回结构保持不变：

```json
{
  "code": 200,
  "data": {
    "result": {
      "realtime": [],
      "forecast": [],
      "forecast_hours": []
    }
  }
}
```

`WorkView.vue` 只负责转换为卡片协议：

```js
{
  provider: 'work_weather',
  location_text: '广东省 · 深圳市 · 宝安区',
  adcode: '440306',
  weather: {
    '实时天气': { result },
    '多日预报': { result },
    '逐时预报': { result }
  }
}
```

### 2. 展示边界

实时天气：读取 `result.realtime[0].infos`。

多日预报：读取 `result.forecast[0].infos`，普通模式最多展示 5 天，compact 模式最多展示 3 天。

逐时预报：读取 `result.forecast_hours[0].infos`，普通模式最多展示 8 条，compact 模式最多展示 4 条。

空数据：如果三类数组都为空，`WorkView` 显示「未解析到天气数据」错误提示。

接口失败：保留工作台原来的 `geo-card/geo-fail` 错误提示样式。

## 四、测试用例

### 用例 1：实时天气

输入：

```text
location=22.55329,113.88308
weather_type=now
```

预期：

```text
WorkView 生成 weather['实时天气']
WeatherCard 展示城市、天气、温度、风向、风力、湿度、气压
页面中不出现旧的 wx-card HTML 拼接结果
```

### 用例 2：多日预报

输入：

```text
adcode=440306
weather_type=future
get_md=0
```

预期：

```text
WorkView 生成 weather['多日预报']
WeatherCard 展示未来预报网格
每一天展示星期、日期、天气、温度范围、风力信息
```

### 用例 3：逐时预报

输入：

```text
adcode=440306
weather_type=hours
```

预期：

```text
WorkView 生成 weather['逐时预报']
WeatherCard 展示逐时预报网格
每条展示时间、温度、天气图标和天气文字
```

### 用例 4：地址解析联动天气

输入：

```text
地址=深圳市宝安区宝安中心
点击「查该地天气」
```

预期：

```text
地址解析结果仍通过 geoHtml 渲染
点击按钮后回填 adcode 或经纬度
自动调用 workWeather()
天气结果渲染为 WeatherCard
```

### 用例 5：异常和空数据

输入：

```text
接口返回 code != 200
或 result 中 realtime/forecast/forecast_hours 都为空
```

预期：

```text
显示工作台错误提示
不渲染空的 WeatherCard
不暴露原始 HTML 字符串
```

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
PASS WorkView 引入 WeatherCard
PASS WorkView 天气结果复用 WeatherCard
PASS WorkView 将接口结果转换为天气卡片协议
PASS WorkView 天气结果不再使用 v-html
PASS WorkView 不再维护旧天气 HTML 拼接函数
PASS WeatherCard 支持逐时预报数据块
PASS WeatherCard 渲染逐时预报网格
```

实际结果：

```text
UI 回归检查通过：71/71
Playwright UI 回归通过：2/2
```

## 六、结论

本轮功能完成后，天气查询展示逻辑统一收敛到 `WeatherCard.vue`。`WorkView.vue` 不再维护独立天气 HTML 模板，后续天气卡片样式、字段兜底和移动端适配只需要在一个组件中维护。
