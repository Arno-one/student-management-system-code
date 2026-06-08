import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles.css'
import { request, setAuth, apiState } from './api'

const app = createApp(App)
app.use(router)
app.mount('#app')

async function bootstrapAuth() {
  if (!apiState.token) return
  const r = await request('GET', '/auth/me')
  if (r.ok && r.data?.data) {
    setAuth(apiState.token, r.data.data)
  } else {
    setAuth('', null)
  }
}

bootstrapAuth()
