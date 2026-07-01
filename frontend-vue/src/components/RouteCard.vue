<template>
  <section class="agent-route-card" v-if="hasRoute">
    <header class="route-head">
      <div class="route-title-block">
        <div class="route-kicker">通勤路线</div>
        <h4>{{ titleText }}</h4>
      </div>
      <span class="route-provider">{{ providerLabel }}</span>
    </header>

    <div class="route-summary">
      <div class="route-point">
        <span class="point-label">起点</span>
        <strong>{{ originText }}</strong>
      </div>
      <div class="route-connector" aria-hidden="true"></div>
      <div class="route-point">
        <span class="point-label">终点</span>
        <strong>{{ destinationText }}</strong>
      </div>
    </div>

    <div class="route-list">
      <article
        class="route-option"
        :class="{ failed: !route.success }"
        v-for="route in visibleRoutes"
        :key="route.mode || route.label"
      >
        <div class="route-option-main">
          <span class="mode-mark">{{ modeLabel(route) }}</span>
          <div>
            <strong>{{ route.label || route.mode || '出行方式' }}</strong>
            <p>{{ route.success ? route.summary || routeLine(route) : route.error || '该方式暂不可用' }}</p>
          </div>
        </div>
        <div class="route-metrics" v-if="route.success">
          <span>{{ route.duration_text || '耗时暂不可用' }}</span>
          <small>{{ route.distance_text || '距离暂不可用' }}</small>
        </div>
        <div class="route-failed" v-else>失败</div>
      </article>
    </div>

    <footer class="route-foot" v-if="footerText">{{ footerText }}</footer>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  card: { type: Object, default: null },
  data: { type: Object, default: null },
  compact: { type: Boolean, default: false },
})

const routeData = computed(() => props.data || props.card?.data || {})
const routes = computed(() => Array.isArray(routeData.value.routes) ? routeData.value.routes : [])
const visibleRoutes = computed(() => props.compact ? routes.value.slice(0, 2) : routes.value)
const hasRoute = computed(() => !!routeData.value && routes.value.length > 0)

const originText = computed(() => routeData.value.origin_text || routeData.value.origin?.name || '起点')
const destinationText = computed(() => routeData.value.destination_text || routeData.value.destination?.name || '终点')
const titleText = computed(() => `${originText.value} → ${destinationText.value}`)

const providerLabel = computed(() => {
  if (routeData.value.provider === 'tencent_mcp') return '腾讯地图 MCP'
  return '路线数据'
})

const footerText = computed(() => {
  if (routeData.value.status === 'partial_success') return '部分出行方式暂不可用，已展示可用路线。'
  return routeData.value.weather_reminder || ''
})

function routeLine(route) {
  const duration = route.duration_text || '耗时暂不可用'
  const distance = route.distance_text || '距离暂不可用'
  return `预计 ${duration}，${distance}`
}

function modeLabel(route) {
  const mode = route.mode || ''
  if (mode === 'transit') return '轨'
  if (mode === 'driving') return '车'
  if (mode === 'walking') return '步'
  return '行'
}
</script>

<style scoped>
.agent-route-card {
  width: 100%;
  margin: 12px 0 4px;
  padding: 14px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: linear-gradient(135deg, var(--panel-solid), var(--panel-2));
  color: var(--text);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.route-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.route-title-block {
  min-width: 0;
}

.route-kicker {
  color: var(--blue-2);
  font-size: 11px;
}

.route-head h4 {
  margin: 2px 0 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.route-provider {
  flex: 0 0 auto;
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--gold-bg);
  color: var(--gold);
  font-size: 11px;
}

.route-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 34px minmax(0, 1fr);
  align-items: stretch;
  gap: 8px;
  margin-bottom: 10px;
}

.route-point {
  min-width: 0;
  padding: 9px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel-2);
}

.point-label {
  display: block;
  margin-bottom: 3px;
  color: var(--text-dim);
  font-size: 11px;
}

.route-point strong {
  display: block;
  overflow-wrap: anywhere;
  font-size: 13px;
}

.route-connector {
  position: relative;
  align-self: center;
  height: 1px;
  background: var(--line-strong);
}

.route-connector::after {
  content: '';
  position: absolute;
  right: 0;
  top: 50%;
  width: 7px;
  height: 7px;
  border-top: 1px solid var(--line-strong);
  border-right: 1px solid var(--line-strong);
  transform: translateY(-50%) rotate(45deg);
}

.route-list {
  display: grid;
  gap: 8px;
}

.route-option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel);
}

.route-option.failed {
  opacity: 0.76;
}

.route-option-main {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 9px;
}

.mode-mark {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: var(--gold-bg);
  color: var(--gold);
  font-weight: 800;
  font-size: 13px;
}

.route-option-main strong {
  display: block;
  margin-bottom: 2px;
  font-size: 13px;
}

.route-option-main p {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.route-metrics {
  text-align: right;
  white-space: nowrap;
}

.route-metrics span {
  display: block;
  color: var(--text);
  font-weight: 700;
  font-size: 13px;
}

.route-metrics small,
.route-foot {
  color: var(--text-muted);
  font-size: 11px;
}

.route-failed {
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--danger-bg, rgba(220, 38, 38, 0.12));
  color: var(--danger);
  font-size: 11px;
  white-space: nowrap;
}

.route-foot {
  margin-top: 10px;
}

@media (max-width: 680px) {
  .route-summary {
    grid-template-columns: minmax(0, 1fr);
  }

  .route-connector {
    display: none;
  }

  .route-option {
    grid-template-columns: minmax(0, 1fr);
  }

  .route-metrics {
    text-align: left;
    white-space: normal;
  }
}
</style>
