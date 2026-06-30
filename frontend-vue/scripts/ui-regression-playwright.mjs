import { spawn } from 'node:child_process'
import http from 'node:http'
import path from 'node:path'
import process from 'node:process'
import { chromium } from '@playwright/test'

const rootDir = process.cwd()
const previewUrl = 'http://127.0.0.1:4173'
const apiBase = 'http://localhost:8088'

const academicWelcome = '你好，我是学业导师。'
const xingeWelcome = '好兄弟，昕哥在。'

const mockUser = {
  username: 'admin',
  real_name: '管理员',
  roles: [{ role_code: 'admin' }],
  menus: [
    { permission_code: 'student:page' },
    { permission_code: 'score:page' },
    { permission_code: 'employment:page' },
    { permission_code: 'class:page' },
    { permission_code: 'teacher:page' },
    { permission_code: 'statistics:page' },
    { permission_code: 'work:page' },
    { permission_code: 'email:page' },
    { permission_code: 'nl2sql:page' },
    { permission_code: 'system:page' },
  ],
  permissions: ['work:use'],
}

const mockPersonas = [
  { id: 'academic_mentor', name: '学业导师', icon: '🎓', description: '帮助学生处理学习与校园问题' },
  { id: 'companion_head_teacher', name: '陪伴班主任', icon: '🌶', description: '适合聊压力、拖延与焦虑' },
  { id: 'xinge', name: '昕哥', icon: '😁', description: '擅长复盘错误、鼓劲打气和拆下一步' },
]

const mockSessions = [
  {
    id: 101,
    title: 'Agent 对话',
    summary: '用户先查通勤，再顺手生成了一张校园学习海报风格图片。',
    update_time: '2026-06-27T15:35:00',
    create_time: '2026-06-27T15:34:00',
  },
  {
    id: 100,
    title: 'Agent 对话',
    summary: '用户查询宝安天气，并确认未来有降雨提醒。',
    update_time: '2026-06-27T12:13:00',
    create_time: '2026-06-27T12:12:00',
  },
]

const mockSessionMessages = {
  101: [
    { role: 'user', content: '历史会话里的用户消息' },
    { role: 'assistant', reply: '历史会话里的真实回复', metadata: { tool_calls: null, sources: null, cards: null } },
  ],
  100: [
    { role: 'user', content: '今天宝安天气怎么样' },
    { role: 'assistant', reply: '今天多云，出门记得带伞。', metadata: { tool_calls: null, sources: null, cards: null } },
  ],
}

const mockAgentDashboard = {
  metrics: {
    window_days: 7,
    total_tasks: 8,
    success_rate: 87.5,
    success_count: 6,
    partial_success_count: 1,
    clarification_count: 0,
    empty_count: 1,
    error_count: 0,
    cancelled_count: 0,
    awaiting_hitl_count: 0,
    running_count: 0,
    avg_duration_ms: 1320,
    p50_duration_ms: 980,
    p99_duration_ms: 2840,
    feedback_count: 3,
    positive_rate: 66.67,
    negative_rate: 0,
  },
  timeseries: [
    { date: '2026-06-23', total: 1, error: 0, avg_duration_ms: 880 },
    { date: '2026-06-24', total: 1, error: 0, avg_duration_ms: 910 },
    { date: '2026-06-25', total: 2, error: 0, avg_duration_ms: 1180 },
    { date: '2026-06-26', total: 1, error: 0, avg_duration_ms: 1020 },
    { date: '2026-06-27', total: 2, error: 0, avg_duration_ms: 1390 },
    { date: '2026-06-28', total: 1, error: 0, avg_duration_ms: 1510 },
    { date: '2026-06-29', total: 1, error: 0, avg_duration_ms: 1760 },
  ],
  intents: [
    { intent: 'commute_plan', total: 4, avg_duration_ms: 1260 },
    { intent: 'nearby_service', total: 2, avg_duration_ms: 980 },
  ],
  tools: [
    { tool_name: 'commute_plan_tool', total: 4, success: 3, partial_success: 1, clarification: 0, empty: 0, error: 0, failure_rate: 0 },
    { tool_name: 'nearby_service_tool', total: 2, success: 1, partial_success: 0, clarification: 0, empty: 1, error: 0, failure_rate: 0 },
  ],
  providers: [
    { provider: 'tencent_mcp', total: 5, fallback_count: 0, empty: 0, error: 0, fallback_rate: 0, empty_rate: 0, failure_rate: 0 },
    { provider: 'tencent_rest_fallback', total: 1, fallback_count: 1, empty: 1, error: 0, fallback_rate: 100, empty_rate: 100, failure_rate: 0 },
  ],
  feedback_reasons: [
    { reason: '地图定位', count: 1, examples: [{ task_id: 901, intent: 'commute_plan', comment: '宝安定位不准确', message: '从宝安到龙岗怎么走' }] },
  ],
  mcp_health: {
    enabled: true,
    connected: true,
    tool_count: 4,
    last_success_at: '2026-06-29 09:30:00',
  },
}

