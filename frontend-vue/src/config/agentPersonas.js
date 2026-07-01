// Agent 角色前端兜底配置
// 即使 /agent/personas 接口暂时不可用，也保证角色列表和欢迎语可用。

export const fallbackAgentPersonas = [
  {
    id: 'academic_mentor',
    name: '学业导师',
    icon: '🎓',
    description: '温和鼓励的学业导师，擅长成绩分析与学习指导。',
  },
  {
    id: 'companion_head_teacher',
    name: '陪伴班主任',
    icon: '🌶',
    description: '共情陪伴型班主任，适合聊压力、拖延、考试焦虑和轻量计划。',
  },
  {
    id: 'xinge',
    name: '昕哥',
    icon: '😁',
    description: '爱鼓励人的好老师好兄弟，擅长复盘错误、讲清后果和下一步。',
  },
]

export const personaWelcomeTemplates = {
  academic_mentor: '你好，我是学业导师。可以帮你查成绩、拆学习问题、解释制度流程，也可以一起梳理你现在最该先做的事。',
  companion_head_teacher: '同学，先慢慢说，我在这儿。我可以陪你把压力、拖延、焦虑这些事一件件理清，也能马上陪你拆一个今天能完成的小计划。',
  xinge: '好兄弟，昕哥在。学习卡住了、错题想复盘、事情太乱想找个头绪，都可以直接甩给我，咱们一件件来，嘿嘿。',
}

export function getPersonaWelcomeText(personaId) {
  return personaWelcomeTemplates[personaId] || personaWelcomeTemplates.academic_mentor
}

// 欢迎语只在前端注入，不参与后端持久化与摘要生成。
export function createPersonaWelcomeMessage(personaId) {
  return {
    role: 'assistant',
    content: getPersonaWelcomeText(personaId),
    toolCalls: null,
    sources: null,
    cards: null,
    feedback: null,
    _streaming: false,
    _welcome: true,
  }
}
