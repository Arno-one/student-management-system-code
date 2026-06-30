<template>
  <section id="page-work" class="page active">
    <!-- 学生评价 -->
    <div id="wk-eval" class="card subcard" :class="{ show: sub === 'wk-eval' }">
      <h3>学生评价（大模型生成）</h3>
      <div class="grid">
        <div class="field"><label>学生ID *</label><input v-model.number="form.eval.stuId" type="number" placeholder="1" /></div>
        <div class="field"><label>评价风格 *</label><CustomSelect v-model="form.eval.style" :options="evalStyleOptions" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workEvaluation">{{ loading ? '处理中...' : '生成评价' }}</button></div>
      <ResultBadge :badge="results.eval.badge" :text="results.eval.text" />
    </div>

    <!-- 文生图 -->
    <div id="wk-img" class="card subcard" :class="{ show: sub === 'wk-img' }">
      <h3>文生图（通义万相）</h3>
      <div class="field"><label>提示词 *</label><textarea v-model="form.img.prompt" rows="3" placeholder="一只在草地上奔跑的柯基犬，阳光明媚"></textarea></div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workImage">{{ loading ? '处理中...' : '生成图片' }}</button></div>
      <div class="img-preview" v-if="imageUrl"><img :src="imageUrl" alt="生成结果" /></div>
      <ResultBadge :badge="results.img.badge" :text="results.img.text" />
    </div>

    <!-- 多轮对话 -->
    <div id="wk-talk" class="card subcard" :class="{ show: sub === 'wk-talk' }">
      <h3>多轮记忆对话</h3>

      <!-- 步骤1：输入用户ID确认身份 -->
      <div v-if="false" class="talk-login">
        <div class="talk-login-box">
          <div class="talk-login-icon">🔑</div>
          <div class="talk-login-title">输入用户标识以开始对话</div>
          <div class="talk-login-hint">每个用户ID拥有独立的对话历史和会话记录</div>
          <div class="field" style="max-width:360px; margin: 0 auto;">
            <input
              v-model="talkInputUserId"
              placeholder="请输入你的用户ID"
            />
          </div>
          <button class="btn" :disabled="!talkInputUserId.trim()" @click="confirmUserId">
            确认并进入对话
          </button>
        </div>
      </div>

      <!-- 步骤2：确认后显示对话界面 -->
      <template v-if="true">
        <div class="talk-toolbar">
          <div class="talk-user-badge">
            <span class="talk-user-label">用户</span>
            <span class="talk-user-value">{{ form.talk.userId }}</span>
            <button class="talk-user-switch" @click="switchUser" title="切换用户">切换</button>
          </div>
          <button class="btn secondary" @click="createNewSession">＋ 新建会话</button>
        </div>

      <!-- 会话列表 + 聊天区 并排 -->
      <div class="talk-layout">
        <!-- 左侧：会话列表 -->
        <div class="talk-session-list">
          <div class="talk-session-head">历史会话</div>
          <div v-if="sessions.length === 0" class="talk-empty">暂无会话，请新建</div>
          <div
            v-for="s in sessions"
            :key="s.id"
            class="talk-session-item"
            :class="{ active: s.id === form.talk.sessionId }"
            @click="selectSession(s)"
          >
            <div class="talk-session-title">{{ s.title }}</div>
            <div class="talk-session-summary" v-if="s.summary">{{ s.summary }}</div>
            <div class="talk-session-time">{{ s.update_time }}</div>
            <button class="talk-session-del" @click.stop="deleteSession(s.id)" title="删除">×</button>
          </div>
        </div>

        <!-- 右侧：聊天区 -->
        <div class="talk-chat">
          <div v-if="!form.talk.sessionId" class="talk-empty">请选择或新建一个会话开始对话</div>
          <template v-else>
            <div class="talk-msgs" ref="chatMsgsRef">
              <div
                v-for="m in messages"
                :key="m.id"
                class="talk-msg"
                :class="'talk-msg--' + m.role"
              >
                <div class="talk-msg-role">{{ m.role === 'user' ? '你' : m.role === 'assistant' ? 'AI' : '系统' }}</div>
                <div class="talk-msg-content">{{ m.role === 'user' ? m.user_content : m.ai_content || m.content }}</div>
              </div>
              <div v-if="loading" class="talk-msg talk-msg--assistant">
                <div class="talk-msg-role">AI</div>
                <div class="talk-msg-content">思考中...</div>
              </div>
            </div>
            <div class="talk-input-row">
              <input
                v-model="form.talk.prompt"
                placeholder="输入消息，按回车发送..."
                :disabled="loading"
              />
              <button class="btn" :disabled="loading || !form.talk.prompt" @click="workTalk">
                {{ loading ? '...' : '发送' }}
              </button>
              <button class="btn danger" :disabled="loading" @click="workClearTalk">清空</button>
            </div>
          </template>
        </div>
      </div>
      </template>
    </div>

    <!-- 天气 / 经纬度 -->
    <div id="wk-weather" class="card subcard" :class="{ show: sub === 'wk-weather' }">
      <!-- 天气查询 -->
      <div class="section-title">天气查询</div>
      <div class="grid">
        <div class="field"><label>经纬度（纬度,经度）</label><input v-model="form.weather.location" placeholder="39.905023,116.724502" /></div>
        <div class="field"><label>行政区划编码</label><input v-model="form.weather.adcode" placeholder="130681" /></div>
        <div class="field"><label>天气类型</label><CustomSelect v-model="form.weather.wtype" :options="weatherTypeOptions" /></div>
        <div class="field"><label>附加字段</label><input v-model="form.weather.added" placeholder="alarm,air" /></div>
        <div class="field"><label>天数控制（多日生效）</label><input v-model.number="form.weather.getmd" type="number" placeholder="0" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workWeather">查天气</button></div>
      <!-- 天气结果区：单独 ref，方便地址联动后滚动定位（对应原生 wk_weather_view） -->
      <div ref="weatherViewRef" id="wk-weather-view" class="weather-view">
        <WeatherCard v-if="weatherCardData" :data="weatherCardData" />
        <div v-else-if="weatherError" class="geo-card">
          <div class="geo-fail">❌ {{ weatherError }}</div>
        </div>
      </div>

      <!-- 地址解析 -->
      <div class="section-title">地址解析为经纬度</div>
      <div class="grid">
        <div class="field" style="grid-column: span 2;"><label>地址 *</label><input v-model="form.geo.address" placeholder="北京市海淀区彩和坊路海淀西大街74号" /></div>
        <div class="field"><label>解析策略</label><CustomSelect v-model="form.geo.policy" :options="geoPolicyOptions" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workGeocoder">解析地址</button></div>
      <!-- 地址解析结果区：用事件委托接管「查该地天气」按钮（v-html 内联 onclick 在 Vue 中不可靠） -->
      <div
        ref="geoViewRef"
        id="wk-geo-view"
        class="weather-view"
        v-html="geoHtml"
        @click="handleGeoViewClick"
      ></div>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, nextTick } from 'vue'
