<template>
  <aside v-if="!isPublicPage" class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <div class="logo-wrap">
        <div class="logo">学</div>
        <span class="brand-signal"></span>
      </div>

      <div class="brand-text">
        <p class="brand-kicker">Campus Operations Suite</p>
        <h1>学生信息管理系统</h1>
        <p>以更精致的方式组织学生、教务、统计与智能流程。</p>
      </div>
    </div>

    <div class="sidebar-section">Workspace</div>

    <nav>
      <button
        v-for="(item, index) in visibleNavItems"
        :key="item.page"
        type="button"
        class="nav-item"
        :class="{ active: currentPage === item.page }"
        :title="collapsed ? item.label : ''"
        @click="$emit('navigate', item.page)"
      >
        <span class="nav-index">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="ico">{{ item.short }}</span>
        <span class="nav-copy">
          <strong>{{ item.label }}</strong>
          <small>{{ item.desc }}</small>
        </span>
        <span class="nav-arrow">↗</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <span class="dot"></span>
      <div>
        <strong>系统运行中</strong>
        <small>数据工作区与智能模块已就绪</small>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { getMenuCodes, hasRole } from '../api'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  currentPage: { type: String, default: 'student' }
})
defineEmits(['navigate'])

const route = useRoute()
const isPublicPage = computed(() => !!route.meta?.public)

const navItems = [
  { page: 'student', short: 'ST', label: '学生信息管理', desc: '档案录入、查询与状态维护', menuCode: 'student:page' },
  { page: 'score', short: 'SC', label: '考核成绩管理', desc: '单条、批量与区间查询', menuCode: 'score:page' },
  { page: 'employment', short: 'EM', label: '就业信息管理', desc: 'offer、薪资与就业跟踪', menuCode: 'employment:page' },
  { page: 'class', short: 'CL', label: '班级管理', desc: '班级建档与排期信息', menuCode: 'class:page' },
  { page: 'teacher', short: 'TE', label: '教师管理', desc: '教师资料、导入与检索', menuCode: 'teacher:page' },
  { page: 'statistics', short: 'BI', label: '统计分析', desc: '关键指标与业务汇总', menuCode: 'statistics:page' },
  { page: 'work', short: 'AI', label: 'AI 作业模块', desc: '评价生成、对话与天气能力', menuCode: 'work:page' },
  { page: 'email', short: 'ML', label: '邮件管理', desc: '智能生成与发送邮件', menuCode: 'email:page' },
  { page: 'nl2sql', short: 'D2', label: 'NL2SQL 智能问数', desc: '自然语言转 SQL 数据查询', menuCode: 'nl2sql:page' },
  { page: 'rag', short: 'RA', label: '四大名著知识库', desc: 'RAG 混合检索 + AI 问答' },
  { page: 'agent', short: 'AG', label: '智能 Agent 助手', desc: '学业导师 · 成绩查询 · 陪伴对话' },
  { page: 'system', short: 'SM', label: '系统管理', desc: '用户、角色与权限分配', menuCode: 'system:page', adminOnly: true }
]

const visibleNavItems = computed(() => {
  const menuCodes = getMenuCodes()
  return navItems.filter(item => {
    if (item.adminOnly && !hasRole('admin')) return false
    if (!item.menuCode) return true  // 无权限要求，始终可见
    return menuCodes.has(item.menuCode)
  })
})
</script>
