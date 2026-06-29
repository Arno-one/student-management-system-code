<template>
  <section id="page-agent" class="page active">
    <div class="sub-bar">
      <label>智能 Agent 助手</label>
      <span class="sub-bar-hint">学业导师 · 成绩查询 · 知识问答 · 陪伴对话</span>
    </div>

    <div class="agent-workspace">
      <div id="agent-chat" class="card subcard show agent-chat-main">
        <!-- ====== 顶部操作栏 ====== -->
        <div class="agent-topbar">
          <div class="agent-topbar-left">
          <div class="agent-persona-row">
              <h3>{{ personaTitle(currentPersona) }}</h3>
              <CustomSelect v-model="selectedPersona" :options="personaOptions" :disabled="loading" />
            </div>
            <p class="hint">{{ currentPersona?.description || '学业导师，帮你查成绩、分析学业、回答问题' }}</p>
          </div>
          <div class="agent-topbar-right">
            <button class="agent-btn secondary" :disabled="loading" @click="newChat">
              + 新对话
            </button>
          </div>
        </div>

        <!-- ====== 消息列表 ====== -->
        <div class="agent-messages" ref="msgListRef">
          <div class="agent-empty" v-if="messages.length === 0 && !loading">
            <div class="agent-empty-icon">🤖</div>
            <p>和{{ currentPersona?.name || '学业导师' }}聊聊吧</p>
            <p class="agent-empty-sub">{{ emptyHint }}</p>
          </div>

          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="agent-msg"
            :class="'agent-msg-' + msg.role"
          >
            <div class="agent-msg-avatar">{{ msg.role === 'user' ? '我' : '师' }}</div>
            <div class="agent-msg-body">
            <!-- Assistant 等待首个流式片段时，复用当前消息气泡，避免额外生成一条带头像的 loading 消息 -->
            <div class="agent-loading" v-if="msg.role === 'assistant' && msg._streaming && !msg.content">
              <span class="agent-loading-dot"></span>
              <span class="agent-loading-dot"></span>
              <span class="agent-loading-dot"></span>
              <span class="agent-loading-text">正在思考...</span>
            </div>
            <!-- 流式输出中显示纯文本，完成后渲染 Markdown -->
            <div
              class="agent-msg-text"
              :class="{ 'streaming-cursor': msg._streaming, 'agent-msg-md': !msg._streaming && msg.role === 'assistant' }"
              v-else-if="msg._streaming || msg.role === 'user'"
            >{{ msg.content }}</div>
            <div
              class="agent-msg-text agent-msg-md"
              v-else
              v-html="renderMarkdown(msg.content)"
            ></div>

            <!-- 结构化卡片：自然语言回复继续走 Markdown，天气等结构化结果单独渲染 -->
            <div class="agent-cards" v-if="msg.cards?.length">
              <WeatherCard
                v-for="(card, ci) in msg.cards.filter(c => c.type === 'weather' && isCardVersionSupported(c))"
                :key="'weather-' + ci"
                :card="card"
              />
              <RouteCard
                v-for="(card, ci) in msg.cards.filter(c => c.type === 'route' && isCardVersionSupported(c))"
                :key="'route-' + ci"
                :card="card"
              />
              <PoiListCard
                v-for="(card, ci) in msg.cards.filter(c => c.type === 'poi_list' && isCardVersionSupported(c))"
                :key="'poi-list-' + ci"
                :card="card"
                @plan-route="fillRouteDraft"
              />
            </div>

            <!-- 工具调用摘要 -->
            <div class="agent-tool-calls" v-if="msg.toolCalls?.length">
              <div class="agent-tool-call" v-for="tc in msg.toolCalls" :key="tc.tool_name">
                <span class="agent-tool-dot" :class="tc.status === 'success' ? 'ok' : (tc.status === 'running' ? 'running' : 'err')"></span>
                <span class="agent-tool-name">{{ toolLabel(tc.tool_name) }}</span>
                <span class="agent-tool-summary">{{ tc.summary }}</span>
              </div>
            </div>

            <!-- HITL 确认卡片（邮件预览等） -->
            <div class="agent-hitl-card" v-if="msg.hitl">
              <div class="agent-hitl-header">
                <span>{{ msg.hitl.confirmTitle || '确认执行操作' }}</span>
                <small :class="'risk-' + (msg.hitl.riskLevel || 'medium')">{{ msg.hitl.riskLevel || 'medium' }}</small>
              </div>
              <p class="agent-hitl-message">{{ msg.hitl.confirmMessage || '请确认内容无误后再继续。' }}</p>
              <div class="agent-hitl-fields">
                <div class="agent-hitl-field">
                  <label>收件人</label>
                  <span>{{ msg.hitl.preview?.receiver || '-' }}</span>
                </div>
                <div class="agent-hitl-field">
                  <label>主题</label>
                  <input v-model="msg.hitl.preview.subject" class="agent-hitl-input" />
                </div>
                <div class="agent-hitl-field">
                  <label>正文</label>
                  <textarea v-model="msg.hitl.preview.body" class="agent-hitl-textarea" rows="6"></textarea>
                </div>
              </div>
              <div class="agent-hitl-actions" v-if="!msg.hitl.resolved">
                <button class="agent-btn agent-hitl-confirm" :disabled="msg.hitl.loading" @click="confirmHitl(msg)">确认发送</button>
                <button class="agent-btn agent-hitl-cancel" :disabled="msg.hitl.loading" @click="cancelHitl(msg)">取消</button>
              </div>
              <div class="agent-hitl-result" :class="msg.hitl.resultStatus" v-else>
                {{ msg.hitl.resultMsg }}
              </div>
            </div>

              <!-- 任务级反馈：绑定 AgentTask.id，同一轮对话只能提交一次 -->
            <div class="agent-feedback" v-if="msg.role === 'assistant' && msg.feedback?.taskId && !msg._streaming">
              <div class="agent-feedback-actions">
                <button
                  class="agent-feedback-btn"
                  :class="{ active: msg.feedback.rating === 5 }"
                  :disabled="msg.feedback.loading || msg.feedback.submitted"
                  @click="rateFeedback(msg, 5)"
                >👍 满意</button>
                <button
                  class="agent-feedback-btn"
                  :class="{ active: msg.feedback.rating === 1 }"
                  :disabled="msg.feedback.loading || msg.feedback.submitted"
                  @click="rateFeedback(msg, 1)"
                >👎 不满意</button>
                <span class="agent-feedback-status">{{ msg.feedback.status }}</span>
              </div>
              <div class="agent-feedback-comment" v-if="msg.feedback.open && !msg.feedback.submitted">
                <textarea
                  v-model="msg.feedback.draftComment"
                  rows="2"
                  maxlength="1000"
                  placeholder="可以简单说说哪里不够好，方便后续优化"
                ></textarea>
                <button
                  class="agent-feedback-save"
                  :disabled="msg.feedback.loading || !msg.feedback.draftComment.trim()"
                  @click="submitFeedback(msg, msg.feedback.rating || 1, true)"
                >提交原因</button>
              </div>
            </div>

            <!-- 知识来源 -->
            <div class="agent-sources" v-if="msg.sources?.length">
              <div class="agent-sources-head">参考来源</div>
              <div class="agent-source-item" v-for="(src, si) in msg.sources" :key="si">
                <span class="agent-source-num">{{ si + 1 }}</span>
                <span class="agent-source-type" :class="'src-' + src.source_type">{{ src.source_type === 'md' ? '校务' : src.source_type === 'qa' ? '问答' : '原文' }}</span>
                <span class="agent-source-file">{{ src.file_name }}</span>
                <span class="agent-source-preview">{{ src.text_preview }}</span>
              </div>
            </div>
            </div>
          </div>

        </div>

        <!-- ====== 示例问题（无消息时展示） ====== -->
        <div class="rag-examples" v-if="messages.length === 0">
          <span class="rag-examples-label">试试问</span>
          <button v-for="q in exampleQuestions" :key="q" class="rag-example-chip"
            :disabled="loading" @click="form.message = q; doSend()">{{ q }}</button>
        </div>

        <!-- ====== 输入区 ====== -->
        <div class="agent-input-area">
          <textarea
            v-model="form.message"
            placeholder="输入你想问的..."
            :disabled="loading"
            rows="2"
            @keydown.ctrl.enter="doSend"
            @keydown.meta.enter="doSend"
          ></textarea>
          <div class="agent-input-bar">
            <span class="rag-input-count">{{ form.message.length }} / 2000</span>
            <button class="rag-submit-btn" :disabled="loading || !form.message.trim()" @click="doSend">
              <span class="rag-submit-icon">→</span>
              <span>{{ loading ? '思考中...' : '发送' }}</span>
            </button>
          </div>
        </div>
      </div>

      <aside class="agent-summary-panel">
        <div class="agent-summary-head">
          <div>
            <h4>历史摘要</h4>
            <p>只展示每轮多轮对话的摘要内容</p>
          </div>
          <button class="agent-summary-new" :disabled="loading" @click="newChat">+</button>
        </div>
        <div class="agent-summary-loading" v-if="sessionsLoading">
          历史摘要加载中...
        </div>
        <div class="agent-summary-error" v-else-if="sessionsLoadError">
          <span>{{ sessionsLoadError }}</span>
          <button type="button" class="agent-summary-retry" @click="loadSessions()">重新加载</button>
        </div>
        <div class="agent-summary-empty" v-else-if="sessions.length === 0">
          暂无历史摘要
        </div>
        <div v-else class="agent-summary-list">
          <button
            v-for="s in sessions"
            :key="s.id"
            class="agent-summary-item"
            :class="{ active: s.id === currentSessionId }"
            @click="loadSession(s.id)"
          >
            <span class="agent-summary-text">{{ sessionSummary(s) }}</span>
            <span class="agent-summary-time">{{ fmtTime(s.update_time || s.create_time) }}</span>
          </button>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, computed, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import { request, getBaseUrl, getAuthHeader } from '../api'
