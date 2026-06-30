export const agentQuickTools = [
  {
    id: 'image_generation',
    label: '文生图',
    emoji: '🎨',
    badge: 'IMG',
    mode: 'inline_send',
    hint: '直接描述想生成的画面',
    inputPlaceholder: '例如：生成一张校园学习海报，暖色调',
    submitLabel: '生成',
  },
  {
    id: 'weather',
    label: '天气',
    emoji: '🌤️',
    badge: 'WTH',
    mode: 'fill_template',
    hint: '填入天气查询模板',
  },
  {
    id: 'commute',
    label: '通勤',
    emoji: '🧭',
    badge: 'TRP',
    mode: 'fill_template',
    hint: '填入通勤规划模板',
  },
  {
    id: 'nearby',
    label: '周边',
    emoji: '📍',
    badge: 'POI',
    mode: 'fill_template',
    hint: '填入周边服务模板',
  },
  {
    id: 'email',
    label: '邮件',
    emoji: '📧',
    badge: 'MAIL',
    mode: 'fill_template',
    hint: '填入邮件草稿模板',
  },
  {
    id: 'nl2sql',
    label: 'NL2SQL智能问数',
    emoji: '📊',
    badge: 'SQL',
    mode: 'inline_send',
    hint: '直接输入你想查的数据问题',
    inputPlaceholder: '例如：统计近30天请假人数',
    submitLabel: '提问',
  },
]

export function buildQuickToolTemplate(toolId) {
  const templates = {
    weather: '帮我查一下 [请补充城市/地点] 的天气。',
    commute: '从 [请补充起点] 到 [请补充终点] 怎么去？',
    nearby: '[请补充地点] 附近有什么 [请补充服务类型]？',
    email: '帮我写一封邮件给 [请补充收件人]，主题是 [请补充主题]，内容说明 [请补充事项]。',
  }
  return templates[toolId] || ''
}

export function buildQuickToolMessage(toolId, input) {
  const text = String(input || '').trim()
  if (!text) return ''
  if (toolId === 'image_generation') return `请帮我生成一张图片：${text}`
  if (toolId === 'nl2sql') return `请用 NL2SQL 智能问数帮我查询：${text}`
  return text
}
