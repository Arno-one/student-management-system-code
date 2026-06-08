<template>
  <section class="login-page">
    <div class="login-shell card">
      <div class="login-kicker">Campus Operations Suite</div>
      <h1>欢迎登录</h1>
      <p class="login-hint">请输入系统账号与密码进入学生信息管理工作台。</p>

      <div class="field">
        <label>登录账号</label>
        <input v-model="form.username" placeholder="请输入账号" @keydown.enter="submit" />
      </div>

      <div class="field">
        <label>登录密码</label>
        <input v-model="form.password" type="password" placeholder="请输入密码" @keydown.enter="submit" />
      </div>

      <div class="actions login-actions">
        <button class="btn" :disabled="loading" @click="submit">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </div>

      <ResultBadge :badge="result.badge" :text="result.text" />

      <div class="login-tips">
        <strong>默认管理员：</strong>
        <span>admin / Admin@123456</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { request, setAuth } from '../api'
import ResultBadge from '../components/ResultBadge.vue'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({ username: 'admin', password: '' })
const result = reactive({ badge: null, text: '' })

function setResult(ok, text) {
  result.badge = { ok, text }
  result.text = ''
}

async function submit() {
  if (!form.username.trim() || !form.password.trim()) {
    setResult(false, '请输入账号和密码')
    return
  }

  loading.value = true
  try {
    const r = await request('POST', '/auth/login', {
      body: { username: form.username.trim(), password: form.password }
    })
    const payload = r?.data?.data
    if (r.ok && payload?.token) {
      setAuth(payload.token, payload.user)
      setResult(true, '登录成功，正在进入系统')
      const redirect = route.query.redirect || '/student'
      router.replace(String(redirect))
    } else {
      setResult(false, r?.data?.msg || '登录失败')
    }
  } catch (e) {
    setResult(false, `网络错误: ${e.message}`)
  } finally {
    loading.value = false
  }
}
</script>
