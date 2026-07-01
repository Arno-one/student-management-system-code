<template>
  <div class="cs-wrap" ref="wrapRef">
    <button
      class="cs-trigger"
      :class="{ 'cs-trigger--open': open, 'cs-trigger--placeholder': !selectedLabel }"
      @click="toggle"
      @keydown.enter.prevent="toggle"
      @keydown.space.prevent="toggle"
      @keydown.arrow-down.prevent="open ? next() : (open = true)"
      @keydown.arrow-up.prevent="open ? prev() : (open = true)"
      @keydown.escape="open = false"
      type="button"
      :disabled="disabled"
    >
      <span class="cs-trigger-text">{{ selectedLabel || placeholder }}</span>
      <svg class="cs-chevron" :class="{ 'cs-chevron--up': open }" viewBox="0 0 14 14" width="14" height="14">
        <path d="M3.5 5.5L7 9L10.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <Teleport to="body">
      <Transition name="cs-drop">
        <div v-if="open" class="cs-drop" :class="dropThemeClass" :style="dropStyle" ref="dropRef">
          <div
            v-for="(opt, idx) in options"
            :key="opt.value"
            class="cs-option"
            :class="{
              'cs-option--selected': isSelected(opt),
              'cs-option--active': idx === activeIdx,
            }"
            @click="select(opt)"
            @mouseenter="activeIdx = idx"
          >
            <span class="cs-option-label">{{ opt.label }}</span>
            <svg v-if="isSelected(opt)" class="cs-check" viewBox="0 0 14 14" width="12" height="12">
              <path d="M2 7L5.5 10.5L12 3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick, inject } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择' },
  disabled: { type: Boolean, default: false },
  width: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const activeIdx = ref(-1)
const wrapRef = ref(null)
const dropRef = ref(null)

const dropStyle = ref({})

const dropThemeClass = ref(null)

// 每次打开下拉框时从 DOM 实时读取主题（localStorage 非响应式，computed 不会自动更新）

const selectedLabel = computed(() => {
  const found = props.options.find(o => String(o.value) === String(props.modelValue))
  return found ? found.label : ''
})

function isSelected(opt) {
  return String(opt.value) === String(props.modelValue)
}

function toggle() {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    const idx = props.options.findIndex(o => isSelected(o))
    activeIdx.value = idx >= 0 ? idx : 0
    nextTick(() => positionDrop())
  }
}

function positionDrop() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  dropStyle.value = {
    position: 'fixed',
    top: (rect.bottom + 6) + 'px',
    left: rect.left + 'px',
    minWidth: (props.width || rect.width) + 'px',
  }
  // 从 DOM 实时读取主题（localStorage 非响应式，computed 不更新）
  const layout = document.querySelector('.app-layout')
  dropThemeClass.value = layout?.classList.contains('theme-light') ? 'cs-theme--light' : null
}

function select(opt) {
  emit('update:modelValue', opt.value)
  open.value = false
}

function next() {
  if (activeIdx.value < props.options.length - 1) activeIdx.value++
}

function prev() {
  if (activeIdx.value > 0) activeIdx.value--
}

function onKey(e) {
  if (!open.value) return
  if (e.key === 'Escape') { open.value = false; return }
  if (e.key === 'ArrowDown') { e.preventDefault(); next(); return }
  if (e.key === 'ArrowUp') { e.preventDefault(); prev(); return }
  if (e.key === 'Enter') {
    e.preventDefault()
    const opt = props.options[activeIdx.value]
    if (opt) select(opt)
  }
}

function onClickOutside(e) {
  if (wrapRef.value && !wrapRef.value.contains(e.target)) {
    open.value = false
  }
}

watch(open, (v) => {
  if (v) {
    document.addEventListener('click', onClickOutside, true)
    document.addEventListener('keydown', onKey, true)
  } else {
    document.removeEventListener('click', onClickOutside, true)
    document.removeEventListener('keydown', onKey, true)
    activeIdx.value = -1
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside, true)
  document.removeEventListener('keydown', onKey, true)
})
</script>

<style scoped>
.cs-wrap { position: relative; display: inline-block; width: 100%; }