const mockAgentMonitorTasks = [
  {
    id: 901,
    create_time: '2026-06-29T09:20:00',
    user_id: 'admin',
    persona: 'academic_mentor',
    intent: 'commute_plan',
    status: 'success',
    total_duration_ms: 1240,
    tool_calls: [{ tool_name: 'commute_plan_tool', status: 'success' }],
    tool_monitoring: { commute_plan_tool: { provider: 'tencent_mcp', status: 'success', result_count: 1 } },
    cards: [{ type: 'route', card_version: 1 }],
    tool_summary: 'commute_plan_tool: success',
    provider_summary: 'commute_plan_tool: tencent_mcp，1条',
    card_summary: 'route×1',
    feedback_rating: null,
    feedback_comment: null,
    original_message: '从宝安到龙岗怎么走',
  },
]

const results = []

function pass(name) {
  results.push({ name, passed: true })
  console.log(`PASS ${name}`)
}

function fail(name, error) {
  results.push({ name, passed: false, error })
  console.error(`FAIL ${name}：${error?.message || error}`)
}

function apiOk(data) {
  return { code: 200, msg: 'ok', data }
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function waitForPreview(timeoutMs = 15000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    const ok = await new Promise(resolve => {
      const req = http.get(previewUrl, res => {
        res.resume()
        resolve(res.statusCode && res.statusCode < 500)
      })
      req.on('error', () => resolve(false))
      req.setTimeout(1000, () => {
        req.destroy()
        resolve(false)
      })
    })
    if (ok) return
    await wait(250)
  }
  throw new Error('Vite preview 启动超时')
}

function startPreview() {
  const viteCli = path.join(rootDir, 'node_modules', 'vite', 'bin', 'vite.js')
  const child = spawn(process.execPath, [viteCli, 'preview', '--host', '127.0.0.1', '--port', '4173'], {
    cwd: rootDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
  })

  child.stdout.on('data', chunk => process.stdout.write(`[preview] ${chunk}`))
  child.stderr.on('data', chunk => process.stderr.write(`[preview] ${chunk}`))
  return child
}

async function stopPreview(child) {
  if (!child || child.killed) return
  child.kill()
  await wait(300)
  if (!child.killed) child.kill('SIGKILL')
}

async function mockAgentApi(page) {
  await page.route(`${apiBase}/auth/me`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk(mockUser)),
  }))

  await page.route(`${apiBase}/agent/personas`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk(mockPersonas)),
  }))

  await page.route(`${apiBase}/agent/sessions`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk(mockSessions)),
  }))

  await page.route(new RegExp(`${apiBase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/agent/sessions/\\d+/messages`), route => {
    const url = new URL(route.request().url())
    const match = url.pathname.match(/\/agent\/sessions\/(\d+)\/messages$/)
    const sessionId = match ? Number(match[1]) : 0
    const data = mockSessionMessages[sessionId] || []
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(apiOk(data)),
    })
  })

  await page.route(`${apiBase}/agent/chat/stream`, async route => {
    await wait(300)
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream; charset=utf-8',
      body: buildSseBody(),
    })
  })

  await page.route(`${apiBase}/system/users**`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk([])),
  }))

  await page.route(`${apiBase}/system/roles**`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk([])),
  }))

  await page.route(`${apiBase}/system/permissions`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk([])),
  }))

  await page.route(`${apiBase}/agent/admin/dashboard**`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk(mockAgentDashboard)),
  }))

  await page.route(`${apiBase}/agent/admin/tasks**`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk(mockAgentMonitorTasks)),
  }))
}

