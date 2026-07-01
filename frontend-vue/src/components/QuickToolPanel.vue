<template>
  <section class="agent-quick-panel" :class="{ compact }" data-quick-panel>
    <button
      type="button"
      class="quick-panel-toggle"
      :disabled="loading"
      @click="open = !open"
      :aria-expanded="open ? 'true' : 'false'"
      data-quick-panel-toggle
    >
      <span class="quick-panel-toggle-title">快捷工具面板</span>
      <span class="quick-panel-toggle-meta">{{ open ? '收起' : '展开' }}</span>
    </button>

    <div class="quick-panel-body" v-if="open">
      <article
        v-for="tool in agentQuickTools"
        :key="tool.id"
        class="quick-tool-card"
        :class="{ compact }"
        :data-tool-id="tool.id"
      >
        <div class="quick-tool-head">
          <span class="quick-tool-badge">{{ tool.emoji || tool.badge }}</span>
          <div class="quick-tool-title-block">
            <strong>{{ tool.label }}</strong>
            <small>{{ tool.hint }}</small>
          </div>
        </div>

        <div class="quick-tool-actions" v-if="tool.mode === 'fill_template'">
          <button
            type="button"
            class="quick-tool-btn"
            :disabled="loading"
            @click="emit('fill-template', buildQuickToolTemplate(tool.id))"
            :data-tool-fill="tool.id"
          >
            填入模板
          </button>
        </div>

        <div class="quick-tool-inline" v-else-if="tool.mode === 'inline_send'">
          <input
            v-model="drafts[tool.id]"
            :placeholder="tool.inputPlaceholder"
            :disabled="loading"
            @keydown.enter.prevent="submitInline(tool)"
            :data-tool-input="tool.id"
          />
          <button
            type="button"
            class="quick-tool-btn primary"
            :disabled="loading || !String(drafts[tool.id] || '').trim()"
            @click="submitInline(tool)"
            :data-tool-submit="tool.id"
          >
            {{ tool.submitLabel }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { agentQuickTools, buildQuickToolMessage, buildQuickToolTemplate } from '../config/agentQuickTools'

const props = defineProps({
  loading: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['fill-template', 'submit-inline'])

const open = ref(false)
const drafts = reactive({
  image_generation: '',
  nl2sql: '',
})

function submitInline(tool) {
  const text = buildQuickToolMessage(tool.id, drafts[tool.id])
  if (!text) return
  emit('submit-inline', { toolId: tool.id, text })
  drafts[tool.id] = ''
}
</script>

<style scoped>
.agent-quick-panel {
  border-bottom: 1px solid var(--line);
  background: var(--panel-solid);
}

.quick-panel-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  text-align: left;
}

.quick-panel-toggle:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.quick-panel-toggle-title {
  font-size: 13px;
  font-weight: 700;
}

.quick-panel-toggle-meta {
  color: var(--text-muted);
  font-size: 12px;
}

.quick-panel-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  padding: 0 14px 14px;
}

.agent-quick-panel.compact .quick-panel-body {
  max-height: 220px;
  overflow-y: auto;
  padding-right: 10px;
  scrollbar-gutter: stable;
}

.quick-tool-card {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: var(--panel);
  overflow: hidden;
}

.quick-tool-card.compact {
  padding: 10px;
}

.quick-tool-card.compact .quick-tool-head {
  gap: 8px;
}

.quick-tool-card.compact .quick-tool-badge {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  font-size: 14px;
}

.quick-tool-card.compact .quick-tool-title-block strong {
  font-size: 12px;
}

.quick-tool-card.compact .quick-tool-title-block small {
  font-size: 10px;
}

.quick-tool-head {
  display: flex;
  gap: 10px;
  min-width: 0;
}

.quick-tool-badge {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 7px;
  background: var(--gold-bg);
  color: var(--gold);
  font-size: 16px;
  font-weight: 800;
  flex: 0 0 auto;
}

.quick-tool-title-block {
  min-width: 0;
}

.quick-tool-title-block strong {
  display: block;
  color: var(--text);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.quick-tool-title-block small {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.45;
}

.quick-tool-actions,
.quick-tool-inline {
  display: flex;
  gap: 8px;
  align-items: center;
}

.quick-tool-inline input {
  flex: 1;
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--text);
  font-size: 12px;
  outline: none;
}

.quick-tool-inline input:focus {
  border-color: var(--gold);
}

.quick-tool-inline input::placeholder {
  color: var(--text-muted);
}

.quick-tool-btn {
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--text-soft);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.quick-tool-btn:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
}

.quick-tool-btn.primary {
  border-color: var(--gold);
  background: var(--gold-bg);
  color: var(--gold);
}

.quick-tool-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 680px) {
  .quick-panel-body {
    grid-template-columns: minmax(0, 1fr);
  }

  .quick-tool-inline {
    flex-wrap: wrap;
  }

  .quick-tool-inline input,
  .quick-tool-inline .quick-tool-btn {
    width: 100%;
  }
}
</style>
