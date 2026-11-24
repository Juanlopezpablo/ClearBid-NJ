<template>
  <div class="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)]">
    <AppHeader />
    <main class="max-w-7xl mx-auto p-4 md:p-8 space-y-6">
      <header class="flex flex-wrap justify-between items-start gap-4">
        <div><p class="text-sm text-[var(--teal)]">{{ roleNames[auth.userRole || ''] || 'Inicio' }}</p><h1 class="text-3xl font-bold">{{ heading }}</h1><p class="mt-2">Hola, {{ auth.user?.fullName || 'bienvenido' }}. {{ description }}</p></div>
        <button @click="load(0)" :disabled="loading" class="border rounded-lg px-4 py-2 disabled:opacity-50">Actualizar resumen</button>
      </header>
      <nav aria-label="Accesos rápidos" class="flex flex-wrap gap-3 text-[var(--teal)]">
        <RouterLink :to="auth.userRole === 'ADMIN' ? '/admin/builder' : '/dev/workbench'" class="underline">{{ auth.userRole === 'ADMIN' ? 'Constructor de proyectos' : 'Mi banco de trabajo' }}</RouterLink>
        <RouterLink v-if="manager" to="/admin/builder" class="underline">Gestionar proyectos</RouterLink>
        <RouterLink to="/sprints" class="underline">Planificación de sprints</RouterLink>
        <RouterLink v-if="manager" to="/admin/incidents" class="underline">Gestionar incidencias</RouterLink>
        <RouterLink to="/tickets/search" class="underline">Búsqueda avanzada</RouterLink>
      </nav>
      <label v-if="manager" class="block max-w-md">Equipo
        <select v-model="teamId" @change="changeTeam" :disabled="loading" class="block w-full mt-2 border rounded-lg p-3 bg-[var(--bg-panel)]"><option value="">Vista general</option><option v-for="team in data?.teams || []" :key="team.id" :value="team.id">{{ team.name }}</option></select>
      </label>
      <p v-if="loading" role="status">Cargando tu resumen…</p>
      <p v-else-if="error" role="alert" class="text-red-600">{{ error }} <button @click="load(0)" class="underline">Reintentar</button></p>
      <template v-else-if="data">
        <p class="text-sm text-[var(--text-secondary)]">{{ data.scope === 'team' ? `Equipo: ${data.team_name}. Solo tickets de sus épicas.` : data.scope === 'personal' ? 'Solo información asignada a tu cuenta.' : 'Resumen general de gestión. Puedes seleccionar un equipo.' }}</p>
        <section aria-label="Indicadores de tickets" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <button v-for="card in cards" :key="card.key" @click="chooseFocus(card.key)" :aria-pressed="focus === card.key" :class="['text-left border rounded-xl p-5 bg-[var(--bg-panel)] hover:border-[var(--teal)]', focus === card.key ? 'border-[var(--teal)] ring-1 ring-[var(--teal)]' : 'border-[var(--border-subtle)]']">
            <span class="block text-sm">{{ card.label }}</span><strong class="block text-3xl mt-2">{{ data.metrics[card.key] }}</strong><span class="block text-xs mt-2">{{ card.hint }}</span>
          </button>
        </section>
        <section class="border rounded-xl p-5 bg-[var(--bg-panel)] space-y-3">
          <h2 class="font-bold text-xl">{{ cards.find(card => card.key === focus)?.label }} <span class="text-base font-normal">({{ data.tickets.total }})</span></h2>
          <p v-if="!data.tickets.items.length">No hay tickets en esta categoría.</p>
          <ul v-else class="divide-y divide-[var(--border-subtle)]">
            <li v-for="ticket in data.tickets.items" :key="ticket.id" class="py-3">
              <RouterLink :to="{ path: auth.userRole === 'ADMIN' ? '/admin/builder' : '/dev/workbench', query: { ticketId: ticket.id } }" class="font-semibold text-[var(--teal)] hover:underline">{{ ticket.title }}</RouterLink>
              <p class="text-sm mt-1">{{ states[ticket.status] || ticket.status }} · {{ priorities[ticket.priority] || ticket.priority }} · {{ ticket.ticket_type === 'SUPPORT' ? 'Soporte' : 'Desarrollo' }}<span v-if="ticket.due_date"> · Vence: {{ dateTime(ticket.due_date) }}</span></p>
            </li>
          </ul>
          <nav v-if="data.tickets.total > 10" aria-label="Paginación de tickets" class="flex items-center gap-5"><button :disabled="data.tickets.skip === 0" @click="load(data.tickets.skip - 10)" class="disabled:opacity-40">Anterior</button><span>Página {{ Math.floor(data.tickets.skip / 10) + 1 }}</span><button :disabled="data.tickets.skip + 10 >= data.tickets.total" @click="load(data.tickets.skip + 10)" class="disabled:opacity-40">Siguiente</button></nav>
        </section>
        <div class="grid gap-5 lg:grid-cols-2">
          <section class="border rounded-xl p-5 bg-[var(--bg-panel)] space-y-3"><h2 class="font-bold text-xl">Sprints activos ({{ data.active_sprints.total }})</h2>
            <p class="text-sm">{{ data.scope === 'personal' ? 'Avance de tus tickets dentro de cada sprint.' : data.scope === 'team' ? 'Avance de los tickets del equipo dentro de cada sprint.' : 'Avance de los tickets de cada sprint.' }}</p>
            <p v-if="!data.active_sprints.items.length">No hay sprints activos en este resumen.</p>
            <article v-for="sprint in data.active_sprints.items" :key="sprint.id" class="border-t py-3"><strong>{{ sprint.name }}</strong><p class="text-sm">{{ sprint.completed_tickets }} de {{ sprint.total_tickets }} tickets completados · {{ sprint.progress }}%</p><progress :value="sprint.progress" max="100" class="w-full" :aria-label="`Avance de ${sprint.name}`" /><RouterLink to="/sprints" class="text-sm underline text-[var(--teal)]">Ver planificación de sprints</RouterLink></article>
            <p v-if="data.active_sprints.total > 5" class="text-sm">Se muestran los primeros cinco sprints, ordenados por fecha de término.</p>
          </section>
          <section class="border rounded-xl p-5 bg-[var(--bg-panel)] space-y-3"><h2 class="font-bold text-xl">{{ data.scope === 'personal' ? 'Mis incidencias abiertas' : 'Incidencias abiertas' }}<span v-if="data.incidents.available"> ({{ data.incidents.total }})</span></h2>
            <p v-if="!data.incidents.available">Las incidencias no están asociadas directamente a equipos. Consulta la vista general para verlas.</p>
            <template v-else><p v-if="!data.incidents.items.length">No hay incidencias abiertas en este resumen.</p><details v-for="incident in data.incidents.items" :key="incident.id" class="border-t py-3"><summary class="cursor-pointer">{{ incident.severity }} · {{ incident.title }}</summary><p class="text-sm mt-2 whitespace-pre-wrap">{{ incident.description || 'Sin descripción' }}</p><p class="text-xs mt-1">{{ incidentStates[incident.status] || incident.status }}</p></details><p v-if="(data.incidents.total || 0) > 5" class="text-sm">Se muestran las cinco incidencias prioritarias.</p></template>
          </section>
        </div>
        <p class="text-xs text-[var(--text-secondary)]">Actualizado: {{ dateTime(data.generated_at) }}. Los vencimientos se muestran en tu hora local. Pendientes incluye los tickets en curso y bloqueados; próximos a vencer comprende los siguientes siete días.</p>
      </template>
    </main>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { apiClient } from '@/services/api'
