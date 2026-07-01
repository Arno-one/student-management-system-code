<template>
  <section id="page-teacher" class="page active">
    <!-- 新增教师 -->
    <div id="te-create" class="card subcard" :class="{ show: sub === 'te-create' }">
      <h3>新增教师</h3>
      <div class="grid">
        <div class="field"><label>姓名 *</label><input v-model="form.create.name" placeholder="李老师" /></div>
        <div class="field"><label>性别 *</label><CustomSelect v-model="form.create.gender" :options="genderOptions" /></div>
        <div class="field"><label>联系电话 *</label><input v-model="form.create.phone" placeholder="13800000000" /></div>
        <div class="field"><label>职务 *</label><input v-model="form.create.title" placeholder="讲师" /></div>
        <div class="field"><label>所带班级ID *</label><input v-model.number="form.create.classId" type="number" placeholder="1" /></div>
        <div class="field"><label>入职日期 *</label><input v-model="form.create.hire" type="datetime-local" /></div>
        <div class="field"><label>出生日期</label><input v-model="form.create.birth" type="date" /></div>
        <div class="field"><label>邮箱</label><input v-model="form.create.email" placeholder="li@example.com" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="createTeacher">{{ loading ? '处理中...' : '新增' }}</button></div>
      <ResultBadge :badge="results.create.badge" :text="results.create.text" />
    </div>

    <!-- 批量导入 -->
    <div id="te-import" class="card subcard" :class="{ show: sub === 'te-import' }">
      <h3>批量导入（Excel / CSV）</h3>
      <p class="hint">第一步：下载标准模板，按列填好教师信息。第二步：选择填好的文件上传导入。</p>
      <div class="actions">
        <button class="btn secondary" @click="downloadTemplate">⬇ 下载导入模板</button>
      </div>
      <div class="field" style="margin-top: 14px;">
        <label>选择 Excel / CSV 文件</label>
        <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv" />
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="importTeachers">{{ loading ? '导入中...' : '开始导入' }}</button></div>
      <div v-if="importSummary" v-html="importSummary"></div>
      <DataTable :data="importFailures" />
      <ResultBadge :badge="results.import.badge" :text="results.import.text" />
    </div>

    <!-- 查询教师 -->
    <div id="te-query" class="card subcard" :class="{ show: sub === 'te-query' }">
      <h3>查询教师</h3>
      <div class="grid">
        <div class="field"><label>姓名</label><input v-model="form.query.name" /></div>
        <div class="field"><label>性别</label><CustomSelect v-model="form.query.gender" :options="genderQueryOptions" /></div>
        <div class="field"><label>职称</label><input v-model="form.query.title" /></div>
        <div class="field"><label>班级ID</label><input v-model.number="form.query.classId" type="number" /></div>
        <div class="field"><label>手机号</label><input v-model="form.query.phone" /></div>
        <div class="field"><label>邮箱</label><input v-model="form.query.email" /></div>
        <div class="field"><label>入职起始</label><input v-model="form.query.hstart" type="datetime-local" /></div>
        <div class="field"><label>入职截止</label><input v-model="form.query.hend" type="datetime-local" /></div>
        <div class="field"><label>排序字段</label><CustomSelect v-model="form.query.sortby" :options="sortbyOptions" /></div>
        <div class="field"><label>排序方向</label><CustomSelect v-model="form.query.sortorder" :options="sortorderOptions" /></div>
        <div class="field"><label>页码</label><input v-model.number="form.query.page" type="number" /></div>
        <div class="field"><label>每页条数</label><input v-model.number="form.query.psize" type="number" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="getTeachers">{{ loading ? '处理中...' : '查询' }}</button></div>
      <DataTable :data="listData" />
      <ResultBadge :badge="results.query.badge" :text="results.query.text" />
    </div>

    <!-- 按ID查/更新 -->
    <div id="te-op" class="card subcard" :class="{ show: sub === 'te-op' }">
      <h3>按ID查 / 更新教师</h3>
      <div class="grid">
        <div class="field"><label>教师ID *</label><input v-model.number="form.op.id" type="number" /></div>
        <div class="field"><label>姓名</label><input v-model="form.op.name" /></div>
        <div class="field"><label>性别</label><input v-model="form.op.gender" /></div>
        <div class="field"><label>手机号</label><input v-model="form.op.phone" /></div>
        <div class="field"><label>职称</label><input v-model="form.op.title" /></div>
        <div class="field"><label>班级ID</label><input v-model.number="form.op.classId" type="number" /></div>
        <div class="field"><label>邮箱</label><input v-model="form.op.email" /></div>
      </div>
      <div class="actions">
        <button class="btn secondary" :disabled="loading" @click="getTeacherById">按ID查</button>
        <button class="btn" :disabled="loading" @click="updateTeacher">更新</button>
      </div>
      <DataTable :data="opData" />
      <ResultBadge :badge="results.op.badge" :text="results.op.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { request, qs, clean, pickList, pickOne, fetchBlob } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import CustomSelect from '../components/CustomSelect.vue'