import CustomSelect from '../components/CustomSelect.vue'
import WeatherCard from '../components/WeatherCard.vue'
import RouteCard from '../components/RouteCard.vue'
import PoiListCard from '../components/PoiListCard.vue'
import { fallbackAgentPersonas } from '../config/agentPersonas'

// 配置 marked 不渲染原始 HTML（防止 XSS）
marked.setOptions({ breaks: true, gfm: true })

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

const loading = ref(false)
const messages = ref([])
const sessions = ref([])
const sessionsLoading = ref(false)
const sessionsLoadError = ref('')
const personas = ref([...fallbackAgentPersonas])
const selectedPersona = ref('academic_mentor')
const currentSessionId = ref(null)
const msgListRef = ref(null)

const form = reactive({ message: '' })

const currentPersona = computed(() => personas.value.find(p => p.id === selectedPersona.value))
const personaOptions = computed(() => personas.value.map(p => ({ value: p.id, label: personaTitle(p) })))

const personaExamples = {
  academic_mentor: [
    '帮我查一下我的成绩',
    '我最近成绩有进步吗',
    '系统里怎么查作业',
    '请假流程是怎样的',
    '快要考试了好紧张',
    '帮我赏析"长风破浪会有时"',
  ],
  companion_head_teacher: [
    '最近压力有点大，能陪我梳理一下吗',
    '我总是拖延，今天该先做什么',
    '快考试了我很焦虑，怎么缓一缓',
    '我和同学相处有点别扭，想聊聊',
    '帮我做一个今晚能完成的小计划',
    '我今天状态不好，但又不想放弃',
  ],
  xinge: [
    '昕哥，我这次又粗心错题了，帮我复盘下',
    '好兄弟，我最近学习有点没劲',
    '我这个错误以后怎么避免？',
    '帮我把今天要做的事拆一下',
    '从宝安中心到龙岗坐地铁怎么去',
    '帮我写封邮件给老师说明情况',
  ],
}

