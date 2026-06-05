<template>
  <header class="topbar">
    <div class="topbar-main">
      <button
        type="button"
        class="sidebar-toggle"
        :aria-label="sidebarCollapsed ? '展开 Workspace 侧栏' : '收起 Workspace 侧栏'"
        @click="$emit('toggle-sidebar')"
      >
        <span class="toggle-rail"></span>
        <span class="toggle-icon">{{ sidebarCollapsed ? '→' : '←' }}</span>
      </button>

      <div class="title-group">
        <span class="title-kicker">Operations Deck</span>
        <div class="title-row">
          <div class="title">{{ title }}</div>
          <span class="title-pill">Live Workspace</span>
        </div>
      </div>
    </div>

    <div class="topbar-actions">
      <button
        type="button"
        class="theme-toggle"
        :aria-label="theme === 'light' ? '切换到深色主题' : '切换到浅色主题'"
        @click="$emit('toggle-theme')"
      >
        <span class="theme-toggle-icon" aria-hidden="true">{{ theme === 'light' ? '☀' : '☾' }}</span>
      </button>

      <label class="api-box">
        <span>API Endpoint</span>
        <input :value="apiState.baseUrl" placeholder="http://127.0.0.1:8000" @input="onChange" />
      </label>
    </div>
  </header>
</template>

<script setup>
import { apiState, setBaseUrl } from '../api'

defineEmits(['toggle-sidebar', 'toggle-theme'])

defineProps({
  title: { type: String, default: '' },
  sidebarCollapsed: { type: Boolean, default: false },
  theme: { type: String, default: 'dark' }
})

function onChange(e) {
  setBaseUrl(e.target.value)
}
</script>
