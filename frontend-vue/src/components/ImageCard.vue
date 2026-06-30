<template>
  <section class="agent-image-card" v-if="imageUrl">
    <header class="image-head">
      <div class="image-title-block">
        <div class="image-kicker">文生图</div>
        <h4>{{ titleText }}</h4>
      </div>
      <span class="image-provider">{{ providerLabel }}</span>
    </header>

    <div class="image-preview">
      <img :src="imageUrl" :alt="promptText || 'AI 生成图片'" loading="lazy" />
    </div>

    <div class="image-meta">
      <span v-if="imageData.model">{{ imageData.model }}</span>
      <span>{{ compact ? '聊天内预览' : '已生成图片' }}</span>
    </div>

    <div class="image-prompt" v-if="promptText">
      <label>提示词</label>
      <p>{{ promptText }}</p>
    </div>

    <div class="image-actions">
      <button type="button" class="primary" @click="emit('regenerate', promptText)" :disabled="!promptText">
        重新生成
      </button>
      <button type="button" @click="copyPrompt" :disabled="!promptText">
        {{ copiedKey === 'prompt' ? '已复制提示词' : '复制提示词' }}
      </button>
      <button type="button" @click="copyImageUrl">
        {{ copiedKey === 'url' ? '已复制链接' : '复制图片链接' }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  card: { type: Object, default: null },
  data: { type: Object, default: null },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['regenerate'])

const copiedKey = ref('')
const imageData = computed(() => props.data || props.card?.data || {})
const imageUrl = computed(() => String(imageData.value.image_url || '').trim())
const promptText = computed(() => String(imageData.value.prompt || '').trim())

const providerLabel = computed(() => {
  if (imageData.value.provider === 'qwen_image') return '通义万相'
  return 'AI 图片'
})

const titleText = computed(() => {
  if (!promptText.value) return '已生成 1 张图片'
  return promptText.value.length > 18 ? `${promptText.value.slice(0, 18)}...` : promptText.value
})

async function copyText(type, text) {
  if (!text) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    copiedKey.value = type
    window.setTimeout(() => {
      if (copiedKey.value === type) copiedKey.value = ''
    }, 1400)
  } catch (_) {
    copiedKey.value = ''
  }
}

function copyPrompt() {
  copyText('prompt', promptText.value)
}

function copyImageUrl() {
  copyText('url', imageUrl.value)
}
</script>

<style scoped>
.agent-image-card {
  width: 100%;
  margin: 12px 0 4px;
  padding: 14px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: linear-gradient(135deg, var(--panel-solid), var(--panel-2));
  color: var(--text);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.image-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.image-title-block {
  min-width: 0;
}

.image-kicker {
  color: var(--blue-2);
  font-size: 11px;
}

.image-head h4 {
  margin: 2px 0 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.image-provider {
  flex: 0 0 auto;
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--gold-bg);
  color: var(--gold);
  font-size: 11px;
}

.image-preview {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--panel);
  aspect-ratio: 1 / 1;
}

.image-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.image-meta span {
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--panel);
  color: var(--text-muted);
  font-size: 11px;
}

.image-prompt {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel);
}

.image-prompt label {
  display: block;
  margin-bottom: 4px;
  color: var(--text-dim);
  font-size: 11px;
}

.image-prompt p {
  margin: 0;
  color: var(--text);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.image-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.image-actions button {
  padding: 6px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--text-soft);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.image-actions button:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
}

.image-actions button.primary {
  border-color: var(--gold);
  background: var(--gold-bg);
  color: var(--gold);
}

.image-actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 680px) {
  .image-actions {
    gap: 6px;
  }

  .image-actions button {
    flex: 1 1 calc(50% - 6px);
    min-width: 0;
  }
}
</style>