function buildSseBody() {
  const weatherCard = {
    type: 'weather',
    card_version: 1,
    data: {
      provider: 'tencent_rest_fallback',
      location_text: '龙岗',
      weather: {
        实时天气: {
          infos: {
            weather: '多云',
            temperature: 28,
            wind_direction: '东南风',
            wind_power: '2级',
            humidity: 66,
          },
        },
      },
    },
  }

  const imageCard = {
    type: 'image',
    card_version: 1,
    data: {
      provider: 'qwen_image',
      model: 'qwen-image-2.0-pro',
      prompt: '生成一张校园学习海报风格插画，暖色调，书桌、台灯、笔记本清晰可见',
      image_url: 'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=1200&q=80',
    },
  }

  const routeCard = {
    type: 'route',
    card_version: 1,
    data: {
      provider: 'tencent_mcp',
      status: 'success',
      origin_text: '宝安',
      destination_text: '龙岗',
      weather_reminder: '天气建议暂不可用，路线规划结果不受影响。',
      routes: [
        {
          mode: 'transit',
          label: '公交/地铁',
          success: true,
          summary: '公交/地铁预计耗时 1 小时 30 分钟，距离 55.0 公里。',
          duration_text: '1 小时 30 分钟',
          distance_text: '55.0 公里',
        },
      ],
    },
  }

  const poiListCard = {
    type: 'poi_list',
    card_version: 1,
    data: {
      provider: 'tencent_mcp',
      query: '餐饮',
      radius_meters: 2000,
      center: { name: '腾讯滨海大厦', address: '深圳市南山区海天二路', lat: 22.53, lng: 113.93 },
      items: [
        { id: 'p1', name: '南山餐厅一号', category: '餐饮', address: '深圳市南山区海天一路 1 号', distance_meters: 180, source: 'tencent_map' },
        { id: 'p2', name: '滨海简餐', category: '餐饮', address: '深圳市南山区海天二路 2 号', distance_meters: 320, source: 'tencent_map' },
        { id: 'p3', name: '软件园咖啡', category: '餐饮', address: '深圳市南山区科技园 3 号', distance_meters: 860, source: 'tencent_map' },
        { id: 'p4', name: '第四条仅主 Agent 展示', category: '餐饮', address: '深圳市南山区科技园 4 号', distance_meters: 1200, source: 'tencent_map' },
      ],
    },
  }

  const ignoredCard = {
    type: 'unknown_debug_card',
    card_version: 1,
    data: { title: '不应该出现在页面中' },
  }

  const unsupportedRouteCard = {
    type: 'route',
    card_version: 999,
    data: {
      origin_text: '旧协议起点',
      destination_text: '旧协议终点',
      routes: [{ mode: 'walking', success: true, summary: '旧协议不应该渲染' }],
    },
  }

  const unsupportedPoiCard = {
    type: 'poi_list',
    card_version: 999,
    data: {
      query: '旧协议 POI',
      center: { name: '旧协议中心' },
      items: [{ id: 'old-poi', name: '旧协议 POI 不应该渲染', address: '旧协议地址' }],
    },
  }

  return [
    'event: session',
    'data: {"session_id": 101}',
    '',
    'event: chunk',
    'data: {"text":"已为你生成通勤建议和图片。"}',
    '',
    'event: done',
    `data: ${JSON.stringify({
      task_id: 202,
      cards: [weatherCard, imageCard, routeCard, poiListCard, ignoredCard, unsupportedRouteCard, unsupportedPoiCard],
      tool_calls: [
        { tool_name: 'image_tool', status: 'success', summary: '图片已生成' },
        { tool_name: 'commute_plan_tool', status: 'success', summary: '通勤规划完成' },
        { tool_name: 'nearby_service_tool', status: 'success', summary: '周边服务查询完成' },
      ],
    })}`,
    '',
    '',
  ].join('\n')
}

async function prepareLoggedInPage(page, theme = 'light') {
  await mockAgentApi(page)
  await page.addInitScript(({ user, selectedTheme }) => {
    localStorage.setItem('auth-token', 'ui-regression-token')
    localStorage.setItem('auth-user', JSON.stringify(user))
    localStorage.setItem('workspace-theme', selectedTheme)
    localStorage.setItem('api-base-url', 'http://localhost:8088')
  }, { user: mockUser, selectedTheme: theme })
}

