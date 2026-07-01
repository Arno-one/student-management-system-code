<template>
  <section id="page-employment" class="page active">
    <!-- 新建 -->
    <div id="em-create" class="card subcard" :class="{ show: sub === 'em-create' }">
      <h3>新建就业信息</h3>
      <div class="grid">
        <div class="field"><label>学号 *</label><input v-model="form.create.no" /></div>
        <div class="field"><label>姓名 *</label><input v-model="form.create.name" /></div>
        <div class="field"><label>班级ID *</label><input v-model.number="form.create.classId" type="number" /></div>
        <div class="field"><label>就业开放时间</label><input v-model="form.create.open" type="date" /></div>
        <div class="field"><label>offer下发时间</label><input v-model="form.create.offer" type="date" /></div>
        <div class="field"><label>公司名称</label><input v-model="form.create.company" /></div>
        <div class="field"><label>薪资</label><input v-model.number="form.create.salary" type="number" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="createEmployment">{{ loading ? '处理中...' : '新建' }}</button></div>
      <ResultBadge :badge="results.create.badge" :text="results.create.text" />
    </div>

    <!-- 查询 -->
    <div id="em-query" class="card subcard" :class="{ show: sub === 'em-query' }">
      <h3>查询就业信息</h3>
      <div class="grid">
        <div class="field"><label>页码</label><input v-model.number="form.query.page" type="number" /></div>
        <div class="field"><label>每页条数（1~100）</label><input v-model.number="form.query.size" type="number" /></div>
        <div class="field"><label>学生姓名</label><input v-model="form.query.name" /></div>
        <div class="field"><label>班级ID</label><input v-model.number="form.query.classId" type="number" /></div>
        <div class="field"><label>公司名</label><input v-model="form.query.company" /></div>
        <div class="field"><label>就业记录ID（按ID查）</label><input v-model.number="form.query.id" type="number" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="listEmployment">分页查询</button>
        <button class="btn secondary" :disabled="loading" @click="getEmployment">按ID查</button>
      </div>
      <DataTable :data="listData" />
      <ResultBadge :badge="results.query.badge" :text="results.query.text" />
    </div>

    <!-- 修改/删除/恢复 -->
    <div id="em-op" class="card subcard" :class="{ show: sub === 'em-op' }">
      <h3>修改 / 删除 / 恢复就业信息</h3>
      <div class="grid">
        <div class="field"><label>就业记录ID *</label><input v-model.number="form.op.id" type="number" /></div>
        <div class="field"><label>公司名称（修改用）</label><input v-model="form.op.company" /></div>
        <div class="field"><label>薪资（修改用）</label><input v-model.number="form.op.salary" type="number" /></div>
        <div class="field"><label>offer时间（修改用）</label><input v-model="form.op.offer" type="date" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="updateEmployment">修改</button>
        <button class="btn danger" :disabled="loading" @click="deleteEmployment">逻辑删除</button>
        <button class="btn secondary" :disabled="loading" @click="recoverEmployment">逻辑恢复</button>
        <button class="btn danger" :disabled="loading" @click="hardDeleteEmployment">物理删除</button>
      </div>
      <ResultBadge :badge="results.op.badge" :text="results.op.text" />
    </div>

    <!-- 智能录入 -->
    <div id="em-nl" class="card subcard" :class="{ show: sub === 'em-nl' }">
      <SmartInput
        title="智能录入就业信息"
        input-label="用自然语言描述就业信息"
        placeholder="例如：学号S2025001的学生张三，3班，拿到了字节跳动的offer，月薪25000"
        extract-btn-text="智能提取"
        confirm-btn-text="确认创建"
        extract-url="/Employment/employment_extract"
        submit-url="/Employment/employment_create"
        submit-method="POST"
        :fields="employmentFields"
        :field-map="employmentFieldMap"
        @submitted="onNlSubmitted"
      />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { request, qs, clean, pickList, pickOne } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import SmartInput from '../components/SmartInput.vue'
