<template>
  <section id="page-score" class="page active">
    <div class="sub-bar">
      <label>选择功能</label>
      <select v-model="sub" @change="saveSub">
        <option value="sc-add">新增成绩</option>
        <option value="sc-batch">批量导入成绩</option>
        <option value="sc-op">修改 / 删除成绩</option>
        <option value="sc-query">查询成绩</option>
      </select>
    </div>

    <!-- 新增成绩 -->
    <div id="sc-add" class="card subcard" :class="{ show: sub === 'sc-add' }">
      <h3>新增成绩</h3>
      <div class="grid">
        <div class="field"><label>学号 *</label><input v-model="form.add.no" placeholder="S2025001" /></div>
        <div class="field"><label>考试次序 *</label><input v-model.number="form.add.order" type="number" placeholder="1" /></div>
        <div class="field"><label>成绩 *（0~100）</label><input v-model.number="form.add.score" type="number" placeholder="88" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="addScore">{{ loading ? '处理中...' : '新增' }}</button></div>
      <ResultBadge :badge="results.add.badge" :text="results.add.text" />
    </div>

    <!-- 批量导入 -->
    <div id="sc-batch" class="card subcard" :class="{ show: sub === 'sc-batch' }">
      <h3>批量导入成绩（Excel / CSV）</h3>
      <p class="hint">第一步：下载标准模板，按列填好学生成绩。第二步：选择填好的文件上传导入。</p>
      <div class="actions">
        <button class="btn secondary" @click="downloadTemplate">⬇ 下载导入模板</button>
      </div>
      <div class="field" style="margin-top: 14px;">
        <label>选择 Excel / CSV 文件</label>
        <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv" />
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="importScores">{{ loading ? '导入中...' : '开始导入' }}</button></div>
      <div v-if="importSummary" v-html="importSummary"></div>
      <DataTable :data="importFailures" />
      <ResultBadge :badge="results.batch.badge" :text="results.batch.text" />
    </div>

    <!-- 修改/删除 -->
    <div id="sc-op" class="card subcard" :class="{ show: sub === 'sc-op' }">
      <h3>修改 / 删除成绩</h3>
      <div class="grid">
        <div class="field"><label>学号 *</label><input v-model="form.op.no" placeholder="S2025001" /></div>
        <div class="field"><label>考试次序 *</label><input v-model.number="form.op.order" type="number" placeholder="1" /></div>
        <div class="field"><label>新成绩（修改用）</label><input v-model.number="form.op.score" type="number" placeholder="95" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="updateScore">修改成绩</button>
        <button class="btn danger" :disabled="loading" @click="deleteScore">删除成绩</button>
      </div>
      <ResultBadge :badge="results.op.badge" :text="results.op.text" />
    </div>

    <!-- 查询成绩 -->
    <div id="sc-query" class="card subcard" :class="{ show: sub === 'sc-query' }">
      <h3>查询成绩</h3>
      <div class="grid">
        <div class="field"><label>页码</label><input v-model.number="form.query.page" type="number" /></div>
        <div class="field"><label>每页条数（1~100）</label><input v-model.number="form.query.psize" type="number" /></div>
        <div class="field"><label>学号</label><input v-model="form.query.no" placeholder="S2025001" /></div>
        <div class="field"><label>考试次序</label><input v-model.number="form.query.order" type="number" /></div>
        <div class="field"><label>班级ID</label><input v-model.number="form.query.classId" type="number" /></div>
        <div class="field"><label>最低分</label><input v-model.number="form.query.min" type="number" /></div>
        <div class="field"><label>最高分</label><input v-model.number="form.query.max" type="number" /></div>
        <div class="field"><label>按学号排序</label><select v-model="form.query.sortNo"><option value="">不排序</option><option value="asc">升序</option><option value="desc">降序</option></select></div>
        <div class="field"><label>按成绩排序</label><select v-model="form.query.sortSc"><option value="">不排序</option><option value="asc">升序</option><option value="desc">降序</option></select></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="queryScore">{{ loading ? '处理中...' : '查询' }}</button></div>
      <DataTable :data="listData" />
      <ResultBadge :badge="results.query.badge" :text="results.query.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { request, qs, pickList, getBaseUrl } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import { validateFields } from '../utils/helpers'

