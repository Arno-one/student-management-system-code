<template>
  <div class="app-layout">
    <Sidebar :current-page="currentPage" @navigate="navigate" />
    <div class="main">
      <TopBar :title="pageTitle" />
      <div class="content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'

const router = useRouter()
const route = useRoute()

const currentPage = computed(() => route.name || 'student')
const pageTitle = computed(() => route.meta?.title || '学生信息管理系统')

function navigate(page) {
  router.push({ name: page })
}
</script>
