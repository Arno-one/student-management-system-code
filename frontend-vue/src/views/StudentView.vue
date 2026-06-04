<template>
  <section class="page active">
    <div class="sub-bar">
      <label>选择功能</label>
      <select v-model="sub" @change="saveSub">
        <option value="st-create">创建学生</option>
        <option value="st-query">查询学生</option>
        <option value="st-op">更新 / 删除 / 恢复学生</option>
      </select>
    </div>

    <!-- 创建学生 -->
    <div class="card subcard" :class="{ show: sub === 'st-create' }">
      <h3>创建学生</h3>
      <div class="grid">
        <div class="field"><label>学号 *</label><input v-model="form.create.no" placeholder="S2024001" /></div>
        <div class="field"><label>班级ID *</label><input v-model.number="form.create.classId" type="number" placeholder="1" /></div>
        <div class="field"><label>姓名 *</label><input v-model="form.create.name" placeholder="张三" /></div>
        <div class="field"><label>性别</label><input v-model="form.create.gender" placeholder="男" /></div>
        <div class="field"><label>年龄</label><input v-model.number="form.create.age" type="number" placeholder="20" /></div>
        <div class="field"><label>籍贯</label><input v-model="form.create.native" placeholder="北京市" /></div>
        <div class="field"><label>毕业院校</label><input v-model="form.create.school" placeholder="北京一中" /></div>
        <div class="field"><label>专业</label><input v-model="form.create.major" placeholder="计算机科学" /></div>
        <div class="field"><label>学历</label><input v-model="form.create.edu" placeholder="本科" /></div>
        <div class="field"><label>入学时间</label><input v-model="form.create.admit" type="date" /></div>
        <div class="field"><label>毕业时间</label><input v-model="form.create.grad" type="date" /></div>
        <div class="field"><label>顾问编号</label><input v-model.number="form.create.advisor" type="number" placeholder="1" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="createStudent">{{ loading ? '处理中...' : '创建' }}</button>
      </div>
      <ResultBadge :badge="results.create.badge" :text="results.create.text" />
    </div>

    <!-- 查询学生 -->
    <div class="card subcard" :class="{ show: sub === 'st-query' }">
      <h3>查询学生</h3>
      <div class="grid">
        <div class="field"><label>偏移量</label><input v-model.number="form.query.skip" type="number" /></div>
        <div class="field"><label>每页条数（1~100）</label><input v-model.number="form.query.limit" type="number" /></div>
        <div class="field"><label>学生ID（按ID查）</label><input v-model.number="form.query.id" type="number" placeholder="1" /></div>
        <div class="field"><label>学号（按学号查）</label><input v-model="form.query.no" placeholder="S2024001" /></div>
        <div class="field"><label>班级ID（按班级查）</label><input v-model.number="form.query.classId" type="number" placeholder="1" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="getAllStudents">查全部</button>
        <button class="btn secondary" :disabled="loading" @click="getStudentById">按ID查</button>
        <button class="btn secondary" :disabled="loading" @click="getStudentByNo">按学号查</button>
        <button class="btn secondary" :disabled="loading" @click="getStudentByClass">按班级查</button>
      </div>
      <DataTable :data="listData" />
      <ResultBadge :badge="results.query.badge" :text="results.query.text" />
    </div>

    <!-- 更新/删除/恢复 -->
    <div class="card subcard" :class="{ show: sub === 'st-op' }">
      <h3>更新 / 删除 / 恢复学生</h3>
      <div class="grid">
        <div class="field"><label>学生ID *</label><input v-model.number="form.op.id" type="number" placeholder="1" /></div>
        <div class="field"><label>班级ID</label><input v-model.number="form.op.classId" type="number" /></div>
        <div class="field"><label>姓名</label><input v-model="form.op.name" /></div>
        <div class="field"><label>性别</label><input v-model="form.op.gender" /></div>
        <div class="field"><label>年龄</label><input v-model.number="form.op.age" type="number" /></div>
        <div class="field"><label>专业</label><input v-model="form.op.major" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="updateStudent">更新</button>
        <button class="btn danger" :disabled="loading" @click="deleteStudent">逻辑删除</button>
        <button class="btn secondary" :disabled="loading" @click="restoreStudent">恢复</button>
      </div>
      <ResultBadge :badge="results.op.badge" :text="results.op.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { request, qs, clean, pickList, pickOne } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import { validateFields } from '../utils/helpers'

const sub = ref(localStorage.getItem('sub-student') || 'st-create')
const loading = ref(false)
const listData = ref(null)

const form = reactive({
  create: { no: '', classId: null, name: '', gender: '', age: null, native: '', school: '', major: '', edu: '', admit: '', grad: '', advisor: null },
  query: { skip: 0, limit: 100, id: null, no: '', classId: null },
  op: { id: null, classId: null, name: '', gender: '', age: null, major: '' }
})

const results = reactive({
  create: { badge: null, text: '' },
  query: { badge: null, text: '' },
  op: { badge: null, text: '' }
})

function saveSub() { localStorage.setItem('sub-student', sub.value) }

function setResult(target, ok, text) {
  results[target].badge = { ok, text: ok ? `${text}` : text }
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
    return { ok: false, error: e }
  } finally {
    loading.value = false
  }
}

async function createStudent() {
  if (!validateFields([['#st-create', '学号', form.create.no], ['#st-create', '班级ID', form.create.classId], ['#st-create', '姓名', form.create.name]])) return
  const body = clean({
    student_no: form.create.no, class_id: form.create.classId, student_name: form.create.name,
    gender: form.create.gender, age: form.create.age, native_place: form.create.native,
    graduate_school: form.create.school, major: form.create.major, education: form.create.edu,
    admission_time: form.create.admit, graduate_time: form.create.grad, advisor_id: form.create.advisor
  })
  await doRequest('create', 'POST', '/student/students', { body })
}

async function getAllStudents() {
  const r = await doRequest('query', 'GET', '/student/students' + qs({ skip: form.query.skip || null, limit: form.query.limit || null }))
  listData.value = pickList(r.data)
}

async function getStudentById() {
  if (!validateFields([['#st-query', '学生ID', form.query.id]])) return
  const r = await doRequest('query', 'GET', '/student/students/' + form.query.id)
  listData.value = pickOne(r.data)
}

async function getStudentByNo() {
  if (!validateFields([['#st-query', '学号', form.query.no]])) return
  const r = await doRequest('query', 'GET', '/student/students/no/' + encodeURIComponent(form.query.no))
  listData.value = pickOne(r.data)
}

async function getStudentByClass() {
  if (!validateFields([['#st-query', '班级ID', form.query.classId]])) return
  const r = await doRequest('query', 'GET', '/student/students/class/' + form.query.classId + qs({ skip: form.query.skip || null, limit: form.query.limit || null }))
  listData.value = pickList(r.data)
}

async function updateStudent() {
  if (!validateFields([['#st-op', '学生ID', form.op.id]])) return
  const body = clean({
    class_id: form.op.classId, student_name: form.op.name,
    gender: form.op.gender, age: form.op.age, major: form.op.major
  })
  await doRequest('op', 'PATCH', '/student/students/' + form.op.id, { body })
}

async function deleteStudent() {
  if (!validateFields([['#st-op', '学生ID', form.op.id]])) return
  if (!confirm('确认逻辑删除该学生？')) return
  await doRequest('op', 'DELETE', '/student/students/' + form.op.id)
}

async function restoreStudent() {
  if (!validateFields([['#st-op', '学生ID', form.op.id]])) return
  await doRequest('op', 'POST', '/student/students/' + form.op.id + '/restore')
}
</script>
