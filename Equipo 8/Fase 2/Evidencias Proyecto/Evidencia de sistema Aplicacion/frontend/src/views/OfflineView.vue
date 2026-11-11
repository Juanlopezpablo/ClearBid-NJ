<template>
  <div class="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)]">
    <AppHeader v-if="auth.isAuthenticated" />
    <main class="max-w-5xl mx-auto p-4 md:p-8 space-y-5">
      <h1 class="text-2xl font-bold">Sin conexión y sincronización diferida</h1>
      <p>Las copias guardadas pueden estar desactualizadas. Solo se permite consultar tickets y guardar nuevos comentarios pendientes.</p>
      <p>Se conservan hasta 200 tickets durante 7 días en este navegador. Los comentarios pendientes no se borran automáticamente.</p>
      <div class="flex flex-wrap gap-4"><RouterLink to="/" class="underline">Volver al inicio</RouterLink><RouterLink to="/login?redirect=/offline" class="underline">Iniciar sesión para sincronizar</RouterLink><button @click="refresh" class="underline">Actualizar datos locales</button></div>
      <p v-if="!online" role="status">Estás sin conexión. Esta pantalla no inicia una sesión ni concede permisos en el servidor.</p>
      <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
      <p v-if="notice" role="status">{{ notice }}</p>
      <template v-if="profile">
        <p>Datos locales de <strong>{{ profile.name }}</strong>. Los pendientes solo se envían con una sesión válida de esa misma cuenta.</p>
        <button v-if="online" @click="retry" :disabled="syncingOffline" class="primary">{{ syncingOffline ? 'Sincronizando…' : 'Sincronizar pendientes' }}</button>
        <p v-if="offlineSyncMessage" role="status">{{ offlineSyncMessage }}</p>
        <section class="panel">
          <h2 class="text-lg font-semibold">Tickets guardados</h2>
          <p v-if="!tickets.length">No hay copias vigentes. Consulta tickets con conexión para guardarlos aquí.</p>
          <label v-else>Seleccionar ticket<select v-model="selectedId" :disabled="saving || !!body.trim()"><option v-for="ticket in tickets" :key="ticket.id" :value="ticket.id">{{ ticket.title }}</option></select></label>
          <template v-if="selected">
            <h3 class="font-semibold">{{ selected.title }}</h3>
            <p class="text-xs">Copia del {{ new Date(selected.savedAt).toLocaleString() }} · {{ selected.status }} · {{ selected.priority }}</p>
            <p class="whitespace-pre-wrap break-words">{{ selected.description || 'Sin descripción' }}</p>
            <form @submit.prevent="save" class="space-y-3">
              <label>Nuevo comentario pendiente<textarea v-model="body" maxlength="5000" rows="4" required :disabled="saving" placeholder="Se guardará en este navegador hasta poder sincronizar." /></label>
              <p class="text-xs">Las menciones se validarán al sincronizar. Editar comentarios publicados y subir archivos requieren conexión.</p>
              <button :disabled="saving || !body.trim()" class="primary">{{ saving ? 'Guardando…' : 'Guardar comentario pendiente' }}</button>
              <button v-if="body" type="button" @click="body = ''" :disabled="saving" class="ml-3 underline">Vaciar borrador</button>
            </form>
          </template>
        </section>
        <section class="panel">
          <h2 class="text-lg font-semibold">{{ pending.length }} comentarios pendientes</h2>
          <p v-if="!pending.length">No hay comentarios pendientes para esta cuenta.</p>
          <article v-for="item in pending" :key="item.id" class="py-3 border-b border-[var(--border-subtle)] space-y-2">
            <strong>{{ item.title }}</strong><p class="text-xs">{{ new Date(item.createdAt).toLocaleString() }} · {{ item.error ? 'Requiere revisión' : 'Pendiente de sincronizar' }}</p>
            <p class="whitespace-pre-wrap break-words">{{ item.body }}</p><p v-if="item.error" role="alert" class="text-red-600">{{ item.error }}</p>
            <button v-if="item.error" @click="retryItem(item)" :disabled="syncingOffline" class="underline mr-4">Reintentar este comentario</button>
            <button @click="discard(item)" :disabled="syncingOffline" class="underline">Descartar expresamente</button>
          </article>
        </section>
        <button @click="clearCopies" class="underline">Eliminar las copias de tickets de esta cuenta</button>
      </template>
      <p v-else>No hay una cuenta local disponible. Inicia sesión con conexión al menos una vez. Los pendientes de otras cuentas permanecen separados.</p>
    </main>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useDialogStore } from '@/stores/dialog'
