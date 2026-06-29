<template>
  <section id="page-rag" class="page active">
    <div class="rag-shell">
      <div class="rag-hero card">
        <div class="rag-hero-copy">
          <p class="rag-kicker">Retrieval Workspace</p>
          <h2>RAG 知识库工作台</h2>
          <p class="rag-summary">
            把经典文学问答与工程文档检索拆成两个独立工作区，避免混检，也方便后续继续扩更多知识库。
          </p>
        </div>
        <div class="rag-mode-strip">
          <button
            v-for="mode in modeList"
            :key="mode.key"
            type="button"
            class="rag-mode-card"
            :class="{ active: sub === mode.key }"
            @click="switchMode(mode.key)"
          >
            <span class="rag-mode-name">{{ mode.name }}</span>
            <span class="rag-mode-tag">{{ mode.tag }}</span>
            <span class="rag-mode-desc">{{ mode.desc }}</span>
          </button>
        </div>
      </div>

      <div class="rag-grid">
        <aside class="rag-side card">
          <div class="rag-side-head">
            <span class="rag-side-title">当前入口</span>
            <span class="rag-side-badge">{{ currentMode.tag }}</span>
          </div>

          <h3>{{ currentMode.name }}</h3>
          <p class="rag-side-desc">{{ currentMode.longDesc }}</p>

          <div class="rag-notice" :class="`notice-${currentMode.accent}`">
            <strong>{{ currentMode.noticeTitle }}</strong>
            <p>{{ currentMode.noticeText }}</p>
          </div>

          <div class="rag-status-box">
            <div class="rag-status-head">
              <span>知识库状态</span>
              <button type="button" class="rag-link-btn" :disabled="currentPanel.statusLoading" @click="loadStatus(sub, true)">
                {{ currentPanel.statusLoading ? '刷新中...' : '刷新' }}
              </button>
            </div>

            <div v-if="currentPanel.statusData" class="rag-status-list">
              <div class="rag-status-item">
                <span>知识库 ID</span>
                <strong>{{ currentPanel.statusData.kb_id }}</strong>
              </div>
              <div class="rag-status-item">
                <span>Collection</span>
                <strong>{{ currentPanel.statusData.collection_name }}</strong>
              </div>
              <div class="rag-status-item">
                <span>切片总数</span>
                <strong>{{ currentPanel.statusData.total_chunks }}</strong>
              </div>
              <div class="rag-status-item">
                <span>文档数</span>
                <strong>{{ currentPanel.statusData.files?.length || 0 }}</strong>
              </div>
            </div>

            <div v-if="currentPanel.statusData?.files?.length" class="rag-file-list">
              <span class="rag-file-title">已加载文件</span>
              <span v-for="file in currentPanel.statusData.files" :key="file" class="rag-file-chip">{{ file }}</span>
            </div>

            <ResultBadge :badge="currentPanel.statusBadge" :text="currentPanel.statusText" />
          </div>
        </aside>

        <div class="rag-main card">
          <div class="sub-bar">
            <label>{{ currentMode.headerLabel }}</label>
            <span class="sub-bar-hint">{{ currentMode.headerHint }}</span>
          </div>

          <div class="rag-query-card">
            <div class="rag-examples">
              <span class="rag-examples-label">快速试问</span>
              <button
                v-for="question in currentMode.examples"
                :key="question"
                type="button"
                class="rag-example-chip"
                :disabled="currentPanel.loading"
                @click="fillQuestion(question)"
              >
                {{ question }}
              </button>
            </div>

            <div class="rag-input-area">
              <textarea
                v-model="currentPanel.form.question"
                :placeholder="currentMode.placeholder"
                :disabled="currentPanel.loading"
                rows="4"
                @keydown.ctrl.enter="doAsk(sub)"
                @keydown.meta.enter="doAsk(sub)"
              ></textarea>

              <div class="rag-input-bar">
                <label class="rag-toggle">
                  <input v-model="currentPanel.form.enableRerank" type="checkbox" />
                  <span class="rag-toggle-track"><span class="rag-toggle-thumb"></span></span>
                  <span class="rag-toggle-label">启用精排</span>
                </label>

                <label class="rag-topk">
                  <span>Top K</span>
                  <input v-model.number="currentPanel.form.topK" type="number" min="1" max="10" />
                </label>

                <span class="rag-input-count">{{ currentPanel.form.question.length }} / 500</span>

                <button
                  type="button"
                  class="rag-submit-btn"
                  :disabled="currentPanel.loading || !currentPanel.form.question.trim()"
                  @click="doAsk(sub)"
                >
                  <span class="rag-submit-icon">↗</span>
                  <span>{{ currentPanel.loading ? '检索中...' : '开始检索' }}</span>
                </button>
              </div>
            </div>
          </div>

          <div v-if="currentPanel.loading" class="rag-loading">
            <span class="rag-loading-dot"></span>
            <span class="rag-loading-dot"></span>
            <span class="rag-loading-dot"></span>
            <span class="rag-loading-text">{{ currentMode.loadingText }}</span>
          </div>

          <template v-else-if="currentPanel.answerData">
            <div class="rag-meta-row">
              <span v-for="item in traceSummary(currentPanel.answerData.trace)" :key="item.label" class="rag-meta-pill">
                <em>{{ item.label }}</em>
                <strong>{{ item.value }}</strong>
              </span>
            </div>

            <div v-if="currentPanel.answerData.rewritten_query" class="rag-rewrite">
              <span class="rag-rewrite-label">检索改写</span>
              <span class="rag-rewrite-text">{{ currentPanel.answerData.rewritten_query }}</span>
            </div>

            <div class="rag-answer-card" :class="{ 'rag-answer-card--refuse': currentPanel.answerData.trace?.answer_mode === 'refuse' }">
              <div class="rag-answer-head">
                <span class="rag-answer-icon">{{ currentPanel.answerData.trace?.answer_mode === 'refuse' ? '!' : '✓' }}</span>
                <span>{{ answerModeLabel(currentPanel.answerData.trace?.answer_mode) }}</span>
                <span class="rag-answer-badge">{{ currentMode.answerBadge }}</span>
              </div>
              <div class="rag-answer-body" v-html="renderAnswer(currentPanel.answerData.answer)"></div>
            </div>

            <div v-if="currentPanel.answerData.citations?.length" class="rag-citations">
              <div class="rag-citations-head">
                <span>参考来源</span>
                <span class="rag-citations-count">{{ currentPanel.answerData.citations.length }} 条</span>
              </div>
              <div class="rag-citation-list">
                <div v-for="citation in currentPanel.answerData.citations" :key="citation.source_id + '-' + citation.chunk_index" class="rag-citation-item">
                  <span class="rag-citation-num">{{ citation.source_id }}</span>
                  <span class="rag-citation-type" :class="`tag-${citation.source_type || 'text'}`">
                    {{ sourceTypeLabel(citation.source_type) }}
                  </span>
                  <div class="rag-citation-copy">
                    <strong>{{ citation.file_name }}</strong>
                    <p>{{ citation.text_preview || citation.answer_preview || '已命中知识库来源' }}</p>
                  </div>
                </div>
              </div>
            </div>

            <ResultBadge :badge="currentPanel.resultBadge" :text="currentPanel.resultText" />
          </template>

          <div v-else class="rag-empty">
            <div class="rag-empty-icon">{{ currentMode.emptyIcon }}</div>
            <p>{{ currentMode.emptyTitle }}</p>
            <p class="rag-empty-sub">{{ currentMode.emptyDesc }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { request } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import { useModuleSubPage } from '../composables/useModuleSubPage'

function createPanelState() {
  return {
    loading: false,
    statusLoading: false,
    answerData: null,
    resultBadge: null,
    resultText: '',
    statusBadge: null,
    statusText: '',
    statusData: null,
    form: {
      question: '',
      enableRerank: true,
      topK: 3,
    },
  }
}

// 两套知识库入口共用一个页面骨架，只在配置层区分文案、接口和示例问题。
const modeMap = {
  'rg-novels': {
    key: 'rg-novels',
    name: '经典文学问答',
    tag: 'novels',
    kbId: 'novels',
    accent: 'amber',
    askPath: '/rag/ask',
    statusPath: '/rag/status',
    desc: '沿用原来的四大名著问答入口，适合人物、剧情、典故类问题。',
    longDesc: '只检索《三国演义》《水浒传》《红楼梦》《西游记》这套文学知识库，不会混入工程文档结果。',
    noticeTitle: '检索范围',
    noticeText: '仅查询经典文学知识库，继续兼容原有接口与旧问答习惯。',
    headerLabel: '经典文学 / 智能问答',
    headerHint: '兼容旧链路：混合检索 + 精排 + LLM 回答',
    answerBadge: 'Literature',
    loadingText: 'AI 正在翻阅四大名著...',
    placeholder: '输入文学问题，例如：桃园三结义是哪三个人？',
    emptyIcon: '卷',
    emptyTitle: '输入一个文学问题，开始检索四大名著知识库',
    emptyDesc: '适合人物关系、章节情节、典故出处等问法。',
    examples: [
      '桃园三结义是哪三个人？',
      '孙悟空大闹天宫在第几回？',
      '林黛玉和薛宝钗各有什么特点？',
      '曹操煮酒论英雄时说了什么？',
    ],
  },
  'rg-production': {
    key: 'rg-production',
    name: '工程文档检索',
    tag: 'production',
    kbId: 'production',
    accent: 'cyan',
    askPath: '/rag/kbs/production/ask',
    statusPath: '/rag/kbs/production/status',
    desc: '面向工程初设文档与标准 Q&A，适合参数、规模、配置、口径类问题。',
    longDesc: '只检索 production 工程知识库，不和四大名著、学生档案或其他业务数据混检。',
    noticeTitle: '检索范围',
    noticeText: '先查标准 Q&A，再回退原文切片；证据不足时会明确拒答，避免乱编。',
    headerLabel: '工程文档 / 专项检索',
    headerHint: 'production 独立知识库：QA 优先，原文回退，证据不足拒答',
    answerBadge: 'Production',
    loadingText: 'AI 正在扫描工程文档与标准问答...',
    placeholder: '输入工程问题，例如：本工程项目名称是什么？',
    emptyIcon: '塔',
    emptyTitle: '输入一个工程问题，开始检索 production 文档库',
    emptyDesc: '适合项目名称、装机容量、机型配置、海缆与电气方案等问题。',
    examples: [
      '本工程项目名称是什么？',
      '本项目风机的单机容量有哪些？',
      '本项目的总装机容量是多少？',
      '本工程66kV配电装置的接线方式是什么？',
    ],
  },
}

const modeList = Object.values(modeMap)
const panelMap = reactive({
  'rg-novels': createPanelState(),
  'rg-production': createPanelState(),
})

const { sub } = useModuleSubPage('rag', {
  onChange(nextSub) {
    loadStatus(nextSub)
  },
})

const currentMode = computed(() => modeMap[sub.value] || modeList[0])
const currentPanel = computed(() => panelMap[sub.value] || panelMap[modeList[0].key])

function switchMode(modeKey) {
  sub.value = modeKey
}

function fillQuestion(question) {
  currentPanel.value.form.question = question
}

async function loadStatus(modeKey = sub.value, force = false) {
  const mode = modeMap[modeKey]
  const panel = panelMap[modeKey]
  if (!mode || !panel) return
  if (!force && panel.statusData) return

  panel.statusLoading = true
  panel.statusBadge = null
  panel.statusText = ''
  try {
    const response = await request('GET', mode.statusPath)
    if (response.ok && response.data?.code === 200) {
      panel.statusData = response.data.data
      panel.statusBadge = { ok: true, text: '知识库就绪' }
    } else {
      panel.statusBadge = { ok: false, text: response.data?.msg || '状态读取失败' }
      panel.statusText = typeof response.data === 'string' ? response.data : ''
    }
  } catch (error) {
    panel.statusBadge = { ok: false, text: '网络错误' }
    panel.statusText = error.message
  } finally {
    panel.statusLoading = false
  }
}

async function doAsk(modeKey = sub.value) {
  const mode = modeMap[modeKey]
  const panel = panelMap[modeKey]
  if (!mode || !panel || !panel.form.question.trim()) return

  panel.loading = true
  panel.answerData = null
  panel.resultBadge = null
  panel.resultText = ''
  try {
    const response = await request('POST', mode.askPath, {
      body: {
        question: panel.form.question.trim(),
        enable_rerank: panel.form.enableRerank,
        top_k: panel.form.topK,
      },
    })
    if (response.ok && response.data?.code === 200) {
      panel.answerData = response.data.data
      panel.resultBadge = {
        ok: true,
        text: panel.answerData.trace?.answer_mode === 'refuse'
          ? '已按证据策略拒答'
          : (panel.answerData.trace?.fallback ? '完成（回退回答）' : '检索完成'),
      }
    } else {
      panel.resultBadge = { ok: false, text: response.data?.msg || '查询失败' }
      panel.resultText = typeof response.data === 'string' ? response.data : ''
    }
  } catch (error) {
    panel.resultBadge = { ok: false, text: '网络错误' }
    panel.resultText = error.message
  } finally {
    panel.loading = false
  }
}

function renderAnswer(answer) {
  if (!answer) return ''
  let text = answer
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  text = text.replace(/\[来源\s*(\d+)\]/g, '<mark class="rag-mark">[来源 $1]</mark>')
  return '<p>' + text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>'
}

function answerModeLabel(mode) {
  const map = {
    qa_direct: '标准答案直返',
    retrieve_answer: '原文综合回答',
    refuse: '证据不足，明确拒答',
  }
  return map[mode] || '问答结果'
}

function sourceTypeLabel(sourceType) {
  const map = {
    qa: 'Q&A',
    txt: '原文',
    pdf: 'PDF',
    md: 'Markdown',
    docx: 'DOCX',
  }
  return map[sourceType] || '片段'
}

function traceSummary(trace = {}) {
  const items = [
    { label: '模式', value: answerModeLabel(trace.answer_mode) },
    { label: '改写', value: `${trace.rewrite_ms ?? 0}ms` },
    { label: '向量', value: `${trace.embed_ms ?? 0}ms` },
    { label: '生成', value: `${trace.generate_ms ?? 0}ms` },
    { label: '总耗时', value: `${trace.total_ms ?? 0}ms` },
  ]
  if (typeof trace.qa_top_score === 'number' && trace.qa_top_score > 0) {
    items.splice(3, 0, { label: 'QA Top1', value: trace.qa_top_score.toFixed(3) })
  }
  if (typeof trace.doc_top_score === 'number' && trace.doc_top_score > 0) {
    items.splice(4, 0, { label: '原文 Top1', value: trace.doc_top_score.toFixed(3) })
  }
  return items
}

onMounted(() => {
  loadStatus(sub.value, true)
})
</script>

<style scoped>
.rag-shell {
  display: grid;
  gap: 18px;
}

.rag-hero {
  display: grid;
  gap: 18px;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(227, 179, 65, 0.22), transparent 38%),
    linear-gradient(135deg, rgba(10, 16, 34, 0.96), rgba(18, 27, 54, 0.92));
  border: 1px solid rgba(227, 179, 65, 0.18);
}

