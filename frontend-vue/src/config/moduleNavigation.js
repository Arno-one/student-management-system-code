// 统一维护左侧模块与二级子功能，避免侧边栏和页面各写一份配置。
export const moduleNavigation = [
  {
    page: 'student',
    short: 'ST',
    label: '学生信息管理',
    desc: '档案录入、查询与状态维护',
    menuCode: 'student:page',
    children: [
      { value: 'st-create', label: '创建学生' },
      { value: 'st-query', label: '查询学生' },
      { value: 'st-op', label: '更新 / 删除 / 恢复学生' },
      { value: 'st-nl', label: '智能录入' },
      { value: 'st-nl-update', label: '智能修改' },
    ],
  },
  {
    page: 'score',
    short: 'SC',
    label: '考核成绩管理',
    desc: '单条、批量与区间查询',
    menuCode: 'score:page',
    children: [
      { value: 'sc-add', label: '新增成绩' },
      { value: 'sc-batch', label: '批量导入成绩' },
      { value: 'sc-op', label: '修改 / 删除成绩' },
      { value: 'sc-query', label: '查询成绩' },
      { value: 'sc-nl', label: '智能录入' },
    ],
  },
  {
    page: 'employment',
    short: 'EM',
    label: '就业信息管理',
    desc: 'offer、薪资与就业跟踪',
    menuCode: 'employment:page',
    children: [
      { value: 'em-create', label: '新建就业信息' },
      { value: 'em-query', label: '查询就业信息' },
      { value: 'em-op', label: '修改 / 删除 / 恢复就业信息' },
      { value: 'em-nl', label: '智能录入' },
    ],
  },
  {
    page: 'class',
    short: 'CL',
    label: '班级管理',
    desc: '班级建档与排期信息',
    menuCode: 'class:page',
    children: [
      { value: 'cl-save', label: '新增 / 修改班级' },
      { value: 'cl-query', label: '查询 / 删除班级' },
    ],
  },
  {
    page: 'teacher',
    short: 'TE',
    label: '教师管理',
    desc: '教师资料、导入与检索',
    menuCode: 'teacher:page',
    children: [
      { value: 'te-create', label: '新增教师' },
      { value: 'te-import', label: '批量导入（Excel）' },
      { value: 'te-query', label: '查询教师' },
      { value: 'te-op', label: '按 ID 查 / 更新教师' },
    ],
  },
  {
    page: 'statistics',
    short: 'BI',
    label: '统计分析',
    desc: '关键指标与业务汇总',
    menuCode: 'statistics:page',
    children: [
      { value: 'staGeStu', label: '年龄大于阈值的学生' },
      { value: 'staStuCount', label: '学生总数' },
      { value: 'staScoreGreater', label: '每次考试 ≥ 阈值分' },
      { value: 'staScoreFails', label: '2 次以上不及格' },
      { value: 'staClassAvg', label: '班级平均分' },
      { value: 'staTallSal', label: '最高薪资排行' },
      { value: 'staJobTime', label: '就业时长' },
      { value: 'staAvgClassJobTime', label: '班级平均就业时长' },
    ],
  },
  {
    page: 'work',
    short: 'AI',
    label: 'AI 作业模块',
    desc: '评价生成、对话与天气能力',
    menuCode: 'work:page',
    children: [
      { value: 'wk-eval', label: '学生评价（大模型生成）' },
      { value: 'wk-img', label: '文生图（通义万相）' },
      { value: 'wk-talk', label: '多轮记忆对话' },
      { value: 'wk-weather', label: '天气查询 / 经纬度解析' },
    ],
  },
  { page: 'email', short: 'ML', label: '邮件管理', desc: '智能生成与发送邮件', menuCode: 'email:page' },
  {
    page: 'nl2sql',
    short: 'D2',
    label: 'NL2SQL 智能问数',
    desc: '自然语言转 SQL 数据查询',
    menuCode: 'nl2sql:page',
    children: [
      { value: 'ns-query', label: '智能问数' },
      { value: 'ns-schema', label: '表结构概览' },
      { value: 'ns-history', label: '历史记录' },
    ],
  },
  { page: 'rag', short: 'RA', label: '四大名著知识库', desc: 'RAG 混合检索 + AI 问答' },
  { page: 'agent', short: 'AG', label: '智能 Agent 助手', desc: '学业导师 · 成绩查询 · 陪伴对话' },
  {
    page: 'system',
    short: 'SM',
    label: '系统管理',
    desc: '用户、角色与权限分配',
    menuCode: 'system:page',
    adminOnly: true,
    children: [
      { value: 'sys-users', label: '用户管理' },
      { value: 'sys-roles', label: '角色管理' },
      { value: 'sys-agent-monitor', label: 'Agent 监控' },
    ],
  },
]

export function getModuleNavItem(page) {
  return moduleNavigation.find(item => item.page === page) || null
}

export function getModuleSubOptions(page) {
  return getModuleNavItem(page)?.children || []
}

export function getModuleDefaultSub(page) {
  return getModuleSubOptions(page)[0]?.value || ''
}

export function getModuleSubStorageKey(page) {
  return `sub-${page}`
}

export function isValidModuleSub(page, subValue) {
  const value = String(subValue || '')
  return getModuleSubOptions(page).some(item => item.value === value)
}
