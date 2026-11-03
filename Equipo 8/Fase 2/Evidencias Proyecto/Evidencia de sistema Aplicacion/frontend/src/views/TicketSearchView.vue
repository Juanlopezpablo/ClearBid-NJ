<template>
  <div class="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)]">
    <AppHeader />
    <main class="max-w-6xl mx-auto p-4 md:p-8 space-y-5">
      <RouterLink :to="auth.userRole === 'ADMIN' ? '/admin/builder' : '/dev/workbench'" class="text-[var(--teal)]">← Volver al tablero</RouterLink>
      <h1 class="text-2xl font-bold">Búsqueda avanzada de tickets</h1>
      <p class="text-sm">Combina filtros para encontrar tickets de desarrollo y soporte. Se buscarán todas las etiquetas indicadas. Las fechas se interpretan en UTC.</p>
      <form @submit.prevent="submit" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 bg-[var(--bg-panel)] p-5 rounded-xl border border-[var(--border-subtle)]">
        <label>Texto o identificador<input v-model="filters.q" maxlength="200" placeholder="Título, descripción o UUID" /></label>
        <label>Etiquetas<input v-model="filters.labels" maxlength="410" placeholder="interfaz, urgente" /></label>
        <label>Estado<select v-model="filters.status_filter"><option value="">Todos</option><option v-for="(name, key) in states" :key="key" :value="key">{{ name }}</option></select></label>
        <label>Prioridad<select v-model="filters.priority"><option value="">Todas</option><option v-for="(name, key) in priorities" :key="key" :value="key">{{ name }}</option></select></label>
        <label>Tipo<select v-model="filters.ticket_type"><option value="">Todos</option><option value="DEVELOPMENT">Desarrollo</option><option value="SUPPORT">Soporte</option></select></label>
        <label>Aplicación<select v-model="filters.application_id"><option value="">Todas</option><option v-for="app in applications" :key="app.id" :value="app.id">{{ app.name }}</option></select></label>
        <label>Asignación<select v-model="filters.assignment"><option value="">Cualquier responsable</option><option value="mine">Mis tickets</option><option value="unassigned">Sin asignar</option><option v-if="chosenUser" :value="chosenUser.id">{{ chosenUser.full_name }}</option></select></label>
        <div>
          <label>Buscar otro responsable<input v-model="userQuery" maxlength="100" @input="findUsers" placeholder="Nombre de usuario activo" /></label>
          <p v-if="userError" role="alert">{{ userError }}</p>
          <ul v-if="userResults.length" class="max-h-36 overflow-y-auto border border-[var(--border-subtle)]">
            <li v-for="user in userResults" :key="user.id"><button type="button" @click="chooseUser(user)" class="w-full text-left p-2 hover:bg-[var(--bg-app)]">{{ user.full_name }}</button></li>
          </ul>
        </div>
        <label>Creado desde<input v-model="filters.created_from" type="date" /></label>
        <label>Creado hasta<input v-model="filters.created_to" type="date" /></label>
        <div class="flex items-end gap-3">
          <button type="submit" :disabled="loading" class="px-4 py-2 rounded bg-[var(--teal)] text-white disabled:opacity-50">Buscar</button>
          <button type="button" @click="clear" class="px-4 py-2 rounded border border-[var(--border-subtle)]">Limpiar filtros</button>
        </div>
      </form>
      <p v-if="optionsError" role="alert">{{ optionsError }}</p>
      <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
      <p v-if="loading" role="status">Buscando tickets…</p>
      <template v-else-if="!error">
        <p role="status">{{ total }} {{ total === 1 ? 'resultado' : 'resultados' }}</p>
        <p v-if="!items.length">No hay tickets que coincidan con los filtros.</p>
        <div class="space-y-3">
          <button v-for="ticket in items" :key="ticket.id" @click="selected = ticket" class="w-full text-left p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-panel)] hover:border-[var(--teal)]">
            <strong>{{ ticket.title }}</strong>
            <p class="text-sm mt-1">{{ ticket.app_name || 'Sin aplicación' }} · {{ states[ticket.status] || ticket.status }} · {{ priorities[ticket.priority] || ticket.priority }} · {{ ticket.assignee?.full_name || 'Sin asignar' }}</p>
            <div class="flex flex-wrap gap-2 mt-2"><span v-for="label in ticket.labels" :key="label" class="rounded-full px-2 py-1 text-xs bg-[var(--bg-app)]">{{ label }}</span></div>
          </button>
        </div>
        <nav aria-label="Paginación de resultados" class="flex items-center gap-4">
          <button :disabled="skip === 0" @click="search(skip - pageSize)" class="disabled:opacity-40">Anterior</button>
          <span>Página {{ Math.floor(skip / pageSize) + 1 }}</span>
          <button :disabled="skip + pageSize >= total" @click="search(skip + pageSize)" class="disabled:opacity-40">Siguiente</button>
        </nav>
      </template>
    </main>
    <div v-if="selected" class="fixed inset-0 bg-black/40 z-[110] flex justify-end" @click.self="selected = null" @keydown.esc="selected = null">
      <section role="dialog" aria-modal="true" aria-label="Detalle del ticket encontrado" class="w-full max-w-xl overflow-y-auto bg-[var(--bg-panel)] shadow-xl">
        <div class="p-5 sticky top-0 bg-[var(--bg-panel)] border-b border-[var(--border-subtle)] flex justify-between gap-4">
          <h2 class="font-bold text-xl">{{ selected.title }}</h2><button @click="selected = null" aria-label="Cerrar detalle" autofocus>✕</button>
        </div>
        <div class="p-5 space-y-2"><p>{{ selected.app_name }} · {{ selected.epic_title }}</p><p class="whitespace-pre-wrap">{{ selected.description || 'Sin descripción' }}</p><p class="text-xs break-all">{{ selected.id }}</p></div>
        <TicketLabels :key="selected.id" :ticket-id="selected.id" @updated="search(skip)" />
        <TicketComments :key="selected.id" :ticket-id="selected.id" />
        <EvidenceFiles :key="selected.id" :ticket-id="selected.id" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import TicketLabels from '@/components/shared/TicketLabels.vue'
