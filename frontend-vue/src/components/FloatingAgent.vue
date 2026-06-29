<template>
  <div class="float-agent" :class="{ 'float-agent--open': open }" v-if="!isPublicPage">
    <!-- 浮动按钮 -->
    <button class="float-agent-btn" :class="{ 'float-agent-btn--open': open }" @click="toggle" :title="open ? '收起' : 'Agent 助手'">
      <span class="float-agent-btn-icon" v-if="!open">🤖</span>
      <span class="float-agent-btn-close" v-else>✕</span>
      <span class="float-agent-btn-pulse" v-if="!open"></span>
    </button>

    <!-- 聊天面板 -->
    <div class="float-agent-panel" v-show="open">
      <div class="float-agent-header">
        <div class="float-agent-header-left">
          <span class="float-agent-header-icon">🤖</span>
          <div>
            <strong>{{ personaTitle(currentPersona) }}</strong>
            <small>{{ currentPersona?.description || emptyHint }}</small>
          </div>
        </div>
        <div class="float-agent-header-actions">
          <select
            v-model="selectedPersona"
            class="float-agent-persona-select"
            :disabled="loading || personaOptions.length === 0"
            title="切换 Agent 角色"
            @change="savePersonaPreference"
          >
            <option v-for="item in personaOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
          <button class="float-agent-minimize" @click="open = false" title="收起">✕</button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="float-agent-msgs" ref="msgListRef">
        <div class="float-agent-empty" v-if="messages.length === 0 && !loading">
          <p>{{ emptyTitle }}</p>
          <p class="float-agent-empty-sub">{{ emptyHint }}</p>
        </div>

        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="float-agent-msg"
          :class="'float-agent-msg-' + msg.role"
        >
          <div class="float-agent-msg-avatar">{{ msg.role === 'user' ? '我' : 'AI' }}</div>
          <div class="float-agent-msg-body">
            <!-- 等待首个 SSE 文本片段时，复用当前 assistant 消息，避免和全局 loading 形成双头像 -->
            <div class="float-agent-loading" v-if="msg.role === 'assistant' && msg._streaming && !msg.content">
              <span></span><span></span><span></span>
            </div>
            <div
              class="float-agent-msg-text"
              :class="{ 'float-agent-md': !msg._streaming && msg.role === 'assistant' }"
              v-else-if="msg._streaming || msg.role === 'user'"
            >{{ msg.content }}</div>
            <div
              class="float-agent-msg-text float-agent-md"
              v-else
              v-html="renderMarkdown(msg.content)"
            ></div>

            <div class="float-agent-cards" v-if="msg.cards?.length">
              <WeatherCard
                v-for="(card, ci) in msg.cards.filter(c => c.type === 'weather' && isCardVersionSupported(c))"
                :key="'weather-' + ci"
                :card="card"
                compact
              />
              <RouteCard
                v-for="(card, ci) in msg.cards.filter(c => c.type === 'route' && isCardVersionSupported(c))"
                :key="'route-' + ci"
                :card="card"
                compact
              />
              <PoiListCard
                v-for="(card, ci) in msg.cards.filter(c => c.type === 'poi_list' && isCardVersionSupported(c))"
                :key="'poi-list-' + ci"
                :card="card"
                compact
                @plan-route="fillRouteDraft"
              />
            </div>

            <!-- 工具调用 -->
            <div class="float-agent-tools" v-if="msg.toolCalls?.length">
              <div class="float-agent-tool" v-for="tc in msg.toolCalls" :key="tc.tool_name">
                <span class="float-agent-tool-dot" :class="tc.status === 'success' ? 'ok' : (tc.status === 'running' ? 'running' : 'err')"></span>
                <span>{{ toolLabel(tc.tool_name) }}: {{ tc.summary }}</span>
              </div>
            </div>

            <!-- HITL -->
            <div class="float-agent-hitl" v-if="msg.hitl">
              <div class="float-agent-hitl-head">
                <span>{{ msg.hitl.confirmTitle || '确认执行操作' }}</span>
                <small>{{ msg.hitl.riskLevel || 'medium' }}</small>
              </div>
              <p class="float-agent-hitl-msg">{{ msg.hitl.confirmMessage || '请确认内容无误后再继续。' }}</p>
              <div class="float-agent-hitl-field"><label>收件人</label><span>{{ msg.hitl.preview?.receiver }}</span></div>
              <div class="float-agent-hitl-field"><label>主题</label><input v-model="msg.hitl.preview.subject" /></div>
              <div class="float-agent-hitl-field"><label>正文</label><textarea v-model="msg.hitl.preview.body" rows="3"></textarea></div>
              <div class="float-agent-hitl-actions" v-if="!msg.hitl.resolved">
                <button class="float-agent-hitl-ok" :disabled="msg.hitl.loading" @click="confirmHitl(msg)">发送</button>
                <button class="float-agent-hitl-no" :disabled="msg.hitl.loading" @click="cancelHitl(msg)">取消</button>
              </div>
              <div class="float-agent-hitl-result" :class="msg.hitl.resultStatus" v-else>{{ msg.hitl.resultMsg }}</div>
            </div>

            <!-- 任务级反馈 -->
            <div class="float-agent-feedback" v-if="msg.role === 'assistant' && msg.feedback?.taskId && !msg._streaming">
              <div class="float-agent-feedback-actions">
                <button
                  :class="{ active: msg.feedback.rating === 5 }"
                  :disabled="msg.feedback.loading || msg.feedback.submitted"
                  @click="rateFeedback(msg, 5)"
                >👍</button>
                <button
                  :class="{ active: msg.feedback.rating === 1 }"
                  :disabled="msg.feedback.loading || msg.feedback.submitted"
                  @click="rateFeedback(msg, 1)"
                >👎</button>
                <span>{{ msg.feedback.status }}</span>
              </div>
              <div class="float-agent-feedback-comment" v-if="msg.feedback.open && !msg.feedback.submitted">
                <textarea
                  v-model="msg.feedback.draftComment"
                  rows="2"
                  maxlength="1000"
                  placeholder="哪里不够好？"
                ></textarea>
                <button
                  :disabled="msg.feedback.loading || !msg.feedback.draftComment.trim()"
                  @click="submitFeedback(msg, msg.feedback.rating || 1, true)"
                >提交</button>
              </div>
            </div>

            <!-- 来源 -->
            <div class="float-agent-sources" v-if="msg.sources?.length">
              <div class="float-agent-sources-head">参考来源</div>
              <div class="float-agent-source" v-for="(src, si) in msg.sources" :key="si">
                <span class="float-agent-source-num">{{ si + 1 }}</span>
                <span>{{ src.file_name }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- 输入区 -->
      <div class="float-agent-input">
        <textarea
          v-model="form.message"
          placeholder="输入你的问题..."
          :disabled="loading"
          rows="2"
          @keydown.ctrl.enter="doSend"
          @keydown.meta.enter="doSend"
        ></textarea>
        <button @click="doSend" :disabled="loading || !form.message.trim()">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { request, getBaseUrl, getAuthHeader, isLoggedIn } from '../api'
import WeatherCard from './WeatherCard.vue'
import RouteCard from './RouteCard.vue'
import PoiListCard from './PoiListCard.vue'
import { fallbackAgentPersonas } from '../config/agentPersonas'

const props = defineProps({ themeClass: { type: String, default: 'theme-dark' } })

marked.setOptions({ breaks: true, gfm: true })

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

function isCardVersionSupported(card) {
  return !card?.card_version || card.card_version === 1
}

const route = useRoute()
const isPublicPage = computed(() => !!route.meta?.public)
const open = ref(false)
const loading = ref(false)
const messages = ref([])
const currentSessionId = ref(null)
const personas = ref([...fallbackAgentPersonas])
const selectedPersona = ref(localStorage.getItem('floating-agent-persona') || 'academic_mentor')
const msgListRef = ref(null)
const form = reactive({ message: '' })

const currentPersona = computed(() => personas.value.find(item => item.id === selectedPersona.value) || personas.value[0] || null)
const personaOptions = computed(() => personas.value.map(item => ({ value: item.id, label: personaTitle(item) })))
const emptyTitle = computed(() => {
  if (selectedPersona.value === 'companion_head_teacher') return '慢慢说，我在这儿'
  if (selectedPersona.value === 'xinge') return '好兄弟，昕哥在'
  return '有问题随时问我'
})
const emptyHint = computed(() => {
  if (selectedPersona.value === 'companion_head_teacher') return '可以聊压力、拖延、考试焦虑，也可以一起拆一个小计划'
  if (selectedPersona.value === 'xinge') return '复盘错误、鼓劲打气、拆下一步，嘿嘿'
  return '查成绩 · 问天气 · 发邮件 · 聊学习'
})

function toggle() { open.value = !open.value }
function savePersonaPreference() { localStorage.setItem('floating-agent-persona', selectedPersona.value) }
function personaTitle(persona) {
  if (!persona) return '🎓 学业导师'
  return [persona.icon, persona.name].filter(Boolean).join(' ')
}

function toolLabel(name) {
  const map = { score_tool: '成绩', rag_tool: '检索', nl2sql_tool: '数据', student_tool: '身份', weather_tool: '天气', email_tool: '邮件', commute_plan_tool: '通勤', nearby_service_tool: '周边' }
  return map[name] || name
}

function createFeedback(taskId = null) {
  return {
    taskId,
    rating: null,
    draftComment: '',
    open: false,
    loading: false,
    submitted: false,
    status: '',
  }
}

async function loadPersonas() {
  if (!isLoggedIn()) {
    personas.value = [...fallbackAgentPersonas]
    return
  }
  try {
    const r = await request('GET', '/agent/personas')
    if (r.ok && r.data?.code === 200 && Array.isArray(r.data.data) && r.data.data.length > 0) {
      personas.value = r.data.data
      if (personas.value.length && !personas.value.some(item => item.id === selectedPersona.value)) {
        selectedPersona.value = personas.value[0].id
        savePersonaPreference()
      }
    }
  } catch (_) { /* 静默失败，保留前端兜底角色 */ }
}

async function doSend() {
  const text = form.message.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  form.message = ''
  loading.value = true
  scrollBottom()

  const msgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '', toolCalls: [], sources: null, cards: null, feedback: createFeedback(), _streaming: true })

  const body = JSON.stringify({
    message: text,
    persona: selectedPersona.value,
    ...(currentSessionId.value ? { session_id: currentSessionId.value } : {}),
  })

  try {
    const baseUrl = getBaseUrl()
    const headers = { 'Content-Type': 'application/json', ...getAuthHeader() }
    const resp = await fetch(`${baseUrl}/agent/chat/stream`, { method: 'POST', headers, body })
    if (!resp.ok) {
      messages.value[msgIdx] = { role: 'assistant', content: `请求失败 (${resp.status})` }
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const currentMsg = () => messages.value[msgIdx]

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) { eventType = line.slice(7).trim(); continue }
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          handleSSE(eventType, data, currentMsg)
        } catch (_) { /* skip */ }
        eventType = ''
      }
    }
    if (currentMsg()) currentMsg()._streaming = false
  } catch (e) {
    messages.value[msgIdx] = { role: 'assistant', content: '网络错误：' + e.message }
  } finally {
    loading.value = false
    scrollBottom()
  }
}

