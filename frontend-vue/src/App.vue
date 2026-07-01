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
      <span class="public-theme-switch__icon" aria-hidden="true">{{ theme === 'light' ? '🌞' : '🌙' }}</span>
      <span class="public-theme-switch__text">{{ theme === 'light' ? '浅色主题' : '深色主题' }}</span>
    </button>

    <FloatingAgent />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
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
let spotlightObserver = null
let spotlightFrame = 0
let activeSpotlightWindow = null

const SPOTLIGHT_WINDOW_SELECTOR = [
  '.sidebar',
  '.topbar',
  '.sub-bar',
  '.content-shell',
  '.card',
  '.login-shell',
  '.login-left-console',
  '.table-panel',
  '.result',
  '.float-agent-panel',
  '.talk-layout',
  '.talk-session-list',
  '.agent-shell',
  '.agent-panel',
  '.agent-hitl-card',
  '.float-agent-hitl',
  '.quick-tool-panel',
  '.image-card'
].join(', ')

function ensureWindowSpotlights(root = document) {
  root.querySelectorAll?.(SPOTLIGHT_WINDOW_SELECTOR).forEach(el => {
    if (!(el instanceof HTMLElement) || el.dataset.spotlightWindow === '1') return
    el.dataset.spotlightWindow = '1'
    if (window.getComputedStyle(el).position === 'static') {
      el.dataset.spotlightPosition = 'static'
    }
    el.classList.add('window-spotlight-host')

    const layer = document.createElement('span')
    layer.className = 'window-spotlight'
    layer.setAttribute('aria-hidden', 'true')
    el.appendChild(layer)
  })
}

function setActiveSpotlightWindow(el) {
  if (activeSpotlightWindow === el) return
  activeSpotlightWindow?.classList.remove('window-spotlight-active')
  activeSpotlightWindow = el
  activeSpotlightWindow?.classList.add('window-spotlight-active')
}

function clearActiveSpotlightWindow() {
  activeSpotlightWindow?.classList.remove('window-spotlight-active')
  activeSpotlightWindow = null
}

function syncSpotlightPointer(event) {
  const target = event.target instanceof Element
    ? event.target.closest('[data-spotlight-window="1"]')
    : null

  if (!(target instanceof HTMLElement)) {
    clearActiveSpotlightWindow()
    return
  }

  setActiveSpotlightWindow(target)
  if (spotlightFrame) cancelAnimationFrame(spotlightFrame)

  // 只更新当前窗口的局部坐标，避免鼠标移动时触发整页窗口一起重绘。
  spotlightFrame = requestAnimationFrame(() => {
    const rect = target.getBoundingClientRect()
    const localX = Math.max(0, Math.min(event.clientX - rect.left, rect.width))
    const localY = Math.max(0, Math.min(event.clientY - rect.top, rect.height))
    target.style.setProperty('--spotlight-x', localX.toFixed(2))
    target.style.setProperty('--spotlight-y', localY.toFixed(2))
    target.style.setProperty('--spotlight-xp', rect.width ? (localX / rect.width).toFixed(3) : '0')
    spotlightFrame = 0
  })
}

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

onMounted(() => {
  if (typeof document === 'undefined') return
  ensureWindowSpotlights()
  spotlightObserver = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
      mutation.addedNodes.forEach(node => {
        if (node instanceof HTMLElement) {
          ensureWindowSpotlights(node.matches?.(SPOTLIGHT_WINDOW_SELECTOR) ? node.parentElement || document : node)
        }
      })
    })
  })
  spotlightObserver.observe(document.body, { childList: true, subtree: true })
  window.addEventListener('pointermove', syncSpotlightPointer, { passive: true })
  window.addEventListener('pointerleave', clearActiveSpotlightWindow, { passive: true })
})

onUnmounted(() => {
  spotlightObserver?.disconnect()
  window.removeEventListener('pointermove', syncSpotlightPointer)
  window.removeEventListener('pointerleave', clearActiveSpotlightWindow)
  if (spotlightFrame) cancelAnimationFrame(spotlightFrame)
  clearActiveSpotlightWindow()
})
</script>
