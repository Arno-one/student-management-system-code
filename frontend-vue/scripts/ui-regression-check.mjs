import { spawnSync } from 'node:child_process'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'

const rootDir = process.cwd()
const srcDir = path.join(rootDir, 'src')
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
    ['RouteCard', readProjectFile('src', 'components', 'RouteCard.vue')],
    ['PoiListCard', readProjectFile('src', 'components', 'PoiListCard.vue')],
  ]

  for (const [name, content] of componentFiles) {
    // 卡片组件只能读取主题变量，不能直接改全局 theme-light/theme-dark，避免再次污染浅色主题背景。
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
    assertIncludes(content, 'RouteCard', `${name} 接入 route 卡片`)
    assertIncludes(content, 'PoiListCard', `${name} 接入 poi_list 卡片`)
    assertIncludes(content, "c.type === 'weather' && isCardVersionSupported(c)", `${name} 过滤 weather 卡片版本`)
    assertIncludes(content, "c.type === 'route' && isCardVersionSupported(c)", `${name} 过滤 route 卡片版本`)
    assertIncludes(content, "c.type === 'poi_list' && isCardVersionSupported(c)", `${name} 过滤 poi_list 卡片版本`)
    assertIncludes(content, 'card.card_version === 1', `${name} 只接受受支持卡片版本`)
    assertIncludes(content, 'fillRouteDraft', `${name} 支持 poi_list 去这里填充通勤输入`)
    assertNotMatches(content, /MapLocationCard|c\.type === ['"]map_location['"]/, `${name} 暂不渲染 map_location 预留卡片`)
    assertNotMatches(
      content,
      /v-for="[^"]*msg\.cards(?!\.filter)/,
      `${name} 不直接渲染未知 card type`,
      `${name} 存在未过滤的 msg.cards 渲染`,
    )
  }

  const routeCard = readProjectFile('src', 'components', 'RouteCard.vue')
  const weatherCard = readProjectFile('src', 'components', 'WeatherCard.vue')
  const poiListCard = readProjectFile('src', 'components', 'PoiListCard.vue')
  assertIncludes(routeCard, 'props.data || props.card?.data || {}', 'RouteCard 字段缺失时安全降级')
  assertIncludes(routeCard, 'Array.isArray(routeData.value.routes)', 'RouteCard 校验 routes 数组')
  assertIncludes(weatherCard, 'props.data || props.card?.data || {}', 'WeatherCard 字段缺失时安全降级')
  assertIncludes(weatherCard, 'Object.keys(weatherBlocks.value).length', 'WeatherCard 空数据不强制渲染')
  assertIncludes(poiListCard, 'props.data || props.card?.data || {}', 'PoiListCard 字段缺失时安全降级')
  assertIncludes(poiListCard, 'Array.isArray(poiData.value.items)', 'PoiListCard 校验 items 数组')
  assertIncludes(poiListCard, 'items.value.slice(0, 3)', 'PoiListCard compact 模式只展示前 3 条')
}

function checkCardProtocolDocumentation() {
  const protocolDoc = readFileSync(path.join(rootDir, '..', 'docs', 'Agent卡片协议v1.md'), 'utf8')
  assertIncludes(protocolDoc, '`weather`、`route`、`poi_list`', '卡片协议文档声明当前可渲染类型')
  assertIncludes(protocolDoc, '`map_location` | 预留，不实现', '卡片协议文档声明 map_location 仅预留')
  assertIncludes(protocolDoc, '字段缺失时组件做降级展示', '卡片协议文档声明字段降级策略')
  assertIncludes(protocolDoc, '未知 `type`、未知 `card_version` 必须安全忽略', '卡片协议文档声明未知卡片安全忽略')
  assertIncludes(protocolDoc, '普通模式最多展示 8 条，compact 模式最多展示 4 条', '卡片协议文档覆盖逐时天气展示边界')
  assertIncludes(protocolDoc, 'v2.3 默认 2000 米', '卡片协议文档覆盖 poi_list 默认半径')
  assertIncludes(protocolDoc, '主 Agent 最多展示 10 条', '卡片协议文档覆盖 poi_list 展示数量')
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
    // 等待态必须复用当前 assistant 消息，避免“全局 loading + streaming 消息”产生双头像。
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
  assertNotMatches(
    agentView,
    /agent-session-chip|agent-session-title|agent-session-time/,
    'AgentView 不再渲染横向会话 chip',
  )
  assertNotMatches(
    agentView,
    /s\.summary\s*\|\|\s*s\.title/,
    '历史摘要列表不回退显示 Agent 对话标题',
  )
}

