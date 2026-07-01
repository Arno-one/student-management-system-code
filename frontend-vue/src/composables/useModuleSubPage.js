import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getModuleDefaultSub, getModuleSubStorageKey, isValidModuleSub } from '../config/moduleNavigation'

// 统一处理“页面二级功能”与路由 query、localStorage 的同步。
export function useModuleSubPage(page, options = {}) {
  const route = useRoute()
  const router = useRouter()
  const defaultSub = getModuleDefaultSub(page)
  const storageKey = getModuleSubStorageKey(page)

  function normalizeSub(value) {
    const nextValue = String(value || '')
    return isValidModuleSub(page, nextValue) ? nextValue : ''
  }

  function getStoredSub() {
    return normalizeSub(localStorage.getItem(storageKey)) || defaultSub
  }

  const sub = ref(normalizeSub(route.query.sub) || getStoredSub())

  watch(
    () => route.query.sub,
    (routeSub) => {
      const nextSub = normalizeSub(routeSub)
      if (nextSub && sub.value !== nextSub) {
        sub.value = nextSub
      }
    }
  )

  watch(
    sub,
    (value) => {
      const nextSub = normalizeSub(value) || defaultSub
      if (!nextSub) return
      if (sub.value !== nextSub) {
        sub.value = nextSub
        return
      }

      localStorage.setItem(storageKey, nextSub)

      if (normalizeSub(route.query.sub) !== nextSub) {
        // 只更新 sub 参数，避免切页面时二级状态丢失。
        router.replace({ name: route.name, query: { ...route.query, sub: nextSub } })
      }

      options.onChange?.(nextSub)
    },
    { immediate: true }
  )

  return { sub }
}