function fillRouteDraft(destination) {
  form.message = `从 [请补充起点] 到 ${destination} 怎么去？`
}

function handleSSE(event, data, currentMsg) {
  if (!currentMsg()) return
  switch (event) {
    case 'session':
      currentSessionId.value = data.session_id
      break
    case 'tool_start':
      if (!currentMsg().toolCalls) currentMsg().toolCalls = []
      currentMsg().toolCalls.push({ tool_name: data.tool_name, status: 'running', summary: '执行中...' })
      scrollBottom()
      break
    case 'tool_end':
      if (currentMsg().toolCalls) {
        const tc = currentMsg().toolCalls.find(t => t.tool_name === data.tool_name && t.status === 'running')
        if (tc) { tc.status = data.status; tc.summary = data.summary || '' }
      }
      scrollBottom()
      break
    case 'chunk':
      currentMsg().content += data.text
      scrollBottom()
      break
    case 'done':
      if (data.tool_calls) currentMsg().toolCalls = data.tool_calls
      if (data.sources) currentMsg().sources = data.sources
      if (data.cards) currentMsg().cards = data.cards
      if (data.task_id) currentMsg().feedback = createFeedback(data.task_id)
      currentMsg()._streaming = false
      scrollBottom()
      break
    case 'awaiting_confirmation':
      currentMsg().hitl = {
        tool_name: data.tool_name,
        stepId: data.step_id || 1,
        preview: data.preview || {},
        riskLevel: data.risk_level || 'medium',
        timeoutSeconds: data.timeout_seconds || 600,
        expiresAt: data.expires_at || null,
        confirmTitle: data.confirm_title || '确认执行操作',
        confirmMessage: data.confirm_message || '请确认内容无误后再继续。',
        resolved: false,
        loading: false,
        resultStatus: '',
        resultMsg: '',
      }
      if (!currentMsg().feedback) currentMsg().feedback = createFeedback()
      currentMsg()._streaming = false
      scrollBottom()
      break
    case 'error':
      currentMsg().content = data.message || '请求被拒绝'
      currentMsg()._streaming = false
      break
  }
}