const personaEmptyHints = {
  academic_mentor: '可以查成绩、问制度、聊学习，也可以说说心里话',
  companion_head_teacher: '可以聊压力、拖延、考试焦虑，也可以一起拆一个小计划',
  xinge: '可以让昕哥帮你复盘错误、鼓劲打气、拆下一步行动',
}

const exampleQuestions = computed(() => personaExamples[selectedPersona.value] || personaExamples.academic_mentor)
const emptyHint = computed(() => personaEmptyHints[selectedPersona.value] || personaEmptyHints.academic_mentor)

function toolLabel(name) {
  const map = {
    score_tool: '成绩查询',
    rag_tool: '知识检索',
    nl2sql_tool: '数据查询',
    student_tool: '身份识别',
    weather_tool: '天气查询',
    commute_plan_tool: '通勤规划',
    nearby_service_tool: '周边服务',
  }
  return map[name] || name
}

function personaTitle(persona) {
  if (!persona) return '🎓 学业导师'
  return [persona.icon, persona.name].filter(Boolean).join(' ')
}

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function normalizeSessions(payload) {
  // 兼容后端直接返回数组，或将列表包在常见字段里的情况
  if (Array.isArray(payload)) return payload.filter(item => item && typeof item === 'object')
  if (payload && typeof payload === 'object') {
    for (const key of ['items', 'list', 'records', 'rows', 'result']) {
      if (Array.isArray(payload[key])) {
        return payload[key].filter(item => item && typeof item === 'object')
      }
    }
  }
  return []
}

