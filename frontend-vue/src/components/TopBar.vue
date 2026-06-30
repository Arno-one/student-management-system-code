<template>
  <header v-if="!isPublicPage" class="topbar">
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
        <span class="title-kicker">Campus AI Workspace</span>
        <div class="title-row">
          <div class="title">{{ title }}</div>
          <span class="title-pill">统一业务工作台</span>
        </div>
      </div>
    </div>

    <div class="topbar-actions">
      <div class="topbar-user" v-if="apiState.user">
        <strong>{{ apiState.user.real_name || apiState.user.username }}</strong>
        <small>{{ apiState.user.username }}</small>
      </div>

      <button
        type="button"
        class="theme-toggle"
        :aria-label="theme === 'light' ? '切换到深色主题' : '切换到浅色主题'"
        @click="$emit('toggle-theme')"
      >
        <span class="theme-toggle-icon" aria-hidden="true">{{ theme === 'light' ? '☀' : '☾' }}</span>
      </button>

      <button type="button" class="theme-toggle" aria-label="退出登录" @click="logout">⎋</button>

      <label class="api-box">
        <span>API Endpoint</span>
        <input :value="apiState.baseUrl" placeholder="http://127.0.0.1:8000" @input="onChange" />
      </label>
    </div>
  </header>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'
import { apiState, clearAuth, setBaseUrl } from '../api'

defineEmits(['toggle-sidebar', 'toggle-theme'])

defineProps({
  title: { type: String, default: '' },
  sidebarCollapsed: { type: Boolean, default: false },
  theme: { type: String, default: 'dark' }
})

const route = useRoute()
const router = useRouter()
const isPublicPage = computed(() => !!route.meta?.public)

function onChange(e) {
  setBaseUrl(e.target.value)
}

function logout() {
  clearAuth()
  router.replace({ name: 'login' })
}
</script>
