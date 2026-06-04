/**
 * Validate required form fields.
 * fields: array of [sectionId, label, value] tuples.
 * The sectionId is used to scope validation (e.g. '#st-create').
 * Returns true if all fields pass, false otherwise.
 */
export function validateFields(fields) {
  const missing = []
  fields.forEach(([sectionId, label, value]) => {
    const v = value === null || value === undefined ? '' : String(value).trim()
    if (!v) {
      missing.push(label)
      // Highlight the invalid input within the section
      const section = document.querySelector(sectionId)
      if (section) {
        const inputs = section.querySelectorAll('input, select, textarea')
        for (const el of inputs) {
          if (!el.value || !el.value.toString().trim()) {
            el.classList.add('invalid')
          } else {
            el.classList.remove('invalid')
          }
        }
      }
    }
  })
  if (missing.length) {
    alert('请填写：' + missing.join('、'))
  }
  // Clear invalid markers when validation passes
  if (missing.length === 0) {
    document.querySelectorAll('.invalid').forEach(el => el.classList.remove('invalid'))
  }
  return missing.length === 0
}

/**
 * Map weather description to emoji.
 */
export function weatherEmoji(weather) {
  const w = String(weather || '')
  if (/雷/.test(w)) return '⛈️'
  if (/冰雹/.test(w)) return '🌨️'
  if (/雨夹雪|冻雨/.test(w)) return '🌨️'
  if (/暴雪|大雪|中雪|小雪|阵雪|雪/.test(w)) return '❄️'
  if (/暴雨|大雨|中雨|小雨|阵雨|雨/.test(w)) return '🌧️'
  if (/沙尘暴|浮尘|扬沙/.test(w)) return '🌪️'
  if (/霾/.test(w)) return '😷'
  if (/雾/.test(w)) return '🌫️'
  if (/多云/.test(w)) return '⛅'
  if (/阴/.test(w)) return '☁️'
  if (/晴/.test(w)) return '☀️'
  return '🌡️'
}

/**
 * Recursively find an image URL in the response object.
 */
export function findImageUrl(obj) {
  if (typeof obj === 'string' && /^https?:\/\/.+\.(png|jpe?g|webp|gif)/i.test(obj)) return obj
  if (typeof obj === 'string' && /^https?:\/\//.test(obj) && /(image|wanx|dashscope|oss)/i.test(obj)) return obj
  if (Array.isArray(obj)) {
    for (const x of obj) { const u = findImageUrl(x); if (u) return u }
  } else if (obj && typeof obj === 'object') {
    for (const k in obj) { const u = findImageUrl(obj[k]); if (u) return u }
  }
  return null
}

// Global listener to clear invalid class on input
if (typeof document !== 'undefined') {
  document.addEventListener('input', e => {
    const t = e.target
    if (t?.classList?.contains('invalid')) t.classList.remove('invalid')
  })
}
