<template>
  <section id="page-rag" class="page active">
    <div class="rag-shell">
      <div class="rag-stage card">
        <div class="sub-bar">
          <label>{{ currentMode.headerLabel }}</label>
          <span class="sub-bar-hint">{{ currentMode.headerHint }}</span>
        </div>

        <div class="rag-brief">
          <div class="rag-brief-main">
            <span class="rag-kicker">{{ currentMode.kicker }}</span>
            <h2>{{ currentMode.name }}</h2>
            <p>{{ currentMode.longDesc }}</p>
          </div>
          <span class="rag-brief-tag">{{ currentMode.tag }}</span>
        </div>

        <div class="rag-notice" :class="`notice-${currentMode.accent}`">
          <strong>{{ currentMode.noticeTitle }}</strong>
          <p>{{ currentMode.noticeText }}</p>
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
              <div class="rag-answer-title">
                <span class="rag-answer-mode">{{ answerModeLabel(currentPanel.answerData.trace?.answer_mode) }}</span>
                <span class="rag-answer-badge">{{ currentMode.answerBadge }}</span>
              </div>
              <span class="rag-answer-total">耗时 {{ currentPanel.answerData.trace?.total_ms ?? 0 }}ms</span>
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
                <div class="rag-citation-copy">
                  <div class="rag-citation-top">
                    <strong>{{ citation.file_name }}</strong>
                    <span class="rag-citation-type" :class="`tag-${citation.source_type || 'text'}`">
                      {{ sourceTypeLabel(citation.source_type) }}
                    </span>
                  </div>
                  <p>{{ citation.text_preview || citation.answer_preview || '已命中知识库来源' }}</p>
                </div>
              </div>
            </div>
          </div>

          <ResultBadge :badge="currentPanel.resultBadge" :text="currentPanel.resultText" />
        </template>

        <div v-else class="rag-empty">
          <p>{{ currentMode.emptyTitle }}</p>
          <p class="rag-empty-sub">{{ currentMode.emptyDesc }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { request } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import { useModuleSubPage } from '../composables/useModuleSubPage'

function createPanelState() {
  return {
    loading: false,
    answerData: null,
    resultBadge: null,
    resultText: '',
    form: {
      question: '',
      enableRerank: true,
      topK: 3,
    },
  }
}

// 通过侧边栏子入口区分当前知识库方向，页面内部只展示当前方向，不再并排展示两套目标。
const modeMap = {
  'rg-novels': {
    key: 'rg-novels',
    name: '经典文学问答',
    tag: 'novels',
    accent: 'amber',
    askPath: '/rag/ask',
    kicker: 'Classic Literature',
    headerLabel: '经典文学 / 智能问答',
    headerHint: '仅面向四大名著知识库',
    longDesc: '只检索《三国演义》《水浒传》《红楼梦》《西游记》这套文学知识库，不会混入工程文档或学校业务数据。',
    noticeTitle: '检索范围',
    noticeText: '兼容原有四大名著问答链路，适合人物、剧情、典故出处等问题。',
    answerBadge: 'Literature',
    loadingText: 'AI 正在翻阅四大名著...',
    placeholder: '输入文学问题，例如：桃园三结义是哪三个人？',
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
    accent: 'cyan',
    askPath: '/rag/kbs/production/ask',
    kicker: 'Production Knowledge Base',
    headerLabel: '工程文档 / 专项检索',
    headerHint: '仅面向 production 工程知识库',
    longDesc: '只检索 production 工程知识库，不和四大名著、学生档案或其他业务数据混检。',
    noticeTitle: '检索范围',
    noticeText: '先查标准 Q&A，再回退原文切片；证据不足时会明确拒答，避免乱编。',
    answerBadge: 'Production',
    loadingText: 'AI 正在扫描工程文档与标准问答...',
    placeholder: '输入工程问题，例如：本工程项目名称是什么？',
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

const panelMap = reactive({
  'rg-novels': createPanelState(),
  'rg-production': createPanelState(),
})

const { sub } = useModuleSubPage('rag')
const currentMode = computed(() => modeMap[sub.value] || modeMap['rg-novels'])
const currentPanel = computed(() => panelMap[sub.value] || panelMap['rg-novels'])

function fillQuestion(question) {
  currentPanel.value.form.question = question
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
  ]
  if (typeof trace.qa_top_score === 'number' && trace.qa_top_score > 0) {
    items.push({ label: 'QA Top1', value: trace.qa_top_score.toFixed(3) })
  }
  if (typeof trace.doc_top_score === 'number' && trace.doc_top_score > 0) {
    items.push({ label: '原文 Top1', value: trace.doc_top_score.toFixed(3) })
  }
  return items
}
</script>

<style scoped>
.rag-shell {
  display: grid;
}

.rag-stage {
  display: grid;
  gap: 16px;
  padding: 22px;
  background:
    radial-gradient(circle at top right, rgba(227, 179, 65, 0.14), transparent 34%),
    linear-gradient(180deg, rgba(16, 23, 39, 0.94), rgba(14, 21, 34, 0.98));
  border: 1px solid rgba(227, 179, 65, 0.16);
}

.theme-light .rag-stage {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 251, 255, 0.98)),
    radial-gradient(circle at top right, rgba(53, 122, 196, 0.06), transparent 42%);
  border-color: rgba(139, 174, 214, 0.28);
  box-shadow: 0 18px 46px rgba(169, 188, 213, 0.18);
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

.rag-brief {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.theme-light .rag-brief {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(245, 249, 255, 0.95));
  border-color: rgba(185, 206, 231, 0.48);
}

.rag-kicker {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gold);
}