.theme-light .rag-hero {
  background:
    radial-gradient(circle at top right, rgba(197, 138, 10, 0.12), transparent 35%),
    linear-gradient(135deg, rgba(255, 251, 244, 0.98), rgba(244, 247, 253, 0.98));
}

.rag-kicker {
  margin: 0 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--gold);
}

.rag-hero h2 {
  margin: 0;
  font-size: 28px;
}

.rag-summary {
  max-width: 760px;
  margin: 10px 0 0;
  color: var(--text-dim);
  line-height: 1.8;
}

.rag-mode-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.rag-mode-card {
  display: grid;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--line-strong);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: transform var(--dur-fast), border-color var(--dur-fast), background var(--dur-fast);
}

.rag-mode-card:hover {
  transform: translateY(-2px);
  border-color: rgba(227, 179, 65, 0.5);
}

.rag-mode-card.active {
  border-color: var(--gold);
  background: rgba(227, 179, 65, 0.12);
  box-shadow: inset 0 0 0 1px rgba(227, 179, 65, 0.2);
}

.rag-mode-name {
  font-size: 16px;
  font-weight: 700;
}

.rag-mode-tag {
  width: fit-content;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(227, 179, 65, 0.14);
  color: var(--gold);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.rag-mode-desc {
  color: var(--text-dim);
  line-height: 1.7;
}

.rag-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
}