function sessionSummary(session) {
  // 旧会话可能还没生成 summary，这里优先回退到 title，避免列表看起来像“没数据”
  const summary = String(session?.summary || session?.title || '').trim()
  if (summary) return summary
  return '摘要生成中，继续对话后会自动更新。'
}

function isCardVersionSupported(card) {
  return !card?.card_version || card.card_version === 1
}

function createFeedback(taskId = null, saved = null) {
  const submitted = !!saved?.submitted
  return {
    taskId,
    rating: saved?.rating || null,
    draftComment: saved?.comment || '',
    open: false,
    loading: false,
    submitted,
    status: submitted ? '已记录反馈' : '',
  }
}

async function loadSessions({ silent = false } = {}) {
  if (!silent) {
    sessionsLoading.value = true
    sessionsLoadError.value = ''
  }
  try {
    const r = await request('GET', '/agent/sessions')
    if (r.ok && r.data?.code === 200) {
      sessions.value = normalizeSessions(r.data.data)
      return
    }
    if (!silent) {
      if (r.status === 401) {
        sessionsLoadError.value = '登录状态已失效，请重新登录后查看历史摘要'
        return
      }
      sessionsLoadError.value = r.data?.msg || `历史摘要加载失败（${r.status || '未知状态'}）`
    }
  } catch (_) {
    if (!silent) {
      sessionsLoadError.value = '历史摘要加载失败，请检查后端服务或稍后重试'
    }
  } finally {
    if (!silent) {
      sessionsLoading.value = false
    }
  }
}

async function loadSession(sessionId) {
  currentSessionId.value = sessionId
  try {
    const r = await request('GET', `/agent/sessions/${sessionId}/messages`)
    if (r.ok && r.data?.code === 200) {
      const raw = r.data.data || []
      messages.value = raw.map(m => ({
        role: m.role,
        content: m.role === 'user' ? m.content : m.reply,
        toolCalls: m.metadata?.tool_calls || null,
        sources: m.metadata?.sources || null,
        cards: m.metadata?.cards || null,
        feedback: m.role === 'assistant' && m.metadata?.task_id
          ? createFeedback(m.metadata.task_id, m.metadata.feedback)
          : null,
        // 从持久化 metadata 重建 HITL 卡片
        hitl: m.metadata?.hitl ? {
          tool_name: m.metadata.hitl.tool_name,
          stepId: m.metadata.hitl.step_id || 1,
          preview: m.metadata.hitl.preview || {},
          riskLevel: m.metadata.hitl.risk_level || 'medium',
          timeoutSeconds: m.metadata.hitl.timeout_seconds || 600,
          expiresAt: m.metadata.hitl.expires_at || null,
          confirmTitle: m.metadata.hitl.confirm_title || '确认执行操作',
          confirmMessage: m.metadata.hitl.confirm_message || '请确认内容无误后再继续。',
          resolved: m.metadata.hitl.resolved || false,
          loading: false,
          resultStatus: m.metadata.hitl.resultStatus || '',
          resultMsg: m.metadata.hitl.resultMsg || '',
        } : null,
      }))
      scrollBottom()
    }
  } catch (_) { /* 静默失败 */ }
}

function newChat() {
  currentSessionId.value = null
  messages.value = []
}

function fillRouteDraft(destination) {
  form.message = `从 [请补充起点] 到 ${destination} 怎么去？`
}

async function doSend() {
  const text = form.message.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  form.message = ''
  loading.value = true
  scrollBottom()

  // 创建空的 assistant 消息占位
  const msgIdx = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    toolCalls: [],
    sources: null,
    cards: null,
    feedback: createFeedback(),
    _streaming: true,
  })

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
      messages.value[msgIdx] = { role: 'assistant', content: `请求失败 (${resp.status})`, toolCalls: null, sources: null }
      return
    }

    // 解析 SSE 流
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const currentMsg = () => messages.value[msgIdx]

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''  // 保留不完整的行

      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            handleSSE(eventType, data, currentMsg, msgIdx)
          } catch (_) { /* 跳过解析失败的行 */ }
          eventType = ''
        }
      }
    }

    // 标记流结束
    if (currentMsg()) currentMsg()._streaming = false
  } catch (e) {
    messages.value[msgIdx] = { role: 'assistant', content: '网络错误：' + e.message, toolCalls: null, sources: null }
  } finally {
    loading.value = false
    scrollBottom()
    loadSessions({ silent: true })
  }
}