async function expectCount(locator, expected, message) {
  const count = await locator.count()
  if (count !== expected) throw new Error(`${message}，实际 ${count}，期望 ${expected}`)
}

async function expectInputValue(locator, expected, message) {
  const value = await locator.inputValue()
  if (value !== expected) throw new Error(`${message}，实际 ${value}，期望 ${expected}`)
}

async function ensureQuickPanelExpanded(toggleLocator) {
  if ((await toggleLocator.getAttribute('aria-expanded')) !== 'true') {
    await toggleLocator.click()
  }
}

async function runAgentPageCase(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  try {
    await prepareLoggedInPage(page, 'light')
    await page.goto(`${previewUrl}/#/agent`)

    await page.locator('.app-layout.theme-light').waitFor()
    await page.locator('#page-agent').waitFor()
    await page.locator('.agent-summary-panel').waitFor()
    await page.getByText('Campus AI Workspace').first().waitFor()
    await page.getByText('校园智能工作台').waitFor()
    await page.getByText('统一业务工作台').waitFor()
    await page.getByText('用户先查通勤，再顺手生成了一张校园学习海报风格图片。').waitFor()
    await page.locator('#page-agent').getByText(academicWelcome).waitFor()
    await expectCount(page.locator('.agent-empty'), 0, '主 Agent 初始欢迎语出现后不应再显示空态占位')
    await expectCount(page.locator('.agent-session-chip'), 0, '旧横向会话 chip 不应继续渲染')
    await expectCount(page.getByText('Agent 对话'), 0, '历史摘要栏不应显示默认 Agent 对话标题')
    const firstAgentAvatar = await page.locator('.agent-msg-assistant .agent-msg-avatar').first().innerText()
    if (firstAgentAvatar.trim() !== '🎓') {
      throw new Error(`主 Agent 助手头像应跟随学业导师 persona，实际为 ${firstAgentAvatar}`)
    }

    await page.locator('.agent-summary-item').first().click()
    await page.getByText('历史会话里的真实回复').waitFor()
    await expectCount(page.locator('#page-agent').getByText(academicWelcome), 0, '切换历史会话后不应保留前端欢迎语')

    await page.locator('.agent-summary-new').click()
    await page.locator('#page-agent').getByText(academicWelcome).waitFor()

    const quickPanelToggle = page.locator('.agent-input-area [data-quick-panel-toggle]')
    await quickPanelToggle.waitFor()
    if ((await quickPanelToggle.getAttribute('aria-expanded')) !== 'false') {
      throw new Error('主 Agent 快捷工具面板默认应为折叠状态')
    }

    await ensureQuickPanelExpanded(quickPanelToggle)
    if ((await quickPanelToggle.getAttribute('aria-expanded')) !== 'true') {
      throw new Error('主 Agent 快捷工具面板展开状态未正确更新')
    }

    await page.locator('.agent-input-area [data-tool-fill="weather"]').click()
    await expectInputValue(
      page.locator('.agent-input-area textarea'),
      '帮我查一下 [请补充城市/地点] 的天气。',
      '主 Agent 天气快捷模板未正确回填',
    )

    await page.locator('.agent-input-area [data-tool-fill="commute"]').click()
    await expectInputValue(
      page.locator('.agent-input-area textarea'),
      '从 [请补充起点] 到 [请补充终点] 怎么去？',
      '主 Agent 通勤快捷模板未正确回填',
    )

    await page.locator('.agent-input-area [data-tool-input="image_generation"]').fill('校园学习角，暖色插画')
    const quickImageRequest = page.waitForRequest(request => request.method() === 'POST' && request.url().includes('/agent/chat/stream'))
    await page.locator('.agent-input-area [data-tool-submit="image_generation"]').click()
    const quickImagePayload = (await quickImageRequest).postData() || ''
    if (!quickImagePayload.includes('请帮我生成一张图片：校园学习角，暖色插画')) {
      throw new Error('主 Agent 文生图快捷工具没有正确发送格式化消息')
    }

    await page.locator('.agent-loading').waitFor()
    await expectCount(page.locator('.agent-msg-assistant .agent-msg-avatar'), 2, '主 Agent 发送后应保留欢迎语与当前 assistant 头像各一条')

    await page.locator('.agent-weather-card').waitFor()
    await page.locator('.agent-image-card').waitFor()
    await page.locator('.agent-route-card').waitFor()
    await page.locator('.agent-poi-card').waitFor()
    await expectCount(page.getByText('不应该出现在页面中'), 0, '未知 card type 被错误渲染')
    await expectCount(page.getByText('旧协议不应该渲染'), 0, '不支持的 route card_version 被错误渲染')
    await expectCount(page.getByText('旧协议 POI 不应该渲染'), 0, '不支持的 poi_list card_version 被错误渲染')

    await page.getByText('公交/地铁预计耗时').waitFor()
    await page.getByText('南山餐厅一号').waitFor()
    await page.getByText('复制提示词').waitFor()
    await page.getByText('复制图片链接').waitFor()

    const regenerateRequest = page.waitForRequest(request => request.method() === 'POST' && request.url().includes('/agent/chat/stream'))
    await page.locator('.agent-image-card button.primary').click()
    const regeneratePayload = (await regenerateRequest).postData() || ''
    if (!regeneratePayload.includes('请根据以下提示词重新生成一张图片：')) {
      throw new Error('image 卡片重新生成没有正确发起新一轮文生图请求')
    }

    await page.locator('.agent-poi-card').getByText('去这里').first().click()
    const routeDraft = await page.locator('.agent-input-area textarea').inputValue()
    if (!routeDraft.includes('从 [请补充起点] 到 深圳市南山区海天一路 1 号 怎么去？')) {
      throw new Error('poi_list 去这里没有正确填入通勤规划输入')
    }

    const themeColorsOk = await page.locator('.agent-image-card').evaluate(card => {
      const styles = getComputedStyle(card)
      return styles.backgroundImage.includes('gradient') && styles.color !== ''
    })
    if (!themeColorsOk) throw new Error('主 Agent image 卡片未正确使用主题样式')

    await page.locator('.agent-summary-new').click()
    await page.locator('#page-agent').getByText(academicWelcome).waitFor()
    await ensureQuickPanelExpanded(quickPanelToggle)
    await page.locator('.agent-input-area [data-tool-input="nl2sql"]').fill('统计近30天请假人数')
    const quickNl2sqlRequest = page.waitForRequest(request => request.method() === 'POST' && request.url().includes('/agent/chat/stream'))
    await page.locator('.agent-input-area [data-tool-submit="nl2sql"]').click()
    const quickNl2sqlPayload = (await quickNl2sqlRequest).postData() || ''
    if (!quickNl2sqlPayload.includes('请用 NL2SQL 智能问数帮我查询：统计近30天请假人数')) {
      throw new Error('主 Agent NL2SQL 快捷工具没有正确发送格式化消息')
    }
    await page.locator('.agent-weather-card').waitFor()

    pass('Playwright 主 Agent 欢迎语、快捷工具面板与图片卡片回归')
  } finally {
    await page.close()
  }
}