const sub = ref(localStorage.getItem('sub-score') || 'sc-add')
const loading = ref(false)
const listData = ref(null)
const fileInput = ref(null)
const importSummary = ref('')
const importFailures = ref(null)

const form = reactive({
  add: { no: '', order: null, score: null },
  op: { no: '', order: null, score: null },
  query: { page: 1, psize: 10, no: '', order: null, classId: null, min: null, max: null, sortNo: '', sortSc: '' }
})

const results = reactive({
  add: { badge: null, text: '' }, batch: { badge: null, text: '' },
  op: { badge: null, text: '' }, query: { badge: null, text: '' }
})

function saveSub() { localStorage.setItem('sub-score', sub.value) }

function setResult(target, ok, msg) {
  results[target].badge = { ok, text: ok ? msg : msg }
  results[target].text = ''
}

async function doRequest(target, method, path, opts = {}) {
  loading.value = true
  try {
    const r = await request(method, path, opts)
    setResult(target, r.ok, r.ok ? '操作成功' : (r.data?.msg || '操作失败'))
    return r
  } catch (e) {
    setResult(target, false, `网络错误: ${e.message}`)
    return { ok: false }
  } finally { loading.value = false }
}

async function addScore() {
  if (!validateFields([['#sc-add', '学号', form.add.no], ['#sc-add', '考试次序', form.add.order], ['#sc-add', '成绩', form.add.score]])) return
  await doRequest('add', 'POST', '/score/add', { body: { student_no: form.add.no, exam_order: form.add.order, score: form.add.score } })
}

async function downloadTemplate() {
  try {
    const resp = await fetch(getBaseUrl() + '/score/import/template')
    if (!resp.ok) throw new Error('HTTP ' + resp.status)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'score_import_template.xlsx'
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('下载模板失败：' + e.message + '\n请确认后端已启动。')
  }
}

async function importScores() {
  if (!fileInput.value?.files?.length) {
    return alert('请先选择要导入的 Excel/CSV 文件')
  }
  importSummary.value = ''
  importFailures.value = null
  loading.value = true
  const fd = new FormData()
  fd.append('file', fileInput.value.files[0])
  try {
    const resp = await fetch(getBaseUrl() + '/score/import', { method: 'POST', body: fd })
    const data = await resp.json()
    setResult('batch', resp.ok, resp.ok ? '导入完成' : (data.msg || '导入失败'))
    if (resp.ok && data?.data) {
      const d = data.data
      importSummary.value = `<div style="font-size:13px;color:var(--text);margin-top:8px">本次共 <b>${d.total ?? 0}</b> 行，<b style="color:var(--success)">成功 ${d.success_count ?? 0} 条</b>，<b style="color:var(--danger)">失败 ${d.fail_count ?? 0} 条</b>。</div>`
      if (d.failures?.length) {
        importFailures.value = d.failures.map(f => ({ '行号': f.row, '学号': f.student_no || '', '失败原因': f.reason }))
      }
    }
  } catch (e) {
    setResult('batch', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

async function updateScore() {
  if (!validateFields([['#sc-op', '学号', form.op.no], ['#sc-op', '考试次序', form.op.order], ['#sc-op', '新成绩', form.op.score]])) return
  await doRequest('op', 'PUT', '/score/update', { body: { student_no: form.op.no, exam_order: form.op.order, score: form.op.score } })
}

async function deleteScore() {
  if (!validateFields([['#sc-op', '学号', form.op.no], ['#sc-op', '考试次序', form.op.order]])) return
  if (!confirm('确认删除该成绩？')) return
  await doRequest('op', 'POST', '/score/is_delete' + qs({ student_no: form.op.no, exam_order: form.op.order }))
}

async function queryScore() {
  const r = await doRequest('query', 'GET', '/score/query' + qs({
    page: form.query.page || null, page_size: form.query.psize || null,
    student_no: form.query.no || null, exam_order: form.query.order,
    class_id: form.query.classId, min_score: form.query.min, max_score: form.query.max,
    sort_no: form.query.sortNo || null, sort_score: form.query.sortSc || null
  }))
  listData.value = pickList(r.data)
}
</script>