function handleSSE(event, data, currentMsg, msgIdx) {
  if (!currentMsg()) return

  switch (event) {
    case 'intent':
      break
    case 'guard_pass':
    case 'rewritten':
      break
    case 'error':
      currentMsg().content = data.message || '请求被拒绝'
      currentMsg()._streaming = false
      break
    case 'session':
      currentSessionId.value = data.session_id
      break
    case 'plan':
      // 计划信息供内部使用
      break
    case 'tool_start':
      if (!currentMsg().toolCalls) currentMsg().toolCalls = []
      currentMsg().toolCalls.push({
        tool_name: data.tool_name,
        status: 'running',
        summary: '执行中...',
      })
      scrollBottom()
      break
    case 'tool_end':
      // 更新对应的 tool call 状态
      if (currentMsg().toolCalls) {
        const tc = currentMsg().toolCalls.find(t => t.tool_name === data.tool_name && t.status === 'running')
        if (tc) {
          tc.status = data.status
          tc.summary = data.summary || ''
        }
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
      // HITL: 暂停流，展示确认卡片
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
  }
}

async function rateFeedback(msg, rating) {
  if (!msg.feedback?.taskId || msg.feedback.loading || msg.feedback.submitted) return
  msg.feedback.rating = rating
  if (rating === 1) {
    msg.feedback.open = true
    msg.feedback.status = '请填写原因后提交'
    return
  }
  msg.feedback.open = false
  await submitFeedback(msg, rating, false)
}

async function submitFeedback(msg, rating, withComment = false) {
  if (!msg.feedback?.taskId || msg.feedback.loading || msg.feedback.submitted) return
  const comment = withComment ? msg.feedback.draftComment.trim() : ''
  if (withComment && !comment) {
    msg.feedback.status = '请先填写原因'
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
      msg.feedback.status = '已记录反馈'
    } else {
      if (r.status === 409) msg.feedback.submitted = true
      msg.feedback.status = r.data?.detail || r.data?.msg || '反馈提交失败'
    }
  } catch (e) {
    msg.feedback.status = '网络错误：' + e.message
  } finally {
    msg.feedback.loading = false
  }
}

async function confirmHitl(msg) {
  if (!msg.hitl || msg.hitl.resolved) return
  msg.hitl.loading = true
  try {
    const r = await request('POST', '/agent/step/confirm', {
      body: {
        task_id: String(currentSessionId.value || 'default'),
        step_id: msg.hitl.stepId || 1,
        confirmed: true,
        modified_params: {
          subject: msg.hitl.preview.subject,
          body: msg.hitl.preview.body,
          receiver: msg.hitl.preview.receiver,
        },
      },
    })
    if (r.ok && r.data?.code === 200) {
      msg.hitl.resolved = true
      msg.hitl.resultStatus = 'ok'
      msg.hitl.resultMsg = r.data.data?.message || '邮件已发送'
    } else {
      msg.hitl.resolved = true
      msg.hitl.resultStatus = 'err'
      msg.hitl.resultMsg = r.data?.detail || '发送失败'
    }
  } catch (e) {
    msg.hitl.resolved = true
    msg.hitl.resultStatus = 'err'
    msg.hitl.resultMsg = '网络错误：' + e.message
  } finally {
    msg.hitl.loading = false
  }
}

async function cancelHitl(msg) {
  if (!msg.hitl || msg.hitl.resolved) return
  msg.hitl.loading = true
  try {
    await request('POST', '/agent/step/confirm', {
      body: { task_id: String(currentSessionId.value || 'default'), step_id: msg.hitl.stepId || 1, confirmed: false },
    })
  } catch (_) { /* 静默 */ }
  msg.hitl.resolved = true
  msg.hitl.resultStatus = 'cancelled'
  msg.hitl.resultMsg = '已取消'
  msg.hitl.loading = false
}