.rag-side,
.rag-main {
  display: grid;
  gap: 16px;
}

.rag-side {
  align-content: start;
  padding: 20px;
}

.rag-side-head,
.rag-status-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rag-side-title,
.rag-file-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-muted);
}

.rag-side-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--gold-bg);
  color: var(--gold);
  font-size: 11px;
  font-weight: 700;
}

.rag-side h3 {
  margin: 0;
  font-size: 22px;
}

.rag-side-desc {
  margin: 0;
  color: var(--text-dim);
  line-height: 1.8;
}

.rag-notice {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: var(--panel-2);
}

.rag-notice strong {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
}

.rag-notice p {
  margin: 0;
  color: var(--text-dim);
  line-height: 1.7;
}

.notice-amber {
  border-color: rgba(227, 179, 65, 0.25);
  background: rgba(227, 179, 65, 0.08);
}

.notice-cyan {
  border-color: rgba(74, 189, 196, 0.25);
  background: rgba(74, 189, 196, 0.08);
}

.rag-status-box {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: 16px;
  background: var(--panel-2);
  border: 1px solid var(--line);
}

.rag-link-btn {
  border: none;
  background: transparent;
  color: var(--gold);
  cursor: pointer;
  font-size: 12px;
}

.rag-link-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.rag-status-list {
  display: grid;
  gap: 10px;
}