async function runFloatingAgentCase(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
  try {
    await prepareLoggedInPage(page, 'dark')
    await page.goto(`${previewUrl}/#/student`)

    await page.locator('.float-agent-btn').click()
    await page.locator('.float-agent-panel').waitFor()
    await page.locator('.float-agent-panel').getByText(academicWelcome).waitFor()
    await expectCount(page.locator('.float-agent-empty'), 0, '悬浮 Agent 欢迎语出现后不应再显示空态占位')

    await page.selectOption('.float-agent-persona-select', 'xinge')
    await page.locator('.float-agent-panel').getByText(xingeWelcome).waitFor()
    await expectCount(page.locator('.float-agent-panel').getByText(academicWelcome), 0, '切换 persona 后欢迎语应同步更新')
    const firstFloatingAvatar = await page.locator('.float-agent-msg-assistant .float-agent-msg-avatar').first().innerText()
    if (firstFloatingAvatar.trim() !== '😁') {
      throw new Error(`悬浮 Agent 助手头像应跟随昕哥 persona，实际为 ${firstFloatingAvatar}`)
    }

    const floatQuickPanelToggle = page.locator('.float-agent-input [data-quick-panel-toggle]')
    await floatQuickPanelToggle.waitFor()
    if ((await floatQuickPanelToggle.getAttribute('aria-expanded')) !== 'false') {
      throw new Error('悬浮 Agent 快捷工具面板默认应为折叠状态')
    }

    await floatQuickPanelToggle.click()
    const floatQuickPanelBody = page.locator('.float-agent-input .quick-panel-body')
    const quickPanelScrollOk = await floatQuickPanelBody.evaluate(node => {
      const styles = getComputedStyle(node)
      return node.scrollHeight > node.clientHeight && ['auto', 'scroll'].includes(styles.overflowY)
    })
    if (!quickPanelScrollOk) {
      throw new Error('悬浮 Agent 快捷工具面板展开后未提供内部滚动能力')
    }
    await expectCount(page.locator('.float-agent-input [data-tool-id]'), 6, '悬浮 Agent 快捷工具面板应展示全部 6 个工具')
    await floatQuickPanelBody.evaluate(node => { node.scrollTop = node.scrollHeight })
    await page.locator('.float-agent-input [data-tool-id="nl2sql"]').waitFor()
    await page.locator('.float-agent-input [data-tool-fill="nearby"]').click()
    await expectInputValue(
      page.locator('.float-agent-input textarea'),
      '[请补充地点] 附近有什么 [请补充服务类型]？',
      '悬浮 Agent 周边快捷模板未正确回填',
    )

    await page.locator('.float-agent-input [data-tool-input="image_generation"]').fill('宿舍自习桌，柔和灯光')
    const floatQuickImageRequest = page.waitForRequest(request => request.method() === 'POST' && request.url().includes('/agent/chat/stream'))
    await page.locator('.float-agent-input [data-tool-submit="image_generation"]').click()
    const floatQuickImagePayload = (await floatQuickImageRequest).postData() || ''
    if (!floatQuickImagePayload.includes('请帮我生成一张图片：宿舍自习桌，柔和灯光')) {
      throw new Error('悬浮 Agent 文生图快捷工具没有正确发送格式化消息')
    }

    await page.locator('.float-agent-loading').waitFor()
    await expectCount(page.locator('.float-agent-msg-assistant .float-agent-msg-avatar'), 2, '悬浮 Agent 发送后应保留欢迎语与当前 assistant 头像各一条')
    await page.locator('.float-agent-cards .agent-weather-card').waitFor()
    await page.locator('.float-agent-cards .agent-image-card').waitFor()
    await page.locator('.float-agent-cards .agent-route-card').waitFor()
    await page.locator('.float-agent-cards .agent-poi-card').waitFor()
    await expectCount(page.locator('.float-agent-cards .agent-poi-card .poi-item'), 3, '悬浮 Agent poi_list compact 模式应只展示前 3 条')
    await expectCount(page.getByText('第四条仅主 Agent 展示'), 0, '悬浮 Agent poi_list compact 模式不应展示第 4 条')

    const overflow = await page.locator('.float-agent-panel').evaluate(panel => {
      const panelBox = panel.getBoundingClientRect()
      return [...panel.querySelectorAll('.agent-weather-card, .agent-image-card, .agent-route-card, .agent-poi-card')].some(card => {
        const box = card.getBoundingClientRect()
        return box.left < panelBox.left - 1 || box.right > panelBox.right + 1
      })
    })
    if (overflow) throw new Error('悬浮 Agent 卡片横向溢出面板')

    const themeColorsOk = await page.locator('.float-agent-cards .agent-image-card').evaluate(card => {
      const styles = getComputedStyle(card)
      return styles.backgroundImage.includes('gradient') && styles.color !== ''
    })
    if (!themeColorsOk) throw new Error('悬浮 Agent image 卡片未正确使用主题样式')

    pass('Playwright 悬浮 Agent 欢迎语、快捷工具面板与图片卡片回归')
  } finally {
    await page.close()
  }
}

