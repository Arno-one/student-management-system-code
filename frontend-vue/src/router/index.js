import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/student' },
  { path: '/student', name: 'student', component: () => import('../views/StudentView.vue'), meta: { title: '学生信息管理' } },
  { path: '/score', name: 'score', component: () => import('../views/ScoreView.vue'), meta: { title: '考核成绩管理' } },
  { path: '/employment', name: 'employment', component: () => import('../views/EmploymentView.vue'), meta: { title: '就业信息管理' } },
  { path: '/class', name: 'class', component: () => import('../views/ClassView.vue'), meta: { title: '班级管理' } },
  { path: '/teacher', name: 'teacher', component: () => import('../views/TeacherView.vue'), meta: { title: '教师管理' } },
  { path: '/statistics', name: 'statistics', component: () => import('../views/StatisticsView.vue'), meta: { title: '统计分析' } },
  { path: '/work', name: 'work', component: () => import('../views/WorkView.vue'), meta: { title: 'AI 作业模块' } },
  { path: '/email', name: 'email', component: () => import('../views/EmailView.vue'), meta: { title: '邮件管理' } },
  { path: '/nl2sql', name: 'nl2sql', component: () => import('../views/NL2SQLView.vue'), meta: { title: 'NL2SQL 智能问数' } }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
