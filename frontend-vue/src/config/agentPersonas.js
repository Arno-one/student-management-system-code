// Agent 角色前端兜底配置：
// 即使 /agent/personas 接口暂时不可用，也保证下拉选项可见。
export const fallbackAgentPersonas = [
  {
    id: 'academic_mentor',
    name: '学业导师',
    icon: '🎓',
    description: '温和鼓励的学业导师，擅长成绩分析与学习指导',
  },
  {
    id: 'companion_head_teacher',
    name: '陪伴班主任',
    icon: '🌿',
    description: '共情陪伴型班主任，适合聊压力、拖延、考试焦虑和轻量计划',
  },
  {
    id: 'xinge',
    name: '昕哥',
    icon: '😎',
    description: '爱鼓励人的好老师好兄弟，擅长复盘错误、讲清后果和下一步',
  },
]