import { request, qs, pickApiContent, apiState } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import CustomSelect from '../components/CustomSelect.vue'
import WeatherCard from '../components/WeatherCard.vue'
import { useModuleSubPage } from '../composables/useModuleSubPage'
import { validateFields, findImageUrl } from '../utils/helpers'

const { sub } = useModuleSubPage('work')
const evalStyleOptions = [
  { value: '幽默', label: '幽默' },
  { value: '严肃', label: '严肃' },
  { value: '激励', label: '激励' },
  { value: '批判', label: '批判' },
]
const weatherTypeOptions = [
  { value: 'now', label: '实时' },
  { value: 'future', label: '多日' },
  { value: 'hours', label: '逐时' },
]
const geoPolicyOptions = [
  { value: '0', label: '标准' },
  { value: '1', label: '宽松' },
]
const loading = ref(false)
const imageUrl = ref('')
const weatherCardData = ref(null)
const weatherError = ref('')
const geoHtml = ref('')
const weatherViewRef = ref(null)
const geoViewRef = ref(null)

const form = reactive({
  eval: { stuId: null, style: '幽默' },
  img: { prompt: '' },
  talk: { userId: '', sessionId: null, prompt: '' },
  weather: { location: '', adcode: '', wtype: 'now', added: '', getmd: null },
  geo: { address: '', policy: '0' }
})

