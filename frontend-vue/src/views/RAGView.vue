<template>
  <section id="page-rag" class="page active">
    <div class="sub-bar">
      <label>四大名著 · 知识问答</label>
      <span class="sub-bar-hint">基于 RAG 混合检索（语义 + 关键词）+ CrossEncoder 精排</span>
    </div>

    <div id="rag-ask" class="card subcard show">
      <h3>AI 知识问答</h3>
      <p class="hint">向 AI 提问关于《三国演义》《水浒传》《红楼梦》《西游记》的问题，系统将从原著与 QA 知识库中检索并生成答案。</p>

      <!-- ====== 提问外框卡片 ====== -->
      <div class="rag-query-card" ref="inputRowRef">
        <!-- 示例问题 -->
        <div class="rag-examples">
          <span class="rag-examples-label">试试问</span>
          <button
            v-for="q in exampleQuestions"
            :key="q"
            class="rag-example-chip"
            :disabled="loading"
            @click="form.question = q"
          >{{ q }}</button>
        </div>

        <!-- 输入区 -->
        <div class="rag-input-area">
          <textarea
            v-model="form.question"
            placeholder="输入你的问题，例如：桃园三结义是哪三个人？"
            :disabled="loading"
            rows="3"
            @keydown.ctrl.enter="doAsk"
            @keydown.meta.enter="doAsk"
          ></textarea>
          <div class="rag-input-bar">
            <label class="rag-toggle" title="开启 CrossEncoder 精排可提高准确性，但增加约 300ms 延迟">
              <input type="checkbox" v-model="form.enableRerank" />
              <span class="rag-toggle-track"><span class="rag-toggle-thumb"></span></span>
              <span class="rag-toggle-label">精排</span>
            </label>
            <span class="rag-input-count">{{ form.question.length }} / 500</span>
            <button
              class="rag-submit-btn"
              :disabled="loading || !form.question.trim()"
              @click="doAsk"
            >
              <span class="rag-submit-icon">→</span>
              <span>{{ loading ? '检索中...' : '提问' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 耗时 meta -->
      <div class="nl-meta" v-if="answerData">
        <span class="nl-meta-item">改写: {{ answerData.trace.rewrite_ms }}ms</span>
        <span class="nl-meta-item">检索: {{ answerData.trace.search_ms }}ms</span>
        <span class="nl-meta-item" v-if="answerData.trace.rerank_ms > 0">精排: {{ answerData.trace.rerank_ms }}ms</span>
        <span class="nl-meta-item">生成: {{ answerData.trace.generate_ms }}ms</span>
        <span class="nl-meta-item total">总计: {{ answerData.trace.total_ms }}ms</span>
      </div>

      <!-- 加载动画 -->
      <div class="rag-loading" v-if="loading">
        <span class="rag-loading-dot"></span>
        <span class="rag-loading-dot"></span>
        <span class="rag-loading-dot"></span>
        <span class="rag-loading-text">AI 正在阅读四大名著...</span>
      </div>

      <!-- 答案展示区 -->
      <div class="rag-answer-section" v-if="answerData && !loading">
        <div class="rag-rewrite" v-if="answerData.rewritten_query">
          <span class="rag-rewrite-label">检索优化</span>
          <span class="rag-rewrite-text">{{ answerData.rewritten_query }}</span>
        </div>

        <div class="rag-answer-card">
          <div class="rag-answer-head">
            <span class="rag-answer-icon">✦</span>
            <span>AI 回答</span>
            <span class="rag-answer-badge">DeepSeek</span>
          </div>
          <div class="rag-answer-body" v-html="renderedAnswer"></div>
        </div>

        <div class="rag-citations" v-if="answerData.citations?.length">
          <div class="rag-citations-head">
            <span class="rag-citations-icon">⚑</span>
            <span>参考来源</span>
            <span class="rag-citations-count">{{ answerData.citations.length }} 条</span>
          </div>
          <div class="rag-citation-list">
            <div v-for="cit in answerData.citations" :key="cit.source_id" class="rag-citation-item">
              <span class="rag-citation-num">{{ cit.source_id }}</span>
              <span class="rag-citation-type" :class="'tag-' + cit.source_type">
                {{ cit.source_type === 'qa' ? '问答对' : '原文' }}
              </span>
              <span class="rag-citation-file">{{ cit.file_name }}</span>
              <span class="rag-citation-text">{{ cit.text_preview }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="rag-empty" v-if="!answerData && !loading">
        <div class="rag-empty-icon">📚</div>
        <p>输入一个问题，探索四大名著的精彩世界</p>
        <p class="rag-empty-sub">支持原著情节、人物关系、典故出处等各类问题</p>
      </div>

      <ResultBadge :badge="resultBadge" :text="resultText" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { request } from '../api'
import ResultBadge from '../components/ResultBadge.vue'

const loading = ref(false)
const answerData = ref(null)
const inputRowRef = ref(null)
const resultBadge = ref(null)
const resultText = ref('')

const form = reactive({ question: '', enableRerank: true })

const exampleQuestions = [
  '桃园三结义是哪三个人？',
  '孙悟空大闹天宫在第几回？',
  '林黛玉和薛宝钗各有什么特点？',
  '武松打虎的经过是怎样的？',
  '曹操煮酒论英雄时说了什么？',
  '贾宝玉的通灵宝玉有什么来历？',
  '诸葛亮空城计是怎样实施的？',
  '猪八戒的前身是什么身份？',
]

const renderedAnswer = computed(() => {
  if (!answerData.value?.answer) return ''
  let text = answerData.value.answer
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  text = text.replace(/\[来源\s*(\d+)\]/g, '<mark class="rag-mark">[来源 $1]</mark>')
  text = '<p>' + text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>'
  return text
})

async function doAsk() {
  if (!form.question.trim()) return
  loading.value = true
  answerData.value = null
  resultBadge.value = null
  try {
    const r = await request('POST', '/rag/ask', {
      body: { question: form.question.trim(), enable_rerank: form.enableRerank },
    })
    if (r.ok && r.data?.code === 200) {
      answerData.value = r.data.data
      resultBadge.value = { ok: true, text: r.data.data.trace?.fallback ? '完成（降级）' : '检索完成' }
    } else {
      resultBadge.value = { ok: false, text: r.data?.msg || '查询失败' }
    }
  } catch (e) {
    resultBadge.value = { ok: false, text: `网络错误: ${e.message}` }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.sub-bar-hint { margin-left: auto; font-size: 12px; color: var(--text-dim); opacity: 0.7; }

/* ====== 提问外框卡片 ====== */
.rag-query-card {
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--panel-2);
  margin: 16px 0 20px;
}

/* 示例问题 */
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
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-right: 2px;
  white-space: nowrap;
}
.rag-example-chip {
  padding: 4px 12px;
  border-radius: 16px;
  border: 1px solid var(--line-strong);
  background: var(--panel-3);
  color: var(--text-soft);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-out);
  white-space: nowrap;
}
.rag-example-chip:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
  background: var(--gold-bg);
}
.rag-example-chip:disabled { opacity: 0.35; cursor: not-allowed; }

/* 输入区域 */
.rag-input-area { padding: 12px 16px; background: var(--panel-solid); }
.rag-input-area textarea {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 15px;
  font-family: inherit;
  line-height: 1.7;
  resize: vertical;
  min-height: 64px;
  outline: none;
  padding: 0;
}
.rag-input-area textarea::placeholder { color: var(--text-muted); }
.rag-input-area textarea:disabled { opacity: 0.45; }

.rag-input-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}

