<template>
  <section class="agent-weather-card" v-if="hasWeather">
    <header class="agent-weather-head">
      <div>
        <div class="agent-weather-kicker">天气卡片</div>
        <h4>{{ locationTitle }}</h4>
      </div>
      <span class="agent-weather-provider">{{ providerLabel }}</span>
    </header>

    <div class="agent-weather-now" v-if="nowInfo">
      <div class="agent-weather-symbol">{{ weatherEmoji(nowInfo.weather) }}</div>
      <div class="agent-weather-now-main">
        <div class="agent-weather-temp">{{ displayValue(nowInfo.temperature) }}<small>℃</small></div>
        <div class="agent-weather-desc">{{ nowInfo.weather || '天气状况未知' }}</div>
      </div>
      <div class="agent-weather-time" v-if="nowUpdateTime">{{ nowUpdateTime }}</div>
    </div>

    <div class="agent-weather-metrics" v-if="metrics.length">
      <div class="agent-weather-metric" v-for="item in metrics" :key="item.label">
        <span class="metric-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>

    <div class="agent-weather-forecast" v-if="forecastDays.length">
      <div class="agent-weather-section-title">未来预报</div>
      <div class="agent-weather-days">
        <article class="agent-weather-day" v-for="day in forecastDays" :key="day.key">
          <div class="day-top">
            <span>{{ day.week || '未来' }}</span>
            <small>{{ day.date || '' }}</small>
          </div>
          <div class="day-icon">{{ weatherEmoji(day.weather) }}</div>
          <strong>{{ day.tempRange }}</strong>
          <span>{{ day.weather || '--' }}</span>
          <small>{{ day.wind || '' }}</small>
        </article>
      </div>
    </div>

    <div class="agent-weather-hourly" v-if="hourlyItems.length">
      <div class="agent-weather-section-title">逐时预报</div>
      <div class="agent-weather-hours">
        <article class="agent-weather-hour" v-for="hour in hourlyItems" :key="hour.key">
          <span>{{ hour.time }}</span>
          <strong>{{ hour.temperature }}℃</strong>
          <div>{{ weatherEmoji(hour.weather) }}</div>
          <small>{{ hour.weather || '--' }}</small>
        </article>
      </div>
    </div>

    <footer class="agent-weather-foot" v-if="footerText">{{ footerText }}</footer>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { weatherEmoji } from '../utils/helpers'

const props = defineProps({
  card: { type: Object, default: null },
  data: { type: Object, default: null },
  compact: { type: Boolean, default: false },
})

const weatherData = computed(() => props.data || props.card?.data || {})
const weatherBlocks = computed(() => weatherData.value.weather || {})

function unwrapPayload(payload) {
  if (!payload || typeof payload !== 'object') return {}
  if (payload.result && typeof payload.result === 'object') return payload.result
  return payload
}

const nowPayload = computed(() => unwrapPayload(weatherBlocks.value['实时天气']))
const futurePayload = computed(() => unwrapPayload(weatherBlocks.value['多日预报']))
const hourlyPayload = computed(() => unwrapPayload(weatherBlocks.value['逐时预报']))

const nowItem = computed(() => {
  const realtime = nowPayload.value.realtime
  if (Array.isArray(realtime) && realtime.length) return realtime[0]
  if (nowPayload.value.infos) return nowPayload.value
  return null
})

const nowInfo = computed(() => nowItem.value?.infos || null)
const nowUpdateTime = computed(() => nowItem.value?.update_time || '')

const forecastDays = computed(() => {
  const forecast = futurePayload.value.forecast
  const first = Array.isArray(forecast) && forecast.length ? forecast[0] : null
  const infos = first?.infos || []
  return infos.slice(0, props.compact ? 3 : 5).map((item, idx) => {
    const day = item.day || {}
    const night = item.night || {}
    const weather = day.weather || night.weather || ''
    const low = displayValue(night.temperature)
    const high = displayValue(day.temperature)
    return {
      key: `${item.date || idx}-${item.week || ''}`,
      week: item.week,
      date: item.date,
      weather,
      tempRange: `${low}~${high}℃`,
      wind: [day.wind_direction, day.wind_power].filter(Boolean).join(' '),
    }
  })
})

const hourlyItems = computed(() => {
  const forecastHours = hourlyPayload.value.forecast_hours
  const first = Array.isArray(forecastHours) && forecastHours.length ? forecastHours[0] : null
  const infos = first?.infos || []
  return infos.slice(0, props.compact ? 4 : 8).map((item, idx) => {
    const info = item.info || {}
    return {
      key: `${item.hour || idx}-${info.weather || ''}`,
      time: displayHour(item.hour),
      weather: info.weather || '',
      temperature: displayValue(info.temperature),
    }
  })
})

