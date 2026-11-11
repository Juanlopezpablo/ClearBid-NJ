import { ref } from 'vue'
import { apiClient } from '@/services/api'
import { discardComment, getOfflineOwner, pendingComments, pendingError } from '@/services/offlineDb'

export const syncingOffline = ref(false)
export const offlineSyncMessage = ref('')
let running: Promise<void> | null = null

export function syncComments(): Promise<void> {
  if (running) return running
  running = run().finally(() => { running = null })
  return running
}
async function run() {
  const owner = getOfflineOwner()
  if (!owner || !navigator.onLine) return
  syncingOffline.value = true
  offlineSyncMessage.value = ''
  try {
    const pending = await pendingComments(owner)
    if (!pending.some(item => !item.error)) return
    // El servidor también garantiza idempotencia si dos pestañas envían a la vez.
    const { data: user } = await apiClient.get('/auth/me')
    if (getOfflineOwner() !== owner || user.id !== owner) return
    for (const item of pending) {
      if (getOfflineOwner() !== owner || !navigator.onLine) break
      if (item.error) continue
      try {
        await apiClient.post(`/tickets/${item.ticketId}/comments/offline`, { client_id: item.id, author_id: owner, body: item.body })
        await discardComment(owner, item.id)
      } catch (cause) {
        const status = (cause as { response?: { status?: number } }).response?.status
        if (!status || status >= 500 || status === 429) { offlineSyncMessage.value = 'No se pudo sincronizar. Tus comentarios siguen guardados; puedes reintentar.'; break }
        if (status === 401) { offlineSyncMessage.value = 'Inicia sesión con la misma cuenta para sincronizar los pendientes.'; break }
        const detail = (cause as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
        await pendingError(item, typeof detail === 'string' ? detail : 'No se pudo enviar. El ticket, las menciones o tus permisos cambiaron. Revisa o descarta el pendiente.')
      }
    }
  } catch {
    offlineSyncMessage.value = 'Se necesita conexión y una sesión válida de la misma cuenta para sincronizar.'
  } finally { syncingOffline.value = false }
}
