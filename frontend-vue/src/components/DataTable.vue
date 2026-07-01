<template>
  <div v-if="columns.length && rows.length" class="table-panel">
    <div class="table-head">
      <div class="table-meta">
        <span class="table-kicker">Query Result</span>
        <strong>{{ rows.length }} 条记录</strong>
      </div>
      <span class="table-columns">{{ columns.length }} 列</span>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in rows" :key="ri">
            <td v-for="col in columns" :key="col">{{ formatCell(row[col]) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: [Array, Object], default: null }
})

const columns = computed(() => {
  if (!props.data) return []
  const rows = Array.isArray(props.data) ? props.data : [props.data]
  if (!rows.length || typeof rows[0] !== 'object') return []
  return [...new Set(rows.flatMap(r => Object.keys(r)))]
})

const rows = computed(() => {
  if (Array.isArray(props.data)) return props.data
  if (props.data && typeof props.data === 'object') return [props.data]
  return []
})

function formatCell(v) {
  if (v === null || v === undefined) return ''
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
</script>