const locationTitle = computed(() => {
  const futureItem = Array.isArray(futurePayload.value.forecast) ? futurePayload.value.forecast[0] : null
  const hourlyItem = Array.isArray(hourlyPayload.value.forecast_hours) ? hourlyPayload.value.forecast_hours[0] : null
  const item = nowItem.value || futureItem || hourlyItem
  const loc = [item?.province, item?.city, item?.district].filter(Boolean).join(' · ')
  return loc || weatherData.value.location_text || '天气查询结果'
})

const providerLabel = computed(() => {
  if (weatherData.value.provider === 'tencent_mcp') return '腾讯地图 MCP'
  if (weatherData.value.provider === 'tencent_rest_fallback') return '腾讯地图 REST'
  if (weatherData.value.provider === 'work_weather') return '工作台天气'
  return '天气数据'
})

const metrics = computed(() => {
  const info = nowInfo.value || {}
  const rows = [
    ['风向', info.wind_direction],
    ['风力', info.wind_power],
    ['湿度', info.humidity != null ? `${info.humidity}%` : ''],
    ['气压', info.air_pressure != null ? `${info.air_pressure} 百帕` : ''],
  ]
  return rows.filter(([, value]) => value !== '' && value != null).map(([label, value]) => ({ label, value }))
})

const footerText = computed(() => {
  if (weatherData.value.fallback_reason) return `已使用 REST 兜底：${weatherData.value.fallback_reason}`
  if (weatherData.value.adcode) return `行政区划编码 ${weatherData.value.adcode}`
  return ''
})

const hasWeather = computed(() => nowInfo.value || forecastDays.value.length || hourlyItems.value.length || Object.keys(weatherBlocks.value).length)

function displayHour(value) {
  const text = String(value || '')
  return text.split(' ')[1] || text || '--'
}

function displayValue(value) {
  return value === null || value === undefined || value === '' ? '--' : value
}
</script>

<style scoped>
.agent-weather-card {
  width: 100%;
  margin: 12px 0 4px;
  padding: 14px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background:
    linear-gradient(135deg, var(--panel-solid), var(--panel-2)),
    repeating-linear-gradient(90deg, var(--line) 0 1px, transparent 1px 12px);
  color: var(--text);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.agent-weather-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.agent-weather-kicker {
  font-size: 11px;
  color: var(--blue-2);
}

.agent-weather-head h4 {
  margin: 2px 0 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0;
}

.agent-weather-provider {
  flex: 0 0 auto;
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--gold-bg);
  color: var(--gold);
  font-size: 11px;
}

.agent-weather-now {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 72px;
}

.agent-weather-symbol {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 8px;
  background: var(--panel-3);
  font-size: 30px;
}

.agent-weather-temp {
  font-size: 34px;
  line-height: 1;
  font-weight: 800;
}

.agent-weather-temp small {
  font-size: 15px;
  margin-left: 2px;
  color: var(--text-dim);
}

.agent-weather-desc {
  margin-top: 4px;
  color: var(--text-soft);
}

.agent-weather-time {
  max-width: 120px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: right;
}

.agent-weather-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.agent-weather-metric {
  min-width: 0;
  padding: 8px;
  border-radius: 7px;
  background: var(--panel-2);
  border: 1px solid var(--line);
}

.metric-label {
  display: block;
  margin-bottom: 3px;
  color: var(--text-dim);
  font-size: 11px;
}

.agent-weather-metric strong {
  font-size: 13px;
  word-break: break-word;
}

.agent-weather-section-title {
  margin: 14px 0 8px;
  color: var(--text);
  font-weight: 700;
  font-size: 13px;
}

.agent-weather-days {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 8px;
}

.agent-weather-hours {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(86px, 1fr));
  gap: 8px;
}

.agent-weather-day {
  min-width: 0;
  padding: 9px;
  border-radius: 7px;
  background: var(--panel-2);
  border: 1px solid var(--line);
}

.agent-weather-hour {
  min-width: 0;
  padding: 9px;
  border-radius: 7px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  text-align: center;
}

.agent-weather-hour span,
.agent-weather-hour small {
  display: block;
  color: var(--text-muted);
  font-size: 11px;
  word-break: break-word;
}

.agent-weather-hour strong {
  display: block;
  margin: 5px 0;
  color: var(--text);
  font-size: 14px;
}

.agent-weather-hour div {
  margin-bottom: 3px;
  font-size: 22px;
}

.day-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  color: var(--text);
  font-size: 12px;
}

.day-top small,
.agent-weather-day small {
  color: var(--text-muted);
}

.day-icon {
  margin: 8px 0 5px;
  font-size: 24px;
}

.agent-weather-day strong {
  display: block;
  margin-bottom: 3px;
}

.agent-weather-day span {
  display: block;
  color: var(--text-soft);
  font-size: 12px;
}

.agent-weather-foot {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 11px;
}

@media (max-width: 680px) {
  .agent-weather-now {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .agent-weather-time {
    grid-column: 1 / -1;
    max-width: none;
    text-align: left;
  }

  .agent-weather-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
