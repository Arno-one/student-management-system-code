<template>
  <section id="page-nl2sql" class="page active">
    <!-- ====== 智能问数 ====== -->
    <div id="ns-query" class="card subcard" :class="{ show: sub === 'ns-query' }">
      <h3>智能问数（NL2SQL）</h3>
      <p class="hint">用自然语言描述你想查询的数据，系统将自动转换为 SQL 并返回结果。</p>

      <!-- 示例问题快捷入口 -->
      <div class="nl-examples">
        <span class="nl-examples-label">试试问：</span>
        <button
          v-for="q in exampleQuestions"
          :key="q"
          class="nl-example-chip"
          :disabled="loading"
          @click="form.question = q"
        >{{ q }}</button>
      </div>

      <!-- 输入区 -->
      <div class="nl-input-row">
        <input
          v-model="form.question"
          placeholder="输入你的问题，例如：张三的平均成绩是多少？"
          :disabled="loading"
        />
        <button class="btn" :disabled="loading || !form.question.trim()" @click="doQuery">
          {{ loading ? '查询中...' : '查询' }}
        </button>
      </div>

      <!-- 耗时提示 -->
      <div class="nl-meta" v-if="queryResult.meta">
        <span :class="queryResult.meta.cached ? 'nl-cached' : ''">
          {{ queryResult.meta.cached ? '⚡ 缓存命中' : '⏱ ' + queryResult.meta.cost }}ms
        </span>
      </div>

      <!-- 生成的 SQL -->
      <div class="nl-sql-section" v-if="queryResult.sql">
        <div class="nl-sql-head">
          <span>生成的 SQL</span>
          <button class="btn-copy" @click="copySql" :title="sqlCopied ? '已复制' : '复制'">
            {{ sqlCopied ? '已复制' : '复制' }}
          </button>
        </div>
        <pre class="nl-sql-block"><code class="language-sql" ref="sqlCodeRef" v-text="queryResult.sql"></code></pre>
      </div>

      <!-- 查询结果 -->
      <div class="nl-result-section" v-if="queryResult.columns">
        <div class="nl-result-head">
          <span>查询结果</span>
          <span class="nl-result-count">{{ queryResult.rowCount }} 行</span>
        </div>
        <DataTable :data="queryResult.tableData" />
      </div>

      <ResultBadge :badge="results.query.badge" :text="results.query.text" />
    </div>

    <!-- ====== 表结构概览 ====== -->
    <div id="ns-schema" class="card subcard" :class="{ show: sub === 'ns-schema' }">
      <h3>数据库表结构概览</h3>
      <p class="hint">以下表格展示了数据库中所有可查询的表和字段，帮助你了解可以提出哪些问题。</p>

      <div v-if="schemaLoading" class="nl-schema-loading">加载中...</div>

      <div class="nl-schema-tables" v-if="schemaData">
        <div class="nl-schema-table-card" v-for="t in schemaData.tables" :key="t.name">
          <div class="nl-schema-table-name">{{ t.name }}</div>
          <div class="nl-schema-table-comment" v-if="t.comment">{{ t.comment }}</div>
          <div class="nl-schema-table-fields">
            <div class="nl-schema-field" v-for="f in t.fields" :key="f.name">
              <span class="nl-schema-field-name">{{ f.name }}</span>
              <span class="nl-schema-field-type">{{ f.type }}</span>
              <span class="nl-schema-field-comment" v-if="f.comment">{{ f.comment }}</span>
            </div>
          </div>
        </div>
      </div>

      <ResultBadge :badge="results.schema.badge" :text="results.schema.text" />
    </div>

    <!-- ====== 历史记录 ====== -->
    <div id="ns-history" class="card subcard" :class="{ show: sub === 'ns-history' }">
      <h3>历史查询记录</h3>
      <p class="hint">查看你的历史 NL2SQL 查询记录，点击可重新加载结果。</p>

      <div class="nl-history-list" v-if="historySessions.length > 0">
        <div
          v-for="s in historySessions"
          :key="s.id"
          class="nl-history-item"
        >
          <div class="nl-history-head">
            <span class="nl-history-title">{{ s.title }}</span>
            <span class="nl-history-time">{{ s.update_time }}</span>
          </div>
          <div class="nl-history-msgs" v-if="s.messages">
            <div class="nl-history-msg" v-for="m in s.messages" :key="m.id">
              <div class="nl-history-q">Q: {{ m.question }}</div>
              <div class="nl-history-sql" v-if="m.generated_sql">
                <code>{{ m.generated_sql.substring(0, 200) }}{{ m.generated_sql.length > 200 ? '...' : '' }}</code>
              </div>
              <div class="nl-history-meta">
                <span v-if="m.is_cached">缓存命中</span>
                <span v-else>{{ m.cost_ms }}ms</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="nl-empty">暂无历史记录，开始一次智能问数吧。</div>

      <ResultBadge :badge="results.history.badge" :text="results.history.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, nextTick, onMounted } from 'vue'
import { request, apiState } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import hljs from 'highlight.js/lib/core'
import sql from 'highlight.js/lib/languages/sql'
import { useModuleSubPage } from '../composables/useModuleSubPage'

hljs.registerLanguage('sql', sql)

const loading = ref(false)
const schemaLoading = ref(false)
const sqlCodeRef = ref(null)
const sqlCopied = ref(false)

const form = reactive({
  question: '',
  userId: apiState.user?.username || 'default',
})