async function rateFeedback(msg, rating) {
  if (!msg.feedback?.taskId || msg.feedback.loading || msg.feedback.submitted) return
  msg.feedback.rating = rating
  if (rating === 1) {
    msg.feedback.open = true
    msg.feedback.status = '请写原因'
    return
  }
  msg.feedback.open = false
  await submitFeedback(msg, rating, false)
}

async function submitFeedback(msg, rating, withComment = false) {
  if (!msg.feedback?.taskId || msg.feedback.loading || msg.feedback.submitted) return
  const comment = withComment ? msg.feedback.draftComment.trim() : ''
  if (withComment && !comment) {
    msg.feedback.status = '请先填写'
    return
  }
  msg.feedback.loading = true
  msg.feedback.status = '提交中...'
  try {
    const r = await request('POST', '/agent/feedback', {
      body: {
        task_id: msg.feedback.taskId,
        rating,
        comment: comment || null,
        tool_name: null,
      },
    })
    if (r.ok && r.data?.code === 200) {
      msg.feedback.rating = r.data.data?.rating || rating
      msg.feedback.submitted = true
      msg.feedback.open = false
      msg.feedback.status = '已记录'
    } else {
      msg.feedback.status = r.data?.detail || r.data?.msg || '失败'
    }
  } catch (_) {
    msg.feedback.status = '网络错误'
  } finally {
    msg.feedback.loading = false
  }
}