const sessions = ref([])
const messages = ref([])
const chatMsgsRef = ref(null)
const talkConfirmed = ref(true)
const talkInputUserId = ref('')

const results = reactive({
  eval: { badge: null, text: '' }, img: { badge: null, text: '' }
})

function setResult(target, ok, msg) {
  results[target].badge = { ok, text: msg }
  results[target].text = ''
}

async function workEvaluation() {
  if (!validateFields([['#wk-eval', '学生ID', form.eval.stuId]])) return
  loading.value = true
  setResult('eval', false, '')
  try {
    const r = await request('POST', '/work/evaluation' + qs({ student_id: form.eval.stuId, style: form.eval.style || null }))
    if (r.ok) {
      setResult('eval', true, '评价生成成功')
      results.eval.text = pickApiContent(r.data)
    } else {
      setResult('eval', false, r.data?.msg || '评价生成失败')
    }
  } catch (e) {
    setResult('eval', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

async function workImage() {
  if (!validateFields([['#wk-img', '提示词', form.img.prompt]])) return
  loading.value = true
  imageUrl.value = ''
  setResult('img', false, '')
  try {
    const r = await request('POST', '/work/image' + qs({ prompt: form.img.prompt || null }))
    const inner = r?.data?.data
    const url = (inner && typeof inner === 'object' && inner.image_url) || findImageUrl(r?.data)
    if (r.ok && url) {
      imageUrl.value = url
      setResult('img', true, '图片已生成，请见上方预览')
    } else {
      setResult('img', false, (inner?.error) || r?.data?.msg || '文生图失败')
    }
  } catch (e) {
    setResult('img', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

function autoScrollChat() {
  nextTick(() => {
    const el = chatMsgsRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function onUserIdChange() {
  form.talk.sessionId = null
  messages.value = []
  loadSessions()
}

// ===== 用户身份确认 / 切换 =====
function confirmUserId() {
  const uid = apiState.user?.username || ''
  if (!uid) return
  form.talk.userId = uid
  talkConfirmed.value = true
  loadSessions()
}

function switchUser() {
  form.talk.userId = apiState.user?.username || ''
  form.talk.sessionId = null
  messages.value = []
  sessions.value = []
  loadSessions()
}

async function loadSessions() {
  if (!form.talk.userId) return
  try {
    const r = await request('GET', '/work/talks/sessions' + qs({ user_id: form.talk.userId }))
    if (r.ok && r.data?.data) {
      sessions.value = r.data.data
    }
  } catch (e) { /* 静默失败 */ }
}

async function createNewSession() {
  if (!form.talk.userId) return alert('请先输入用户标识')
  try {
    const r = await request('POST', '/work/talks/sessions', { body: { user_id: form.talk.userId, title: '新对话' } })
    if (r.ok && r.data?.data) {
      sessions.value.unshift(r.data.data)
      selectSession(r.data.data)
    }
  } catch (e) {
    alert('创建会话失败: ' + e.message)
  }
}

async function selectSession(s) {
  form.talk.sessionId = s.id
  form.talk.prompt = ''
  messages.value = []
  try {
    const r = await request('GET', `/work/talks/${s.id}/messages`)
    if (r.ok && r.data?.data) {
      messages.value = r.data.data.filter(m => m.role !== 'system')
      autoScrollChat()
    }
  } catch (e) { /* 静默失败 */ }
}

async function deleteSession(sid) {
  if (!confirm('确定删除该会话？')) return
  try {
    const r = await request('DELETE', `/work/talks/sessions/${sid}` + qs({ user_id: form.talk.userId }))
    if (r.ok) {
      sessions.value = sessions.value.filter(s => s.id !== sid)
      if (form.talk.sessionId === sid) {
        form.talk.sessionId = null
        messages.value = []
      }
    }
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

async function workTalk() {
  if (!form.talk.userId) return alert('请输入用户标识')
  if (!form.talk.sessionId) return alert('请选择或新建一个会话')
  if (!form.talk.prompt.trim()) return
  const prompt = form.talk.prompt
  form.talk.prompt = ''
  // 乐观追加用户消息
  messages.value.push({ id: Date.now(), role: 'user', user_content: prompt })
  autoScrollChat()
  loading.value = true
  try {
    const r = await request('POST', '/work/talks', { body: {
      session_id: form.talk.sessionId,
      user_id: form.talk.userId,
      prompt
    } })
    if (r.ok) {
      const content = typeof r.data?.data === 'string' ? r.data.data : (r.data?.msg || '')
      messages.value.push({ id: Date.now() + 1, role: 'assistant', ai_content: content })
      // 刷新会话列表（更新时间和标题可能变化）
      loadSessions()
    } else {
      messages.value.push({ id: Date.now() + 1, role: 'assistant', ai_content: '错误: ' + (r.data?.msg || '对话失败') })
    }
  } catch (e) {
    messages.value.push({ id: Date.now() + 1, role: 'assistant', ai_content: '网络错误: ' + e.message })
  } finally {
    loading.value = false
    autoScrollChat()
  }
}

async function workClearTalk() {
  if (!form.talk.sessionId) return
  if (!confirm('确定清空当前会话的全部消息？')) return
  loading.value = true
  try {
    const r = await request('POST', '/work/talks/clear' + qs({ session_id: form.talk.sessionId, user_id: form.talk.userId }))
    if (r.ok) {
      messages.value = []
    } else {
      alert(r.data?.msg || '清空失败')
    }
  } catch (e) {
    alert('网络错误: ' + e.message)
  } finally { loading.value = false }
}

// 初始化：自动使用当前登录用户作为会话归属
form.talk.userId = apiState.user?.username || ''
if (form.talk.userId) {
  loadSessions()
}

async function workWeather() {
  if (!form.weather.location && !form.weather.adcode) {
    return alert('经纬度或行政编码至少填一个')
  }
  loading.value = true
  weatherCardData.value = null
  weatherError.value = ''
  try {
    const r = await request('GET', '/work/weather' + qs({
      location: form.weather.location || null,
      adcode: form.weather.adcode || null,
      weather_type: form.weather.wtype,
      added_fields: form.weather.added || null,
      // 与原生版一致：空值不传，避免 get_md=NaN 导致腾讯接口报错
      get_md: Number.isFinite(form.weather.getmd) ? form.weather.getmd : null
    }))
    if (r.ok && r.data?.code === 200) {
      weatherCardData.value = buildWeatherCardData(r.data)
      if (!weatherCardData.value) weatherError.value = '未解析到天气数据'
    } else {
      weatherError.value = r.data?.msg || '天气查询失败，请检查参数或稍后重试'
    }
  } catch (e) {
    weatherError.value = '天气查询失败'
  } finally { loading.value = false }
}

function buildWeatherCardData(resp) {
  // 把工作台接口的统一响应转换成 Agent 天气卡片协议，后续展示只维护 WeatherCard 一份。
  const inner = resp?.data
  const result = inner?.result
  if (!result || typeof result !== 'object') return null

  const weather = {}
  if (Array.isArray(result.realtime) && result.realtime.length) weather['实时天气'] = { result }
  if (Array.isArray(result.forecast) && result.forecast.length) weather['多日预报'] = { result }
  if (Array.isArray(result.forecast_hours) && result.forecast_hours.length) weather['逐时预报'] = { result }
  if (!Object.keys(weather).length) return null

  const firstItem = result.realtime?.[0] || result.forecast?.[0] || result.forecast_hours?.[0] || {}
  const locationText = [firstItem.province, firstItem.city, firstItem.district].filter(Boolean).join(' · ')
  return {
    provider: 'work_weather',
    location_text: locationText || form.weather.adcode || form.weather.location || '天气查询结果',
    adcode: form.weather.adcode || firstItem.adcode || '',
    weather,
  }
}

async function workGeocoder() {
  if (!validateFields([['#wk-weather', '地址', form.geo.address]])) return
  loading.value = true
  geoHtml.value = ''
  try {
    const r = await request('GET', '/work/geocoder' + qs({ address: form.geo.address, policy: form.geo.policy }))
    if (r.ok && r.data?.code === 200) {
      geoHtml.value = renderGeocoder(r.data)
    } else {
      geoHtml.value = `<div class="geo-card"><div class="geo-fail">❌ ${r.data?.msg || '地址解析失败，请检查地址或稍后重试'}</div></div>`
    }
  } catch (e) {
    geoHtml.value = '<div class="geo-card"><div class="geo-fail">❌ 地址解析失败</div></div>'
  } finally { loading.value = false }
}

// 转义 HTML 属性，防止地址/编码中的特殊字符破坏 data-* 属性
function escAttr(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
}

function renderGeocoder(resp) {
  const d = resp?.data
  if (!d || typeof d !== 'object') return '<div class="hint">未解析到地址数据</div>'
  if (d.success === false) return '<div class="geo-card"><div class="geo-fail">❌ 地址解析失败，请检查地址是否准确</div></div>'

  const c = d.address_components || {}
  const fullAddr = [c.province, c.city, c.district, c.street, c.street_number].filter(Boolean).join('')

  const metrics = [
    ['🧭', '纬度', d.lat], ['🧭', '经度', d.lng], ['🔢', '行政编码', d.adcode], ['🎯', '解析等级', d.level]
  ].filter(([, , v]) => v != null && v !== '')
   .map(([ico, lbl, v]) =>
     `<div class="geo-metric"><span class="ico">${ico}</span><span class="meta"><span class="lbl">${lbl}</span><span class="val">${v}</span></span></div>`
   ).join('')

  let bar = ''
  if (d.reliability != null) {
    const pct = Math.max(0, Math.min(100, Number(d.reliability) * 10))
    bar = `<div class="geo-bar-wrap"><div class="geo-bar-head"><span>📊 解析可信度</span><span>${d.reliability} / 10</span></div><div class="geo-bar"><i style="width:${pct}%"></i></div></div>`
  }

  // 一键联动：优先 adcode，否则用经纬度（格式 "纬度,经度"），与原生 frontend/app.js 一致
  const adcode = d.adcode ? String(d.adcode) : ''
  const location = (d.lat != null && d.lng != null) ? `${d.lat},${d.lng}` : ''
  let linkBtn = ''
  if (adcode || location) {
    linkBtn = `<div style="margin-top:16px">
      <button type="button" class="btn" data-action="geo-weather" data-adcode="${escAttr(adcode)}" data-location="${escAttr(location)}">🌤️ 查该地天气</button>
    </div>`
  }

  return `<div class="geo-card">
    <div class="geo-addr">📍 ${fullAddr || '未知地址'}</div>
    <div class="geo-coord">🌐 经纬度坐标：${d.lat ?? '--'}, ${d.lng ?? '--'}</div>
    <div class="geo-metrics">${metrics}</div>${bar}${linkBtn}
  </div>`
}

// 事件委托：捕获 v-html 渲染出的「查该地天气」按钮点击
function handleGeoViewClick(event) {
  const btn = event.target.closest('[data-action="geo-weather"]')
  if (!btn) return
  useGeoForWeather(btn.dataset.adcode || '', btn.dataset.location || '')
}

// 地址→天气一键联动：回填表单并自动查询，逻辑对齐原生 useGeoForWeather()
async function useGeoForWeather(adcode, location) {
  // 优先用 adcode 查询，更精准；填一个时清空另一个，避免参数冲突
  if (adcode) {
    form.weather.adcode = adcode
    form.weather.location = ''
  } else {
    form.weather.location = location
    form.weather.adcode = ''
  }
  form.weather.wtype = 'now'
  await workWeather()
  await nextTick()
  weatherViewRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
</script>