/* Toggle */
.rag-toggle { display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; font-size: 12px; color: var(--text-dim); }
.rag-toggle input { display: none; }
.rag-toggle-track { width: 34px; height: 20px; border-radius: 10px; background: var(--line-strong); position: relative; transition: background var(--dur-fast); }
.rag-toggle:has(input:checked) .rag-toggle-track { background: var(--gold); }
.rag-toggle-thumb { position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform var(--dur-fast); box-shadow: 0 1px 3px rgba(0,0,0,0.18); }
.rag-toggle:has(input:checked) .rag-toggle-thumb { transform: translateX(14px); }
.rag-toggle-label { font-size: 12px; }

.rag-input-count { margin-left: auto; font-size: 11px; color: var(--text-muted); }

.rag-submit-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 18px;
  border: none; border-radius: 8px;
  background: var(--gold);
  color: #fff;
  font-size: 13px; font-weight: 600;
  cursor: pointer;
  transition: opacity var(--dur-fast), transform var(--dur-fast);
}
.rag-submit-btn:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
.rag-submit-btn:active:not(:disabled) { transform: translateY(0); }
.rag-submit-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.rag-submit-icon { font-size: 16px; }

/* ====== Meta row ====== */
.nl-meta-item.total { font-weight: 600; color: var(--gold); }

