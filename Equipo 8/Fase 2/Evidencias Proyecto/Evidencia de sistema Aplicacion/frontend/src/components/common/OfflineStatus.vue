<template>
  <aside v-if="!online || count || offlineSyncMessage || storageError || shellError" class="p-3 bg-amber-100 text-gray-900 text-sm border-b border-amber-300" aria-label="Estado de conexión">
    <span role="status">{{ online ? 'Con conexión' : 'Sin conexión' }} · {{ count }} comentarios pendientes. </span>
    <RouterLink to="/offline" class="underline font-semibold">Ver datos guardados y pendientes</RouterLink>
    <button v-if="online && count" @click="syncComments" :disabled="syncingOffline" class="ml-3 underline">{{ syncingOffline ? 'Sincronizando…' : 'Reintentar sincronización' }}</button>
    <p v-if="offlineSyncMessage">{{ offlineSyncMessage }}</p>
    <p v-if="storageError" role="alert">No se pudieron guardar datos para uso sin conexión. Revisa el espacio y los permisos del navegador.</p>
    <p v-if="shellError" role="alert">No se pudo preparar la apertura sin conexión. Vuelve a visitar CoreStream con conexión.</p>
  </aside>
</template>
<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { lastProfile, pendingComments } from '@/services/offlineDb'
import { syncComments, syncingOffline, offlineSyncMessage } from '@/services/offlineSync'
const auth = useAuthStore()
const online = ref(navigator.onLine)
const count = ref(0)
const storageError = ref(false)
const shellError = ref(false)
let alive = true
let generation = 0
let timer: ReturnType<typeof setInterval>
async function refresh() {
  const current = ++generation
  try {
    const owner = auth.user?.id || (await lastProfile())?.id
    const items = owner ? await pendingComments(owner) : []
    if (alive && current === generation) count.value = items.length
  } catch { if (alive) storageError.value = true }
}
async function connected() {
  online.value = navigator.onLine
  if (online.value) {
    if (!auth.isAuthenticated) await auth.initialize().catch(() => undefined)
    await syncComments()
  }
  await refresh()
}
const disconnected = () => { online.value = false }
const failed = () => { storageError.value = true }
const shellFailed = () => { shellError.value = true }
watch(() => auth.user?.id, () => { void refresh(); void syncComments() })
onMounted(() => {
  window.addEventListener('online', connected)
  window.addEventListener('offline', disconnected)
  window.addEventListener('offline-data-changed', refresh)
  window.addEventListener('offline-storage-error', failed)
  window.addEventListener('offline-shell-error', shellFailed)
  timer = setInterval(() => { if (document.visibilityState === 'visible') void syncComments() }, 30000)
  void refresh(); void syncComments()
})
onBeforeUnmount(() => {
  alive = false; generation++; clearInterval(timer)
  window.removeEventListener('online', connected); window.removeEventListener('offline', disconnected)
  window.removeEventListener('offline-data-changed', refresh); window.removeEventListener('offline-storage-error', failed)
  window.removeEventListener('offline-shell-error', shellFailed)
})
</script>
