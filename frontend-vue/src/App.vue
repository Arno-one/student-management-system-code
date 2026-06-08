<template>
  <div class="app-layout" :class="[{ 'sidebar-collapsed': sidebarCollapsed }, themeClass, { 'app-layout--public': isPublicPage }]">
    <div class="app-backdrop" aria-hidden="true">
      <span class="glow glow-a"></span>
      <span class="glow glow-b"></span>
      <span class="grid-fade"></span>
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
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'

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
  router.push({ name: page })
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