function scrollBottom() {
  nextTick(() => {
    const el = msgListRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function loadPersonas() {
  try {
    const r = await request('GET', '/agent/personas')
    if (r.ok && r.data?.code === 200 && Array.isArray(r.data.data) && r.data.data.length > 0) {
      personas.value = r.data.data
      if (personas.value.length > 0 && !personas.value.find(p => p.id === selectedPersona.value)) {
        selectedPersona.value = personas.value[0].id
      }
    }
  } catch (_) { /* 静默失败，保留前端兜底角色 */ }
}

onMounted(() => {
  loadPersonas()
  loadSessions()
})
</script>

<style scoped>
.sub-bar-hint { margin-left: auto; font-size: 12px; color: var(--text-dim); opacity: 0.7; }

.agent-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
  gap: 16px;
  align-items: start;
}

.agent-chat-main {
  min-width: 0;
}

/* ====== 顶部 ====== */
.agent-topbar {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 16px;
}
.agent-topbar-left h3 {
  margin: 0 0 4px; font-family: var(--font-display); font-size: 22px; color: var(--text);
}
.agent-topbar-left .hint { margin: 4px 0 0; font-size: 13px; color: var(--text-dim); }
.agent-persona-row { display: flex; align-items: center; gap: 12px; }

.agent-btn {
  padding: 7px 16px; border: 1px solid var(--line-strong); border-radius: var(--radius-sm);
  background: var(--panel); color: var(--text-soft); font-size: 13px; cursor: pointer;
  transition: all var(--dur-fast);
  white-space: nowrap;
}
.agent-btn:hover:not(:disabled) { border-color: var(--gold); color: var(--gold); }
.agent-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ====== 右侧历史摘要 ====== */
.agent-summary-panel {
  position: sticky;
  top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: calc(100vh - 140px);
  padding: 14px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--panel-solid);
  box-shadow: var(--shadow-sm);
  overflow-y: auto;
}

.agent-summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.agent-summary-head h4 {
  margin: 0;
  color: var(--text);
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0;
}

.agent-summary-head p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
}

.agent-summary-new {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  border: 1px solid var(--line-strong);
  border-radius: 7px;
  background: var(--panel-2);
  color: var(--text-soft);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.agent-summary-new:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
  background: var(--gold-bg);
}

.agent-summary-new:disabled { opacity: 0.4; cursor: not-allowed; }

.agent-summary-empty {
  padding: 18px 10px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.agent-summary-loading,
.agent-summary-error {
  display: grid;
  gap: 10px;
  padding: 18px 10px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.agent-summary-list {
  display: grid;
  gap: 8px;
}

.agent-summary-retry {
  justify-self: center;
  padding: 6px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--panel-2);
  color: var(--text-soft);
  cursor: pointer;
  font-size: 12px;
}

.agent-summary-retry:hover {
  border-color: var(--gold);
  color: var(--gold);
  background: var(--gold-bg);
}

.agent-summary-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel-2);
  color: var(--text-soft);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--dur-fast), background var(--dur-fast), transform var(--dur-fast);
}

.agent-summary-item:hover {
  border-color: var(--gold);
  transform: translateY(-1px);
}

.agent-summary-item.active {
  border-color: var(--gold);
  background: var(--gold-bg);
}

.agent-summary-text {
  display: -webkit-box;
  overflow: hidden;
  color: var(--text);
  font-size: 13px;
  font-weight: 650;
  line-height: 1.55;
  overflow-wrap: anywhere;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
}

.agent-summary-time {
  color: var(--text-muted);
  font-size: 11px;
}

/* ====== 消息列表 ====== */
.agent-messages {
  min-height: 280px; max-height: 520px; overflow-y: auto;
  padding: 8px 0; margin-bottom: 16px;
}

.agent-empty { text-align: center; padding: 40px 20px; color: var(--text-dim); }
.agent-empty-icon { font-size: 40px; margin-bottom: 8px; }
.agent-empty p { margin: 4px 0; font-size: 14px; }
.agent-empty-sub { font-size: 12px; opacity: 0.5; }

