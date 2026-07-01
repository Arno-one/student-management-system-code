<template>
  <section class="agent-poi-card" v-if="hasItems">
    <header class="poi-head">
      <div class="poi-title-block">
        <div class="poi-kicker">周边服务</div>
        <h4>{{ titleText }}</h4>
      </div>
      <span class="poi-provider">{{ providerLabel }}</span>
    </header>

    <div class="poi-meta">
      <span>{{ centerText }}</span>
      <span>{{ radiusText }}</span>
      <span>共 {{ items.length }} 条</span>
    </div>

    <div class="poi-list">
      <article class="poi-item" v-for="item in visibleItems" :key="item.id || item.name">
        <div class="poi-rank">{{ itemRank(item) }}</div>
        <div class="poi-main">
          <div class="poi-name-row">
            <strong>{{ item.name || '未命名地点' }}</strong>
            <span>{{ item.category || '地点' }}</span>
          </div>
          <p class="poi-address">{{ item.address || '地址暂不可用' }}</p>
          <div class="poi-foot">
            <small>{{ distanceText(item.distance_meters) }}</small>
            <small>{{ item.source === 'tencent_map' ? '腾讯地图' : '地图数据' }}</small>
          </div>
        </div>
        <div class="poi-actions">
          <button type="button" @click="copyAddress(item)" :title="copyTitle(item)">
            {{ copiedKey === itemKey(item) ? '已复制' : '复制' }}
          </button>
          <button type="button" class="primary" @click="planRoute(item)" title="填充通勤规划输入">
            去这里
          </button>
        </div>
      </article>
    </div>

    <footer class="poi-card-foot" v-if="compact && items.length > visibleItems.length">
      已展示前 {{ visibleItems.length }} 条，可在主 Agent 查看完整列表。
    </footer>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  card: { type: Object, default: null },
  data: { type: Object, default: null },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['plan-route'])

const copiedKey = ref('')
const poiData = computed(() => props.data || props.card?.data || {})
const rawItems = computed(() => Array.isArray(poiData.value.items) ? poiData.value.items : [])
const items = computed(() => {
  return [...rawItems.value].sort((a, b) => {
    const da = Number.isFinite(Number(a?.distance_meters)) ? Number(a.distance_meters) : Number.MAX_SAFE_INTEGER
    const db = Number.isFinite(Number(b?.distance_meters)) ? Number(b.distance_meters) : Number.MAX_SAFE_INTEGER
    return da - db
  })
})
const visibleItems = computed(() => props.compact ? items.value.slice(0, 3) : items.value.slice(0, 10))
const hasItems = computed(() => visibleItems.value.length > 0)

const centerText = computed(() => poiData.value.center?.name || poiData.value.center?.address || '查询地点')
const titleText = computed(() => `${centerText.value}附近的${poiData.value.query || '生活服务'}`)
const radiusText = computed(() => {
  const radius = Number(poiData.value.radius_meters)
  if (!Number.isFinite(radius) || radius <= 0) return '默认范围'
  return radius >= 1000 ? `${(radius / 1000).toFixed(radius % 1000 === 0 ? 0 : 1)} 公里内` : `${radius} 米内`
})

const providerLabel = computed(() => {
  if (poiData.value.provider === 'tencent_mcp') return '腾讯地图 MCP'
  if (poiData.value.provider === 'tencent_rest_fallback') return '腾讯地图 REST'
  return '地图数据'
})

function itemKey(item) {
  return String(item?.id || item?.name || item?.address || '')
}

function itemRank(item) {
  const index = items.value.findIndex(entry => itemKey(entry) === itemKey(item))
  return index >= 0 ? String(index + 1).padStart(2, '0') : '--'
}

function distanceText(distance) {
  const value = Number(distance)
  if (!Number.isFinite(value)) return '距离暂不可用'
  return value >= 1000 ? `${(value / 1000).toFixed(1)} 公里` : `${value} 米`
}

function copyTitle(item) {
  return item?.address ? '复制地址' : '地址暂不可用'
}

async function copyAddress(item) {
  const text = item?.address || item?.name || ''
  if (!text) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    copiedKey.value = itemKey(item)
    window.setTimeout(() => {
      if (copiedKey.value === itemKey(item)) copiedKey.value = ''
    }, 1400)
  } catch (_) {
    copiedKey.value = ''
  }
}

function planRoute(item) {
  const destination = item?.address || item?.name
  if (!destination) return
  emit('plan-route', destination)
}
</script>

<style scoped>
.agent-poi-card {
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

.poi-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.poi-title-block {
  min-width: 0;
}

.poi-kicker {
  color: var(--blue-2);
  font-size: 11px;
}

.poi-head h4 {
  margin: 2px 0 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.poi-provider {
  flex: 0 0 auto;
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--gold-bg);
  color: var(--gold);
  font-size: 11px;
}

.poi-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.poi-meta span {
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--panel);
  color: var(--text-muted);
  font-size: 11px;
}

.poi-list {
  display: grid;
  gap: 8px;
}

.poi-item {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel);
}

.poi-rank {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 7px;
  background: var(--gold-bg);
  color: var(--gold);
  font-size: 12px;
  font-weight: 800;
}

.poi-main {
  min-width: 0;
}

.poi-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 3px;
}

.poi-name-row strong {
  font-size: 13px;
  overflow-wrap: anywhere;
}

.poi-name-row span {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--blue-bg);
  color: var(--blue);
  font-size: 10px;
}

.poi-address {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.poi-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 5px;
}

.poi-foot small,
.poi-card-foot {
  color: var(--text-muted);
  font-size: 11px;
}

.poi-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.poi-actions button {
  padding: 5px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--text-soft);
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}

.poi-actions button:hover {
  border-color: var(--gold);
  color: var(--gold);
}

.poi-actions button.primary {
  border-color: var(--gold);
  background: var(--gold-bg);
  color: var(--gold);
}

.poi-card-foot {
  margin-top: 10px;
}

@media (max-width: 680px) {
  .poi-item {
    grid-template-columns: 30px minmax(0, 1fr);
    align-items: start;
  }

  .poi-actions {
    grid-column: 2;
    justify-content: flex-start;
  }
}
</style>
