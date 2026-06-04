<template>
  <div class="result" :class="{ hidden: !text && !showEmpty }">
    <span v-if="badge" class="badge" :class="badge.ok ? 'ok' : 'err'">
      {{ badge.ok ? '✓ ' : '✗ ' }}{{ badge.text }}
    </span>
    <template v-if="text">{{ text }}</template>
    <template v-else-if="showEmpty">（尚未请求）</template>
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
.result.hidden:empty { display: none; }
</style>
