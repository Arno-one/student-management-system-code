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

const ENTER_SUBMIT_SCOPE_SELECTOR = [
  '.preview',
  '.mail-edit',
  '.smart-input',
  '.agent-hitl-card',
  '.float-agent-hitl',
  '.login-shell',
  '.card',
  '.subcard',
  '.page',
].join(', ')

const ENTER_SUBMIT_ACTION_SELECTOR = [
  '.actions',
  '.talk-input-row',
  '.nl-input-row',
  '.agent-hitl-actions',
  '.float-agent-hitl-actions',
  '.sys-perm-head-row',
  '.agent-monitor-filters',
  '.talk-login-box',
].join(', ')

const ENTER_SUBMIT_TEXTAREA_SKIP_SELECTOR = [
  '.rag-input-area',
  '.agent-input-area',
  '.float-agent-input',
  '.agent-feedback-comment',
  '.float-agent-feedback-comment',
  '.agent-hitl-textarea',
  '.rte',
  '.rte-area',
].join(', ')

let enterSubmitInitialized = false

function isEnterSubmitTarget(target) {
  if (!(target instanceof HTMLElement)) return false
  if (target.closest('[data-enter-submit-skip="true"]')) return false
  if (target.isContentEditable || target.closest('[contenteditable="true"]')) return false

  const tag = target.tagName
  if (tag === 'TEXTAREA') {
    return !target.closest(ENTER_SUBMIT_TEXTAREA_SKIP_SELECTOR)
  }
  if (tag !== 'INPUT') return false

  const type = String(target.getAttribute('type') || 'text').toLowerCase()
  return !['button', 'submit', 'reset', 'file', 'checkbox', 'radio', 'range', 'color'].includes(type)
}

function isUsableSubmitButton(button) {
  return button instanceof HTMLButtonElement && !button.disabled && button.getClientRects().length > 0
}

function isAfterTarget(target, button) {
  return !!(target.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING)
}

function findSubmitActionContainer(target, scope) {
  const current = target.closest(ENTER_SUBMIT_ACTION_SELECTOR)
  if (current && scope.contains(current)) return current

  const containers = Array.from(scope.querySelectorAll(ENTER_SUBMIT_ACTION_SELECTOR))
  return containers.find(container => isAfterTarget(target, container)) || containers[0] || null
}

function pickSubmitButton(container) {
  const buttons = Array.from(container.querySelectorAll('button')).filter(isUsableSubmitButton)
  return buttons.find(button => !button.classList.contains('secondary') && !button.classList.contains('danger')) || buttons[0] || null
}

export function initGlobalEnterSubmit() {
  if (enterSubmitInitialized || typeof document === 'undefined') return
  enterSubmitInitialized = true

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.defaultPrevented || event.isComposing) return
    if (event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) return

    const target = event.target
    if (!isEnterSubmitTarget(target)) return

    const scope = target.closest(ENTER_SUBMIT_SCOPE_SELECTOR) || document.body
    const actionContainer = findSubmitActionContainer(target, scope)
    if (!actionContainer) return

    const submitButton = pickSubmitButton(actionContainer)
    if (!submitButton) return

    event.preventDefault()
    submitButton.click()
  })
}

// Global listener to clear invalid class on input
if (typeof document !== 'undefined') {
  document.addEventListener('input', e => {
    const t = e.target
    if (t?.classList?.contains('invalid')) t.classList.remove('invalid')
  })
}