.agent-msg {
  display: flex; gap: 12px; margin-bottom: 16px;
}
.agent-msg-user { flex-direction: row-reverse; }
.agent-msg-avatar {
  width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0;
}
.agent-msg-user .agent-msg-avatar { background: var(--gold); color: #fff; }
.agent-msg-assistant .agent-msg-avatar { background: var(--panel-2); color: var(--gold); border: 1px solid var(--gold); }

.agent-msg-body { max-width: 80%; }
.agent-msg-user .agent-msg-body { text-align: right; }

.agent-msg-text {
  padding: 10px 16px; border-radius: var(--radius-sm); font-size: 14px; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word;
}
.agent-msg-user .agent-msg-text { background: var(--gold-bg); color: var(--text); }
.agent-msg-assistant .agent-msg-text { background: var(--panel-solid); border: 1px solid var(--line); color: var(--text); }

/* ====== Markdown 渲染 ====== */
.agent-msg-md :deep(h1), .agent-msg-md :deep(h2), .agent-msg-md :deep(h3) { margin: 8px 0 4px; font-weight: 700; color: var(--text); }
.agent-msg-md :deep(h1) { font-size: 18px; }
.agent-msg-md :deep(h2) { font-size: 16px; }
.agent-msg-md :deep(h3) { font-size: 14px; }
.agent-msg-md :deep(p) { margin: 4px 0; }
.agent-msg-md :deep(ul), .agent-msg-md :deep(ol) { padding-left: 18px; margin: 4px 0; }
.agent-msg-md :deep(li) { margin: 2px 0; }
.agent-msg-md :deep(code) { background: var(--panel-2); padding: 1px 5px; border-radius: 3px; font-size: 12px; font-family: 'JetBrains Mono', 'Fira Code', monospace; }
.agent-msg-md :deep(pre) { background: var(--panel-2); padding: 10px 14px; border-radius: 6px; overflow-x: auto; margin: 6px 0; }
.agent-msg-md :deep(pre code) { background: none; padding: 0; }
.agent-msg-md :deep(blockquote) { border-left: 3px solid var(--gold); padding-left: 12px; margin: 6px 0; color: var(--text-dim); }
.agent-msg-md :deep(strong) { font-weight: 700; }
.agent-msg-md :deep(em) { font-style: italic; }
.agent-msg-md :deep(table) { border-collapse: collapse; margin: 6px 0; font-size: 12px; }
.agent-msg-md :deep(th), .agent-msg-md :deep(td) { border: 1px solid var(--line); padding: 4px 8px; text-align: left; }
.agent-msg-md :deep(th) { background: var(--panel-2); font-weight: 600; }

/* ====== 工具调用 ====== */
.agent-tool-calls { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.agent-tool-call {
  display: flex; align-items: center; gap: 6px; padding: 4px 10px;
  background: var(--panel-2); border-radius: 6px; font-size: 12px; color: var(--text-dim);
}
.agent-tool-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.agent-tool-dot.ok { background: var(--success); }
.agent-tool-dot.err { background: var(--danger); }
.agent-tool-name { font-weight: 600; color: var(--text-soft); }
.agent-tool-summary { color: var(--text-muted); }

/* ====== 来源 ====== */
.agent-sources { margin-top: 10px; border-top: 1px solid var(--line); padding-top: 8px; }
.agent-sources-head { font-size: 11px; font-weight: 600; color: var(--text-dim); margin-bottom: 6px; }
.agent-source-item { display: flex; align-items: baseline; gap: 8px; padding: 3px 0; font-size: 11px; }
.agent-source-num {
  width: 18px; height: 18px; border-radius: 50%; background: var(--gold); color: #fff;
  font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.agent-source-type {
  font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 3px;
  text-transform: uppercase; flex-shrink: 0;
}
.src-md { background: var(--blue-bg); color: var(--blue); }
.src-qa { background: var(--success-bg); color: var(--success); }
.src-txt { background: var(--gold-bg); color: var(--gold); }
.agent-source-file { color: var(--text-dim); flex-shrink: 0; }
.agent-source-preview { color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }

/* ====== Loading ====== */
.agent-loading { display: flex; align-items: center; gap: 6px; padding: 10px 16px; }
.agent-loading-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--gold); animation: agent-dot 1.2s ease-in-out infinite; }
.agent-loading-dot:nth-child(2) { animation-delay: 0.2s; }
.agent-loading-dot:nth-child(3) { animation-delay: 0.4s; }
.agent-loading-text { margin-left: 6px; font-size: 13px; color: var(--text-dim); }
@keyframes agent-dot {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

/* ====== 输入区 ====== */
.agent-input-area {
  border: 1px solid var(--line-strong); border-radius: var(--radius-sm);
  overflow: hidden; background: var(--panel-solid);
}
.agent-input-area textarea {
  width: 100%; border: none; background: transparent; color: var(--text);
  font-size: 14px; font-family: inherit; line-height: 1.7; resize: vertical;
  min-height: 52px; outline: none; padding: 12px 16px;
}
.agent-input-area textarea::placeholder { color: var(--text-muted); }
.agent-input-area textarea:disabled { opacity: 0.45; }
.agent-input-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 16px; border-top: 1px solid var(--line);
}

/* ====== 复用 RAG 样式（示例问题、提交按钮、字符数） ====== */
.rag-examples {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  padding: 8px 0; margin-bottom: 4px;
}
.rag-examples-label {
  font-size: 12px; font-weight: 600; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.3px; white-space: nowrap;
}
.rag-example-chip {
  padding: 4px 12px; border-radius: 16px;
  border: 1px solid var(--line-strong); background: var(--panel-3);
  color: var(--text-soft); font-size: 12px; cursor: pointer;
  transition: all var(--dur-fast) var(--ease-out); white-space: nowrap;
}
.rag-example-chip:hover:not(:disabled) {
  border-color: var(--gold); color: var(--gold); background: var(--gold-bg);
}
.rag-example-chip:disabled { opacity: 0.35; cursor: not-allowed; }

.rag-input-count { font-size: 11px; color: var(--text-muted); }
.rag-submit-btn {
  display: flex; align-items: center; gap: 6px; margin-left: auto;
  padding: 7px 18px; border: none; border-radius: 8px;
  background: var(--gold); color: #fff; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: opacity var(--dur-fast), transform var(--dur-fast);
}
.rag-submit-btn:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
.rag-submit-btn:active:not(:disabled) { transform: translateY(0); }
.rag-submit-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.rag-submit-icon { font-size: 16px; }

.agent-tool-dot.running { background: var(--gold); animation: dot-pulse 1s ease-in-out infinite; }
@keyframes dot-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }

