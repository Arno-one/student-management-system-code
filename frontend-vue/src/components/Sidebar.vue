<template>
  <aside v-if="!isPublicPage" class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <div class="logo-wrap">
        <div class="logo">学</div>
        <span class="brand-signal"></span>
      </div>

      <div class="brand-text">
        <p class="brand-kicker">Campus AI Workspace</p>
        <h1>校园智能工作台</h1>
        <p>统一承载学生、教务、统计与智能 Agent 能力。</p>
      </div>
    </div>

    <div class="sidebar-section" v-if="!collapsed">Workspace</div>

    <nav
      v-if="collapsed"
      class="sidebar-rail"
      data-sidebar-rail
    >
      <button
        v-for="item in visibleNavItems"
        :key="item.page"
        type="button"
        class="rail-item"
        :class="{ active: isActivePage(item.page) }"
        :title="item.label"
        :data-rail-item="item.page"
        @click="handleNavigate(item)"
      >
        <span class="ico" :class="{ 'ico--emoji': !!item.emoji }">{{ item.emoji || item.short }}</span>
      </button>
    </nav>

    <nav
      v-else
      ref="navMainRef"
      class="sidebar-nav"
      data-sidebar-main
    >
      <div
        v-for="(item, index) in visibleNavItems"
        :key="item.page"
        class="nav-group"
        :class="{ 'nav-group-active': isActivePage(item.page) }"
      >
        <button
          type="button"
          class="nav-item"
          :class="{ active: isActivePage(item.page) }"
          :title="collapsed ? item.label : ''"
          :data-nav-page="item.page"
          @click="handleNavigate(item)"
        >
          <span class="nav-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="ico" :class="{ 'ico--emoji': !!item.emoji }">{{ item.emoji || item.short }}</span>
          <span class="nav-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.desc }}</small>
          </span>
          <span class="nav-arrow">{{ hasChildren(item) && !collapsed ? '▾' : '↗' }}</span>
        </button>

        <div v-if="showChildren(item)" class="nav-children">
          <button
            v-for="child in item.children"
            :key="child.value"
            type="button"
            class="nav-child"
            :class="{ active: currentSub === child.value }"
            @click="$emit('navigate', { page: item.page, sub: child.value })"
          >
            <span class="nav-child-dot"></span>
            <span class="nav-child-label">{{ child.label }}</span>
          </button>
        </div>
      </div>
    </nav>

    <div class="sidebar-footer" v-if="!collapsed">
      <span class="dot"></span>
      <div>
        <strong>系统运行中</strong>
        <small>数据工作区与智能模块已就绪</small>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getMenuCodes, hasRole } from '../api'
import { getModuleDefaultSub, getModuleSubStorageKey, isValidModuleSub, moduleNavigation } from '../config/moduleNavigation'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  currentPage: { type: String, default: 'student' }
})
const emit = defineEmits(['navigate'])

const route = useRoute()
const isPublicPage = computed(() => !!route.meta?.public)
const expandedPage = ref('')
const navMainRef = ref(null)

const visibleNavItems = computed(() => {
  const menuCodes = getMenuCodes()
  return moduleNavigation.filter(item => {
    if (item.adminOnly && !hasRole('admin')) return false
    if (!item.menuCode) return true  // 无权限要求，始终可见
    return menuCodes.has(item.menuCode)
  })
})

const currentSub = computed(() => {
  const page = String(route.name || '')
  const routeSub = String(route.query.sub || '')
  if (isValidModuleSub(page, routeSub)) return routeSub

  const storedSub = localStorage.getItem(getModuleSubStorageKey(page))
  if (isValidModuleSub(page, storedSub)) return storedSub

  return getModuleDefaultSub(page)
})

function isActivePage(page) {
  return props.currentPage === page
}

function hasChildren(item) {
  return Array.isArray(item.children) && item.children.length > 0
}

function showChildren(item) {
  return !props.collapsed && expandedPage.value === item.page && hasChildren(item)
}

function getTargetSub(item) {
  if (!hasChildren(item)) return ''
  const storedSub = localStorage.getItem(getModuleSubStorageKey(item.page))
  return isValidModuleSub(item.page, storedSub) ? storedSub : getModuleDefaultSub(item.page)
}

function handleNavigate(item) {
  if (hasChildren(item)) {
    // 有二级功能的模块也要能直接进入，避免侧栏折叠或子菜单未渲染时入口失效。
    if (!props.collapsed) {
      expandedPage.value = expandedPage.value === item.page ? '' : item.page
    }
    emit('navigate', { page: item.page, sub: getTargetSub(item) })
    return
  }
  emit('navigate', { page: item.page, sub: getTargetSub(item) })
}

function syncExpandedToCurrent(page = props.currentPage) {
  const currentItem = visibleNavItems.value.find(item => item.page === page)
  expandedPage.value = currentItem && hasChildren(currentItem) ? currentItem.page : ''
}

function scrollCurrentNavItemIntoView() {
  if (props.collapsed) return
  nextTick(() => {
    const nav = navMainRef.value
    const activeButton = nav?.querySelector?.('.nav-item.active')
    activeButton?.scrollIntoView({ block: 'nearest' })
  })
}

watch(
  () => props.currentPage,
  (page) => {
    syncExpandedToCurrent(page)
    scrollCurrentNavItemIntoView()
  },
  { immediate: true }
)

watch(
  () => props.collapsed,
  (collapsed) => {
    if (!collapsed) {
      syncExpandedToCurrent(props.currentPage)
      scrollCurrentNavItemIntoView()
    }
  }
)
</script>
