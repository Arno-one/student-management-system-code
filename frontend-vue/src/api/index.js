import { reactive } from 'vue'

// Default base URL — can be changed from the topbar
const state = reactive({
  baseUrl: localStorage.getItem('api-base-url') || 'http://localhost:8088'
})

export function getBaseUrl() {
  return state.baseUrl.replace(/\/+$/, '')
}

export function setBaseUrl(url) {
  state.baseUrl = url
  localStorage.setItem('api-base-url', url)
}

export { state as apiState }

// Clean null/undefined/empty from object
export function clean(obj) {
  const out = {}
  for (const k in obj) {
    if (obj[k] !== null && obj[k] !== undefined && obj[k] !== '') out[k] = obj[k]
  }
  return out
}

// Convert params to query string
export function qs(params) {
  const sp = new URLSearchParams()
  for (const k in params) {
    const v = params[k]
    if (v !== null && v !== undefined && v !== '') sp.append(k, v)
  }
  const s = sp.toString()
  return s ? '?' + s : ''
}

// Unified request method
export async function request(method, path, { body, silent = false, signal } = {}) {
  const opts = { method, headers: {}, signal }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const resp = await fetch(getBaseUrl() + path, opts)
  const text = await resp.text()
  let data
  try { data = JSON.parse(text) } catch { data = text }
  return { ok: resp.ok, status: resp.status, data }
}

// Pick list from various response structures
export function pickList(data) {
  if (Array.isArray(data)) return data
  if (data && typeof data === 'object') {
    for (const key of ['data', 'items', 'list', 'records', 'result', 'rows']) {
      if (Array.isArray(data[key])) return data[key]
      if (data[key] && Array.isArray(data[key].items)) return data[key].items
    }
  }
  return null
}

// Pick single record
export function pickOne(resp) {
  const inner = (resp && typeof resp === 'object' && 'data' in resp) ? resp.data : resp
  if (Array.isArray(inner)) return inner
  if (inner && typeof inner === 'object') return [inner]
  return null
}

// Pick content from API response for display
export function pickApiContent(apiBody) {
  if (!apiBody || typeof apiBody !== 'object') return ''
  const inner = apiBody.data
  if (typeof inner === 'string') return inner
  if (typeof inner === 'number') return String(inner)
  if (inner && typeof inner === 'object') {
    if (inner.reply != null) return String(inner.reply)
    if (inner.message) return String(inner.message)
    if (inner.error) return String(inner.error)
  }
  return ''
}