.rag-status-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--line);
  color: var(--text-dim);
  font-size: 13px;
}

.rag-status-item:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.rag-status-item strong {
  color: var(--text);
  text-align: right;
  word-break: break-all;
}

.rag-file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rag-file-chip {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--panel-solid);
  border: 1px solid var(--line-strong);
  font-size: 12px;
  color: var(--text-soft);
}

.rag-main {
  padding: 20px;
}

.sub-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.sub-bar label {
  font-size: 18px;
  font-weight: 700;
}

.sub-bar-hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-dim);
}

.rag-query-card {
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--panel-2);
}

.rag-examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}

.rag-examples-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-dim);
}

.rag-example-chip {
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--panel-3);
  color: var(--text-soft);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-out);
}

.rag-example-chip:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
  background: var(--gold-bg);
}

.rag-example-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.rag-input-area {
  display: grid;
  gap: 12px;
  padding: 16px;
  background: var(--panel-solid);
}

.rag-input-area textarea {
  width: 100%;
  min-height: 110px;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 15px;
  line-height: 1.75;
  resize: vertical;
  outline: none;
}

.rag-input-area textarea::placeholder {
  color: var(--text-muted);
}

.rag-input-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.rag-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  color: var(--text-dim);
}

.rag-toggle input {
  display: none;
}

