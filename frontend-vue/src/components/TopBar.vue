<template>
  <div class="topbar">
    <div class="title">{{ title }}</div>
    <div class="api-box">
      <span>接口地址：</span>
      <input :value="apiState.baseUrl" @input="onChange" />
    </div>
  </div>
</template>

<script setup>
import { apiState, setBaseUrl } from '../api'

defineProps({
  title: { type: String, default: '' }
})

function onChange(e) {
  setBaseUrl(e.target.value)
}
</script>
