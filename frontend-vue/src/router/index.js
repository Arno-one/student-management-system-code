import { createRouter, createWebHashHistory } from 'vue-router'
import { apiState, clearAuth, hasRole, isLoggedIn, getMenuCodes } from '../api'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { title: '登录', public: true } },
  { path: '/', redirect: '/student' },
  { path: '/student', name: 'student', component: () => import('../views/StudentView.vue'), meta: { title: '学生信息管理', menuCode: 'student:page' } },
  { path: '/score', name: 'score', component: () => import('../views/ScoreView.vue'), meta: { title: '考核成绩管理', menuCode: 'score:page' } },
  { path: '/employment', name: 'employment', component: () => import('../views/EmploymentView.vue'), meta: { title: '就业信息管理', menuCode: 'employment:page' } },
  { path: '/class', name: 'class', component: () => import('../views/ClassView.vue'), meta: { title: '班级管理', menuCode: 'class:page' } },
  { path: '/teacher', name: 'teacher', component: () => import('../views/TeacherView.vue'), meta: { title: '教师管理', menuCode: 'teacher:page' } },
  { path: '/statistics', name: 'statistics', component: () => import('../views/StatisticsView.vue'), meta: { title: '统计分析', menuCode: 'statistics:page' } },
  { path: '/work', name: 'work', component: () => import('../views/WorkView.vue'), meta: { title: 'AI 作业模块', menuCode: 'work:page' } },
  { path: '/email', name: 'email', component: () => import('../views/EmailView.vue'), meta: { title: '邮件管理', menuCode: 'email:page' } },
  { path: '/nl2sql', name: 'nl2sql', component: () => import('../views/NL2SQLView.vue'), meta: { title: 'NL2SQL 智能问数', menuCode: 'nl2sql:page' } },
  { path: '/system', name: 'system', component: () => import('../views/SystemView.vue'), meta: { title: '系统管理', menuCode: 'system:page', adminOnly: true } }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

function getFirstAllowedPath() {
  const menuCodes = getMenuCodes()
  const first = routes.find(route => route.meta?.menuCode && menuCodes.has(route.meta.menuCode) && (!route.meta.adminOnly || hasRole('admin')))
  return first?.path || '/login'
}

router.beforeEach((to, from, next) => {
  if (to.meta?.public) {
    if (to.name === 'login' && isLoggedIn()) {
      next('/student')
      return
    }
    next()
    return
  }

  if (!isLoggedIn()) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  if (!apiState.user) {
    clearAuth()
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  const menuCodes = getMenuCodes()
  if (to.meta?.menuCode && !menuCodes.has(to.meta.menuCode)) {
    if (!menuCodes.size) {
      clearAuth()
      next({ name: 'login' })
      return
    }
    next(getFirstAllowedPath())
    return
  }

  if (to.meta?.adminOnly && !hasRole('admin')) {
    next(getFirstAllowedPath())
    return
  }

  next()
})

export default router