async function confirmHitl(msg) {
  if (!msg.hitl || msg.hitl.resolved) return
  msg.hitl.loading = true
  try {
    const r = await request('POST', '/agent/step/confirm', {
      body: { task_id: String(currentSessionId.value || 'default'), step_id: msg.hitl.stepId || 1, confirmed: true,
        modified_params: { subject: msg.hitl.preview.subject, body: msg.hitl.preview.body, receiver: msg.hitl.preview.receiver } }
    })
    msg.hitl.resolved = true
    if (r.ok && r.data?.code === 200) {
      msg.hitl.resultStatus = 'ok'; msg.hitl.resultMsg = r.data.data?.message || '已发送'
    } else {
      msg.hitl.resultStatus = 'err'; msg.hitl.resultMsg = r.data?.detail || '发送失败'
    }
  } catch (e) {
    msg.hitl.resolved = true; msg.hitl.resultStatus = 'err'; msg.hitl.resultMsg = '网络错误'
  } finally { msg.hitl.loading = false }
}

async function cancelHitl(msg) {
  if (!msg.hitl || msg.hitl.resolved) return
  msg.hitl.loading = true
  try { await request('POST', '/agent/step/confirm', { body: { task_id: String(currentSessionId.value || 'default'), step_id: msg.hitl.stepId || 1, confirmed: false } }) } catch (_) { }
  msg.hitl.resolved = true; msg.hitl.resultStatus = 'cancelled'; msg.hitl.resultMsg = '已取消'; msg.hitl.loading = false
}