async function runCollapsedSidebarSystemCase(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  try {
    await prepareLoggedInPage(page, 'light')
    await page.addInitScript(() => {
      localStorage.setItem('workspace-sidebar-collapsed', '1')
    })
    await page.goto(`${previewUrl}/#/student`)

    await page.locator('.sidebar.collapsed').waitFor()
    const rail = page.locator('.sidebar.collapsed [data-sidebar-rail]')
    await rail.waitFor()
    const systemRailItem = page.locator('.sidebar.collapsed [data-sidebar-rail] [data-rail-item="system"]')
    const systemIcon = await systemRailItem.locator('.ico').innerText()
    if (systemIcon.trim() !== '⚙️') {
      throw new Error(`折叠侧栏系统管理模块应显示 emoji 图标，实际为 ${systemIcon}`)
    }
    await systemRailItem.click()
    await page.waitForURL(/#\/system\?sub=sys-users/)
    await page.locator('#page-system').waitFor()
    await page.locator('#sys-users.show').waitFor()

    // 折叠态进入系统管理后，再展开侧栏，应自动定位并展开当前模块，避免用户重新从头找入口。
    const sidebarToggle = page.locator('.topbar .sidebar-toggle')
    await sidebarToggle.click()
    const expandedNav = page.locator('.sidebar [data-sidebar-main]')
    await expandedNav.waitFor()
    await page.locator('.sidebar [data-nav-page="system"].active').waitFor()
    await page.locator('.sidebar [data-nav-page="system"] + .nav-children').waitFor()
    await page.locator('.sidebar .nav-children .nav-child-label', { hasText: '用户管理' }).waitFor()
    const navFocused = await page.evaluate(() => {
      const nav = document.querySelector('.sidebar [data-sidebar-main]')
      const active = document.querySelector('.sidebar [data-nav-page="system"].active')
      if (!nav || !active) return false
      const navRect = nav.getBoundingClientRect()
      const activeRect = active.getBoundingClientRect()
      return activeRect.top >= navRect.top - 1 && activeRect.bottom <= navRect.bottom + 1
    })
    if (!navFocused) {
      throw new Error('侧栏展开后没有把当前系统管理模块滚动定位到可视区域内')
    }

    await page.waitForFunction(() => {
      const button = document.querySelector('#sys-users.show .actions button')
      return !!button && !button.disabled
    })
    await page.locator('#sys-users.show input').first().fill('admin')
    const enterRequest = page.waitForRequest(request => request.method() === 'GET' && request.url().includes('/system/users'))
    await page.locator('#sys-users.show input').first().press('Enter')
    await enterRequest

    pass('Playwright 折叠侧栏系统管理入口回归')
  } finally {
    await page.close()
  }
}

async function runSystemMonitorAutoLoadCase(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  try {
    await prepareLoggedInPage(page, 'light')
    const dashboardRequest = page.waitForRequest(request => request.method() === 'GET' && request.url().includes('/agent/admin/dashboard') && request.url().includes('days=7'))
    const tasksRequest = page.waitForRequest(request => request.method() === 'GET' && request.url().includes('/agent/admin/tasks') && request.url().includes('days=7'))
    await page.goto(`${previewUrl}/#/system?sub=sys-agent-monitor`)

    await page.locator('#page-system').waitFor()
    await page.locator('#sys-agent-monitor.show').waitFor()
    await dashboardRequest
    await tasksRequest
    await page.getByText('Agent 监控数据加载成功').waitFor()
    await page.getByText('从宝安到龙岗怎么走').waitFor()

    pass('Playwright Agent监控首屏自动加载回归')
  } finally {
    await page.close()
  }
}

async function main() {
  const preview = startPreview()
  let browser = null
  try {
    await waitForPreview()
    try {
      browser = await chromium.launch({ channel: 'msedge' })
    } catch (error) {
      if (String(error?.message || '').includes('msedge')) {
        throw new Error('未找到可用的 Playwright Microsoft Edge，请确认本机已安装 Edge。')
      }
      throw error
    }

    await runAgentPageCase(browser)
    await runFloatingAgentCase(browser)
    await runCollapsedSidebarSystemCase(browser)
    await runSystemMonitorAutoLoadCase(browser)
  } finally {
    if (browser) await browser.close()
    await stopPreview(preview)
  }

  const failed = results.filter(item => !item.passed)
  if (failed.length) {
    console.error(`Playwright UI 回归失败：${failed.length}/${results.length}`)
    process.exit(1)
  }
  console.log(`Playwright UI 回归通过：${results.length}/${results.length}`)
}

main().catch(error => {
  fail('Playwright UI 回归执行', error)
  process.exit(1)
})
