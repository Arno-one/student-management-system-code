<template>
  <section class="page active">
    <div class="sub-bar">
      <label>选择功能</label>
      <select v-model="sub" @change="saveSub">
        <option value="sc-add">新增成绩</option>
        <option value="sc-batch">批量新增成绩</option>
        <option value="sc-op">修改 / 删除成绩</option>
        <option value="sc-query">查询成绩</option>
      </select>
    </div>

    <!-- 新增成绩 -->
    <div class="card subcard" :class="{ show: sub === 'sc-add' }">
      <h3>新增成绩</h3>
      <div class="grid">
        <div class="field"><label>学号 *</label><input v-model="form.add.no" placeholder="S2025001" /></div>
        <div class="field"><label>考试次序 *</label><input v-model.number="form.add.order" type="number" placeholder="1" /></div>
        <div class="field"><label>成绩 *（0~100）</label><input v-model.number="form.add.score" type="number" placeholder="88" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="addScore">{{ loading ? '处理中...' : '新增' }}</button></div>
      <ResultBadge :badge="results.add.badge" :text="results.add.text" />
    </div>

    <!-- 批量新增 -->
    <div class="card subcard" :class="{ show: sub === 'sc-batch' }">
      <h3>批量新增成绩</h3>
      <div class="field">
        <label>成绩列表（JSON 数组）</label>
        <textarea v-model="form.batch.json" rows="6"></textarea>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="batchAddScore">{{ loading ? '处理中...' : '批量新增' }}</button></div>
      <ResultBadge :badge="results.batch.badge" :text="results.batch.text" />
    </div>

    <!-- 修改/删除 -->
    <div class="card subcard" :class="{ show: sub === 'sc-op' }">
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
    <div class="card subcard" :class="{ show: sub === 'sc-query' }">
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
import { request, qs, pickList } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import { validateFields } from '../utils/helpers'

const sub = ref(localStorage.getItem('sub-score') || 'sc-add')
const loading = ref(false)
const listData = ref(null)

const form = reactive({
  add: { no: '', order: null, score: null },
  batch: { json: '[\n  {"student_no": "S2025001", "exam_order": 1, "score": 90},\n  {"student_no": "S2025002", "exam_order": 1, "score": 75}\n]' },
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

async function batchAddScore() {
  let arr
  try { arr = JSON.parse(form.batch.json) } catch (e) { return alert('JSON 格式有误：' + e.message) }
  await doRequest('batch', 'POST', '/score/batch_add', { body: arr })
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
