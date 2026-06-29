import { spawn } from 'node:child_process'
import http from 'node:http'
import path from 'node:path'
import process from 'node:process'
import { chromium } from '@playwright/test'

const rootDir = process.cwd()
const previewUrl = 'http://127.0.0.1:4173'
const apiBase = 'http://localhost:8088'

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

const mockSessions = [
  {
    id: 101,
    title: 'Agent 对话',
    summary: '用户询问从宝安到龙岗的地铁通勤路线，系统返回公交/地铁耗时与距离建议。',
    update_time: '2026-06-27T15:35:00',
    create_time: '2026-06-27T15:34:00',
  },
  {
    id: 100,
    title: 'Agent 对话',
    summary: '用户查询宝安天气并确认未来多雨，后续出行需关注天气提醒。',
    update_time: '2026-06-27T12:13:00',
    create_time: '2026-06-27T12:12:00',
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

async function waitForPreview(timeoutMs = 15_000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    const ok = await new Promise(resolve => {
      const req = http.get(previewUrl, res => {
        res.resume()
        resolve(res.statusCode && res.statusCode < 500)
      })
      req.on('error', () => resolve(false))
      req.setTimeout(1_000, () => {
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
    body: JSON.stringify(apiOk([
      { id: 'academic_mentor', name: '学业导师', description: '帮助学生处理学习与校园问题' },
    ])),
  }))

  await page.route(`${apiBase}/agent/sessions`, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(apiOk(mockSessions)),
  }))

  await page.route(`${apiBase}/agent/chat/stream`, async route => {
    // 延迟返回 SSE，确保页面真实进入 loading 状态，能检查是否出现双 assistant 头像。
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
    data: { title: '不应该出现在页面上' },
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
    'data: {"text":"已为你生成通勤建议。"}',
    '',
    'event: done',
    `data: ${JSON.stringify({
      task_id: 202,
      cards: [weatherCard, routeCard, poiListCard, ignoredCard, unsupportedRouteCard, unsupportedPoiCard],
      tool_calls: [
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

async function runAgentPageCase(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  try {
    await prepareLoggedInPage(page, 'light')
    await page.goto(`${previewUrl}/#/agent`)

    await page.locator('.app-layout.theme-light').waitFor()
    await page.locator('#page-agent').waitFor()
    await page.locator('.agent-summary-panel').waitFor()
    await page.getByText('用户询问从宝安到龙岗的地铁通勤路线').waitFor()
    await expectCount(page.locator('.agent-session-chip'), 0, '旧横向会话 chip 不应继续渲染')
    await expectCount(page.getByText('Agent 对话'), 0, '历史摘要栏不应显示默认 Agent 对话标题')
    await page.locator('.agent-input-area textarea').fill('从宝安到龙岗坐地铁怎么去')
    await page.locator('.rag-submit-btn').click()

    await page.locator('.agent-loading').waitFor()
    await expectCount(page.locator('.agent-msg-assistant .agent-msg-avatar'), 1, '主 Agent loading 阶段 assistant 头像数量不正确')

    await page.locator('.agent-weather-card').waitFor()
    await page.locator('.agent-route-card').waitFor()
    await page.locator('.agent-poi-card').waitFor()
    await expectCount(page.getByText('不应该出现在页面上'), 0, '未知 card type 被错误渲染')
    await expectCount(page.getByText('旧协议不应该渲染'), 0, '不支持 card_version 被错误渲染')
    await expectCount(page.getByText('旧协议 POI 不应该渲染'), 0, '不支持 poi_list card_version 被错误渲染')
    await page.getByText('公交/地铁预计耗时').waitFor()
    await page.getByText('南山餐厅一号').waitFor()
    await page.locator('.agent-poi-card').getByText('去这里').first().click()
    await page.locator('.agent-input-area textarea').waitFor({ state: 'visible' })
    const routeDraft = await page.locator('.agent-input-area textarea').inputValue()
    if (!routeDraft.includes('从 [请补充起点] 到 深圳市南山区海天一路 1 号 怎么去？')) {
      throw new Error('poi_list 去这里没有正确填充通勤规划输入')
    }

    pass('Playwright 主 Agent 浅色主题卡片回归')
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
    await page.locator('.float-agent-input textarea').fill('从宝安到龙岗坐地铁怎么去')
    await page.locator('.float-agent-input button').click()

    await page.locator('.float-agent-loading').waitFor()
    await expectCount(page.locator('.float-agent-msg-assistant .float-agent-msg-avatar'), 1, '悬浮 Agent loading 阶段 assistant 头像数量不正确')
    await page.locator('.float-agent-cards .agent-weather-card').waitFor()
    await page.locator('.float-agent-cards .agent-route-card').waitFor()
    await page.locator('.float-agent-cards .agent-poi-card').waitFor()
    await expectCount(page.locator('.float-agent-cards .agent-poi-card .poi-item'), 3, '悬浮 Agent poi_list compact 模式应只展示前 3 条')
    await expectCount(page.getByText('第四条仅主 Agent 展示'), 0, '悬浮 Agent poi_list compact 模式不应展示第 4 条')

    const overflow = await page.locator('.float-agent-panel').evaluate(panel => {
      const panelBox = panel.getBoundingClientRect()
      return [...panel.querySelectorAll('.agent-weather-card, .agent-route-card, .agent-poi-card')].some(card => {
        const box = card.getBoundingClientRect()
        return box.left < panelBox.left - 1 || box.right > panelBox.right + 1
      })
    })
    if (overflow) throw new Error('悬浮 Agent 卡片横向溢出面板')

    pass('Playwright 悬浮 Agent 移动端卡片回归')
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
    await page.locator('.sidebar.collapsed .nav-item[title="系统管理"]').click()
    await page.waitForURL(/#\/system\?sub=sys-users/)
    await page.locator('#page-system').waitFor()
    await page.locator('#sys-users.show').waitFor()

    pass('Playwright 折叠侧栏系统管理入口回归')
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
      // 优先驱动本机 Edge，避免额外下载 Playwright 自带 Chromium。
      browser = await chromium.launch({ channel: 'msedge' })
    } catch (error) {
      if (String(error?.message || '').includes('msedge')) {
        throw new Error('未找到可由 Playwright 驱动的 Microsoft Edge，请确认本机已安装 Edge。')
      }
      throw error
    }

    await runAgentPageCase(browser)
    await runFloatingAgentCase(browser)
    await runCollapsedSidebarSystemCase(browser)
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