import { useModuleSubPage } from '../composables/useModuleSubPage'
import { validateFields } from '../utils/helpers'

const { sub } = useModuleSubPage('employment')
const loading = ref(false)
const listData = ref(null)

const form = reactive({
  create: { no: '', name: '', classId: null, open: '', offer: '', company: '', salary: null },
  query: { page: 1, size: 10, name: '', classId: null, company: '', id: null },
  op: { id: null, company: '', salary: null, offer: '' }
})

const results = reactive({
  create: { badge: null, text: '' }, query: { badge: null, text: '' }, op: { badge: null, text: '' },
  nl: { badge: null, text: '' }
})

const employmentFields = [
  { key: 'student_no', label: '学号', type: 'text', required: true, placeholder: 'S2024001' },
  { key: 'student_name', label: '姓名', type: 'text', required: true, placeholder: '张三' },
  { key: 'class_id', label: '班级ID', type: 'number', required: true, placeholder: '3' },
  { key: 'job_open_time', label: '就业开放时间', type: 'date', required: false },
  { key: 'offer_send_time', label: 'offer下发时间', type: 'date', required: false },
  { key: 'company_name', label: '公司名称', type: 'text', required: false, placeholder: '字节跳动' },
  { key: 'salary', label: '薪资（元）', type: 'number', required: false, placeholder: '25000' }
]

const employmentFieldMap = {
  student_no: 'student_no',
  student_name: 'student_name',
  class_id: 'class_id',
  job_open_time: 'job_open_time',
  offer_send_time: 'offer_send_time',
  company_name: 'company_name',
  salary: 'salary'
}

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

async function createEmployment() {
  if (!validateFields([['#em-create', '学号', form.create.no], ['#em-create', '姓名', form.create.name], ['#em-create', '班级ID', form.create.classId]])) return
  const body = clean({
    student_no: form.create.no, student_name: form.create.name, class_id: form.create.classId,
    job_open_time: form.create.open, offer_send_time: form.create.offer,
    company_name: form.create.company, salary: form.create.salary
  })
  await doRequest('create', 'POST', '/Employment/employment_create', { body })
}

async function listEmployment() {
  const r = await doRequest('query', 'GET', '/Employment/employment_list' + qs({
    page: form.query.page || null, size: form.query.size || null,
    student_name: form.query.name || null, class_id: form.query.classId, company_name: form.query.company || null
  }))
  listData.value = pickList(r.data)
}

async function getEmployment() {
  if (!validateFields([['#em-query', '就业记录ID', form.query.id]])) return
  const r = await doRequest('query', 'GET', '/Employment/employment_get/' + form.query.id)
  listData.value = pickOne(r.data)
}

async function updateEmployment() {
  if (!validateFields([['#em-op', '就业记录ID', form.op.id]])) return
  const body = clean({ company_name: form.op.company, salary: form.op.salary, offer_send_time: form.op.offer })
  await doRequest('op', 'PUT', '/Employment/employment_update/' + form.op.id, { body })
}

async function deleteEmployment() {
  if (!validateFields([['#em-op', '就业记录ID', form.op.id]])) return
  if (!confirm('确认逻辑删除？')) return
  await doRequest('op', 'DELETE', '/Employment/employment_delete/' + form.op.id)
}

async function recoverEmployment() {
  if (!validateFields([['#em-op', '就业记录ID', form.op.id]])) return
  await doRequest('op', 'PUT', '/Employment/employment_recover/' + form.op.id)
}

async function hardDeleteEmployment() {
  if (!validateFields([['#em-op', '就业记录ID', form.op.id]])) return
  if (!confirm('物理删除不可恢复，确认？')) return
  await doRequest('op', 'DELETE', '/Employment/employment_hard/' + form.op.id)
}

function onNlSubmitted(data) {
  setResult('nl', true, '就业信息创建成功')
}
</script>