/* ====== HITL 确认卡片 ====== */
.agent-hitl-card {
  margin-top: 10px; border: 1px solid var(--gold); border-radius: var(--radius-sm);
  background: var(--gold-bg); padding: 14px 16px;
}
.agent-hitl-header {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  font-size: 14px; font-weight: 700; color: var(--gold); margin-bottom: 6px;
}
.agent-hitl-header small {
  padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line-strong);
  font-size: 10px; text-transform: uppercase; color: var(--text-dim); background: var(--panel-2);
}
.agent-hitl-header small.risk-high { color: var(--danger); border-color: var(--danger); }
.agent-hitl-message { margin: 0 0 10px; color: var(--text-dim); font-size: 12px; line-height: 1.5; }
.agent-hitl-fields { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.agent-hitl-field { display: flex; flex-direction: column; gap: 4px; }
.agent-hitl-field label { font-size: 11px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; }
.agent-hitl-field span { font-size: 13px; color: var(--text); word-break: break-all; }
.agent-hitl-input, .agent-hitl-textarea {
  padding: 6px 10px; border: 1px solid var(--line-strong); border-radius: 4px;
  background: var(--panel); color: var(--text); font-size: 13px; font-family: inherit; outline: none;
  width: 100%; box-sizing: border-box;
}
.agent-hitl-input:focus, .agent-hitl-textarea:focus { border-color: var(--gold); }
.agent-hitl-textarea { resize: vertical; }
.agent-hitl-actions { display: flex; gap: 8px; }
.agent-hitl-confirm { background: var(--gold) !important; color: #fff !important; border-color: var(--gold) !important; }
.agent-hitl-cancel { background: transparent !important; color: var(--text-dim) !important; }
.agent-hitl-result { font-size: 13px; padding: 6px 10px; border-radius: 4px; }
.agent-hitl-result.ok { background: var(--success-bg); color: var(--success); }
.agent-hitl-result.err { background: var(--danger-bg, #ffe8e8); color: var(--danger); }
.agent-hitl-result.cancelled { background: var(--panel-2); color: var(--text-dim); }

/* ====== 任务级反馈 ====== */
.agent-feedback {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
}
.agent-feedback-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.agent-feedback-btn {
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--panel-2);
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--dur-fast);
}
.agent-feedback-btn:hover:not(:disabled),
.agent-feedback-btn.active {
  border-color: var(--gold);
  color: var(--gold);
  background: var(--gold-bg);
}
.agent-feedback-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.agent-feedback-status { font-size: 12px; color: var(--text-muted); min-height: 18px; }
.agent-feedback-comment {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  margin-top: 8px;
}
.agent-feedback-comment textarea {
  flex: 1;
  min-height: 44px;
  padding: 7px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--panel);
  color: var(--text);
  font-size: 12px;
  font-family: inherit;
  resize: vertical;
  outline: none;
}
.agent-feedback-comment textarea:focus { border-color: var(--gold); }
.agent-feedback-save {
  padding: 7px 12px;
  border: none;
  border-radius: 6px;
  background: var(--gold);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.agent-feedback-save:disabled { opacity: 0.45; cursor: not-allowed; }

/* ====== 流式光标动画 ====== */
.streaming-cursor::after {
  content: '▊'; color: var(--gold);
  animation: cursor-blink 0.8s step-end infinite;
}
@keyframes cursor-blink {
  50% { opacity: 0; }
}

@media (max-width: 1120px) {
  .agent-workspace {
    grid-template-columns: minmax(0, 1fr);
  }

  .agent-summary-panel {
    position: static;
    max-height: 320px;
  }
}

@media (max-width: 680px) {
  .agent-topbar,
  .agent-summary-head {
    flex-direction: column;
    align-items: stretch;
  }

  .agent-persona-row {
    flex-direction: column;
    align-items: stretch;
  }

  .agent-msg-body {
    max-width: 88%;
  }
}
</style>