import { useModuleSubPage } from '../composables/useModuleSubPage'
import { validateFields } from '../utils/helpers'

const { sub } = useModuleSubPage('teacher')
const genderOptions = [
  { value: '男', label: '男' },
  { value: '女', label: '女' },
]
const genderQueryOptions = [
  { value: '', label: '全部' },
  { value: '男', label: '男' },
  { value: '女', label: '女' },
]
const sortbyOptions = [
  { value: '', label: '默认' },
  { value: 'id', label: '编号' },
  { value: 'name', label: '姓名' },
  { value: 'hire_date', label: '入职时间' },
  { value: 'create_time', label: '创建时间' },
  { value: 'class_id', label: '班级' },
]
const sortorderOptions = [
  { value: 'asc', label: '升序' },
  { value: 'desc', label: '降序' },
]
const loading = ref(false)
const listData = ref(null)
const opData = ref(null)
const fileInput = ref(null)
const importSummary = ref('')
const importFailures = ref(null)

const form = reactive({
  create: { name: '', gender: '男', phone: '', title: '', classId: null, hire: '', birth: '', email: '' },
  query: { name: '', gender: '', title: '', classId: null, phone: '', email: '', hstart: '', hend: '', sortby: '', sortorder: 'asc', page: 1, psize: 20 },
  op: { id: null, name: '', gender: '', phone: '', title: '', classId: null, email: '' }
})

const results = reactive({
  create: { badge: null, text: '' }, import: { badge: null, text: '' },
  query: { badge: null, text: '' }, op: { badge: null, text: '' }
})

function setResult(target, ok, msg) {
  results[target].badge = { ok, text: msg }
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

async function createTeacher() {
  if (!validateFields([
    ['#te-create', '姓名', form.create.name], ['#te-create', '联系电话', form.create.phone],
    ['#te-create', '职务', form.create.title], ['#te-create', '所带班级ID', form.create.classId],
    ['#te-create', '入职日期', form.create.hire]
  ])) return
  const body = clean({
    name: form.create.name, gender: form.create.gender, phone: form.create.phone,
    title: form.create.title, class_id: form.create.classId, hire_date: form.create.hire,
    birth_date: form.create.birth, email: form.create.email
  })
  await doRequest('create', 'POST', '/teacher', { body })
}

async function downloadTemplate() {
  try {
    const blob = await fetchBlob('/teachers/import/template')
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'teacher_import_template.xlsx'
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('下载模板失败：' + e.message + '\n请确认后端已启动。')
  }
}

async function importTeachers() {
  if (!fileInput.value?.files?.length) {
    return alert('请先选择要导入的 Excel/CSV 文件')
  }
  importSummary.value = ''
  importFailures.value = null
  loading.value = true
  const fd = new FormData()
  fd.append('file', fileInput.value.files[0])
  try {
    const r = await request('POST', '/teachers/import', { body: fd })
    const data = r.data
    setResult('import', r.ok, r.ok ? '导入完成' : (data.msg || '导入失败'))
    if (r.ok && data?.data) {
      const d = data.data
      importSummary.value = `<div style="font-size:13px;color:var(--text);margin-top:8px">本次共 <b>${d.total ?? 0}</b> 行，<b style="color:var(--success)">成功 ${d.success_count ?? 0} 条</b>，<b style="color:var(--danger)">失败 ${d.fail_count ?? 0} 条</b>。</div>`
      if (d.failures?.length) {
        importFailures.value = d.failures.map(f => ({ '行号': f.row, '姓名': f.name || '', '失败原因': f.reason }))
      }
    }
  } catch (e) {
    setResult('import', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

async function getTeachers() {
  const r = await doRequest('query', 'GET', '/teachers' + qs({
    name: form.query.name || null, gender: form.query.gender || null,
    title: form.query.title || null, class_id: form.query.classId,
    phone: form.query.phone || null, email: form.query.email || null,
    hire_date_start: form.query.hstart || null, hire_date_end: form.query.hend || null,
    sort_by: form.query.sortby || null, sort_order: form.query.sortorder || null,
    page: form.query.page || null, page_size: form.query.psize || null
  }))
  listData.value = pickList(r.data)
}

async function getTeacherById() {
  if (!validateFields([['#te-op', '教师ID', form.op.id]])) return
  const r = await doRequest('op', 'GET', '/teachers/' + form.op.id)
  opData.value = pickOne(r.data)
}

async function updateTeacher() {
  if (!validateFields([['#te-op', '教师ID', form.op.id]])) return
  const body = clean({
    name: form.op.name, gender: form.op.gender, phone: form.op.phone,
    title: form.op.title, class_id: form.op.classId, email: form.op.email
  })
  await doRequest('op', 'PUT', '/teachers/' + form.op.id, { body })
}
</script>
