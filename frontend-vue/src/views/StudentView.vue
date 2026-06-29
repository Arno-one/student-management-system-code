<template>
  <section id="page-student" class="page active">
    <!-- 创建学生 -->
    <div id="st-create" class="card subcard" :class="{ show: sub === 'st-create' }">
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
    <div id="st-query" class="card subcard" :class="{ show: sub === 'st-query' }">
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
    <div id="st-op" class="card subcard" :class="{ show: sub === 'st-op' }">
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

    <!-- 智能录入 -->
    <div id="st-nl" class="card subcard" :class="{ show: sub === 'st-nl' }">
      <SmartInput
        title="智能录入学生"
        input-label="用自然语言描述学生信息"
        placeholder="例如：新增学生张三，学号S2024001，班级3班，男，20岁，计算机专业本科"
        extract-btn-text="智能提取"
        confirm-btn-text="确认创建"
        extract-url="/student/students/extract"
        submit-url="/student/students"
        submit-method="POST"
        :fields="studentFields"
        :field-map="studentFieldMap"
        @submitted="onNlSubmitted"
      />
    </div>

    <!-- 智能修改 -->
    <div id="st-nl-update" class="card subcard" :class="{ show: sub === 'st-nl-update' }">
      <h3>智能修改学生</h3>
      <div class="field">
        <label>用自然语言描述你要修改的内容</label>
        <textarea
          v-model="nlUpdate.text"
          placeholder="例如：把学号S2025001的张三的专业改成软件工程，年龄改成21"
          rows="3"
          :disabled="nlUpdate.extracting"
        ></textarea>
      </div>
      <div class="actions">
        <button class="btn" :disabled="nlUpdate.extracting || !nlUpdate.text.trim()" @click="doNlUpdateExtract">
          {{ nlUpdate.extracting ? '提取中...' : '智能提取' }}
        </button>
      </div>
      <ResultBadge :badge="nlUpdate.badge" :text="nlUpdate.errMsg" />

      <!-- 预览确认 -->
      <div v-if="nlUpdate.extracted" class="preview" style="margin-top:20px;border-top:1px solid var(--line);padding-top:18px">
        <h4 style="margin:0 0 14px;font-family:var(--font-display);font-size:16px;color:var(--text-soft)">预览确认</h4>

        <!-- 目标学生 -->
        <div class="grid">
          <div class="field">
            <label>学生ID（只读）</label>
            <input :value="nlUpdate.studentId" disabled />
          </div>
          <div class="field">
            <label>学号（只读）</label>
            <input :value="nlUpdate.studentNo" disabled />
          </div>
          <div class="field">
            <label>姓名（只读）</label>
            <input :value="nlUpdate.studentName" disabled />
          </div>
        </div>

        <h4 style="margin:18px 0 14px;font-family:var(--font-display);font-size:16px;color:var(--text-soft)">变更字段</h4>
        <div class="grid">
          <div v-for="f in updateFields" :key="f.key" class="field">
            <label>{{ f.label }}</label>
            <input
              v-if="f.type !== 'date'"
              :value="nlUpdate.changes[f.key] ?? ''"
              :type="f.type === 'number' ? 'number' : 'text'"
              :placeholder="f.placeholder || ''"
              @input="e => setUpdateField(f.key, f.type === 'number' ? Number(e.target.value) || null : e.target.value)"
            />
            <input
              v-else
              :value="nlUpdate.changes[f.key] ?? ''"
              type="date"
              @input="e => setUpdateField(f.key, e.target.value || null)"
            />
          </div>
        </div>

        <div v-if="!hasUpdateChanges" class="hint warn" style="color:var(--warning);font-size:13px;margin-bottom:12px">
          未检测到需要修改的字段，请在变更字段中手动填写。
        </div>

        <div class="actions">
          <button class="btn" :disabled="nlUpdate.submitting || !hasUpdateChanges" @click="doNlUpdateSubmit">
            {{ nlUpdate.submitting ? '提交中...' : '确认修改' }}
          </button>
          <button class="btn secondary" :disabled="nlUpdate.extracting" @click="doNlUpdateExtract">重新提取</button>
          <button class="btn secondary" :disabled="nlUpdate.extracting" @click="resetNlUpdate">清空</button>
        </div>
        <ResultBadge :badge="nlUpdate.submitBadge" :text="nlUpdate.submitMsg" />
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { request, qs, clean, pickList, pickOne } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import SmartInput from '../components/SmartInput.vue'
import { useModuleSubPage } from '../composables/useModuleSubPage'
import { validateFields } from '../utils/helpers'

const { sub } = useModuleSubPage('student')
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
  op: { badge: null, text: '' },
  nl: { badge: null, text: '' }
})

const studentFields = [
  { key: 'student_no', label: '学号', type: 'text', required: true, placeholder: 'S2024001' },
  { key: 'class_id', label: '班级ID', type: 'number', required: true, placeholder: '1' },
  { key: 'student_name', label: '姓名', type: 'text', required: true, placeholder: '张三' },
  { key: 'gender', label: '性别', type: 'text', required: false, placeholder: '男' },
  { key: 'age', label: '年龄', type: 'number', required: false, placeholder: '20' },
  { key: 'native_place', label: '籍贯', type: 'text', required: false, placeholder: '北京市' },
  { key: 'graduate_school', label: '毕业院校', type: 'text', required: false, placeholder: '北京一中' },
  { key: 'major', label: '专业', type: 'text', required: false, placeholder: '计算机科学' },
  { key: 'education', label: '学历', type: 'text', required: false, placeholder: '本科' },
  { key: 'admission_time', label: '入学时间', type: 'date', required: false },
  { key: 'graduate_time', label: '毕业时间', type: 'date', required: false },
  { key: 'advisor_id', label: '顾问编号', type: 'number', required: false, placeholder: '1' }
]