import { lastProfile, savedTickets, pendingComments, enqueueComment, discardComment, pendingError, clearSnapshots, type LocalProfile, type SavedTicket, type PendingComment } from '@/services/offlineDb'
import { syncComments, syncingOffline, offlineSyncMessage } from '@/services/offlineSync'
const auth = useAuthStore()
const dialog = useDialogStore()
const online = ref(navigator.onLine)
const profile = ref<LocalProfile | null>(null)
const tickets = ref<SavedTicket[]>([])
const pending = ref<PendingComment[]>([])
const selectedId = ref('')
const body = ref('')
const error = ref('')
const notice = ref('')
const saving = ref(false)
const selected = computed(() => tickets.value.find(ticket => ticket.id === selectedId.value))
let generation = 0
let alive = true
async function refresh() {
  const current = ++generation
  try {
    const owner = auth.user ? { id: auth.user.id, name: auth.user.fullName, savedAt: Date.now() } : await lastProfile()
    const [copies, queue] = owner ? await Promise.all([savedTickets(owner.id), pendingComments(owner.id)]) : [[], []]
    if (!alive || current !== generation) return
    if (profile.value?.id !== owner?.id) { body.value = ''; selectedId.value = '' }
    profile.value = owner; tickets.value = copies; pending.value = queue
    if (!copies.some(ticket => ticket.id === selectedId.value)) selectedId.value = copies[0]?.id || ''
  } catch (cause) { if (alive) error.value = cause instanceof Error ? cause.message : 'No se pudieron leer los datos locales.' }
}
async function save() {
  if (saving.value || !selected.value || !profile.value || !body.value.trim()) return
  if (auth.user && auth.user.id !== profile.value.id) { error.value = 'La cuenta cambió. Actualiza los datos locales antes de guardar.'; return }
  saving.value = true; error.value = ''; notice.value = ''
  const ticket = selected.value
  try {
    await enqueueComment({ id: crypto.randomUUID(), owner: profile.value.id, ticketId: ticket.id, title: ticket.title,
      body: body.value.trim(), createdAt: Date.now(), error: '' })
    body.value = ''; notice.value = 'Comentario guardado en este navegador, pendiente de sincronización.'
    await refresh()
    if (navigator.onLine) await syncComments()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : 'No se pudo guardar. El texto sigue en el editor.' }
  finally { saving.value = false }
}
async function retry() { await syncComments(); await refresh() }
async function retryItem(item: PendingComment) {
  try { await pendingError(item, ''); if (navigator.onLine) await retry() }
  catch { error.value = 'No se pudo preparar el reintento.' }
}
async function discard(item: PendingComment) {
  if (!await dialog.confirm('¿Descartar este comentario pendiente de este navegador? Esto no elimina comentarios que ya hayan llegado al servidor.')) return
  try { await discardComment(item.owner, item.id); await refresh() }
  catch { error.value = 'No se pudo descartar el comentario.' }
}
async function clearCopies() {
  if (!profile.value || !await dialog.confirm('¿Eliminar las copias locales de tickets? Los comentarios pendientes se conservarán.')) return
  try { await clearSnapshots(profile.value.id); await refresh() }
  catch { error.value = 'No se pudieron eliminar las copias.' }
}
function connectionChanged() { online.value = navigator.onLine; void refresh() }
watch(() => auth.user?.id, refresh)
onMounted(() => { void refresh(); window.addEventListener('offline-data-changed', refresh); window.addEventListener('online', connectionChanged); window.addEventListener('offline', connectionChanged) })
onBeforeUnmount(() => { alive = false; generation++; window.removeEventListener('offline-data-changed', refresh); window.removeEventListener('online', connectionChanged); window.removeEventListener('offline', connectionChanged) })
</script>
<style scoped>
input, select, textarea { display: block; width: 100%; margin-top: .35rem; padding: .65rem; border: 1px solid var(--border-subtle); border-radius: .5rem; background: var(--bg-app); color: var(--text-primary); }
.panel { display: grid; gap: .8rem; padding: 1.25rem; border: 1px solid var(--border-subtle); border-radius: .75rem; background: var(--bg-panel); }
.primary { background: var(--teal); color: white; padding: .65rem 1rem; border-radius: .5rem; }
button:disabled { opacity: .5; }
</style>
