<template>
  <div class="app-layout" :class="[{ 'sidebar-collapsed': sidebarCollapsed }, themeClass, { 'app-layout--public': isPublicPage }]">
    <div class="app-backdrop" aria-hidden="true">
      <span class="glow glow-a"></span>
      <span class="glow glow-b"></span>
      <span class="grid-fade"></span>
      <!-- 方案 C：黑橙 AI 叙事工作台的舞台背景，只负责视觉氛围，不参与交互。 -->
      <span class="ai-ribbon ai-ribbon-a"></span>
      <span class="ai-ribbon ai-ribbon-b"></span>
      <span class="ai-signal-line"></span>
      <span class="ai-particle-field"></span>
    </div>

    <Sidebar
      :collapsed="sidebarCollapsed"
      :current-page="currentPage"
      @navigate="navigate"
    />

    <div class="main" :class="{ 'main--public': isPublicPage }">
      <TopBar
        :sidebar-collapsed="sidebarCollapsed"
        :title="pageTitle"
        :theme="theme"
        @toggle-sidebar="toggleSidebar"
        @toggle-theme="toggleTheme"
      />
      <div class="content" :class="{ 'content--public': isPublicPage }">
        <div class="content-shell" :class="{ 'content-shell--public': isPublicPage }">
          <router-view />
        </div>
      </div>
    </div>

    <!-- 登录页没有 TopBar，这里单独提供主题切换入口，保证登录前也能预览两套视觉主题。 -->
    <button
      v-if="isPublicPage"
      type="button"
      class="public-theme-switch"
      :aria-label="theme === 'light' ? '切换到深色主题' : '切换到浅色主题'"
      @click="toggleTheme"
    >
      <span class="public-theme-switch__icon" aria-hidden="true">{{ theme === 'light' ? '☀' : '☾' }}</span>
      <span class="public-theme-switch__text">{{ theme === 'light' ? '浅色主题' : '深色主题' }}</span>
    </button>

    <FloatingAgent />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'
import FloatingAgent from './components/FloatingAgent.vue'
import { initGlobalEnterSubmit } from './utils/helpers'

initGlobalEnterSubmit()

const router = useRouter()
const route = useRoute()
const sidebarCollapsed = ref(localStorage.getItem('workspace-sidebar-collapsed') === '1')
const savedTheme = localStorage.getItem('workspace-theme')
const theme = ref(savedTheme === 'light' ? 'light' : 'dark')

const currentPage = computed(() => route.name || 'student')
const pageTitle = computed(() => route.meta?.title || '学生信息管理系统')
const themeClass = computed(() => `theme-${theme.value}`)
const isPublicPage = computed(() => !!route.meta?.public)

function navigate(page) {
  const target = typeof page === 'string' ? { page } : page
  router.push({
    name: target.page,
    query: target.sub ? { sub: target.sub } : {}
  })
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('workspace-sidebar-collapsed', sidebarCollapsed.value ? '1' : '0')
}

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  localStorage.setItem('workspace-theme', theme.value)
}
</script>