/* ====== Loading ====== */
.rag-loading { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 40px 20px; }
.rag-loading-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--gold); animation: rag-dot 1.2s ease-in-out infinite; }
.rag-loading-dot:nth-child(2) { animation-delay: 0.2s; }
.rag-loading-dot:nth-child(3) { animation-delay: 0.4s; }
.rag-loading-text { margin-left: 8px; font-size: 13px; color: var(--text-dim); }
@keyframes rag-dot {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

/* ====== Rewrite ====== */
.rag-rewrite { display: flex; align-items: baseline; gap: 8px; padding: 8px 14px; margin-bottom: 16px; background: var(--gold-bg); border-radius: 6px; border-left: 3px solid var(--gold); }
.rag-rewrite-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--gold); white-space: nowrap; }
.rag-rewrite-text { font-size: 13px; color: var(--text-dim); }

/* ====== Answer card ====== */
.rag-answer-card { background: var(--panel-solid); border: 1px solid var(--line); border-radius: var(--radius-sm); overflow: hidden; margin-bottom: 16px; }
.rag-answer-head { display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: var(--gold-bg); border-bottom: 1px solid var(--line); font-size: 13px; font-weight: 600; color: var(--text); }
.rag-answer-icon { color: var(--gold); font-size: 14px; }
.rag-answer-badge { margin-left: auto; font-size: 10px; font-weight: 500; padding: 2px 8px; border-radius: 10px; background: var(--gold-bg); color: var(--gold); }
.rag-answer-body { padding: 18px 20px; font-size: 15px; line-height: 1.85; color: var(--text); }
.rag-answer-body :deep(p) { margin: 0 0 12px; }
.rag-answer-body :deep(p:last-child) { margin-bottom: 0; }
.rag-answer-body :deep(mark.rag-mark) { background: var(--gold-bg); color: var(--gold); font-weight: 600; padding: 1px 4px; border-radius: 3px; }

/* ====== Citations ====== */
.rag-citations { border: 1px solid var(--line); border-radius: var(--radius-sm); overflow: hidden; }
.rag-citations-head { display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: var(--panel-2); border-bottom: 1px solid var(--line); font-size: 13px; font-weight: 600; color: var(--text-dim); }
.rag-citations-count { margin-left: auto; font-size: 11px; opacity: 0.6; }
.rag-citation-list { padding: 8px 12px; max-height: 280px; overflow-y: auto; }
.rag-citation-item { display: flex; align-items: baseline; gap: 10px; padding: 8px 6px; border-bottom: 1px solid var(--line); font-size: 12px; }
.rag-citation-item:last-child { border-bottom: none; }
.rag-citation-num { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--gold-bg); color: var(--gold); font-weight: 600; font-size: 11px; flex-shrink: 0; }
.rag-citation-type { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.3px; flex-shrink: 0; }
.tag-qa { background: var(--blue-bg); color: var(--blue); }
.tag-txt { background: var(--success-bg); color: var(--success); }
.rag-citation-file { color: var(--text-dim); font-weight: 500; flex-shrink: 0; }
.rag-citation-text { color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }

/* ====== Empty ====== */
.rag-empty { text-align: center; padding: 50px 20px; color: var(--text-dim); }
.rag-empty-icon { font-size: 48px; margin-bottom: 12px; }
.rag-empty p { margin: 4px 0; font-size: 15px; }
.rag-empty-sub { font-size: 13px; opacity: 0.55; }
</style>