.cs-trigger {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  width: 100%; min-height: 48px;
  padding: 12px 14px 12px 16px;
  border: 1.5px solid var(--line-strong); border-radius: var(--radius-sm);
  background: var(--panel-2); color: var(--text); font-size: 14px; font-weight: 500;
  cursor: pointer; text-align: left; font-family: inherit;
  box-shadow: var(--shadow-xs);
  transition: border-color var(--dur-fast), box-shadow var(--dur-fast), background-color var(--dur-fast);
  user-select: none;
}

.cs-trigger:hover:not(:disabled) { border-color: var(--gold); }
.cs-trigger--open { border-color: var(--gold); box-shadow: 0 0 0 4px var(--gold-bg), var(--shadow-sm); }
.cs-trigger--placeholder { color: var(--text-muted); }
.cs-trigger:disabled { opacity: 0.45; cursor: not-allowed; }

.cs-trigger-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cs-chevron { flex-shrink: 0; color: var(--text-muted); transition: transform var(--dur-fast); }
.cs-chevron--up { transform: rotate(180deg); color: var(--gold); }

/* ── 下拉层 ── */
.cs-drop {
  z-index: 10000; background: var(--panel-solid);
  border: 1px solid var(--line-strong); border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg); overflow: hidden;
  max-height: 300px; overflow-y: auto;
  padding: 6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(209, 161, 90, 0.42) rgba(255,255,255,0.04);
}

/* ── 选项 ── */
.cs-option {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: 10px; cursor: pointer;
  font-size: 13px; font-weight: 500; color: var(--text-soft);
  transition: background var(--dur-fast);
}

.cs-option:hover,
.cs-option--active { background: var(--panel-3); }

.cs-option--selected {
  color: var(--gold); font-weight: 700;
  background: linear-gradient(90deg, var(--cs-sel-bg-start, rgba(209,161,90,0.14)), var(--cs-sel-bg-end, rgba(209,161,90,0.04)));
}

.cs-check { flex-shrink: 0; color: var(--gold); }

.cs-theme--light.cs-drop {
  background:
    linear-gradient(180deg, rgba(255,255,255,0.98), rgba(240,248,255,0.96));
  border-color: rgba(61, 149, 232, 0.18);
  box-shadow: 0 20px 45px rgba(65, 122, 176, 0.16);
  scrollbar-color: rgba(61, 149, 232, 0.4) rgba(61, 149, 232, 0.08);
}

.cs-theme--light .cs-option {
  color: #35516c;
}

.cs-theme--light .cs-option:hover,
.cs-theme--light .cs-option--active {
  background: linear-gradient(135deg, rgba(61, 149, 232, 0.1), rgba(61, 149, 232, 0.04));
  color: #163a5c;
}

.cs-theme--light .cs-option--selected {
  color: #1677d2;
  background: linear-gradient(90deg, rgba(22,119,210,0.14), rgba(22,119,210,0.05));
}

.cs-theme--light .cs-check {
  color: #1677d2;
}

.cs-drop::-webkit-scrollbar {
  width: 10px;
}

.cs-drop::-webkit-scrollbar-track {
  background: rgba(255,255,255,0.04);
  border-radius: 999px;
}

.cs-drop::-webkit-scrollbar-thumb {
  border: 2px solid transparent;
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(229, 192, 131, 0.72), rgba(125, 157, 255, 0.44)) padding-box;
  background-clip: padding-box;
}

.cs-drop::-webkit-scrollbar-thumb:hover {
  background:
    linear-gradient(180deg, rgba(229, 192, 131, 0.9), rgba(125, 157, 255, 0.6)) padding-box;
  background-clip: padding-box;
}

.cs-theme--light.cs-drop::-webkit-scrollbar-track {
  background: rgba(61, 149, 232, 0.08);
}

.cs-theme--light.cs-drop::-webkit-scrollbar-thumb {
  background:
    linear-gradient(180deg, rgba(61, 149, 232, 0.72), rgba(22, 119, 210, 0.42)) padding-box;
  background-clip: padding-box;
}

.cs-theme--light.cs-drop::-webkit-scrollbar-thumb:hover {
  background:
    linear-gradient(180deg, rgba(61, 149, 232, 0.88), rgba(22, 119, 210, 0.58)) padding-box;
  background-clip: padding-box;
}

/* ── Teleport 过渡动画 ── */
.cs-drop-enter-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.cs-drop-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.cs-drop-enter-from { opacity: 0; transform: translateY(-6px); }
.cs-drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