const studentFieldMap = {
  student_no: 'student_no',
  student_name: 'student_name',
  class_id: 'class_id',
  gender: 'gender',
  age: 'age',
  native_place: 'native_place',
  graduate_school: 'graduate_school',
  major: 'major',
  education: 'education',
  admission_time: 'admission_time',
  graduate_time: 'graduate_time',
  advisor_id: 'advisor_id'
}

const updateFields = [
  { key: 'class_id', label: '班级ID', type: 'number', placeholder: '1' },
  { key: 'student_name', label: '姓名', type: 'text', placeholder: '张三' },
  { key: 'gender', label: '性别', type: 'text', placeholder: '男' },
  { key: 'age', label: '年龄', type: 'number', placeholder: '20' },
  { key: 'native_place', label: '籍贯', type: 'text', placeholder: '北京市' },
  { key: 'graduate_school', label: '毕业院校', type: 'text', placeholder: '北京一中' },
  { key: 'major', label: '专业', type: 'text', placeholder: '计算机科学' },
  { key: 'education', label: '学历', type: 'text', placeholder: '本科' },
  { key: 'admission_time', label: '入学时间', type: 'date' },
  { key: 'graduate_time', label: '毕业时间', type: 'date' },
  { key: 'advisor_id', label: '顾问编号', type: 'number', placeholder: '1' }
]

const updateFieldMap = {
  class_id: 'class_id', student_name: 'student_name', gender: 'gender',
  age: 'age', native_place: 'native_place', graduate_school: 'graduate_school',
  major: 'major', education: 'education', admission_time: 'admission_time',
  graduate_time: 'graduate_time', advisor_id: 'advisor_id'
}

const nlUpdate = reactive({
  text: '',
  extracting: false,
  submitting: false,
  extracted: false,
  badge: null,
  errMsg: '',
  studentId: null,
  studentNo: '',
  studentName: '',
  changes: {},
  submitBadge: null,
  submitMsg: ''
})

const hasUpdateChanges = computed(() => {
  const c = nlUpdate.changes
  return Object.values(c).some(v => v !== null && v !== undefined && v !== '')
})

function setUpdateField(key, value) {
  nlUpdate.changes[key] = value
}

async function doNlUpdateExtract() {
  if (!nlUpdate.text.trim()) return
  nlUpdate.extracting = true
  nlUpdate.errMsg = ''
  nlUpdate.extracted = false
  nlUpdate.changes = {}
  updateFields.forEach(f => { nlUpdate.changes[f.key] = null })

  try {
    const r = await request('POST', '/student/students/update/extract', {
      body: { text: nlUpdate.text.trim() }
    })
    if (r.ok && r.data?.data) {
      const d = r.data.data
      if (d.error) {
        nlUpdate.errMsg = d.error
      } else {
        const ex = d.extracted
        if (!ex || !ex.student_id) {
          nlUpdate.errMsg = '未能识别要修改的学生，请提供学号或学生ID'
        } else {
          nlUpdate.extracted = true
          nlUpdate.studentId = ex.student_id
          nlUpdate.studentNo = ex.student_no || ''
          nlUpdate.studentName = ex.student_name || ''
          if (ex.changes) {
            for (const [k, v] of Object.entries(ex.changes)) {
              if (k in nlUpdate.changes && v != null) {
                nlUpdate.changes[k] = v
              }
            }
          }
        }
      }
    } else {
      nlUpdate.errMsg = r.data?.msg || '提取请求失败'
    }
  } catch (e) {
    nlUpdate.errMsg = `网络错误: ${e.message}`
  } finally {
    nlUpdate.extracting = false
  }
}

async function doNlUpdateSubmit() {
  if (!nlUpdate.studentId || !hasUpdateChanges.value) return
  nlUpdate.submitting = true
  nlUpdate.submitMsg = ''

  const body = clean(mapToUpdateBody(nlUpdate.changes))
  try {
    const r = await request('PATCH', '/student/students/' + nlUpdate.studentId, { body })
    if (r.ok) {
      nlUpdate.submitMsg = '修改成功'
      nlUpdate.submitBadge = { ok: true, text: '修改成功' }
    } else {
      nlUpdate.submitMsg = r.data?.msg || r.data?.detail || '修改失败'
      nlUpdate.submitBadge = { ok: false, text: '修改失败' }
    }
  } catch (e) {
    nlUpdate.submitMsg = `网络错误: ${e.message}`
    nlUpdate.submitBadge = { ok: false, text: '网络错误' }
  } finally {
    nlUpdate.submitting = false
  }
}

function mapToUpdateBody(changes) {
  const out = {}
  for (const [from, to] of Object.entries(updateFieldMap)) {
    if (changes[from] !== null && changes[from] !== undefined && changes[from] !== '') {
      out[to] = changes[from]
    }
  }
  return out
}

function resetNlUpdate() {
  nlUpdate.text = ''
  nlUpdate.extracted = false
  nlUpdate.errMsg = ''
  nlUpdate.submitMsg = ''
  nlUpdate.studentId = null
  nlUpdate.studentNo = ''
  nlUpdate.studentName = ''
  nlUpdate.changes = {}
  nlUpdate.badge = null
  nlUpdate.submitBadge = null
}

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

function onNlSubmitted(data) {
  setResult('nl', true, '学生创建成功')
}
</script>