function scrollBottom() {
  nextTick(() => {
    const el = msgListRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

watch(selectedPersona, savePersonaPreference)
onMounted(() => { loadPersonas() })
</script>

<style scoped>
.float-agent { position: fixed; right: 24px; bottom: 24px; z-index: 1000; font-family: inherit; }
.float-agent--open { right: 24px; bottom: 24px; }

/* 浮动按钮 */
.float-agent-btn {
  width: 52px; height: 52px; border-radius: 50%; border: 2px solid var(--gold);
  background: var(--panel-solid); color: var(--gold); font-size: 22px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3); transition: all var(--dur-fast);
  position: relative; z-index: 2;
}
.float-agent-btn:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(0,0,0,0.4); }
.float-agent-btn--open { border-color: var(--text-dim); color: var(--text-dim); }
.float-agent-btn-close { font-size: 18px; }
.float-agent-btn-pulse {
  position: absolute; inset: -6px; border-radius: 50%; border: 2px solid var(--gold);
  opacity: 0; animation: float-pulse 2s ease-out infinite;
}
@keyframes float-pulse {
  0% { transform: scale(0.9); opacity: 0.6; }
  100% { transform: scale(1.3); opacity: 0; }
}

/* 面板 */
.float-agent-panel {
  position: absolute; right: 0; bottom: 64px; width: 400px; max-width: calc(100vw - 48px);
  height: 560px; max-height: calc(100vh - 120px); border-radius: 16px;
  background: var(--panel-solid); border: 1px solid var(--line-strong);
  box-shadow: 0 8px 40px rgba(0,0,0,0.4); display: flex; flex-direction: column; overflow: hidden;
}

.float-agent-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid var(--line); flex-shrink: 0;
}
.float-agent-header-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.float-agent-header-icon { font-size: 24px; }
.float-agent-header-left strong { display: block; font-size: 14px; color: var(--text); }
.float-agent-header-left small {
  display: block;
  max-width: 170px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.float-agent-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.float-agent-persona-select {
  width: 112px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--text-soft);
  font-size: 11px;
  outline: none;
}
.float-agent-persona-select:focus { border-color: var(--gold); }
.float-agent-persona-select:disabled { opacity: 0.55; cursor: not-allowed; }
.float-agent-minimize {
  width: 28px; height: 28px; border-radius: 50%; border: none;
  background: var(--panel-2); color: var(--text-dim); font-size: 13px; cursor: pointer;
}

