<template>
  <section id="page-class" class="page active">
    <div class="sub-bar">
      <label>选择功能</label>
      <select v-model="sub" @change="saveSub">
        <option value="cl-save">新增 / 修改班级</option>
        <option value="cl-query">查询 / 删除班级</option>
      </select>
    </div>

    <!-- 新增/修改 -->
    <div id="cl-save" class="card subcard" :class="{ show: sub === 'cl-save' }">
      <h3>新增 / 修改班级</h3>
      <div class="grid">
        <div class="field"><label>班级ID（修改时填）</label><input v-model.number="form.save.id" type="number" /></div>
        <div class="field"><label>班级编号 *</label><input v-model="form.save.code" placeholder="C001" /></div>
        <div class="field"><label>班级名称 *</label><input v-model="form.save.name" placeholder="计算机1班" /></div>
        <div class="field"><label>开班时间 *</label><input v-model="form.save.start" type="datetime-local" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="saveClass">{{ loading ? '处理中...' : '保存' }}</button></div>
      <ResultBadge :badge="results.save.badge" :text="results.save.text" />
    </div>

    <!-- 查询/删除 -->
    <div id="cl-query" class="card subcard" :class="{ show: sub === 'cl-query' }">
      <h3>查询 / 删除班级</h3>
      <div class="grid">
        <div class="field"><label>页码</label><input v-model.number="form.query.page" type="number" /></div>
        <div class="field"><label>每页条数</label><input v-model.number="form.query.limit" type="number" /></div>
        <div class="field"><label>班级ID（按ID查 / 删除）</label><input v-model.number="form.query.id" type="number" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="getClasses">分页查询</button>
        <button class="btn secondary" :disabled="loading" @click="getClassById">按ID查</button>
        <button class="btn danger" :disabled="loading" @click="delClass">删除班级</button>
      </div>
      <DataTable :data="listData" />
      <ResultBadge :badge="results.query.badge" :text="results.query.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { request, qs, pickList, pickOne } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import { validateFields } from '../utils/helpers'

const sub = ref(localStorage.getItem('sub-class') || 'cl-save')
const loading = ref(false)
const listData = ref(null)

const form = reactive({
  save: { id: null, code: '', name: '', start: '' },
  query: { page: 1, limit: 10, id: null }
})

const results = reactive({
  save: { badge: null, text: '' }, query: { badge: null, text: '' }
})

function saveSub() { localStorage.setItem('sub-class', sub.value) }

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

async function saveClass() {
  if (!validateFields([['#cl-save', '班级编号', form.save.code], ['#cl-save', '班级名称', form.save.name], ['#cl-save', '开班时间', form.save.start]])) return
  const body = { class_code: form.save.code, class_name: form.save.name, start_time: form.save.start ? form.save.start + ':00' : null }
  await doRequest('save', 'POST', '/class/create_or_update_class' + qs({ id: form.save.id }), { body })
}

async function getClasses() {
  const r = await doRequest('query', 'GET', '/class/get_class' + qs({ page: form.query.page || null, limit: form.query.limit || null }))
  listData.value = pickList(r.data)
}

async function getClassById() {
  if (!validateFields([['#cl-query', '班级ID', form.query.id]])) return
  const r = await doRequest('query', 'GET', '/class/get_class/' + form.query.id)
  listData.value = pickOne(r.data)
}

async function delClass() {
  if (!validateFields([['#cl-query', '班级ID', form.query.id]])) return
  if (!confirm('确认删除该班级？')) return
  await doRequest('query', 'DELETE', '/class/del_class' + qs({ id: form.query.id }))
}
</script>
