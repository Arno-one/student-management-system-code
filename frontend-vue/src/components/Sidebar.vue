<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="logo">学</div>
      <div>
        <h1>学生信息管理系统</h1>
        <p>逐光小组作品 · v0.5.0</p>
      </div>
    </div>
    <nav>
      <div
        v-for="item in navItems"
        :key="item.page"
        class="nav-item"
        :class="{ active: currentPage === item.page }"
        @click="$emit('navigate', item.page)"
      >
        <span class="ico">{{ item.icon }}</span>{{ item.label }}
      </div>
    </nav>
  </aside>
</template>

<script setup>
defineProps({
  currentPage: { type: String, default: 'student' }
})
defineEmits(['navigate'])

const navItems = [
  { page: 'student', icon: '🎓', label: '学生信息管理' },
  { page: 'score', icon: '📊', label: '考核成绩管理' },
  { page: 'employment', icon: '💼', label: '就业信息管理' },
  { page: 'class', icon: '🏫', label: '班级管理' },
  { page: 'teacher', icon: '👨‍🏫', label: '教师管理' },
  { page: 'statistics', icon: '📈', label: '统计分析' },
  { page: 'work', icon: '🤖', label: 'AI 作业模块' },
  { page: 'email', icon: '✉️', label: '邮件管理' }
]
</script>