type Focus = 'pending' | 'in_progress' | 'blocked' | 'overdue' | 'upcoming'
interface Dashboard {
  role: string; scope: string; team_id: string | null; team_name: string | null; generated_at: string
  teams: { id: string; name: string }[]; metrics: Record<Focus, number>
  tickets: { total: number; skip: number; items: { id: string; title: string; status: string; priority: string; due_date: string | null; ticket_type: string }[] }
  active_sprints: { total: number; items: { id: string; name: string; application_id: string; completed_tickets: number; total_tickets: number; progress: number }[] }
  incidents: { available: boolean; total: number | null; items: { id: string; title: string; severity: string; status: string; description: string }[] }
}
const auth = useAuthStore(), data = ref<Dashboard | null>(null), loading = ref(false), error = ref(''), teamId = ref(''), focus = ref<Focus>('pending')
const manager = computed(() => auth.userRole === 'ADMIN' || auth.userRole === 'TEAM_LEADER')
const heading = computed(() => auth.userRole === 'ADMIN' ? 'Inicio de administración' : auth.userRole === 'TEAM_LEADER' ? 'Inicio de gestión' : 'Mi inicio')
const description = computed(() => manager.value ? 'Revisa el trabajo pendiente y los puntos que requieren atención.' : 'Revisa tus tareas y organiza tu próximo paso.')
const roleNames: Record<string, string> = { ADMIN: 'Administrador', TEAM_LEADER: 'Líder de equipo', DEVELOPER: 'Desarrollador' }
const cards: { key: Focus; label: string; hint: string }[] = [{ key: 'pending', label: 'Pendientes', hint: 'Tickets sin terminar' }, { key: 'in_progress', label: 'En curso', hint: 'Desarrollo o investigación' }, { key: 'blocked', label: 'Bloqueados', hint: 'Bloqueo o pregunta pendiente' }, { key: 'overdue', label: 'Vencidos', hint: 'Fecha límite ya superada' }, { key: 'upcoming', label: 'Próximos a vencer', hint: 'En los siguientes siete días' }]
const states: Record<string, string> = { TODO: 'Por hacer', IN_PROGRESS: 'En progreso', BLOCKED: 'Bloqueado', BLOCKED_QUESTION: 'Pregunta pendiente', REDIRECTED: 'Redirigido', COMPLETED: 'Completado', REPORTED: 'Reportado', INVESTIGATING: 'En investigación', RESOLVED: 'Resuelto' }
const priorities: Record<string, string> = { LOW: 'Baja', MEDIUM: 'Media', HIGH: 'Alta', URGENT: 'Urgente' }
const incidentStates: Record<string, string> = { REPORTED: 'Reportada', INVESTIGATING: 'En investigación', MITIGATED: 'Mitigada', RESOLVED: 'Resuelta' }
let generation = 0
function dateTime(value: string) { return new Date(value).toLocaleString() }
async function load(skip: number) {
  const current = ++generation
  loading.value = true; error.value = ''
  try {
    const response = await apiClient.get<Dashboard>('/dashboard', { params: { focus: focus.value, skip, limit: 10, ...(manager.value && teamId.value ? { team_id: teamId.value } : {}) } })
    if (current === generation) data.value = response.data
  } catch { if (current === generation) error.value = 'No se pudo cargar el inicio. Revisa tu conexión e inténtalo nuevamente.' }
  finally { if (current === generation) loading.value = false }
}
function chooseFocus(value: Focus) { focus.value = value; void load(0) }
function changeTeam() { focus.value = 'pending'; void load(0) }
onMounted(() => { void load(0) })
onBeforeUnmount(() => { generation++ })
</script>