.theme-light .rag-kicker {
  color: #3b6ea5;
}

.rag-brief h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
}

.rag-brief p {
  max-width: 760px;
  margin: 10px 0 0;
  color: var(--text-dim);
  line-height: 1.8;
}

.rag-brief-tag {
  flex-shrink: 0;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(227, 179, 65, 0.14);
  color: var(--gold);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.theme-light .rag-brief-tag {
  background: rgba(53, 122, 196, 0.1);
  color: #357ac4;
}

.rag-notice {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: var(--panel-2);
}

.rag-notice strong {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
}

.rag-notice p {
  margin: 0;
  line-height: 1.8;
  color: var(--text-dim);
}

.notice-amber {
  border-color: rgba(227, 179, 65, 0.2);
  background: rgba(227, 179, 65, 0.08);
}

.notice-cyan {
  border-color: rgba(96, 178, 206, 0.28);
  background: rgba(96, 178, 206, 0.1);
}

.theme-light .notice-amber {
  border-color: rgba(198, 157, 65, 0.18);
  background: rgba(255, 248, 232, 0.92);
}

.theme-light .notice-cyan {
  border-color: rgba(141, 196, 224, 0.42);
  background: rgba(236, 247, 253, 0.94);
}

.rag-query-card {
  border: 1px solid var(--line-strong);
  border-radius: 20px;
  overflow: hidden;
  background: var(--panel-2);
}

.theme-light .rag-query-card {
  border-color: rgba(186, 208, 233, 0.52);
  background: rgba(255, 255, 255, 0.95);
}

.rag-examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 16px 18px;
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

.theme-light .rag-example-chip:hover:not(:disabled) {
  border-color: #4f86c6;
  color: #2a5f98;
  background: rgba(220, 236, 249, 0.72);
}

.rag-example-chip:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.rag-input-area {
  display: grid;
  gap: 12px;
  padding: 18px;
  background: var(--panel-solid);
}

.theme-light .rag-input-area {
  background: rgba(255, 255, 255, 0.98);
}

.rag-input-area textarea {
  width: 100%;
  min-height: 128px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 15px;
  line-height: 1.8;
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

.theme-light .rag-toggle input:checked + .rag-toggle-track {
  background: #4e89ca;
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

.theme-light .rag-topk input {
  background: rgba(247, 251, 255, 0.98);
  border-color: rgba(180, 204, 232, 0.68);
}

.rag-input-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

.rag-submit-btn {
  padding: 10px 18px;
  border: none;
  border-radius: 12px;
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

.theme-light .rag-submit-btn {
  background: linear-gradient(135deg, #4e89ca, #2f6cab);
}

.rag-submit-btn:disabled {
  opacity: 0.42;
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

.theme-light .rag-loading-dot {
  background: #4e89ca;
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

.theme-light .rag-meta-pill {
  background: rgba(250, 252, 255, 0.96);
  border-color: rgba(186, 208, 233, 0.52);
}

.rag-meta-pill em {
  font-style: normal;
  color: var(--text-muted);
}

.rag-rewrite {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px;
  border-left: 3px solid var(--gold);
  border-radius: 10px;
  background: var(--gold-bg);
}

.theme-light .rag-rewrite {
  border-left-color: #4e89ca;
  background: rgba(235, 244, 253, 0.92);
}

.rag-rewrite-label {
  color: var(--gold);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.theme-light .rag-rewrite-label {
  color: #3b6ea5;
}

.rag-rewrite-text {
  color: var(--text-dim);
  line-height: 1.7;
}

.rag-answer-card {
  border-radius: 18px;
  border: 1px solid var(--line);
  overflow: hidden;
  background: var(--panel-solid);
}

.theme-light .rag-answer-card {
  border-color: rgba(186, 208, 233, 0.52);
  background: rgba(255, 255, 255, 0.98);
}

.rag-answer-card--refuse {
  border-color: rgba(210, 82, 82, 0.35);
}

.rag-answer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  background: var(--panel-2);
  border-bottom: 1px solid var(--line);
}

.theme-light .rag-answer-head {
  background: rgba(248, 251, 255, 0.98);
}

.rag-answer-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.rag-answer-mode {
  font-weight: 700;
}

.rag-answer-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--text-dim);
  background: var(--panel-solid);
  border: 1px solid var(--line);
}

.theme-light .rag-answer-badge {
  background: rgba(255, 255, 255, 0.96);
  border-color: rgba(186, 208, 233, 0.52);
}

.rag-answer-total {
  font-size: 12px;
  color: var(--text-muted);
}

.rag-answer-body {
  padding: 20px 22px;
  line-height: 1.9;
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

.theme-light .rag-answer-body :deep(mark.rag-mark) {
  background: rgba(224, 238, 252, 0.92);
  color: #2f6cab;
}

.rag-citations {
  border-radius: 18px;
  border: 1px solid var(--line);
  overflow: hidden;
}

.theme-light .rag-citations {
  border-color: rgba(186, 208, 233, 0.52);
  background: rgba(255, 255, 255, 0.96);
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

.theme-light .rag-citations-head {
  background: rgba(248, 251, 255, 0.98);
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
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 12px;
  border-radius: 12px;
  background: var(--panel-solid);
  border: 1px solid var(--line);
}

.theme-light .rag-citation-item {
  background: rgba(252, 254, 255, 0.98);
  border-color: rgba(199, 216, 236, 0.58);
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

.theme-light .rag-citation-num {
  background: rgba(224, 238, 252, 0.92);
  color: #2f6cab;
}

.rag-citation-copy {
  min-width: 0;
}

.rag-citation-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 6px;
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

.theme-light .tag-qa { background: rgba(83, 142, 214, 0.12); color: #2f6cab; }
.theme-light .tag-pdf { background: rgba(81, 172, 152, 0.14); color: #2f8f78; }
.theme-light .tag-txt,
.theme-light .tag-md,
.theme-light .tag-docx,
.theme-light .tag-text { background: rgba(219, 184, 107, 0.16); color: #946a15; }

.rag-citation-copy strong {
  display: block;
}

.rag-citation-copy p {
  margin: 0;
  color: var(--text-dim);
  line-height: 1.7;
  word-break: break-word;
}

.rag-empty {
  display: grid;
  gap: 8px;
  justify-items: center;
  padding: 56px 20px 46px;
  text-align: center;
  color: var(--text-dim);
}

.rag-empty p {
  margin: 0;
  font-size: 16px;
}

.rag-empty-sub {
  max-width: 620px;
  font-size: 13px;
  opacity: 0.78;
}

@media (max-width: 720px) {
  .rag-stage {
    padding: 16px;
  }

  .rag-brief {
    flex-direction: column;
    align-items: flex-start;
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
  }

  .rag-answer-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
