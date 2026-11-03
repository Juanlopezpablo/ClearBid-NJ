<template>
  <div class="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)]">
    <AppHeader />
    <main class="max-w-7xl mx-auto p-4 md:p-8 space-y-5">
      <RouterLink :to="auth.userRole === 'ADMIN' ? '/admin/builder' : '/dev/workbench'" class="text-[var(--teal)]">← Volver al tablero</RouterLink>
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div><h1 class="text-2xl font-bold">Sprints e iteraciones</h1><p class="text-sm mt-2">Planifica tickets de desarrollo de distintas épicas de una misma aplicación.</p></div>
        <div class="flex gap-3">
          <button @click="retry" :disabled="busy || loading || initializing" class="secondary">Actualizar</button>
          <button v-if="manager" :disabled="!applicationId || busy || loading" @click="openPlan()" class="primary">Nuevo sprint</button>
        </div>
      </div>
      <label class="block max-w-md">Aplicación
        <select v-model="applicationId" :disabled="busy || initializing"><option value="">Selecciona una aplicación</option><option v-for="app in applications" :key="app.id" :value="app.id">{{ app.name }}</option></select>
      </label>
      <p v-if="initializing || loading" role="status">Cargando planificación…</p>
      <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
      <p v-if="notice" role="status" class="text-[var(--teal)]">{{ notice }}</p>
      <button v-if="error" @click="retry" :disabled="busy" class="secondary">Reintentar</button>

      <form v-if="showPlan && manager" @submit.prevent="savePlan" class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-panel)] p-5 space-y-4">
        <h2 class="text-lg font-bold">{{ editingId ? 'Editar sprint planificado' : 'Crear sprint' }}</h2>
        <div class="grid gap-4 sm:grid-cols-2">
          <label>Nombre<input v-model="plan.name" required maxlength="120" :disabled="busy" /></label>
          <label>Objetivo<textarea v-model="plan.goal" required maxlength="2000" :disabled="busy" /></label>
          <label>Fecha de inicio<input v-model="plan.start_date" type="date" required :disabled="busy" /></label>
          <label>Fecha de término<input v-model="plan.end_date" type="date" required :min="plan.start_date" :disabled="busy" /></label>
        </div>
        <div class="flex gap-3"><button class="primary" :disabled="busy">Guardar sprint</button><button type="button" class="secondary" @click="showPlan = false" :disabled="busy">Cancelar</button></div>
      </form>

      <div v-if="applicationId" class="grid gap-5 lg:grid-cols-[18rem_1fr]">
        <aside class="space-y-3" aria-label="Lista de sprints">
          <h2 class="font-semibold">{{ sprintTotal }} {{ sprintTotal === 1 ? 'sprint' : 'sprints' }}</h2>
          <p v-if="!loading && !sprints.length">Aún no hay sprints en esta aplicación.</p>
          <button v-for="sprint in sprints" :key="sprint.id" :disabled="busy" @click="selectSprint(sprint.id)" class="w-full text-left p-4 rounded-xl border bg-[var(--bg-panel)]" :class="selected?.id === sprint.id ? 'border-[var(--teal)]' : 'border-[var(--border-subtle)]'">
            <strong>{{ sprint.name }}</strong><span class="block text-sm mt-1">{{ statuses[sprint.status] }} · {{ sprint.progress }}%</span>
            <span class="block text-xs mt-1">{{ sprint.start_date }} → {{ sprint.end_date }}</span>
          </button>
          <nav aria-label="Páginas de sprints" class="flex gap-3"><button :disabled="busy || loading || sprintSkip === 0" @click="loadList(sprintSkip - 25)">Anterior</button><button :disabled="busy || loading || sprintSkip + 25 >= sprintTotal" @click="loadList(sprintSkip + 25)">Siguiente</button></nav>
        </aside>

        <section v-if="selected" class="space-y-5 min-w-0">
          <div class="bg-[var(--bg-panel)] border border-[var(--border-subtle)] rounded-xl p-5 space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-3"><h2 class="text-xl font-bold">{{ selected.name }}</h2><span>{{ statuses[selected.status] }}</span></div>
            <p class="whitespace-pre-wrap break-words">{{ selected.goal }}</p>
            <p>{{ selected.start_date }} → {{ selected.end_date }}</p>
            <p>{{ selected.completed_tickets }} de {{ selected.total_tickets }} tickets completados · {{ selected.progress }}%</p>
            <progress :value="selected.progress" max="100" class="w-full" aria-label="Avance del sprint" />
            <p v-if="selected.status === 'FINISHED'" class="text-sm">Resumen al cierre: {{ selected.released_tickets }} tickets pendientes volvieron al backlog, conservando su responsable y estado.</p>
            <div v-if="manager" class="flex flex-wrap gap-3">
              <button v-if="selected.status === 'PLANNED'" @click="openPlan(selected)" :disabled="busy" class="secondary">Editar plan</button>
              <button v-if="selected.status === 'PLANNED'" @click="changeStatus('start')" :disabled="busy || selected.total_tickets === 0 || otherActive" class="primary">Iniciar sprint</button>
              <button v-if="selected.status === 'ACTIVE'" @click="changeStatus('finish')" :disabled="busy" class="primary">Finalizar sprint</button>
            </div>
            <p v-if="selected.status === 'PLANNED' && otherActive" class="text-sm">Finaliza el sprint activo de la aplicación antes de iniciar otro.</p>
            <p v-if="selected.status === 'PLANNED' && !selected.total_tickets" class="text-sm">Agrega al menos un ticket antes de iniciar.</p>
          </div>

          <section class="panel">
            <h3 class="font-semibold">{{ selected.status === 'FINISHED' ? 'Tickets completados conservados en el sprint' : 'Tickets del sprint' }}</h3>
            <p v-if="tasksLoading" role="status">Cargando tickets…</p>
            <p v-else-if="!assigned.items.length">No hay tickets en esta página.</p>
            <ul class="divide-y divide-[var(--border-subtle)]">
              <li v-for="ticket in assigned.items" :key="ticket.id" class="py-3 flex flex-wrap items-center justify-between gap-3">
                <div class="min-w-0"><button class="text-left font-medium hover:underline break-words" @click="openTicket(ticket.id)">{{ ticket.title }}</button><p class="text-xs">{{ ticket.epic_title }} · {{ ticketStates[ticket.status] || ticket.status }} · {{ ticket.assignee?.full_name || 'Sin asignar' }}</p></div>
                <button v-if="manager && selected.status !== 'FINISHED'" @click="moveTicket(ticket.id, false)" :disabled="busy" class="secondary">Retirar</button>
              </li>
            </ul>
            <nav aria-label="Páginas de tickets del sprint" class="flex gap-3"><button :disabled="busy || tasksLoading || assigned.skip === 0" @click="loadTasks(assigned.skip - 25, available.skip)">Anterior</button><span>{{ assigned.total }} tickets</span><button :disabled="busy || tasksLoading || assigned.skip + 25 >= assigned.total" @click="loadTasks(assigned.skip + 25, available.skip)">Siguiente</button></nav>
          </section>

          <section v-if="manager && selected.status !== 'FINISHED'" class="panel">
            <h3 class="font-semibold">Backlog disponible para este sprint</h3>
            <p class="text-sm">Tickets de desarrollo pendientes sin sprint, tengan o no responsable.</p>
            <form @submit.prevent="applyBacklogSearch" class="flex flex-wrap gap-3 items-end"><label class="flex-1">Buscar por título<input v-model="backlogQuery" maxlength="200" /></label><button :disabled="busy || tasksLoading" class="secondary">Buscar en backlog</button></form>
            <p v-if="!tasksLoading && !available.items.length">No hay tickets disponibles que coincidan.</p>
            <ul class="divide-y divide-[var(--border-subtle)]"><li v-for="ticket in available.items" :key="ticket.id" class="py-3 flex items-center justify-between gap-3"><div class="min-w-0"><button @click="openTicket(ticket.id)" class="font-medium text-left break-words hover:underline">{{ ticket.title }}</button><p class="text-xs">{{ ticket.epic_title }} · {{ ticketStates[ticket.status] || ticket.status }} · {{ ticket.assignee?.full_name || 'Sin asignar' }}</p></div><button @click="moveTicket(ticket.id, true)" :disabled="busy" class="secondary shrink-0">Agregar</button></li></ul>
            <nav aria-label="Páginas del backlog" class="flex gap-3"><button :disabled="busy || tasksLoading || available.skip === 0" @click="loadTasks(assigned.skip, available.skip - 25)">Anterior</button><span>{{ available.total }} disponibles</span><button :disabled="busy || tasksLoading || available.skip + 25 >= available.total" @click="loadTasks(assigned.skip, available.skip + 25)">Siguiente</button></nav>
          </section>
        </section>
      </div>
    </main>
    <TicketPanel v-if="selectedTicket" :key="selectedTicket.id" :ticket="selectedTicket" :is-open="true" @close="closeTicket" @updated="ticketUpdated" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import TicketPanel from '@/components/dev/TicketPanel.vue'
