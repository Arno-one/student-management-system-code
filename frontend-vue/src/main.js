import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles.css'
import { request, setAuth, apiState } from './api'

const app = createApp(App)
app.use(router)

async function bootstrapAuth() {
  if (!apiState.token) return
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)
    const r = await request('GET', '/auth/me', { signal: controller.signal })
    clearTimeout(timeout)
    if (r.ok && r.data?.data) {
      setAuth(apiState.token, r.data.data)
    } else {
      setAuth('', null)
    }
  } catch {
    // 网络异常或超时：保留 token 但清除用户数据，让 router guard 重定向到登录页
    setAuth('', null)
  }
}

// 先验证 token 有效性，再挂载应用，避免用过期 token 渲染错误页面
bootstrapAuth().finally(() => {
  app.mount('#app')
})
