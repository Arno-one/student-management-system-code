<template>
  <section id="page-statistics" class="page active">
    <div class="sub-bar">
      <label>统计项目</label>
      <CustomSelect v-model="selectedStat" :options="statOptions" />
    </div>

    <div class="card">
      <h3>统计查询</h3>
      <div class="grid">
        <div class="field"><label>偏移量</label><input v-model.number="form.skip" type="number" /></div>
        <div class="field"><label>每页条数</label><input v-model.number="form.limit" type="number" /></div>
        <div class="field"><label>年龄阈值</label><input v-model.number="form.age" type="number" /></div>
        <div class="field"><label>分数阈值</label><input v-model.number="form.grade" type="number" /></div>
        <div class="field"><label>薪资榜条数（≥5）</label><input v-model.number="form.salLimit" type="number" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="runStat">{{ loading ? '处理中...' : '执行统计' }}</button></div>
      <DataTable :data="listData" />
      <ResultBadge :badge="result.badge" :text="result.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { request, qs, pickList } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import CustomSelect from '../components/CustomSelect.vue'

const selectedStat = ref('staGeStu')
const statOptions = [
  { value: 'staGeStu', label: '年龄大于阈值的学生' },
  { value: 'staStuCount', label: '学生总数' },
  { value: 'staScoreGreater', label: '每次考试≥阈值分' },
  { value: 'staScoreFails', label: '2次以上不及格' },
  { value: 'staClassAvg', label: '班级平均分' },
  { value: 'staTallSal', label: '最高薪资排行' },
  { value: 'staJobTime', label: '就业时长' },
  { value: 'staAvgClassJobTime', label: '班级平均就业时长' },
]
const loading = ref(false)
const listData = ref(null)
const result = reactive({ badge: null, text: '' })

const form = reactive({ skip: 0, limit: 10, age: 30, grade: 80, salLimit: 5 })

const statFns = {
  staGeStu: async () => {
    const r = await request('GET', '/statistics/ge_stu/plus' + qs({ skip: form.skip || null, limit: form.limit || null, age: form.age || null }))
    return { data: r, list: pickList(r.data) }
  },
  staStuCount: async () => {
    const r = await request('GET', '/statistics/stu_count')
    const n = r?.data?.data
    return { data: r, text: r?.ok ? `学生总数：${n ?? '—'}` : '统计失败', isText: true }
  },
  staScoreGreater: async () => {
    const r = await request('GET', '/statistics/score_greater/plus' + qs({ skip: form.skip || null, limit: form.limit || null, grade: form.grade || null }))
    return { data: r, list: pickList(r.data) }
  },
  staScoreFails: async () => {
    const r = await request('GET', '/statistics/score_fails' + qs({ skip: form.skip || null, limit: form.limit || null }))
    return { data: r, list: pickList(r.data) }
  },
  staClassAvg: async () => {
    const r = await request('GET', '/statistics/class_avg' + qs({ skip: form.skip || null, limit: form.limit || null }))
    return { data: r, list: pickList(r.data) }
  },
  staTallSal: async () => {
    const r = await request('GET', '/statistics/tall_sal' + qs({ limit: form.salLimit || null }))
    return { data: r, list: pickList(r.data) }
  },
  staJobTime: async () => {
    const r = await request('GET', '/statistics/job_time' + qs({ skip: form.skip || null, limit: form.limit || null }))
    return { data: r, list: pickList(r.data) }
  },
  staAvgClassJobTime: async () => {
    const r = await request('GET', '/statistics/avg_class_job_time' + qs({ skip: form.skip || null, limit: form.limit || null }))
    return { data: r, list: pickList(r.data) }
  }
}

async function runStat() {
  loading.value = true
  listData.value = null
  result.badge = null
  result.text = ''
  try {
    const fn = statFns[selectedStat.value]
    if (!fn) return
    const res = await fn()
    if (res.isText) {
      result.badge = { ok: res.data?.ok, text: res.data?.ok ? '统计完成' : '统计失败' }
      result.text = res.text || ''
    } else {
      listData.value = res.list
      result.badge = { ok: res.data?.ok, text: res.data?.ok ? '统计完成' : (res.data?.data?.msg || '统计失败') }
      result.text = ''
    }
  } catch (e) {
    result.badge = { ok: false, text: '网络错误' }
    result.text = e.message
  } finally { loading.value = false }
}
</script>
