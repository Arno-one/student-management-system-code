<template>
  <section class="page active">
    <div class="card">
      <h3>智能邮件助手</h3>

      <!-- 步骤一 -->
      <div class="section-title">① 描述需求，生成邮件</div>
      <div class="field"><label>需求描述 *</label><textarea v-model="form.prompt" rows="3" placeholder="给老师写一封请假邮件，请假两天"></textarea></div>
      <div class="actions">
        <button class="btn" :disabled="genLoading" @click="generateEmail">{{ genLoading ? '生成中...' : '✨ 生成邮件' }}</button>
      </div>

      <!-- 步骤二 -->
      <div v-if="showEdit" class="mail-edit">
        <div class="section-title">② 编辑确认后寄出（可自由修改主题和正文）</div>
        <div class="field"><label>收件邮箱 *</label><input v-model="form.receiver" /></div>
        <div class="field"><label>邮件主题 *</label><input v-model="form.subject" placeholder="邮件主题" /></div>
        <div class="field">
          <label>邮件正文 *（支持加粗 / 列表 / 换行等排版）</label>
          <div class="rte" :class="{ invalid: bodyInvalid }">
            <div class="rte-toolbar">
              <button type="button" title="加粗" @mousedown.prevent="rteCmd('bold')"><b>B</b></button>
              <button type="button" title="斜体" @mousedown.prevent="rteCmd('italic')"><i>I</i></button>
              <button type="button" title="下划线" @mousedown.prevent="rteCmd('underline')"><u>U</u></button>
              <span class="rte-sep"></span>
              <button type="button" title="标题" @mousedown.prevent="rteCmd('formatBlock', '<h3>')">H</button>
              <button type="button" title="无序列表" @mousedown.prevent="rteCmd('insertUnorderedList')">• 列表</button>
              <button type="button" title="有序列表" @mousedown.prevent="rteCmd('insertOrderedList')">1. 列表</button>
              <span class="rte-sep"></span>
              <button type="button" title="清除格式" @mousedown.prevent="rteCmd('removeFormat')">清除格式</button>
            </div>
            <div
              ref="bodyEl"
              class="rte-area"
              contenteditable="true"
              data-placeholder="邮件正文"
              @input="onBodyInput"
              v-html="form.body"
            ></div>
          </div>
        </div>
        <div class="actions">
          <button class="btn" :disabled="sendLoading" @click="sendEmail">{{ sendLoading ? '寄出中...' : '📨 寄出邮件' }}</button>
          <button class="btn secondary" @click="generateEmail">🔄 重新生成</button>
        </div>
      </div>

      <ResultBadge :badge="result.badge" :text="result.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, nextTick } from 'vue'
import { request, qs, getBaseUrl } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import { validateFields } from '../utils/helpers'

const form = reactive({
  prompt: '', receiver: '786453528@qq.com', subject: '', body: ''
})

const showEdit = ref(false)
const genLoading = ref(false)
const sendLoading = ref(false)
const bodyInvalid = ref(false)
const bodyEl = ref(null)
const result = reactive({ badge: null, text: '' })

function mailStatus(ok, msg) {
  result.badge = { ok, text: msg }
  result.text = ''
}

function rteCmd(cmd, value) {
  bodyEl.value?.focus()
  document.execCommand(cmd, false, value || null)
}

function textToHtml(text) {
  const esc = String(text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return esc.replace(/\n/g, '<br>')
}

function onBodyInput() {
  bodyInvalid.value = false
}

async function generateEmail() {
  if (!validateFields([['#page-email', '需求描述', form.prompt]])) return
  genLoading.value = true
  try {
    const r = await request('POST', '/email/generate' + qs({ prompt: form.prompt }), { silent: true })
    const content = r?.ok && r?.data?.data
    if (content) {
      form.subject = content.subject || ''
      form.body = textToHtml(content.body)
      showEdit.value = true
      await nextTick()
      // Scroll edit box into view
      const editBox = document.querySelector('.mail-edit')
      editBox?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      mailStatus(true, '邮件内容已生成，请在下方编辑后寄出')
    } else {
      mailStatus(false, '邮件生成失败，请重试')
    }
  } catch (e) {
    mailStatus(false, `网络错误: ${e.message}`)
  } finally {
    genLoading.value = false
  }
}

async function sendEmail() {
  const bodyText = bodyEl.value?.innerText?.trim() || ''
  bodyInvalid.value = !bodyText

  if (!validateFields([['#page-email', '收件邮箱', form.receiver], ['#page-email', '邮件主题', form.subject]])) return
  if (!bodyText) {
    alert('请填写：邮件正文')
    return
  }

  sendLoading.value = true
  try {
    const bodyHtml = bodyEl.value?.innerHTML || ''
    const r = await request('POST', '/email/send' + qs({
      subject: form.subject, body: bodyHtml, receiver: form.receiver
    }), { silent: true })
    const res = r?.data?.data
    if (res?.success) {
      mailStatus(true, res.message || '邮件已发送')
    } else {
      mailStatus(false, res?.message || '邮件发送失败')
    }
  } catch (e) {
    mailStatus(false, `网络错误: ${e.message}`)
  } finally {
    sendLoading.value = false
  }
}
</script>
