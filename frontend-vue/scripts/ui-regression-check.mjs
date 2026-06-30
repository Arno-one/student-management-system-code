import { spawnSync } from 'node:child_process'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'

const rootDir = process.cwd()
const distAssetsDir = path.join(rootDir, 'dist', 'assets')
const checks = []

function readProjectFile(...segments) {
  return readFileSync(path.join(rootDir, ...segments), 'utf8')
}

function record(name, passed, detail = '') {
  checks.push({ name, passed, detail })
}

function assertIncludes(content, needle, name, detail = '') {
  record(name, content.includes(needle), detail || `缺少片段：${needle}`)
}

function assertNotMatches(content, pattern, name, detail = '') {
  record(name, !pattern.test(content), detail || `命中不应出现的模式：${pattern}`)
}

function runBuild() {
  const viteCli = path.join(rootDir, 'node_modules', 'vite', 'bin', 'vite.js')
  const result = spawnSync(process.execPath, [viteCli, 'build'], {
    cwd: rootDir,
    stdio: 'inherit',
    shell: false,
  })
  record('前端生产构建通过', result.status === 0, result.error?.message || 'vite build 执行失败')
}

function checkThemeIsolation() {
  const componentFiles = [
    ['WeatherCard', readProjectFile('src', 'components', 'WeatherCard.vue')],
    ['ImageCard', readProjectFile('src', 'components', 'ImageCard.vue')],
    ['RouteCard', readProjectFile('src', 'components', 'RouteCard.vue')],
    ['PoiListCard', readProjectFile('src', 'components', 'PoiListCard.vue')],
    ['QuickToolPanel', readProjectFile('src', 'components', 'QuickToolPanel.vue')],
  ]

  for (const [name, content] of componentFiles) {
    assertNotMatches(
      content,
      /:global\([^)]*theme-(light|dark)|\.theme-(light|dark)/,
      `${name} 不覆盖全局主题类`,
      `${name} 中出现了全局主题选择器`,
    )
    assertIncludes(content, 'var(--panel', `${name} 使用主题变量`)
    assertIncludes(content, 'overflow: hidden', `${name} 卡片内容不会溢出外框`)
    assertIncludes(content, '@media (max-width: 680px)', `${name} 具备移动端约束`)
  }
}