/* 消息 */
.float-agent-msgs { flex: 1; overflow-y: auto; padding: 12px 14px; }
.float-agent-empty { text-align: center; padding: 40px 12px; color: var(--text-dim); font-size: 13px; }
.float-agent-empty-sub { font-size: 11px; opacity: 0.5; margin-top: 4px; }
.float-agent-msg { display: flex; gap: 8px; margin-bottom: 12px; }
.float-agent-msg-user { flex-direction: row-reverse; }
.float-agent-msg-avatar {
  width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0;
  background: var(--panel-2); color: var(--text-soft);
}
.float-agent-msg-user .float-agent-msg-avatar { background: var(--gold); color: #fff; }
.float-agent-msg-body { max-width: 85%; min-width: 0; }
.float-agent-msg-text {
  padding: 8px 12px; border-radius: 10px; font-size: 13px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-word;
}
.float-agent-msg-user .float-agent-msg-text { background: var(--gold-bg); color: var(--text); }
.float-agent-msg-assistant .float-agent-msg-text { background: var(--panel-2); color: var(--text); }

/* Markdown */
.float-agent-md :deep(h1), .float-agent-md :deep(h2), .float-agent-md :deep(h3) { margin: 6px 0 3px; font-weight: 700; font-size: 14px; }
.float-agent-md :deep(p) { margin: 3px 0; }
.float-agent-md :deep(ul), .float-agent-md :deep(ol) { padding-left: 16px; margin: 3px 0; }
.float-agent-md :deep(code) { background: var(--panel-solid); padding: 1px 4px; border-radius: 3px; font-size: 11px; }
.float-agent-md :deep(pre) { background: var(--panel-solid); padding: 6px 10px; border-radius: 4px; overflow-x: auto; margin: 4px 0; font-size: 12px; }
.float-agent-md :deep(blockquote) { border-left: 2px solid var(--gold); padding-left: 8px; margin: 4px 0; color: var(--text-dim); }
.float-agent-md :deep(strong) { font-weight: 700; }

/* 工具调用 */
.float-agent-tools { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
.float-agent-tool { font-size: 10px; padding: 2px 8px; border-radius: 4px; background: var(--panel-solid); color: var(--text-dim); display: flex; align-items: center; gap: 4px; }
.float-agent-tool-dot { width: 5px; height: 5px; border-radius: 50%; }
.float-agent-tool-dot.ok { background: var(--success); }
.float-agent-tool-dot.err { background: var(--danger); }
.float-agent-tool-dot.running { background: var(--gold); animation: float-dot 1s infinite; }
@keyframes float-dot { 0%,100% { opacity: 0.3; } 50% { opacity: 1; } }

/* HITL */
.float-agent-hitl { margin-top: 6px; padding: 8px 10px; border: 1px solid var(--gold); border-radius: 8px; background: var(--gold-bg); font-size: 11px; }
.float-agent-hitl-head {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  font-weight: 700; color: var(--gold); margin-bottom: 4px;
}
.float-agent-hitl-head small {
  padding: 1px 6px; border-radius: 999px; border: 1px solid var(--line-strong);
  color: var(--text-dim); font-size: 9px; text-transform: uppercase; font-weight: 600;
}
.float-agent-hitl-msg { margin: 0 0 6px; color: var(--text-dim); font-size: 10px; line-height: 1.4; }
.float-agent-hitl-field { margin-bottom: 4px; }
.float-agent-hitl-field label { display: block; font-size: 10px; color: var(--text-dim); text-transform: uppercase; margin-bottom: 2px; }
.float-agent-hitl-field span { font-size: 11px; color: var(--text); word-break: break-all; }
.float-agent-hitl-field input, .float-agent-hitl-field textarea {
  width: 100%; box-sizing: border-box; padding: 4px 6px; border: 1px solid var(--line-strong);
  border-radius: 4px; background: var(--panel); color: var(--text); font-size: 11px; font-family: inherit; outline: none;
}
.float-agent-hitl-field input:focus, .float-agent-hitl-field textarea:focus { border-color: var(--gold); }
.float-agent-hitl-actions { display: flex; gap: 6px; margin-top: 8px; }
.float-agent-hitl-ok { padding: 3px 14px; background: var(--gold); color: #fff; border: none; border-radius: 4px; font-size: 11px; cursor: pointer; }
.float-agent-hitl-no { padding: 3px 14px; background: transparent; color: var(--text-dim); border: 1px solid var(--line); border-radius: 4px; font-size: 11px; cursor: pointer; }
.float-agent-hitl-result { font-size: 11px; padding: 4px 8px; border-radius: 4px; margin-top: 6px; }
.float-agent-hitl-result.ok { background: var(--success-bg); color: var(--success); }
.float-agent-hitl-result.err { background: #ffe8e8; color: var(--danger); }
.float-agent-hitl-result.cancelled { background: var(--panel-2); color: var(--text-dim); }

/* 任务级反馈 */
.float-agent-feedback {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--line);
}
.float-agent-feedback-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.float-agent-feedback-actions button {
  width: 26px;
  height: 24px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--panel-solid);
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
}
.float-agent-feedback-actions button.active,
.float-agent-feedback-actions button:hover:not(:disabled) {
  border-color: var(--gold);
  background: var(--gold-bg);
}
.float-agent-feedback-actions button:disabled { opacity: 0.45; cursor: not-allowed; }
.float-agent-feedback-actions span {
  min-height: 16px;
  color: var(--text-muted);
  font-size: 10px;
}
.float-agent-feedback-comment {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  margin-top: 6px;
}
.float-agent-feedback-comment textarea {
  flex: 1;
  min-height: 36px;
  padding: 5px 7px;
  border: 1px solid var(--line-strong);
  border-radius: 5px;
  background: var(--panel);
  color: var(--text);
  font-size: 11px;
  font-family: inherit;
  resize: vertical;
  outline: none;
}
.float-agent-feedback-comment textarea:focus { border-color: var(--gold); }
.float-agent-feedback-comment button {
  padding: 5px 8px;
  border: none;
  border-radius: 5px;
  background: var(--gold);
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}
.float-agent-feedback-comment button:disabled { opacity: 0.45; cursor: not-allowed; }

/* 来源 */
.float-agent-sources { margin-top: 6px; border-top: 1px solid var(--line); padding-top: 6px; }
.float-agent-sources-head { font-size: 10px; font-weight: 600; color: var(--text-dim); margin-bottom: 4px; }
.float-agent-source { display: flex; align-items: center; gap: 6px; font-size: 10px; color: var(--text-dim); }
.float-agent-source-num {
  width: 16px; height: 16px; border-radius: 50%; background: var(--gold); color: #fff;
  font-size: 9px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}

/* loading */
.float-agent-loading { display: flex; align-items: center; gap: 5px; padding: 8px 12px; }
.float-agent-loading span { width: 6px; height: 6px; border-radius: 50%; background: var(--gold); animation: float-dot 1.2s infinite; }
.float-agent-loading span:nth-child(2) { animation-delay: 0.2s; }
.float-agent-loading span:nth-child(3) { animation-delay: 0.4s; }

/* 输入 */
.float-agent-input { display: flex; gap: 8px; padding: 10px 14px; border-top: 1px solid var(--line); flex-shrink: 0; }
.float-agent-input textarea {
  flex: 1; border: 1px solid var(--line); border-radius: 8px; background: var(--panel-2);
  color: var(--text); font-size: 13px; font-family: inherit; line-height: 1.5;
  resize: none; outline: none; padding: 8px 10px; min-height: 38px;
}
.float-agent-input textarea:focus { border-color: var(--gold); }
.float-agent-input textarea::placeholder { color: var(--text-muted); }
.float-agent-input button {
  padding: 8px 16px; border: none; border-radius: 8px; background: var(--gold);
  color: #fff; font-size: 13px; font-weight: 600; cursor: pointer; flex-shrink: 0;
}
.float-agent-input button:disabled { opacity: 0.35; cursor: not-allowed; }

@media (max-width: 520px) {
  .float-agent-header { padding: 10px 12px; gap: 8px; }
  .float-agent-header-icon { display: none; }
  .float-agent-header-left small { max-width: 120px; }
  .float-agent-header-actions { gap: 6px; }
  .float-agent-persona-select { width: 96px; padding: 0 6px; }
}
</style>
