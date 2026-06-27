<template>
  <div class="smart-input">
    <h3>{{ title }}</h3>

    <div class="field">
      <label>{{ inputLabel }}</label>
      <textarea
        v-model="text"
        :placeholder="placeholder"
        rows="3"
        :disabled="extracting"
      />
    </div>

    <div class="actions">
      <button class="btn" :disabled="extracting || !text.trim()" @click="doExtract">
        {{ extracting ? '提取中...' : extractBtnText }}
      </button>
    </div>

    <ResultBadge :badge="extractBadge" :text="extractError" />

    <!-- 预览区 -->
    <div v-if="extracted" class="preview">
      <h4>预览确认</h4>
      <div class="grid">
        <div
          v-for="f in fields"
          :key="f.key"
          class="field"
          :class="{ missing: isMissing(f.key) }"
        >
          <label>
            {{ f.label }}
            <span v-if="f.required" class="req">*</span>
            <span v-if="isMissing(f.key)" class="missing-hint">（待补填）</span>
          </label>
          <input
            v-if="f.type !== 'date'"
            :value="extracted[f.key] ?? ''"
            :type="f.type === 'number' ? 'number' : 'text'"
            :placeholder="f.placeholder || ''"
            @input="e => setField(f.key, f.type === 'number' ? Number(e.target.value) || null : e.target.value)"
          />
          <input
            v-else
            :value="extracted[f.key] ?? ''"
            type="date"
            @input="e => setField(f.key, e.target.value || null)"
          />
        </div>
      </div>

      <div v-if="missingRequired.length" class="hint warn">
        请补填标红的必填字段后再确认提交。
      </div>

      <div class="actions">
        <button class="btn" :disabled="submitting || missingRequired.length > 0" @click="doSubmit">
          {{ submitting ? '提交中...' : confirmBtnText }}
        </button>
        <button class="btn secondary" :disabled="extracting" @click="doExtract">
          重新提取
        </button>
        <button class="btn secondary" :disabled="extracting" @click="reset">
          清空
        </button>
      </div>

      <ResultBadge :badge="submitBadge" :text="submitMessage" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { request, clean } from '../api'
import ResultBadge from './ResultBadge.vue'

const props = defineProps({
  title: { type: String, default: '智能录入' },
  inputLabel: { type: String, default: '用自然语言描述' },
  placeholder: { type: String, default: '例如：新增学生张三，学号S2024001，班级3班，男，20岁，计算机专业本科' },
  extractBtnText: { type: String, default: '智能提取' },
  confirmBtnText: { type: String, default: '确认创建' },
  extractUrl: { type: String, required: true },
  submitUrl: { type: String, required: true },
  submitMethod: { type: String, default: 'POST' },
  fields: { type: Array, required: true },
  fieldMap: { type: Object, default: null }
})

const emit = defineEmits(['submitted'])

const text = ref('')
const extracting = ref(false)
const submitting = ref(false)
const extracted = ref(null)
const extractError = ref('')
const submitMessage = ref('')

const extractBadge = computed(() => {
  if (!extractError.value && !extracted.value) return null
  if (extracted.value) return { ok: true, text: extractError.value ? '提取完成（部分字段缺失）' : '提取完成' }
  return null
})

const submitBadge = computed(() => {
  if (!submitMessage.value) return null
  if (submitMessage.value.includes('成功')) return { ok: true, text: '提交成功' }
  if (submitMessage.value.includes('失败') || submitMessage.value.includes('错误'))
    return { ok: false, text: '提交失败' }
  return null
})

const missingRequired = computed(() => {
  if (!extracted.value) return []
  return props.fields
    .filter(f => f.required)
    .filter(f => {
      const v = extracted.value[f.key]
      return v === null || v === undefined || v === ''
    })
    .map(f => f.key)
})

function isMissing(key) {
  return missingRequired.value.includes(key)
}

function setField(key, value) {
  if (extracted.value) {
    extracted.value = { ...extracted.value, [key]: value }
  }
}

async function doExtract() {
  if (!text.value.trim()) return
  extracting.value = true
  extractError.value = ''
  extracted.value = null

  try {
    const r = await request('POST', props.extractUrl, {
      body: { text: text.value.trim() }
    })

    if (r.ok && r.data?.data) {
      const d = r.data.data
      if (d.error) {
        extractError.value = d.error
        // 即使失败也展示字段区域让用户手动填
        extracted.value = initEmptyFields()
      } else {
        extracted.value = mergeExtracted(d.extracted || {})
        if (d.missing_required?.length) {
          extractError.value = `以下必填字段需要手动补填：${d.missing_required.join('、')}`
        }
      }
    } else {
      extractError.value = r.data?.msg || '提取请求失败'
      extracted.value = initEmptyFields()
    }
  } catch (e) {
    extractError.value = `网络错误: ${e.message}`
    extracted.value = initEmptyFields()
  } finally {
    extracting.value = false
  }
}

function initEmptyFields() {
  const obj = {}
  props.fields.forEach(f => { obj[f.key] = null })
  return obj
}

function mergeExtracted(data) {
  const obj = {}
  props.fields.forEach(f => {
    obj[f.key] = data[f.key] !== undefined ? data[f.key] : null
  })
  return obj
}

async function doSubmit() {
  if (missingRequired.value.length > 0) return
  submitting.value = true
  submitMessage.value = ''

  const body = clean(mapToSubmitBody(extracted.value))

  try {
    const r = await request(props.submitMethod, props.submitUrl, { body })
    if (r.ok) {
      submitMessage.value = '创建成功'
      emit('submitted', r.data)
    } else {
      submitMessage.value = r.data?.msg || r.data?.detail || '提交失败'
    }
  } catch (e) {
    submitMessage.value = `网络错误: ${e.message}`
  } finally {
    submitting.value = false
  }
}

function mapToSubmitBody(data) {
  const map = props.fieldMap
  if (!map) return { ...data }
  const out = {}
  for (const [from, to] of Object.entries(map)) {
    if (data[from] !== null && data[from] !== undefined && data[from] !== '') {
      out[to] = data[from]
    }
  }
  return out
}

function reset() {
  text.value = ''
  extracted.value = null
  extractError.value = ''
  submitMessage.value = ''
}
</script>

<style scoped>
.smart-input h3 {
  margin: 0 0 22px;
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1.25;
  font-weight: 600;
  color: var(--text);
}

.smart-input textarea {
  width: 100%;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  color: var(--text);
  font-family: var(--font-body);
  font-size: 14px;
  resize: vertical;
  outline: none;
  transition: border-color var(--dur-fast) var(--ease-out);
}

.smart-input textarea:focus {
  border-color: var(--gold);
}

.smart-input textarea:disabled {
  opacity: 0.5;
}

.preview {
  margin-top: 20px;
  border-top: 1px solid var(--line);
  padding-top: 18px;
}

.preview h4 {
  margin: 0 0 14px;
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--text-soft);
}

.field.missing input {
  border-color: var(--danger) !important;
  background: var(--danger-bg);
}

.missing-hint {
  color: var(--danger);
  font-size: 12px;
  font-weight: 400;
}

.req {
  color: var(--danger);
}

.hint.warn {
  color: var(--warning);
  font-size: 13px;
  margin-bottom: 12px;
}
</style>