.rag-toggle-track {
  position: relative;
  width: 34px;
  height: 20px;
  border-radius: 10px;
  background: var(--line-strong);
  transition: background var(--dur-fast);
}

.rag-toggle input:checked + .rag-toggle-track {
  background: var(--gold);
}

.rag-toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform var(--dur-fast);
}

.rag-toggle input:checked + .rag-toggle-track .rag-toggle-thumb {
  transform: translateX(14px);
}

.rag-topk {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-dim);
}

.rag-topk input {
  width: 62px;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid var(--line-strong);
  background: var(--panel-3);
  color: var(--text);
}

.rag-input-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

.rag-submit-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  border: none;
  border-radius: 10px;
  background: var(--gold);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  transition: transform var(--dur-fast), opacity var(--dur-fast);
}

.rag-submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  opacity: 0.92;
}

.rag-submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.rag-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 160px;
}

.rag-loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gold);
  animation: rag-dot 1.2s ease-in-out infinite;
}

.rag-loading-dot:nth-child(2) { animation-delay: 0.2s; }
.rag-loading-dot:nth-child(3) { animation-delay: 0.4s; }

.rag-loading-text {
  margin-left: 8px;
  color: var(--text-dim);
}

@keyframes rag-dot {
  0%, 80%, 100% { opacity: 0.25; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

.rag-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.rag-meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  font-size: 12px;
}

.rag-meta-pill em {
  font-style: normal;
  color: var(--text-muted);
}

.rag-meta-pill strong {
  color: var(--text);
}

.rag-rewrite {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px;
  border-left: 3px solid var(--gold);
  border-radius: 8px;
  background: var(--gold-bg);
}

.rag-rewrite-label {
  color: var(--gold);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.rag-rewrite-text {
  color: var(--text-dim);
  line-height: 1.7;
}

.rag-answer-card {
  border-radius: 16px;
  border: 1px solid var(--line);
  overflow: hidden;
  background: var(--panel-solid);
}

.rag-answer-card--refuse {
  border-color: rgba(210, 82, 82, 0.35);
}

.rag-answer-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--panel-2);
  border-bottom: 1px solid var(--line);
  font-weight: 700;
}

