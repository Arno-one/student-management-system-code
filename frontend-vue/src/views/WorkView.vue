<template>
  <section class="page active">
    <div class="sub-bar">
      <label>选择功能</label>
      <select v-model="sub" @change="saveSub">
        <option value="wk-eval">学生评价（大模型生成）</option>
        <option value="wk-img">文生图（通义万相）</option>
        <option value="wk-talk">多轮记忆对话</option>
        <option value="wk-weather">天气查询 / 经纬度解析</option>
      </select>
    </div>

    <!-- 学生评价 -->
    <div class="card subcard" :class="{ show: sub === 'wk-eval' }">
      <h3>学生评价（大模型生成）</h3>
      <div class="grid">
        <div class="field"><label>学生ID *</label><input v-model.number="form.eval.stuId" type="number" placeholder="1" /></div>
        <div class="field"><label>评价风格 *</label><select v-model="form.eval.style"><option>幽默</option><option>严肃</option><option>激励</option><option>批判</option></select></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workEvaluation">{{ loading ? '处理中...' : '生成评价' }}</button></div>
      <ResultBadge :badge="results.eval.badge" :text="results.eval.text" />
    </div>

    <!-- 文生图 -->
    <div class="card subcard" :class="{ show: sub === 'wk-img' }">
      <h3>文生图（通义万相）</h3>
      <div class="field"><label>提示词 *</label><textarea v-model="form.img.prompt" rows="3" placeholder="一只在草地上奔跑的柯基犬，阳光明媚"></textarea></div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workImage">{{ loading ? '处理中...' : '生成图片' }}</button></div>
      <div class="img-preview" v-if="imageUrl"><img :src="imageUrl" alt="生成结果" /></div>
      <ResultBadge :badge="results.img.badge" :text="results.img.text" />
    </div>

    <!-- 多轮对话 -->
    <div class="card subcard" :class="{ show: sub === 'wk-talk' }">
      <h3>多轮记忆对话</h3>
      <div class="grid">
        <div class="field"><label>会话ID *</label><input v-model="form.talk.session" /></div>
        <div class="field" style="grid-column: span 2;"><label>本轮输入 *</label><input v-model="form.talk.prompt" placeholder="你好，帮我介绍一下这个系统" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="workTalk">发送</button>
        <button class="btn danger" :disabled="loading" @click="workClearTalk">清空记忆</button>
      </div>
      <ResultBadge :badge="results.talk.badge" :text="results.talk.text" />
    </div>

    <!-- 天气 / 经纬度 -->
    <div class="card subcard" :class="{ show: sub === 'wk-weather' }">
      <!-- 天气查询 -->
      <div class="section-title">天气查询</div>
      <div class="grid">
        <div class="field"><label>经纬度（纬度,经度）</label><input v-model="form.weather.location" placeholder="39.905023,116.724502" /></div>
        <div class="field"><label>行政区划编码</label><input v-model="form.weather.adcode" placeholder="130681" /></div>
        <div class="field"><label>天气类型</label><select v-model="form.weather.wtype"><option value="now">实时</option><option value="future">多日</option><option value="hours">逐时</option></select></div>
        <div class="field"><label>附加字段</label><input v-model="form.weather.added" placeholder="alarm,air" /></div>
        <div class="field"><label>天数控制（多日生效）</label><input v-model.number="form.weather.getmd" type="number" placeholder="0" /></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workWeather">查天气</button></div>
      <div class="weather-view" v-html="weatherHtml"></div>

      <!-- 地址解析 -->
      <div class="section-title">地址解析为经纬度</div>
      <div class="grid">
        <div class="field" style="grid-column: span 2;"><label>地址 *</label><input v-model="form.geo.address" placeholder="北京市海淀区彩和坊路海淀西大街74号" /></div>
        <div class="field"><label>解析策略</label><select v-model="form.geo.policy"><option value="0">标准</option><option value="1">宽松</option></select></div>
      </div>
      <div class="actions"><button class="btn" :disabled="loading" @click="workGeocoder">解析地址</button></div>
      <div class="weather-view" v-html="geoHtml"></div>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { request, qs, pickApiContent } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import { validateFields, weatherEmoji, findImageUrl } from '../utils/helpers'

const sub = ref(localStorage.getItem('sub-work') || 'wk-eval')
const loading = ref(false)
const imageUrl = ref('')
const weatherHtml = ref('')
const geoHtml = ref('')

const form = reactive({
  eval: { stuId: null, style: '幽默' },
  img: { prompt: '' },
  talk: { session: 'user-001', prompt: '' },
  weather: { location: '', adcode: '', wtype: 'now', added: '', getmd: null },
  geo: { address: '', policy: '0' }
})

const results = reactive({
  eval: { badge: null, text: '' }, img: { badge: null, text: '' },
  talk: { badge: null, text: '' }
})

function saveSub() { localStorage.setItem('sub-work', sub.value) }

function setResult(target, ok, msg) {
  results[target].badge = { ok, text: msg }
  results[target].text = ''
}