const queryResult = reactive({
  sql: '',
  columns: null,
  rows: null,
  rowCount: 0,
  tableData: null,
  meta: null,
})

const results = reactive({
  query: { badge: null, text: '' },
  schema: { badge: null, text: '' },
  history: { badge: null, text: '' },
})

const schemaData = ref(null)
const historySessions = ref([])
const { sub } = useModuleSubPage('nl2sql', {
  onChange(nextSub) {
    if (nextSub === 'ns-schema' && !schemaData.value) loadSchema()
    if (nextSub === 'ns-history') loadHistory()
  }
})

const exampleQuestions = [
  '每个班级有多少学生？',
  '就业薪资最高的前5名学生是谁？',
  '张三的平均成绩是多少？',
  '有哪些学生成绩不及格？',
  '列出每个班级的班主任姓名',
]

function setResult(target, ok, text) {
  results[target].badge = { ok, text: ok ? text : text }
  results[target].text = ''
}

// ====== 智能问数 ======

async function doQuery() {
  if (!form.question.trim()) return
  loading.value = true
  queryResult.sql = ''
  queryResult.columns = null
  queryResult.tableData = null
  queryResult.meta = null
  setResult('query', null, '运行中')

  try {
    const r = await request('POST', '/nl2sql/query', {
      body: { question: form.question.trim(), user_id: form.userId }
    })
    if (r.ok && r.data?.code === 200) {
      const d = r.data.data
      queryResult.sql = d.sql || ''
      queryResult.columns = d.columns || []
      queryResult.rows = d.rows || []
      queryResult.rowCount = d.row_count || 0
      queryResult.meta = { cost: d.cost_ms, cached: d.is_cached }

      if (d.columns && d.rows) {
        queryResult.tableData = [d.columns, ...d.rows]
      }
      setResult('query', true, '查询成功')
      await nextTick()
      highlightSql()
    } else {
      setResult('query', false, r.data?.msg || '查询失败')
    }
  } catch (e) {
    setResult('query', false, `网络错误: ${e.message}`)
  } finally {
    loading.value = false
  }
}

function highlightSql() {
  if (sqlCodeRef.value) {
    sqlCodeRef.value.innerHTML = hljs.highlight(queryResult.sql, { language: 'sql' }).value
  }
}

async function copySql() {
  try {
    await navigator.clipboard.writeText(queryResult.sql)
    sqlCopied.value = true
    setTimeout(() => { sqlCopied.value = false }, 2000)
  } catch {
    // fallback for older browsers
    const ta = document.createElement('textarea')
    ta.value = queryResult.sql
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    sqlCopied.value = true
    setTimeout(() => { sqlCopied.value = false }, 2000)
  }
}

// ====== 表结构概览 ======

async function loadSchema() {
  schemaLoading.value = true
  setResult('schema', null, '运行中')
  try {
    const r = await request('GET', '/nl2sql/schema')
    if (r.ok && r.data?.code === 200) {
      schemaData.value = parseSchema(r.data.data)
      setResult('schema', true, '加载成功')
    } else {
      setResult('schema', false, r.data?.msg || '加载失败')
    }
  } catch (e) {
    setResult('schema', false, `网络错误: ${e.message}`)
  } finally {
    schemaLoading.value = false
  }
}

function parseSchema(data) {
  const tables = []
  const text = data.schema || ''
  const sections = text.split(/\n## /)
  let joinPaths = ''
  let enumMap = ''
  let aggDefaults = ''

  for (const sec of sections) {
    const lines = sec.trim().split('\n')
    const header = lines[0].trim()
    if (!header) continue

    if (header.startsWith('跨表 JOIN') || header.startsWith('枚举值') || header.startsWith('聚合口径')) {
      if (header.startsWith('跨表 JOIN')) joinPaths = lines.slice(1).join('\n')
      if (header.startsWith('枚举值')) enumMap = lines.slice(1).join('\n')
      if (header.startsWith('聚合口径')) aggDefaults = lines.slice(1).join('\n')
      continue
    }

    const nameParts = header.split('—').map(s => s.trim())
    const tableName = nameParts[0] || header
    const tableComment = nameParts[1] || ''

    const fields = []
    for (const line of lines.slice(1)) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('---') || trimmed.startsWith('FOREIGN')) continue
      const parts = trimmed.split(/\s{2,}/)
      if (parts.length >= 1) {
        const fieldName = parts[0].trim()
        const fieldType = parts.length >= 2 ? parts[1].trim() : ''
        const fieldComment = trimmed.includes('--') ? trimmed.split('--').pop().trim() : ''
        fields.push({ name: fieldName, type: fieldType, comment: fieldComment })
      }
    }
    if (fields.length > 0) {
      tables.push({ name: tableName, comment: tableComment, fields })
    }
  }

  return { tables, joinPaths, enumMap, aggDefaults }
}

// ====== 历史记录 ======

async function loadHistory() {
  setResult('history', null, '运行中')
  try {
    const r = await request('GET', '/nl2sql/sessions?user_id=' + encodeURIComponent(form.userId))
    if (r.ok && r.data?.code === 200) {
      historySessions.value = r.data.data || []
      setResult('history', true, '加载成功')
    } else {
      historySessions.value = []
      setResult('history', false, r.data?.msg || '加载失败')
    }
  } catch (e) {
    setResult('history', false, `网络错误: ${e.message}`)
  }
}

</script>