.rag-answer-icon {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--gold-bg);
  color: var(--gold);
}

.rag-answer-badge {
  margin-left: auto;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--text-dim);
  background: var(--panel-solid);
  border: 1px solid var(--line);
}

.rag-answer-body {
  padding: 18px 20px;
  line-height: 1.85;
}

.rag-answer-body :deep(p) {
  margin: 0 0 12px;
}

.rag-answer-body :deep(p:last-child) {
  margin-bottom: 0;
}

.rag-answer-body :deep(mark.rag-mark) {
  padding: 1px 4px;
  border-radius: 4px;
  background: var(--gold-bg);
  color: var(--gold);
}

.rag-citations {
  border-radius: 16px;
  border: 1px solid var(--line);
  overflow: hidden;
}

.rag-citations-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: var(--panel-2);
  border-bottom: 1px solid var(--line);
  font-weight: 700;
}

.rag-citations-count {
  color: var(--text-muted);
  font-size: 12px;
}

.rag-citation-list {
  display: grid;
  gap: 10px;
  padding: 14px;
}

.rag-citation-item {
  display: grid;
  grid-template-columns: 28px 68px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 12px;
  border-radius: 12px;
  background: var(--panel-solid);
  border: 1px solid var(--line);
}

.rag-citation-num {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--gold-bg);
  color: var(--gold);
  font-weight: 700;
}

.rag-citation-type {
  display: inline-flex;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.tag-qa { background: rgba(64, 130, 255, 0.14); color: #5d95ff; }
.tag-pdf { background: rgba(80, 190, 152, 0.14); color: #52c38f; }
.tag-txt, .tag-md, .tag-docx, .tag-text { background: rgba(227, 179, 65, 0.14); color: var(--gold); }

.rag-citation-copy {
  min-width: 0;
}

.rag-citation-copy strong {
  display: block;
  margin-bottom: 6px;
}

.rag-citation-copy p {
  margin: 0;
  color: var(--text-dim);
  line-height: 1.7;
  word-break: break-word;
}

.rag-empty {
  min-height: 220px;
  display: grid;
  place-items: center;
  text-align: center;
  color: var(--text-dim);
}

.rag-empty-icon {
  font-size: 44px;
  margin-bottom: 10px;
}

.rag-empty p {
  margin: 4px 0;
  font-size: 15px;
}

.rag-empty-sub {
  font-size: 13px;
  opacity: 0.72;
}

@media (max-width: 1080px) {
  .rag-grid {
    grid-template-columns: 1fr;
  }

  .rag-side {
    order: 2;
  }

  .rag-main {
    order: 1;
  }
}

@media (max-width: 720px) {
  .rag-hero,
  .rag-side,
  .rag-main {
    padding: 16px;
  }

  .rag-mode-strip {
    grid-template-columns: 1fr;
  }

  .rag-input-bar {
    align-items: stretch;
  }

  .rag-input-count {
    width: 100%;
    margin-left: 0;
  }

  .rag-submit-btn {
    width: 100%;
    justify-content: center;
  }

  .rag-citation-item {
    grid-template-columns: 28px 1fr;
  }

  .rag-citation-copy {
    grid-column: 1 / -1;
  }
}
</style>