async function workEvaluation() {
  if (!validateFields([['#wk-eval', '学生ID', form.eval.stuId]])) return
  loading.value = true
  setResult('eval', false, '')
  try {
    const r = await request('POST', '/work/evaluation' + qs({ student_id: form.eval.stuId, style: form.eval.style || null }))
    if (r.ok) {
      setResult('eval', true, '评价生成成功')
      results.eval.text = pickApiContent(r.data)
    } else {
      setResult('eval', false, r.data?.msg || '评价生成失败')
    }
  } catch (e) {
    setResult('eval', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

async function workImage() {
  if (!validateFields([['#wk-img', '提示词', form.img.prompt]])) return
  loading.value = true
  imageUrl.value = ''
  setResult('img', false, '')
  try {
    const r = await request('POST', '/work/image' + qs({ prompt: form.img.prompt || null }))
    const inner = r?.data?.data
    const url = (inner && typeof inner === 'object' && inner.image_url) || findImageUrl(r?.data)
    if (r.ok && url) {
      imageUrl.value = url
      setResult('img', true, '图片已生成，请见上方预览')
    } else {
      setResult('img', false, (inner?.error) || r?.data?.msg || '文生图失败')
    }
  } catch (e) {
    setResult('img', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

async function workTalk() {
  if (!validateFields([['#wk-talk', '会话ID', form.talk.session], ['#wk-talk', '本轮输入', form.talk.prompt]])) return
  loading.value = true
  setResult('talk', false, '')
  try {
    const r = await request('POST', '/work/talks' + qs({ session_id: form.talk.session, prompt: form.talk.prompt }))
    if (r.ok) {
      setResult('talk', true, '对话成功')
      results.talk.text = pickApiContent(r.data) || '（无回复内容）'
    } else {
      setResult('talk', false, r.data?.msg || '对话失败')
    }
  } catch (e) {
    setResult('talk', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

async function workClearTalk() {
  if (!validateFields([['#wk-talk', '会话ID', form.talk.session]])) return
  loading.value = true
  setResult('talk', false, '')
  try {
    const r = await request('POST', '/work/talks/clear' + qs({ session_id: form.talk.session }))
    const msg = (r?.ok && r?.data?.data?.message) || r?.data?.msg || '记忆已清空'
    setResult('talk', r?.ok, r?.ok ? `已清空记忆: ${msg}` : msg)
  } catch (e) {
    setResult('talk', false, `网络错误: ${e.message}`)
  } finally { loading.value = false }
}

async function workWeather() {
  if (!form.weather.location && !form.weather.adcode) {
    return alert('经纬度或行政编码至少填一个')
  }
  loading.value = true
  weatherHtml.value = ''
  try {
    const r = await request('GET', '/work/weather' + qs({
      location: form.weather.location || null, adcode: form.weather.adcode || null,
      weather_type: form.weather.wtype, added_fields: form.weather.added || null,
      get_md: form.weather.getmd
    }))
    if (r.ok) {
      weatherHtml.value = renderWeather(r.data)
    } else {
      weatherHtml.value = '<div class="geo-card"><div class="geo-fail">❌ 天气查询失败，请检查参数或稍后重试</div></div>'
    }
  } catch (e) {
    weatherHtml.value = '<div class="geo-card"><div class="geo-fail">❌ 天气查询失败</div></div>'
  } finally { loading.value = false }
}

function renderWeather(resp) {
  const result = resp?.data?.result
  if (!result) return '<div class="hint">未解析到天气数据</div>'

  // 实时天气
  if (Array.isArray(result.realtime)?.length) {
    return result.realtime.map(item => {
      const f = item.infos || {}
      return `<div class="wx-card">
        ${renderWeatherHead(item)}
        <div class="wx-main">
          <div class="wx-emoji">${weatherEmoji(f.weather)}</div>
          <div>
            <div class="wx-temp">${f.temperature ?? '--'}<small>℃</small></div>
            <div class="wx-desc">${f.weather ?? '未知天气'}</div>
          </div>
        </div>
        <div class="wx-metrics">${renderMetrics(f)}</div>
      </div>`
    }).join('')
  }

  // 多日预报
  if (Array.isArray(result.forecast)?.length) {
    return result.forecast.map(item => {
      const days = (item.infos || []).map(d => {
        const day = d.day || {}, night = d.night || {}
        return `<div class="wx-day">
          <div class="wx-day-title">${d.week || ''}</div><div class="wx-day-sub">${d.date || ''}</div>
          <div class="wx-day-emoji">${weatherEmoji(day.weather || night.weather)}</div>
          <div class="wx-day-temp">${night.temperature ?? '--'}~${day.temperature ?? '--'}℃</div>
          <div class="wx-day-line">☀️ ${day.weather || '--'}</div>
          <div class="wx-day-line">🌙 ${night.weather || '--'}</div>
          <div class="wx-day-line">💨 ${day.wind_direction || ''} ${day.wind_power || ''}</div>
        </div>`
      }).join('')
      return `<div class="card" style="padding:16px">${renderWeatherHead(item)}<div class="wx-section-h">未来天气预报</div><div class="wx-list">${days}</div></div>`
    }).join('')
  }

  // 逐时预报
  if (Array.isArray(result.forecast_hours)?.length) {
    return result.forecast_hours.map(item => {
      const hours = (item.infos || []).map(h => {
        const info = h.info || {}
        const hm = String(h.hour || '').split(' ')[1] || h.hour || ''
        return `<div class="wx-day">
          <div class="wx-day-title">${hm}</div>
          <div class="wx-day-emoji">${weatherEmoji(info.weather)}</div>
          <div class="wx-day-temp">${info.temperature ?? '--'}℃</div>
          <div class="wx-day-line">${info.weather || '--'}</div>
          <div class="wx-day-line">💨 ${info.wind_direction || ''} ${info.wind_power || ''}</div>
        </div>`
      }).join('')
      return `<div class="card" style="padding:16px">${renderWeatherHead(item)}<div class="wx-section-h">24小时逐时预报</div><div class="wx-list">${hours}</div></div>`
    }).join('')
  }

  return '<div class="hint">暂无可展示的天气数据</div>'
}

function renderWeatherHead(item) {
  const loc = [item.province, item.city, item.district].filter(Boolean).join(' · ')
  const adcode = item.adcode ? `<span class="wx-adcode">编码 ${item.adcode}</span>` : ''
  const time = item.update_time ? `<div class="wx-time">🕒 更新于 ${item.update_time}</div>` : ''
  return `<div class="wx-head"><div class="wx-loc">📍 ${loc}${adcode}</div>${time}</div>`
}

function renderMetrics(infos) {
  const items = [
    ['🧭', '风向', infos.wind_direction, ''],
    ['💨', '风力', infos.wind_power, ''],
    ['🍃', '标准风力', infos.wind_power_v2, ''],
    ['💧', '湿度', infos.humidity, '%'],
    ['⏲️', '气压', infos.air_pressure, ' 百帕']
  ]
  return items.filter(([, , v]) => v != null && v !== '')
    .map(([ico, lbl, v, unit]) =>
      `<div class="wx-metric"><span class="ico">${ico}</span><span class="meta"><span class="lbl">${lbl}</span><span class="val">${v}${unit}</span></span></div>`
    ).join('')
}

async function workGeocoder() {
  if (!validateFields([['#wk-weather', '地址', form.geo.address]])) return
  loading.value = true
  geoHtml.value = ''
  try {
    const r = await request('GET', '/work/geocoder' + qs({ address: form.geo.address, policy: form.geo.policy }))
    if (r.ok) {
      geoHtml.value = renderGeocoder(r.data)
    } else {
      geoHtml.value = '<div class="geo-card"><div class="geo-fail">❌ 地址解析失败，请检查地址或稍后重试</div></div>'
    }
  } catch (e) {
    geoHtml.value = '<div class="geo-card"><div class="geo-fail">❌ 地址解析失败</div></div>'
  } finally { loading.value = false }
}

function renderGeocoder(resp) {
  const d = resp?.data
  if (!d || typeof d !== 'object') return '<div class="hint">未解析到地址数据</div>'
  if (d.success === false) return '<div class="geo-card"><div class="geo-fail">❌ 地址解析失败，请检查地址是否准确</div></div>'

  const c = d.address_components || {}
  const fullAddr = [c.province, c.city, c.district, c.street, c.street_number].filter(Boolean).join('')

  const metrics = [
    ['🧭', '纬度', d.lat], ['🧭', '经度', d.lng], ['🔢', '行政编码', d.adcode], ['🎯', '解析等级', d.level]
  ].filter(([, , v]) => v != null && v !== '')
   .map(([ico, lbl, v]) =>
     `<div class="geo-metric"><span class="ico">${ico}</span><span class="meta"><span class="lbl">${lbl}</span><span class="val">${v}</span></span></div>`
   ).join('')

  let bar = ''
  if (d.reliability != null) {
    const pct = Math.max(0, Math.min(100, Number(d.reliability) * 10))
    bar = `<div class="geo-bar-wrap"><div class="geo-bar-head"><span>📊 解析可信度</span><span>${d.reliability} / 10</span></div><div class="geo-bar"><i style="width:${pct}%"></i></div></div>`
  }

  const adcode = d.adcode ? String(d.adcode) : ''
  const location = (d.lat != null && d.lng != null) ? `${d.lat},${d.lng}` : ''
  let linkBtn = ''
  if (adcode || location) {
    linkBtn = `<div style="margin-top:16px"><button class="btn" onclick="window._useGeoForWeather && window._useGeoForWeather('${adcode}','${location}')">🌤️ 查该地天气</button></div>`
  }

  return `<div class="geo-card">
    <div class="geo-addr">📍 ${fullAddr || '未知地址'}</div>
    <div class="geo-coord">🌐 经纬度坐标：${d.lat ?? '--'}, ${d.lng ?? '--'}</div>
    <div class="geo-metrics">${metrics}</div>${bar}${linkBtn}
  </div>`
}
</script>
