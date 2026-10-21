<!--
  Aviso de inactividad del WebSocket (migración a GCP, plan D13).

  Dos estados, ambos controlados por composables/useWebSocket.ts:
  - idlePromptVisible: "¿Sigues ahí?" con cuenta regresiva. "Sigo aquí" lo cierra.
  - idlePaused: la conexión en tiempo real se cerró por inactividad.
    "Reconectar" abre una nueva y recarga lo que cambió.
  La sesión (login) no se toca en ningún caso.
-->
<template>
  <Teleport to="body">
    <Transition name="idle-fade">
      <div
        v-if="idlePromptVisible || idlePaused"
        class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      >
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="idle-prompt-title"
          aria-describedby="idle-prompt-message"
          class="bg-white dark:bg-gray-900 border border-slate-200 dark:border-gray-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
        >
          <div class="p-6 pb-4 flex items-center gap-4">
            <div
              class="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 bg-amber-100 dark:bg-amber-900/30"
            >
              <span class="text-2xl" aria-hidden="true">{{ idlePaused ? '⏸️' : '👋' }}</span>
            </div>
            <h2 id="idle-prompt-title" class="text-xl font-bold text-slate-900 dark:text-white">
              {{ idlePaused ? t('realtime.pausedTitle') : t('realtime.idleTitle') }}
            </h2>
          </div>

          <div class="px-6 py-2">
            <p
              id="idle-prompt-message"
              class="text-slate-600 dark:text-gray-300 text-[15px] leading-relaxed"
            >
              {{ idlePaused ? t('realtime.pausedMessage') : t('realtime.idleMessage', { time: countdown }) }}
            </p>
          </div>

          <div
            class="px-6 py-5 mt-4 flex justify-end bg-slate-50 dark:bg-gray-950/50 border-t border-slate-100 dark:border-gray-800/50"
          >
            <button
              ref="actionButton"
              type="button"
              class="px-5 py-2.5 rounded-xl font-bold text-white shadow-lg transition-colors min-w-[120px] bg-[var(--teal)] opacity-90 hover:opacity-100 disabled:opacity-50"
              :disabled="busy"
              @click="onAction"
            >
              {{ idlePaused ? t('realtime.reconnect') : t('realtime.idleConfirm') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWebSocket } from '@/composables/useWebSocket'

const { t } = useI18n()
const { idlePromptVisible, idlePaused, idleDeadline, confirmPresence, resumeFromIdle } =
  useWebSocket()

const now = ref(Date.now())
const busy = ref(false)
const actionButton = ref<HTMLButtonElement | null>(null)
let tickId: ReturnType<typeof setInterval> | null = null

const countdown = computed(() => {
  const ms = Math.max(0, (idleDeadline.value ?? now.value) - now.value)
  const total = Math.ceil(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
})

function stopTick(): void {
  if (tickId) {
    clearInterval(tickId)
    tickId = null
  }
}

watch(
  [idlePromptVisible, idlePaused],
  async ([prompt, paused]) => {
    stopTick()
    if (prompt) {
      now.value = Date.now()
      tickId = setInterval(() => (now.value = Date.now()), 1000)
    }
    if (prompt || paused) {
      await nextTick()
      actionButton.value?.focus()
    }
  },
  { immediate: true }
)

async function onAction(): Promise<void> {
  if (idlePaused.value) {
    busy.value = true
    try {
      await resumeFromIdle()
    } finally {
      busy.value = false
    }
  } else {
    confirmPresence()
  }
}

onUnmounted(stopTick)
</script>

<style scoped>
.idle-fade-enter-active,
.idle-fade-leave-active {
  transition: opacity 0.2s ease;
}

.idle-fade-enter-from,
.idle-fade-leave-to {
  opacity: 0;
}
</style>