import TicketComments from '@/components/shared/TicketComments.vue'
import EvidenceFiles from '@/components/shared/EvidenceFiles.vue'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

interface SearchTicket {
  id: string; title: string; description: string | null; labels: string[]; status: string; priority: string;
  app_name: string | null; epic_title: string | null; assignee: { full_name: string } | null
}
interface Person { id: string; full_name: string }
const auth = useAuthStore()
const defaults = () => ({ q: '', labels: '', status_filter: '', priority: '', ticket_type: '', application_id: '', assignment: '', created_from: '', created_to: '' })
const filters = reactive(defaults())
const items = ref<SearchTicket[]>([])
const selected = ref<SearchTicket | null>(null)
const applications = ref<{ id: string; name: string }[]>([])
const chosenUser = ref<Person | null>(null)
const userQuery = ref('')
const userResults = ref<Person[]>([])
const userError = ref('')
const optionsError = ref('')
const error = ref('')
const loading = ref(false)
const total = ref(0)
const skip = ref(0)
const pageSize = 25
let generation = 0
let userGeneration = 0
let userTimer: ReturnType<typeof setTimeout>
let applied: Record<string, string | string[]> = {}
const states: Record<string, string> = { TODO: 'Por hacer', IN_PROGRESS: 'En progreso', BLOCKED: 'Bloqueado', BLOCKED_QUESTION: 'Pregunta pendiente', REDIRECTED: 'Redirigido', COMPLETED: 'Completado', REPORTED: 'Reportado', INVESTIGATING: 'En investigación', RESOLVED: 'Resuelto' }
const priorities: Record<string, string> = { LOW: 'Baja', MEDIUM: 'Media', HIGH: 'Alta', URGENT: 'Urgente' }
function submit() {
  if (filters.created_from && filters.created_to && filters.created_from > filters.created_to) {
    error.value = 'La fecha inicial debe ser anterior o igual a la final.'
    return
  }
  const labels = filters.labels.split(',').map(value => value.trim()).filter(Boolean)
  if (labels.length > 10 || labels.some(value => value.length > 40)) {
    error.value = 'Usa hasta 10 etiquetas de 40 caracteres cada una.'
    return
  }
  applied = {}
  for (const key of ['q', 'status_filter', 'priority', 'ticket_type', 'application_id'] as const) {
    if (filters[key]) applied[key] = filters[key]
  }
  if (labels.length) applied.labels = labels
  if (filters.assignment === 'unassigned') applied.unassigned = 'true'
  else if (filters.assignment) applied.assignee_id = filters.assignment === 'mine' ? auth.user!.id : filters.assignment
  if (filters.created_from) applied.created_from = `${filters.created_from}T00:00:00.000Z`
  if (filters.created_to) applied.created_to = `${filters.created_to}T23:59:59.999999Z`
  void search(0)
}
async function search(offset: number) {
  const current = ++generation
  loading.value = true
  error.value = ''
  items.value = []
  const params = new URLSearchParams({ skip: String(offset), limit: String(pageSize) })
  for (const [key, value] of Object.entries(applied)) {
    for (const item of Array.isArray(value) ? value : [value]) params.append(key, item)
  }
  try {
    const { data } = await apiClient.get<{ items: SearchTicket[]; total: number }>('/tickets/search', { params })
    if (current !== generation) return
    items.value = data.items
    total.value = data.total
    skip.value = offset
  } catch {
    if (current === generation) error.value = 'No se pudo realizar la búsqueda. Revisa la conexión y vuelve a pulsar Buscar.'
  } finally {
    if (current === generation) loading.value = false
  }
}
function clear() {
  Object.assign(filters, defaults())
  chosenUser.value = null
  userQuery.value = ''
  userError.value = ''
  userResults.value = []
  userGeneration++
  clearTimeout(userTimer)
  submit()
}
function chooseUser(user: Person) {
  chosenUser.value = user
  filters.assignment = user.id
  userQuery.value = user.full_name
  userResults.value = []
  userGeneration++
  clearTimeout(userTimer)
}
function findUsers() {
  const current = ++userGeneration
  clearTimeout(userTimer)
  userResults.value = []
  userError.value = ''
  if (!userQuery.value.trim()) return
  userTimer = setTimeout(async () => {
    try {
      const { data } = await apiClient.get<Person[]>('/tickets/comment-mentions', { params: { q: userQuery.value } })
      if (current === userGeneration) {
        userResults.value = data
        if (!data.length) userError.value = 'No hay usuarios activos con ese nombre.'
      }
    } catch {
      if (current === userGeneration) userError.value = 'No se pudieron buscar responsables.'
    }
  }, 250)
}
onMounted(async () => {
  submit()
  try {
    const all: { id: string; name: string }[] = []
    for (let offset = 0; ; offset += 500) {
      const { data } = await apiClient.get<{ id: string; name: string }[]>('/applications/', { params: { skip: offset, limit: 500 } })
      all.push(...data)
      if (data.length < 500) break
    }
    applications.value = all
  } catch { optionsError.value = 'No se pudieron cargar las aplicaciones. Puedes buscar con los demás filtros.' }
})
onBeforeUnmount(() => { generation++; userGeneration++; clearTimeout(userTimer) })
</script>

<style scoped>
label { display: block; font-size: .875rem; }
input, select { display: block; width: 100%; margin-top: .35rem; padding: .6rem; border: 1px solid var(--border-subtle); border-radius: .5rem; background: var(--bg-app); color: var(--text-primary); }
</style>