import { api, apiClient } from '@/services/api'
import { sprintApi, type Sprint, type SprintPlan, type SprintTicket, type Page } from '@/services/sprints'
import { useAuthStore } from '@/stores/auth'
import { useDialogStore } from '@/stores/dialog'
import type { Ticket } from '@/types'

const auth = useAuthStore()
const dialog = useDialogStore()
const manager = computed(() => ['ADMIN', 'TEAM_LEADER'].includes(auth.userRole || ''))
const applications = ref<{ id: string; name: string }[]>([])
const applicationId = ref('')
const sprints = ref<Sprint[]>([])
const sprintTotal = ref(0)
const sprintSkip = ref(0)
const selected = ref<Sprint | null>(null)
const selectedTicket = ref<Ticket | null>(null)
const emptyPage = (): Page<SprintTicket> => ({ items: [], total: 0, skip: 0, limit: 25 })
const assigned = ref(emptyPage())
const available = ref(emptyPage())
const backlogQuery = ref('')
let appliedQuery = ''
const initializing = ref(false)
const loading = ref(false)
const tasksLoading = ref(false)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const showPlan = ref(false)
const editingId = ref<string | null>(null)
const blankPlan = (): SprintPlan => ({ name: '', goal: '', start_date: '', end_date: '' })
const plan = reactive(blankPlan())
let listGeneration = 0
let detailGeneration = 0
let taskGeneration = 0
let ticketGeneration = 0
let alive = true
const statuses = { PLANNED: 'Planificado', ACTIVE: 'Activo', FINISHED: 'Finalizado' }
const ticketStates: Record<string, string> = { TODO: 'Por hacer', IN_PROGRESS: 'En progreso', BLOCKED: 'Bloqueado', BLOCKED_QUESTION: 'Pregunta pendiente', REDIRECTED: 'Redirigido', COMPLETED: 'Completado' }
const otherActive = computed(() => sprints.value.some(sprint => sprint.status === 'ACTIVE' && sprint.id !== selected.value?.id))
function message(cause: unknown): string {
  const detail = (cause as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'No se pudo completar la operación. Comprueba la conexión e inténtalo otra vez.'
}
async function init() {
  initializing.value = true
  error.value = ''
  try {
    const all: { id: string; name: string }[] = []
    for (let skip = 0; ; skip += 500) {
      const { data } = await apiClient.get<{ id: string; name: string }[]>('/applications/', { params: { skip, limit: 500 } })
      all.push(...data)
      if (!alive || data.length < 500) break
    }
    if (!alive) return
    applications.value = all
    if (!applicationId.value) applicationId.value = all[0]?.id || ''
  } catch (cause) { if (alive) error.value = message(cause) }
  finally { if (alive) initializing.value = false }
}
watch(applicationId, () => {
  detailGeneration++; taskGeneration++; ticketGeneration++
  selected.value = null
  selectedTicket.value = null
  sprints.value = []
  assigned.value = emptyPage()
  available.value = emptyPage()
  showPlan.value = false
  error.value = ''; notice.value = ''; backlogQuery.value = ''; appliedQuery = ''
  void loadList(0)
})
async function loadList(offset = 0, preferred?: string) {
  const current = ++listGeneration
  const app = applicationId.value
  if (!app) { loading.value = false; return }
  loading.value = true
  try {
    const page = await sprintApi.list(app, offset)
    if (!alive || current !== listGeneration) return
    sprints.value = page.items; sprintTotal.value = page.total; sprintSkip.value = page.skip
    const id = preferred || page.items[0]?.id
    if (id) await selectSprint(id)
    else { selected.value = null; assigned.value = emptyPage(); available.value = emptyPage() }
  } catch (cause) { if (current === listGeneration && alive) error.value = message(cause) }
  finally { if (current === listGeneration && alive) loading.value = false }
}
async function selectSprint(id: string) {
  const current = ++detailGeneration
  taskGeneration++
  selected.value = null
  assigned.value = emptyPage(); available.value = emptyPage()
  backlogQuery.value = ''; appliedQuery = ''; showPlan.value = false
  try {
    const sprint = await sprintApi.get(id)
    if (!alive || current !== detailGeneration) return
    selected.value = sprint
    await loadTasks()
  } catch (cause) { if (current === detailGeneration && alive) error.value = message(cause) }
}
async function loadTasks(memberSkip = 0, backlogSkip = 0) {
  const current = ++taskGeneration
  const sprint = selected.value
  if (!sprint) return
  tasksLoading.value = true
  try {
    const [members, backlog] = await Promise.all([
      sprintApi.tickets(sprint.id, false, memberSkip),
      manager.value && sprint.status !== 'FINISHED' ? sprintApi.tickets(sprint.id, true, backlogSkip, appliedQuery) : Promise.resolve(emptyPage()),
    ])
    if (!alive || current !== taskGeneration) return
    assigned.value = members; available.value = backlog
  } catch (cause) { if (current === taskGeneration && alive) error.value = message(cause) }
  finally { if (current === taskGeneration && alive) tasksLoading.value = false }
}
function applyBacklogSearch() { appliedQuery = backlogQuery.value; void loadTasks(assigned.value.skip, 0) }
function openPlan(sprint?: Sprint) {
  editingId.value = sprint?.id || null
  Object.assign(plan, sprint ? { name: sprint.name, goal: sprint.goal, start_date: sprint.start_date, end_date: sprint.end_date } : blankPlan())
  showPlan.value = true
}
async function savePlan() {
  if (busy.value) return
  if (!plan.name.trim() || !plan.goal.trim() || !plan.start_date || !plan.end_date || plan.start_date > plan.end_date) {
    error.value = 'Completa nombre, objetivo y un período válido.'; return
  }
  busy.value = true; error.value = ''; notice.value = ''
  try {
    const sprint = editingId.value ? await sprintApi.edit(editingId.value, { ...plan }) : await sprintApi.create(applicationId.value, { ...plan })
    if (!alive) return
    showPlan.value = false
    await loadList(0, sprint.id)
    notice.value = 'Plan del sprint guardado.'
  } catch (cause) { if (alive) error.value = message(cause) }
  finally { if (alive) busy.value = false }
}
async function changeStatus(action: 'start' | 'finish') {
  if (!selected.value || busy.value) return
  const id = selected.value.id
  if (action === 'finish' && !await dialog.confirm('Los tickets pendientes quedarán sin sprint, conservando su responsable y estado. El resumen de cierre quedará guardado. ¿Finalizar el sprint?', 'Finalizar sprint')) return
  if (busy.value || selected.value?.id !== id) return
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await sprintApi[action](id)
    if (!alive) return
    await loadList(sprintSkip.value, id)
    notice.value = action === 'start' ? 'Sprint iniciado.' : 'Sprint finalizado. Los pendientes volvieron al backlog.'
  } catch (cause) { if (alive) error.value = message(cause) }
  finally { if (alive) busy.value = false }
}
async function moveTicket(id: string, add: boolean) {
  if (!selected.value || busy.value) return
  const sprint = selected.value.id
  busy.value = true; error.value = ''; notice.value = ''
  try {
    if (add) await sprintApi.add(sprint, id)
    else await sprintApi.remove(sprint, id)
    if (!alive) return
    await loadList(sprintSkip.value, sprint)
    notice.value = add ? 'Ticket agregado al sprint.' : 'Ticket retirado del sprint; conserva su responsable y estado.'
  } catch (cause) { if (alive) error.value = message(cause) }
  finally { if (alive) busy.value = false }
}
async function openTicket(id: string) {
  const current = ++ticketGeneration
  try {
    const ticket = await api.tickets.getById(id)
    if (alive && current === ticketGeneration) selectedTicket.value = ticket
  } catch (cause) { if (alive && current === ticketGeneration) error.value = message(cause) }
}
function closeTicket() { ticketGeneration++; selectedTicket.value = null; if (selected.value) void loadList(sprintSkip.value, selected.value.id) }
async function ticketUpdated(id: string) { await openTicket(id); if (selected.value) await loadList(sprintSkip.value, selected.value.id) }
async function retry() { error.value = ''; if (!applications.value.length) await init(); else await loadList(sprintSkip.value, selected.value?.id) }
onMounted(init)
onBeforeUnmount(() => { alive = false; listGeneration++; detailGeneration++; taskGeneration++; ticketGeneration++ })
</script>

<style scoped>
input, select, textarea { display: block; width: 100%; margin-top: .35rem; padding: .6rem; border: 1px solid var(--border-subtle); border-radius: .5rem; background: var(--bg-app); color: var(--text-primary); }
button:disabled { opacity: .45; cursor: not-allowed; }
.primary { border-radius: .5rem; padding: .55rem 1rem; background: var(--teal); color: white; }
.secondary { border: 1px solid var(--border-subtle); border-radius: .5rem; padding: .5rem .8rem; }
.panel { border: 1px solid var(--border-subtle); border-radius: .75rem; padding: 1.25rem; background: var(--bg-panel); display: grid; gap: 1rem; }
</style>