function checkFloatingPersonaMemory() {
  const personaPrompt = readFileSync(path.join(rootDir, '..', 'agent_system', 'prompts', 'persona_prompt.py'), 'utf8')
  const agentView = readProjectFile('src', 'views', 'AgentView.vue')
  const floatingAgent = readProjectFile('src', 'components', 'FloatingAgent.vue')
  assertIncludes(personaPrompt, '"xinge"', '后端注册昕哥 persona')
  assertIncludes(personaPrompt, 'XINGE_PERSONA', '后端存在昕哥提示词')
  assertIncludes(agentView, 'personaTitle(p)', 'AgentView 角色选项显示 emoji 标识')
  assertIncludes(agentView, 'xinge', 'AgentView 支持昕哥示例和空态')
  assertIncludes(floatingAgent, "localStorage.getItem('floating-agent-persona')", 'FloatingAgent 读取 persona 偏好')
  assertIncludes(floatingAgent, "localStorage.setItem('floating-agent-persona'", 'FloatingAgent 保存 persona 偏好')
  assertIncludes(floatingAgent, 'persona: selectedPersona.value', 'FloatingAgent 发送时使用当前 persona')
  assertNotMatches(
    floatingAgent,
    /persona:\s*['"]academic_mentor['"]/,
    'FloatingAgent 不再硬编码默认 persona 发送',
  )
  assertIncludes(floatingAgent, 'companion_head_teacher', 'FloatingAgent 支持陪伴班主任空态')
  assertIncludes(floatingAgent, 'xinge', 'FloatingAgent 支持昕哥空态')
  assertIncludes(floatingAgent, 'personaTitle(item)', 'FloatingAgent 角色选项显示 emoji 标识')
}

function checkDistArtifacts() {
  if (!existsSync(distAssetsDir)) {
    record('dist 产物存在', false, '未找到 dist/assets')
    return
  }

  const cssFiles = readdirSync(distAssetsDir).filter(file => file.endsWith('.css'))
  const cssBundle = cssFiles.map(file => readFileSync(path.join(distAssetsDir, file), 'utf8')).join('\n')
  record('dist CSS 产物存在', cssFiles.length > 0, 'dist/assets 下没有 CSS 文件')
  assertNotMatches(
    cssBundle,
    /:global\([^)]*theme-(light|dark)/,
    '构建产物不包含 scoped 全局主题污染',
  )
}

function checkSidebarModuleChildrenNavigation() {
  const sidebar = readProjectFile('src', 'components', 'Sidebar.vue')
  const moduleNav = readProjectFile('src', 'config', 'moduleNavigation.js')

  assertIncludes(sidebar, "emit('navigate', { page: item.page, sub: getTargetSub(item) })", 'Sidebar 父模块点击可进入默认子功能')
  assertIncludes(sidebar, 'if (!props.collapsed)', 'Sidebar 折叠状态下不依赖子菜单展示')
  assertIncludes(moduleNav, "page: 'system'", '系统管理模块配置存在')
  assertIncludes(moduleNav, "value: 'sys-users'", '系统管理保留用户管理子功能')
  assertIncludes(moduleNav, "value: 'sys-roles'", '系统管理保留角色管理子功能')
  assertIncludes(moduleNav, "value: 'sys-agent-monitor'", '系统管理保留 Agent 监控子功能')
}

runBuild()
checkThemeIsolation()
checkCardProtocolRendering()
checkCardProtocolDocumentation()
checkWorkViewWeatherCardReuse()
checkLoadingSingleAvatar()
checkAgentSummarySidebar()
checkFloatingPersonaMemory()
checkSidebarModuleChildrenNavigation()
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