function checkCardProtocolRendering() {
  const agentView = readProjectFile('src', 'views', 'AgentView.vue')
  const floatingAgent = readProjectFile('src', 'components', 'FloatingAgent.vue')

  for (const [name, content] of [['AgentView', agentView], ['FloatingAgent', floatingAgent]]) {
    assertIncludes(content, 'WeatherCard', `${name} 接入 weather 卡片`)
    assertIncludes(content, 'ImageCard', `${name} 接入 image 卡片`)
    assertIncludes(content, 'RouteCard', `${name} 接入 route 卡片`)
    assertIncludes(content, 'PoiListCard', `${name} 接入 poi_list 卡片`)
    assertIncludes(content, "c.type === 'weather' && isCardVersionSupported(c)", `${name} 过滤 weather 卡片版本`)
    assertIncludes(content, "c.type === 'image' && isCardVersionSupported(c)", `${name} 过滤 image 卡片版本`)
    assertIncludes(content, "c.type === 'route' && isCardVersionSupported(c)", `${name} 过滤 route 卡片版本`)
    assertIncludes(content, "c.type === 'poi_list' && isCardVersionSupported(c)", `${name} 过滤 poi_list 卡片版本`)
    assertIncludes(content, 'card.card_version === 1', `${name} 只接受受支持卡片版本`)
    assertIncludes(content, 'fillRouteDraft', `${name} 支持 poi_list 去这里填入通勤输入`)
    assertIncludes(content, 'regenerateImage', `${name} 支持 image 卡片重新生成`)
    assertNotMatches(content, /MapLocationCard|c\.type === ['"]map_location['"]/, `${name} 暂不渲染 map_location 预留卡片`)
    assertNotMatches(
      content,
      /v-for="[^"]*msg\.cards(?!\.filter)/,
      `${name} 不直接渲染未知 card type`,
      `${name} 存在未过滤的 msg.cards 渲染`,
    )
  }

  const weatherCard = readProjectFile('src', 'components', 'WeatherCard.vue')
  const imageCard = readProjectFile('src', 'components', 'ImageCard.vue')
  const routeCard = readProjectFile('src', 'components', 'RouteCard.vue')
  const poiListCard = readProjectFile('src', 'components', 'PoiListCard.vue')

  assertIncludes(weatherCard, 'props.data || props.card?.data || {}', 'WeatherCard 字段缺失时安全降级')
  assertIncludes(weatherCard, 'Object.keys(weatherBlocks.value).length', 'WeatherCard 空数据不强制渲染')
  assertIncludes(imageCard, 'props.data || props.card?.data || {}', 'ImageCard 字段缺失时安全降级')
  assertIncludes(imageCard, "emit('regenerate'", 'ImageCard 支持重新生成事件')
  assertIncludes(imageCard, 'navigator.clipboard?.writeText', 'ImageCard 支持复制提示词和链接')
  assertIncludes(routeCard, 'props.data || props.card?.data || {}', 'RouteCard 字段缺失时安全降级')
  assertIncludes(routeCard, 'Array.isArray(routeData.value.routes)', 'RouteCard 校验 routes 数组')
  assertIncludes(poiListCard, 'props.data || props.card?.data || {}', 'PoiListCard 字段缺失时安全降级')
  assertIncludes(poiListCard, 'Array.isArray(poiData.value.items)', 'PoiListCard 校验 items 数组')
  assertIncludes(poiListCard, 'items.value.slice(0, 3)', 'PoiListCard compact 模式只展示前 3 条')
}

function checkCardProtocolDocumentation() {
  const protocolDoc = readFileSync(path.join(rootDir, '..', 'docs', 'Agent卡片协议v1.md'), 'utf8')
  assertIncludes(protocolDoc, '`weather`、`image`、`route`、`poi_list`', '卡片协议文档声明当前可渲染类型')
  assertIncludes(protocolDoc, '`image` | 已实现 | `image_tool` | `frontend-vue/src/components/ImageCard.vue`', '卡片协议文档声明 image 卡片接线')
  assertIncludes(protocolDoc, '`map_location` | 预留，不实现', '卡片协议文档声明 map_location 仅预留')
  assertIncludes(protocolDoc, '字段缺失时组件做降级展示', '卡片协议文档声明字段降级策略')
  assertIncludes(protocolDoc, '未知 `type`、未知 `card_version` 必须安全忽略', '卡片协议文档声明未知卡片安全忽略')
  assertIncludes(protocolDoc, '普通模式最多展示 8 条，compact 模式最多展示 4 条', '卡片协议文档覆盖逐时天气展示边界')
  assertIncludes(protocolDoc, 'v2.3 默认 2000 米', '卡片协议文档覆盖 poi_list 默认半径')
  assertIncludes(protocolDoc, '单个 Agent 最多展示 10 条', '卡片协议文档覆盖 poi_list 展示数量')
  assertIncludes(protocolDoc, '重新生成', '卡片协议文档覆盖 image 卡片操作')
  assertIncludes(protocolDoc, '不新增 `MapLocationCard.vue`', '卡片协议文档约束本版本不实现 map_location 组件')
}

function checkWorkViewWeatherCardReuse() {
  const workView = readProjectFile('src', 'views', 'WorkView.vue')
  const weatherCard = readProjectFile('src', 'components', 'WeatherCard.vue')
  assertIncludes(workView, "import WeatherCard from '../components/WeatherCard.vue'", 'WorkView 引入 WeatherCard')
  assertIncludes(workView, '<WeatherCard v-if="weatherCardData"', 'WorkView 天气结果复用 WeatherCard')
  assertIncludes(workView, 'buildWeatherCardData', 'WorkView 将接口结果转换为天气卡片协议')
  assertNotMatches(workView, /v-html="weatherHtml"/, 'WorkView 天气结果不再使用 v-html')
  assertNotMatches(workView, /function renderWeather\(/, 'WorkView 不再维护旧天气 HTML 拼接函数')
  assertIncludes(weatherCard, "weatherBlocks.value['逐时预报']", 'WeatherCard 支持逐时预报数据块')
  assertIncludes(weatherCard, 'agent-weather-hours', 'WeatherCard 渲染逐时预报网格')
}

function checkLoadingSingleAvatar() {
  const files = [
    ['AgentView', readProjectFile('src', 'views', 'AgentView.vue')],
    ['FloatingAgent', readProjectFile('src', 'components', 'FloatingAgent.vue')],
  ]

  for (const [name, content] of files) {
    assertIncludes(content, "role: 'assistant'", `${name} 创建 assistant 占位消息`)
    assertIncludes(content, '_streaming: true', `${name} 使用 streaming 占位状态`)
    assertIncludes(content, "msg.role === 'assistant' && msg._streaming && !msg.content", `${name} loading 绑定当前 assistant 消息`)
    assertNotMatches(
      content,
      /class="(?:agent|float-agent)-msg[^"]*"[\s\S]{0,220}v-if="loading"/,
      `${name} 不新增独立 loading 消息`,
      `${name} 中疑似存在独立 loading 消息块`,
    )
  }
}

function checkAgentSummarySidebar() {
  const agentView = readProjectFile('src', 'views', 'AgentView.vue')
  assertIncludes(agentView, 'class="agent-workspace"', 'AgentView 使用左右工作区布局')
  assertIncludes(agentView, 'class="agent-summary-panel"', 'AgentView 右侧历史摘要栏存在')
  assertIncludes(agentView, 'sessionSummary(s)', '历史会话只渲染摘要文本')
  assertNotMatches(agentView, /agent-session-chip|agent-session-title|agent-session-time/, 'AgentView 不再渲染横向会话 chip')
  assertNotMatches(agentView, /s\.summary\s*\|\|\s*s\.title/, '历史摘要列表不回退显示 Agent 对话标题')
}

function checkFloatingPersonaMemory() {
  const personaConfig = readProjectFile('src', 'config', 'agentPersonas.js')
  const personaPrompt = readFileSync(path.join(rootDir, '..', 'agent_system', 'prompts', 'persona_prompt.py'), 'utf8')
  const agentView = readProjectFile('src', 'views', 'AgentView.vue')
  const floatingAgent = readProjectFile('src', 'components', 'FloatingAgent.vue')
  assertIncludes(personaPrompt, '"xinge"', '后端注册昕哥 persona')
  assertIncludes(personaPrompt, 'XINGE_PERSONA', '后端存在昕哥提示词')
  assertIncludes(personaConfig, 'personaWelcomeTemplates', '前端 persona 配置包含欢迎语模板')
  assertIncludes(personaConfig, 'createPersonaWelcomeMessage', '前端提供欢迎语消息工厂')
  assertIncludes(agentView, 'personaTitle(p)', 'AgentView 角色选项显示 emoji 标识')
  assertIncludes(agentView, 'xinge', 'AgentView 支持昕哥示例和空态')
  assertIncludes(agentView, 'createPersonaWelcomeMessage', 'AgentView 接入 persona 欢迎语工厂')
  assertIncludes(agentView, '_welcome', 'AgentView 标记前端欢迎语消息')
  assertIncludes(agentView, 'syncWelcomeMessage(true)', 'AgentView 新会话注入欢迎语')
  assertIncludes(agentView, "currentPersona.value?.icon || 'AI'", 'AgentView 助手头像按 persona emoji 回退 AI')
  assertNotMatches(agentView, /msg\.role === 'user' \? '我' : '师'/, 'AgentView 不再使用固定“师”头像')
  assertIncludes(floatingAgent, "localStorage.getItem('floating-agent-persona')", 'FloatingAgent 读取 persona 偏好')
  assertIncludes(floatingAgent, "localStorage.setItem('floating-agent-persona'", 'FloatingAgent 保存 persona 偏好')
  assertIncludes(floatingAgent, 'persona: selectedPersona.value', 'FloatingAgent 发送时使用当前 persona')
  assertNotMatches(floatingAgent, /persona:\s*['"]academic_mentor['"]/, 'FloatingAgent 不再硬编码默认 persona 发送')
  assertIncludes(floatingAgent, 'companion_head_teacher', 'FloatingAgent 支持陪伴班主任空态')
  assertIncludes(floatingAgent, 'xinge', 'FloatingAgent 支持昕哥空态')
  assertIncludes(floatingAgent, 'personaTitle(item)', 'FloatingAgent 角色选项显示 emoji 标识')
  assertIncludes(floatingAgent, 'createPersonaWelcomeMessage', 'FloatingAgent 接入 persona 欢迎语工厂')
  assertIncludes(floatingAgent, '_welcome', 'FloatingAgent 标记前端欢迎语消息')
  assertIncludes(floatingAgent, 'syncWelcomeMessage(true)', 'FloatingAgent 空会话注入欢迎语')
  assertIncludes(floatingAgent, "currentPersona.value?.icon || 'AI'", 'FloatingAgent 助手头像按 persona emoji 回退 AI')
  assertNotMatches(floatingAgent, /msg\.role === 'user' \? '我' : 'AI'/, 'FloatingAgent 不再固定使用 AI 头像')
}

function checkQuickToolPanel() {
  const quickToolConfig = readProjectFile('src', 'config', 'agentQuickTools.js')
  const quickToolPanel = readProjectFile('src', 'components', 'QuickToolPanel.vue')
  const agentView = readProjectFile('src', 'views', 'AgentView.vue')
  const floatingAgent = readProjectFile('src', 'components', 'FloatingAgent.vue')

  assertIncludes(quickToolConfig, 'agentQuickTools', '快捷工具配置存在')
  assertIncludes(quickToolConfig, 'NL2SQL智能问数', '快捷工具配置包含 NL2SQL 入口')
  assertIncludes(quickToolConfig, "emoji: '🎨'", '快捷工具配置包含文生图 emoji')
  assertIncludes(quickToolConfig, "emoji: '📊'", '快捷工具配置包含 NL2SQL emoji')
  assertIncludes(quickToolConfig, 'buildQuickToolTemplate', '快捷工具配置包含模板生成器')
  assertIncludes(quickToolConfig, 'buildQuickToolMessage', '快捷工具配置包含消息生成器')
  assertIncludes(quickToolPanel, '快捷工具面板', '快捷工具面板组件存在折叠标题')
  assertIncludes(quickToolPanel, 'tool.emoji || tool.badge', '快捷工具面板优先展示 emoji')
  assertIncludes(quickToolPanel, "tool.mode === 'inline_send'", '快捷工具面板支持面板内直接发送')
  assertIncludes(quickToolPanel, "tool.mode === 'fill_template'", '快捷工具面板支持填入模板')
  assertIncludes(quickToolPanel, 'buildQuickToolTemplate(tool.id)', '快捷工具面板填入模板接线存在')
  assertIncludes(quickToolPanel, 'buildQuickToolMessage(tool.id, drafts[tool.id])', '快捷工具面板直接发送接线存在')
  assertIncludes(quickToolPanel, '.agent-quick-panel.compact .quick-panel-body', '快捷工具面板 compact 模式限制高度')
  assertIncludes(quickToolPanel, 'overflow-y: auto', '快捷工具面板 compact 模式支持纵向滚动')
  assertIncludes(agentView, 'QuickToolPanel', 'AgentView 接入快捷工具面板')
  assertIncludes(agentView, 'applyQuickToolTemplate', 'AgentView 支持快捷工具模板回填')
  assertIncludes(agentView, 'submitQuickTool', 'AgentView 支持快捷工具直接发送')
  assertIncludes(floatingAgent, 'QuickToolPanel', 'FloatingAgent 接入快捷工具面板')
  assertIncludes(floatingAgent, 'compact', 'FloatingAgent 以 compact 模式接入快捷工具面板')
  assertIncludes(floatingAgent, 'applyQuickToolTemplate', 'FloatingAgent 支持快捷工具模板回填')
  assertIncludes(floatingAgent, 'submitQuickTool', 'FloatingAgent 支持快捷工具直接发送')
}

function checkSidebarModuleChildrenNavigation() {
  const sidebar = readProjectFile('src', 'components', 'Sidebar.vue')
  const moduleNav = readProjectFile('src', 'config', 'moduleNavigation.js')
  const styles = readProjectFile('src', 'assets', 'styles.css')

  assertIncludes(sidebar, "emit('navigate', { page: item.page, sub: getTargetSub(item) })", 'Sidebar 父模块点击可进入默认子功能')
  assertIncludes(sidebar, 'sidebar-rail', 'Sidebar 折叠态使用独立 emoji 列表')
  assertIncludes(sidebar, 'data-sidebar-rail', 'Sidebar 折叠态提供独立 rail 标识')
  assertIncludes(sidebar, 'data-sidebar-main', 'Sidebar 展开态提供主导航标识')
  assertIncludes(sidebar, 'scrollIntoView', 'Sidebar 展开时滚动定位当前模块')
  assertIncludes(sidebar, "item.emoji || item.short", 'Sidebar 模块图标优先展示 emoji')
  assertIncludes(sidebar, "ico--emoji", 'Sidebar 为 emoji 图标提供独立样式类')
  assertIncludes(moduleNav, "page: 'system'", '系统管理模块配置存在')
  assertIncludes(moduleNav, "emoji: '🧑‍🎓'", '模块导航配置包含学生管理 emoji')
  assertIncludes(moduleNav, "emoji: '⚙️'", '模块导航配置包含系统管理 emoji')
  assertIncludes(moduleNav, "value: 'sys-users'", '系统管理保留用户管理子功能')
  assertIncludes(moduleNav, "value: 'sys-roles'", '系统管理保留角色管理子功能')
  assertIncludes(moduleNav, "value: 'sys-agent-monitor'", '系统管理保留 Agent 监控子功能')
  assertIncludes(styles, '.ico--emoji', '全局样式包含侧栏 emoji 图标样式')
  assertIncludes(styles, '.sidebar.collapsed .ico--emoji', '折叠态侧栏包含 emoji 图标样式')
  assertIncludes(styles, '.sidebar-rail', '全局样式包含折叠态 rail 列表样式')
  assertIncludes(styles, '.rail-item', '全局样式包含折叠态 rail 图标项样式')
}

function checkAgentMonitorDashboardOptimization() {
  const systemView = readProjectFile('src', 'views', 'SystemView.vue')
  const agentApi = readFileSync(path.join(rootDir, '..', 'agent_system', 'api', 'agent_api.py'), 'utf8')
  const databaseFile = readFileSync(path.join(rootDir, '..', 'database.py'), 'utf8')
  const agentTaskModel = readFileSync(path.join(rootDir, '..', 'model', 'AgentTask.py'), 'utf8')

  assertIncludes(systemView, '/agent/admin/dashboard', 'SystemView 使用监控聚合 dashboard 接口')
  assertIncludes(agentApi, '@agent_router.get("/admin/dashboard"', '后端提供 Agent 监控聚合 dashboard 接口')
  assertIncludes(agentApi, '_build_dashboard_payload', '后端存在 Agent 监控聚合构建器')
  assertIncludes(databaseFile, 'idx_agent_task_create_time', '数据库初始化补齐 AgentTask create_time 索引')
  assertIncludes(databaseFile, 'idx_agent_task_status', '数据库初始化补齐 AgentTask status 索引')
  assertIncludes(databaseFile, 'idx_agent_task_intent', '数据库初始化补齐 AgentTask intent 索引')
  assertIncludes(agentTaskModel, 'intent = Column(String(50), index=True', 'AgentTask intent 字段声明索引')
  assertIncludes(agentTaskModel, 'status = Column(String(30), index=True', 'AgentTask status 字段声明索引')
  assertIncludes(agentTaskModel, 'create_time = Column(DateTime, index=True', 'AgentTask create_time 字段声明索引')
  assertIncludes(systemView, "() => sub.value", 'SystemView 监听系统子功能切换')
  assertIncludes(systemView, "if (nextSub === 'sys-agent-monitor')", 'SystemView 进入 Agent 监控页自动加载')
}

function checkWorkspaceBrandTone() {
  const sidebar = readProjectFile('src', 'components', 'Sidebar.vue')
  const topbar = readProjectFile('src', 'components', 'TopBar.vue')
  assertIncludes(sidebar, 'Campus AI Workspace', '侧栏品牌区使用统一英文标签')
  assertIncludes(sidebar, '校园智能工作台', '侧栏品牌区使用统一中文标题')
  assertIncludes(sidebar, '统一承载学生、教务、统计与智能 Agent 能力。', '侧栏品牌区使用统一描述文案')
  assertIncludes(topbar, 'Campus AI Workspace', '顶部标题使用统一英文标签')
  assertIncludes(topbar, '统一业务工作台', '顶部标题使用统一胶囊文案')
}

function checkGlobalEnterSubmit() {
  const app = readProjectFile('src', 'App.vue')
  const helpers = readProjectFile('src', 'utils', 'helpers.js')
  assertIncludes(app, "import { initGlobalEnterSubmit } from './utils/helpers'", 'App 接入全局回车提交初始化')
  assertIncludes(app, 'initGlobalEnterSubmit()', 'App 启动时初始化全局回车提交')
  assertIncludes(helpers, 'export function initGlobalEnterSubmit()', 'helpers 提供全局回车提交初始化函数')
  assertIncludes(helpers, '.actions', '全局回车提交覆盖常规操作区')
  assertIncludes(helpers, '.agent-monitor-filters', '全局回车提交覆盖监控筛选区')
  assertIncludes(helpers, '.rag-input-area', '全局回车提交保留聊天类文本域特例')
}

function checkDistArtifacts() {
  if (!existsSync(distAssetsDir)) {
    record('dist 产物存在', false, '未找到 dist/assets')
    return
  }

  const cssFiles = readdirSync(distAssetsDir).filter(file => file.endsWith('.css'))
  const cssBundle = cssFiles.map(file => readFileSync(path.join(distAssetsDir, file), 'utf8')).join('\n')
  record('dist CSS 产物存在', cssFiles.length > 0, 'dist/assets 下没有 CSS 文件')
  assertNotMatches(cssBundle, /:global\([^)]*theme-(light|dark)/, '构建产物不包含 scoped 全局主题污染')
}

runBuild()
checkThemeIsolation()
checkCardProtocolRendering()
checkCardProtocolDocumentation()
checkWorkViewWeatherCardReuse()
checkLoadingSingleAvatar()
checkAgentSummarySidebar()
checkFloatingPersonaMemory()
checkQuickToolPanel()
checkSidebarModuleChildrenNavigation()
checkWorkspaceBrandTone()
checkAgentMonitorDashboardOptimization()
checkGlobalEnterSubmit()
checkDistArtifacts()

const failed = checks.filter(item => !item.passed)
for (const item of checks) {
  const mark = item.passed ? 'PASS' : 'FAIL'
  console.log(`${mark} ${item.name}${item.passed ? '' : `：${item.detail}`}`)
}

if (failed.length) {
  console.error(`UI 回归检查失败：${failed.length}/${checks.length}`)
  process.exit(1)
}

console.log(`UI 回归检查通过：${checks.length}/${checks.length}`)
