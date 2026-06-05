<template>
  <div class="result" :class="{ hidden: !text && !showEmpty && !badge }">
    <div v-if="badge" class="result-head">
      <span class="badge" :class="badge.ok === true ? 'ok' : badge.ok === false ? 'err' : 'pending'">
        {{ badge.ok === true ? '✓ ' : badge.ok === false ? '✗ ' : '… ' }}{{ badge.text }}
      </span>
    </div>
    <div v-if="text" class="result-body">{{ text }}</div>
    <div v-else-if="showEmpty && !badge" class="result-empty">（尚未请求）</div>
  </div>
</template>

<script setup>
defineProps({
  badge: { type: Object, default: null },
  text: { type: String, default: '' },
  showEmpty: { type: Boolean, default: false }
})
</script>

<style scoped>
.result.hidden { display: none; }
</style>
